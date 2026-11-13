"""
Security Module for FiscWise

Handles password hashing, verification, and JWT token generation.
Uses bcrypt directly for password hashing (bcrypt 4.x+ compatible)
and python-jose for JWT tokens.

Note: passlib 1.7.x is incompatible with bcrypt >= 4.0 because it reads
bcrypt.__about__.__version__ which was removed in bcrypt 4.0.  We call the
bcrypt library directly instead of going through passlib to avoid this.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt

# JWT Configuration - Import from config for consistency
from app.core.config import settings

JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt-hashed password.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hashed password from database

    Returns:
        bool: True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Bcrypt has a maximum input length of 72 bytes; passwords longer than
    that are silently truncated by the underlying C library.  We reject
    them explicitly so callers get a clear error instead of silent data loss.

    Args:
        password: The plain text password to hash

    Returns:
        str: The bcrypt hashed password (60-char string starting with $2b$)

    Raises:
        ValueError: If the password exceeds 72 bytes.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password must be at most 72 bytes.")

    hashed = bcrypt.hashpw(encoded, bcrypt.gensalt())
    return hashed.decode("utf-8")


def create_access_token(user_id: str, tenant_id: str, role: str) -> str:
    """
    Create a JWT access token for authentication.
    
    Args:
        user_id: The user's UUID as string
        tenant_id: The tenant's UUID as string
        role: The user's role (owner/admin/member)
        
    Returns:
        str: The encoded JWT token
    """
    # Calculate expiration time
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Create JWT payload
    payload = {
        "sub": user_id,  # Subject (user ID)
        "tenant_id": tenant_id,  # Tenant ID for multi-tenancy
        "role": role,  # User role for RBAC
        "exp": expire,  # Expiration time
        "iat": issued_at,  # Issued at time
    }
    
    # Encode and return JWT token
    encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_mfa_token(user_id: str) -> str:
    """
    Create a short-lived MFA challenge token (5 minutes).

    This token is returned when the user's first login step succeeds but 2FA
    is enabled. The frontend uses it to call /auth/login/verify-2fa.

    Args:
        user_id: The user's UUID as string

    Returns:
        str: Short-lived JWT with type='mfa'
    """
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(minutes=5)
    payload = {
        "sub": user_id,
        "type": "mfa",  # Distinguishes from full access tokens
        "exp": expire,
        "iat": issued_at,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_mfa_token(token: str) -> str | None:
    """
    Verify a MFA challenge token and return the user_id if valid.

    Args:
        token: The MFA token string

    Returns:
        str | None: user_id if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "mfa":
            return None
        return payload.get("sub")
    except Exception:
        return None


GOOGLE_SIGNUP_TOKEN_MINUTES = 30


def create_google_signup_token(email: str, full_name: str | None) -> str:
    """Token curto (30 min) que prova "este e-mail Google foi verificado".

    Primeiro login Google de um e-mail sem conta NÃO cria escritório nem dá
    acesso: devolve este token, e o cadastro (escritório, termos, plano) é
    concluído em /onboarding/register-google. Não vale como access token
    (type='google_signup' é recusado em get_current_user).
    """
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "name": full_name or "",
        "type": "google_signup",
        "exp": issued_at + timedelta(minutes=GOOGLE_SIGNUP_TOKEN_MINUTES),
        "iat": issued_at,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_google_signup_token(token: str) -> tuple[str, str] | None:
    """Devolve (email, nome) se o token de cadastro Google for válido."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None
    if payload.get("type") != "google_signup" or not payload.get("sub"):
        return None
    return str(payload["sub"]).lower().strip(), str(payload.get("name") or "")


DEVICE_TOKEN_EXPIRE_DAYS = 30
# Teto da cadeia de renovações: 180 dias depois do login que registrou o
# dispositivo, a renovação é recusada e o usuário precisa entrar de novo online
# (docs/audit/SECURITY-REVIEW-2026-11-12-offline-sync.md, achado BAIXO 1).
DEVICE_TOKEN_MAX_LIFETIME_DAYS = 180


def create_device_token(
    user_id: str,
    tenant_id: str,
    role: str,
    device_id: str,
    first_issued_at: Optional[datetime] = None,
) -> str:
    """Token do dispositivo offline (30 dias, type='device').

    Só os endpoints /api/v1/sync/* aceitam este token, e só ele os acessa
    (docs/arquitetura/OFFLINE_SYNC.md 5.1). get_current_user recusa type != None.

    ``first_issued_at`` é o instante do login que começou a cadeia (claim
    ``fia``); a renovação o repassa e o ``exp`` nunca passa de
    ``fia + DEVICE_TOKEN_MAX_LIFETIME_DAYS``.
    """
    issued_at = datetime.now(timezone.utc)
    fia = first_issued_at or issued_at
    if fia.tzinfo is None:
        fia = fia.replace(tzinfo=timezone.utc)
    expires_at = min(
        issued_at + timedelta(days=DEVICE_TOKEN_EXPIRE_DAYS),
        fia + timedelta(days=DEVICE_TOKEN_MAX_LIFETIME_DAYS),
    )
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "device_id": device_id,
        "type": "device",
        "exp": expires_at,
        "iat": issued_at,
        "fia": int(fia.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def device_chain_started_at(payload: dict, fallback: Optional[datetime] = None) -> Optional[datetime]:
    """Início da cadeia de renovações do token de dispositivo (claim ``fia``).

    Tokens emitidos antes do teto não têm ``fia``: usa ``fallback`` (o
    ``created_at`` do dispositivo).
    """
    fia = payload.get("fia")
    if isinstance(fia, (int, float)):
        return datetime.fromtimestamp(fia, tz=timezone.utc)
    if fallback is not None and fallback.tzinfo is None:
        return fallback.replace(tzinfo=timezone.utc)
    return fallback


# ─── Redefinição de senha ("esqueci minha senha") ────────────────────────────

PASSWORD_RESET_PURPOSE = "password_reset"
PASSWORD_RESET_EXPIRE_MINUTES = 60


def _password_fingerprint(hashed_password: str) -> str:
    """Impressão do hash atual da senha (HMAC com a chave do JWT).

    Vai dentro do token de reset: quando a senha muda, a impressão deixa de
    bater e o link já usado (ou qualquer link anterior) morre — uso único sem
    tabela, mesmo dentro do mesmo segundo do ``tokens_valid_after``.
    """
    return hmac.new(
        JWT_SECRET_KEY.encode("utf-8"), hashed_password.encode("utf-8"), hashlib.sha256
    ).hexdigest()[:32]


def create_password_reset_token(user_id: str, hashed_password: str) -> str:
    """JWT de 1 h, propósito único (nunca serve como access token)."""
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "purpose": PASSWORD_RESET_PURPOSE,
        "jti": secrets.token_urlsafe(16),
        "pwh": _password_fingerprint(hashed_password),
        "exp": issued_at + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES),
        "iat": issued_at,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_password_reset_token(token: str) -> dict | None:
    """Valida assinatura, expiração e propósito. Devolve o payload ou None.

    A checagem contra o usuário (impressão da senha, ``tokens_valid_after``)
    fica em ``password_reset_token_matches_user``.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None
    if payload.get("purpose") != PASSWORD_RESET_PURPOSE or not payload.get("sub"):
        return None
    if not isinstance(payload.get("iat"), int) or not payload.get("pwh"):
        return None
    return payload


def password_reset_token_matches_user(payload: dict, user) -> bool:
    """Token ainda vale para este usuário? (senha não mudou desde a emissão)."""
    if not hmac.compare_digest(
        str(payload.get("pwh", "")), _password_fingerprint(user.hashed_password)
    ):
        return False
    valid_after = getattr(user, "tokens_valid_after", None)
    if valid_after is not None:
        if valid_after.tzinfo is None:  # SQLite devolve sem fuso
            valid_after = valid_after.replace(tzinfo=timezone.utc)
        if payload["iat"] < int(valid_after.timestamp()):
            return False
    return True
