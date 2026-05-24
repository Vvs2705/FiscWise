"""
Authentication Endpoints for FiscWise

Handles user authentication, login, token generation, and
Two-Factor Authentication (2FA) setup and verification.

2FA Flow:
  1. POST /auth/login  →  if 2FA enabled: returns {status: "requires_2fa", mfa_token: "..."}
  2. POST /auth/login/verify-2fa  →  validates OTP code + mfa_token, returns full AuthResponse
  3. GET  /auth/2fa/setup   →  generates TOTP secret + QR code URI (authenticated)
  4. POST /auth/2fa/enable  →  confirms first OTP code, activates 2FA (authenticated)
  5. POST /auth/2fa/disable →  deactivates 2FA after password confirmation (authenticated)
"""

import io
import os
import base64
import logging
import secrets
import string
from datetime import datetime, timezone, timedelta

import pyotp
import qrcode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, Field
from typing import Optional, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.core.plan_access import resolve_plan
from app.core.security import (
    verify_password,
    create_access_token,
    create_mfa_token,
    verify_mfa_token,
    get_password_hash,
)
from app.core.auth_rate_limiter import auth_rate_limiter, get_client_ip
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.schemas.token import AuthResponse, UserInfo
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)

router = APIRouter()

# ─── OTP e-mail cache (in-process, por simplicidade) ─────────────────────────
# Em produção com múltiplas instâncias, use Redis.
_EMAIL_OTP_STORE: dict[str, tuple[str, datetime]] = {}
_EMAIL_OTP_TTL_MINUTES = 10


def _generate_email_otp(user_id: str) -> str:
    """Generate and cache a 6-digit OTP for email verification."""
    code = "".join(secrets.choice(string.digits) for _ in range(6))
    _EMAIL_OTP_STORE[user_id] = (code, datetime.now(timezone.utc))
    return code


def _verify_email_otp(user_id: str, code: str) -> bool:
    """Verify cached email OTP. Returns True if valid and not expired."""
    entry = _EMAIL_OTP_STORE.get(user_id)
    if not entry:
        return False
    stored_code, created_at = entry
    if datetime.now(timezone.utc) - created_at > timedelta(minutes=_EMAIL_OTP_TTL_MINUTES):
        _EMAIL_OTP_STORE.pop(user_id, None)
        return False
    if secrets.compare_digest(stored_code, code):
        _EMAIL_OTP_STORE.pop(user_id, None)
        return True
    return False


def _build_auth_response(user: User, tenant_id: str) -> AuthResponse:
    """Helper to build a full AuthResponse from a User object."""
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value,
    )
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        tenant_id=tenant_id,
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            full_name=getattr(user, "full_name", None),
            phone=getattr(user, "phone", None),
            role=user.role.value,
        ),
    )


# ─── Schemas ──────────────────────────────────────────────────────────────────

class MfaChallengeResponse(BaseModel):
    """Response when 2FA is required during login."""
    status: str = "requires_2fa"
    mfa_token: str
    two_factor_method: str  # 'totp' | 'email'
    message: str


class Verify2FARequest(BaseModel):
    mfa_token: str = Field(..., description="Short-lived token received from login step")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class Setup2FAResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_code_base64: str  # PNG base64 for inline display
    method: str  # 'totp'


class Enable2FARequest(BaseModel):
    otp_code: str = Field(..., min_length=6, max_length=6)
    method: str = Field(default="totp", description="'totp' or 'email'")


class Disable2FARequest(BaseModel):
    current_password: str = Field(..., description="Current password for confirmation")
    otp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token (JWT)


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    summary="User Login",
    response_model=Union[AuthResponse, MfaChallengeResponse],
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Union[AuthResponse, MfaChallengeResponse]:
    """
    OAuth2 compatible token login endpoint.

    Rate limited: max 10 tentativas por IP a cada 15 minutos.
    Se 2FA ativo, retorna MfaChallengeResponse em vez do JWT definitivo.
    """
    client_ip = get_client_ip(request)

    # ── Rate limit check (IP) ───────────────────────────────────────────
    auth_rate_limiter.check_login_ip(client_ip)
    result = await db.execute(select(User).where(User.email == form_data.username))
    users = result.scalars().all()

    if len(users) != 1:
        # Conta falha mesmo para emails inexistentes (evita user enumeration)
        auth_rate_limiter.record_login_failure(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = users[0]

    if not verify_password(form_data.password, user.hashed_password):
        auth_rate_limiter.record_login_failure(client_ip)
        await log_audit_event(
            db=db,
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            actor_role=user.role.value,
            action="auth.login_failed",
            entity_type="auth",
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent") if request else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta inativa. Entre em contato com o suporte.",
        )

    # ── 2FA gate ──────────────────────────────────────────────────────────────
    if getattr(user, "two_factor_enabled", False):
        method = getattr(user, "two_factor_method", "totp")

        # For email OTP, generate and send the code now
        if method == "email":
            otp_code = _generate_email_otp(str(user.id))
            # TODO: integrate with email provider (Resend / SMTP)
            # For now log it — replace with real send when email provider is configured
            logger.info("EMAIL OTP for %s: %s", user.email, otp_code)

        mfa_token = create_mfa_token(user_id=str(user.id))
        return MfaChallengeResponse(
            status="requires_2fa",
            mfa_token=mfa_token,
            two_factor_method=method,
            message=(
                "Código enviado para seu e-mail."
                if method == "email"
                else "Abra o app autenticador e insira o código de 6 dígitos."
            ),
        )

    # ── Normal login ───────────────────────────────────────────
    # Login bem-sucedido — reseta contador de falhas
    auth_rate_limiter.record_login_success(client_ip)
    await log_audit_event(
        db=db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        actor_role=user.role.value,
        action="auth.login_success",
        entity_type="auth",
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    return _build_auth_response(user, str(user.tenant_id))


# ─── Verify 2FA ───────────────────────────────────────────────────────────────

@router.post("/login/verify-2fa", response_model=AuthResponse, summary="Complete 2FA Login")
async def verify_2fa(
    body: Verify2FARequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Segundo passo do fluxo de login 2FA.

    Rate limited: max 5 tentativas por user_id a cada 15 minutos.
    Após 5 falhas o user_id é bloqueado por 15 minutos.
    """
    user_id = verify_mfa_token(body.mfa_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de desafio 2FA inválido ou expirado. Faça login novamente.",
        )

    # ── Rate limit check (user_id) ───────────────────────────────────
    auth_rate_limiter.check_otp_user(user_id)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")

    method = getattr(user, "two_factor_method", "totp")
    otp_code = body.otp_code.strip()

    if method == "totp":
        secret = getattr(user, "two_factor_secret", None)
        if not secret:
            raise HTTPException(status_code=400, detail="2FA TOTP não configurado corretamente")
        totp = pyotp.TOTP(secret)
        if not totp.verify(otp_code, valid_window=1):
            auth_rate_limiter.record_otp_failure(user_id)
            remaining = auth_rate_limiter.get_otp_remaining_attempts(user_id)
            detail = "Código inválido. Verifique o app autenticador e tente novamente."
            if remaining > 0:
                detail += f" ({remaining} tentativa(s) restante(s) antes do bloqueio)"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=detail,
            )

    elif method == "email":
        if not _verify_email_otp(user_id, otp_code):
            auth_rate_limiter.record_otp_failure(user_id)
            remaining = auth_rate_limiter.get_otp_remaining_attempts(user_id)
            detail = "Código inválido ou expirado. Solicite um novo código."
            if remaining > 0:
                detail += f" ({remaining} tentativa(s) restante(s) antes do bloqueio)"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=detail,
            )
    else:
        raise HTTPException(status_code=400, detail="Método 2FA desconhecido")

    # OTP válido — reseta contador
    auth_rate_limiter.record_otp_success(user_id)

    await log_audit_event(
        db=db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        actor_role=user.role.value,
        action="auth.login_2fa_success",
        entity_type="auth",
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    return _build_auth_response(user, str(user.tenant_id))


# ─── Google OAuth ─────────────────────────────────────────────────────────────

@router.post("/google", response_model=Union[AuthResponse, MfaChallengeResponse], summary="Google OAuth Login / Register")
async def google_auth(
    body: GoogleAuthRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Union[AuthResponse, MfaChallengeResponse]:
    """
    Authenticate or register a user via Google OAuth.

    If the existing user has 2FA enabled, returns a MfaChallengeResponse
    instead of the full token.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth não está configurado neste servidor",
        )

    try:
        id_info = google_id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except ValueError as exc:
        logger.warning("Invalid Google token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Google inválido ou expirado",
        )

    google_email: str = id_info.get("email", "").lower().strip()
    google_name: str = id_info.get("name", "")

    if not google_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível obter o e-mail da conta Google",
        )

    result = await db.execute(select(User).where(User.email == google_email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        if not existing_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta inativa.")

        # ── 2FA gate ──────────────────────────────────────────────────────────
        if getattr(existing_user, "two_factor_enabled", False):
            method = getattr(existing_user, "two_factor_method", "totp")
            if method == "email":
                otp_code = _generate_email_otp(str(existing_user.id))
                logger.info("EMAIL OTP for %s: %s", existing_user.email, otp_code)
            mfa_token = create_mfa_token(user_id=str(existing_user.id))
            return MfaChallengeResponse(
                status="requires_2fa",
                mfa_token=mfa_token,
                two_factor_method=method,
                message=(
                    "Código enviado para seu e-mail."
                    if method == "email"
                    else "Abra o app autenticador e insira o código de 6 dígitos."
                ),
            )

        await log_audit_event(
            db=db,
            tenant_id=existing_user.tenant_id,
            actor_user_id=existing_user.id,
            actor_role=existing_user.role.value,
            action="auth.login_google_success",
            entity_type="auth",
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("User-Agent") if request else None,
        )
        return _build_auth_response(existing_user, str(existing_user.tenant_id))

    # New user — create tenant + owner
    try:
        new_tenant = Tenant(
            name=google_name or google_email.split("@")[0],
            subscription_status=SubscriptionStatus.TRIAL,
        )
        db.add(new_tenant)
        await db.flush()

        random_password = get_password_hash(os.urandom(32).hex())
        new_user = User(
            tenant_id=new_tenant.id,
            email=google_email,
            hashed_password=random_password,
            full_name=google_name,
            role=UserRole.OWNER,
            is_active=True,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_tenant)
        await db.refresh(new_user)

        await log_audit_event(
            db=db,
            tenant_id=new_tenant.id,
            actor_user_id=new_user.id,
            actor_role=new_user.role.value,
            action="auth.register_google_success",
            entity_type="auth",
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("User-Agent") if request else None,
        )
        return _build_auth_response(new_user, str(new_tenant.id))

    except Exception as exc:
        await db.rollback()
        logger.error("Failed to create Google OAuth user: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar conta. Tente novamente.",
        )


# ─── 2FA Setup & Management (authenticated) ───────────────────────────────────

@router.get("/2fa/setup", response_model=Setup2FAResponse, summary="Generate 2FA TOTP Setup")
async def setup_2fa(
    current_user: User = Depends(get_current_user),
) -> Setup2FAResponse:
    """
    Generate a TOTP secret and QR code for Google/Microsoft Authenticator setup.

    The user must then call POST /auth/2fa/enable with the first OTP code to
    confirm and activate 2FA. The secret is NOT saved until enable is called.
    """
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    issuer = "FiscWise"
    otpauth_uri = totp.provisioning_uri(name=current_user.email, issuer_name=issuer)

    # Generate QR code as base64 PNG
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(otpauth_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Store secret temporarily in the response — frontend must pass it back to /enable
    return Setup2FAResponse(
        secret=secret,
        otpauth_uri=otpauth_uri,
        qr_code_base64=qr_base64,
        method="totp",
    )


@router.post("/2fa/enable", summary="Enable 2FA")
async def enable_2fa(
    body: Enable2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Activate 2FA after the user scanned the QR code and confirmed the first OTP.

    For TOTP: the frontend must pass the secret from the /setup response back
    via a temporary storage (e.g., React state), plus the first valid OTP.
    For Email: generates and sends an OTP to the user's email.
    """
    if body.method == "totp":
        # The secret must be sent from the client (from the /setup step)
        # We validate the code against it before persisting
        # Since we cannot pass secret through this endpoint directly per the schema,
        # we need it embedded — add it to the request body
        raise HTTPException(
            status_code=400,
            detail="Use /auth/2fa/enable-totp para ativar TOTP com o segredo gerado."
        )

    elif body.method == "email":
        # Generate and send email OTP
        code = _generate_email_otp(str(current_user.id))
        logger.info("2FA EMAIL SETUP OTP for %s: %s", current_user.email, code)
        return {"message": "Código enviado para seu e-mail. Confirme com /auth/2fa/confirm-email."}

    raise HTTPException(status_code=400, detail="Método inválido. Use 'totp' ou 'email'.")


class EnableTOTPRequest(BaseModel):
    secret: str = Field(..., description="TOTP secret from /2fa/setup")
    otp_code: str = Field(..., min_length=6, max_length=6)


@router.post("/2fa/enable-totp", summary="Enable TOTP 2FA")
async def enable_totp_2fa(
    body: EnableTOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm and activate TOTP-based 2FA.

    Validates the first OTP code against the provided secret.
    Saves the secret and activates 2FA on success.
    """
    totp = pyotp.TOTP(body.secret)
    if not totp.verify(body.otp_code.strip(), valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido. Verifique o app autenticador e tente novamente.",
        )

    current_user.two_factor_enabled = True
    current_user.two_factor_secret = body.secret
    current_user.two_factor_method = "totp"
    await db.commit()
    await db.refresh(current_user)

    await log_audit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="auth.2fa_enabled_totp",
        entity_type="auth",
    )
    return {"message": "Autenticação de dois fatores (TOTP) ativada com sucesso!"}


class ConfirmEmailOTPRequest(BaseModel):
    otp_code: str = Field(..., min_length=6, max_length=6)


@router.post("/2fa/confirm-email", summary="Enable Email OTP 2FA")
async def confirm_email_2fa(
    body: ConfirmEmailOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm email OTP and activate email-based 2FA.
    """
    if not _verify_email_otp(str(current_user.id), body.otp_code.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado. Solicite um novo código.",
        )

    current_user.two_factor_enabled = True
    current_user.two_factor_secret = None  # No secret needed for email method
    current_user.two_factor_method = "email"
    await db.commit()
    await db.refresh(current_user)

    await log_audit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="auth.2fa_enabled_email",
        entity_type="auth",
    )
    return {"message": "Autenticação de dois fatores por e-mail ativada com sucesso!"}


@router.post("/2fa/disable", summary="Disable 2FA")
async def disable_2fa(
    body: Disable2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate 2FA. Requires current password for security.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta",
        )

    # If user also wants to validate OTP before disable (optional extra security)
    if body.otp_code and getattr(current_user, "two_factor_method", "totp") == "totp":
        secret = getattr(current_user, "two_factor_secret", None)
        if secret:
            totp = pyotp.TOTP(secret)
            if not totp.verify(body.otp_code.strip(), valid_window=1):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Código 2FA incorreto",
                )

    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    current_user.two_factor_method = "none"
    await db.commit()

    await log_audit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="auth.2fa_disabled",
        entity_type="auth",
    )
    return {"message": "Autenticação de dois fatores desativada."}


@router.get("/2fa/status", summary="Get 2FA Status")
async def get_2fa_status(current_user: User = Depends(get_current_user)):
    """Return current 2FA status for the authenticated user."""
    return {
        "two_factor_enabled": getattr(current_user, "two_factor_enabled", False),
        "two_factor_method": getattr(current_user, "two_factor_method", "none"),
    }


# ─── Other auth endpoints ─────────────────────────────────────────────────────

@router.post("/logout", summary="User Logout")
async def logout():
    """Logout endpoint (stateless JWT — client removes token)."""
    return {"message": "Successfully logged out", "detail": "Remove the access token from client storage"}


@router.get("/me", summary="Get Current User Info")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": getattr(current_user, "phone", None),
        "role": current_user.role.value,
        "tenant_id": str(current_user.tenant_id),
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
        "two_factor_enabled": getattr(current_user, "two_factor_enabled", False),
        "two_factor_method": getattr(current_user, "two_factor_method", "none"),
    }


@router.get("/tenant", summary="Get Current Tenant Info")
async def get_tenant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "document": tenant.document,
        "plan_slug": resolve_plan(getattr(tenant, "plan_slug", None), current_user.email),
        "phone": getattr(tenant, "phone", None),
        "address": getattr(tenant, "address", None),
        "website": getattr(tenant, "website", None),
        "subscription_status": tenant.subscription_status.value,
        "created_at": tenant.created_at.isoformat(),
    }


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)


@router.patch("/me", summary="Update User Profile")
async def update_me(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.phone is not None:
        current_user.phone = body.phone
    await db.commit()
    await db.refresh(current_user)
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": getattr(current_user, "phone", None),
        "role": current_user.role.value,
    }


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    document: Optional[str] = Field(None, max_length=32)
    plan_slug: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=255)


@router.patch("/tenant", summary="Update Tenant")
async def update_tenant(
    body: UpdateTenantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if body.name is not None:
        tenant.name = body.name
    if body.document is not None:
        tenant.document = body.document
    if body.plan_slug is not None:
        tenant.plan_slug = body.plan_slug
    if body.phone is not None:
        tenant.phone = body.phone
    if body.address is not None:
        tenant.address = body.address
    if body.website is not None:
        tenant.website = body.website
    await db.commit()
    await db.refresh(tenant)
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "document": tenant.document,
        "plan_slug": resolve_plan(getattr(tenant, "plan_slug", None), current_user.email),
        "phone": getattr(tenant, "phone", None),
        "address": getattr(tenant, "address", None),
        "website": getattr(tenant, "website", None),
        "subscription_status": tenant.subscription_status.value,
    }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


@router.post("/change-password", summary="Change Password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    current_user.hashed_password = get_password_hash(body.new_password)
    await db.commit()
    return {"message": "Senha alterada com sucesso"}
