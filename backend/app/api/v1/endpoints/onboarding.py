"""
Onboarding Endpoints for FiscWise

Handles public tenant registration and onboarding flow.
Creates tenant and owner user in a single atomic transaction.
"""

import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_rate_limiter import auth_rate_limiter, get_client_ip
from app.core.deps import get_current_user, get_db, signup_complete
from app.core.plan_access import TRIAL_DAYS
from app.core.security import create_access_token, get_password_hash, verify_google_signup_token
from app.core.validators import validate_cpf_or_cnpj
from app.models.billing import TenantSubscription
from app.models.plan import Plan
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.schemas.onboarding import (
    CompleteSignupRequest,
    GoogleTenantRegistrationRequest,
    TenantRegistrationRequest,
)
from app.services.audit import log_audit_event
from app.schemas.token import AuthResponse, UserInfo


router = APIRouter()
logger = logging.getLogger(__name__)

# Teste grátis: todo escritório novo começa com 14 dias do Premium (ou do
# plano pago escolhido), sem cartão. Sem pagamento, a conta fica só leitura
# (plan_access.acesso_expirado). O plano Gratuito permanente deixou de existir
# em 13/11/2026.
TRIAL_PLAN_SLUG = "premium"

# v1.2 (13/11/2026): Termos passam a descrever o teste grátis no lugar do
# plano Gratuito.
# v1.3 (13/11/2026): cláusula das ofertas promocionais depois do teste.
TERMS_VERSION = "v1.3"


DOCUMENTO_INVALIDO_CODE = "INVALID_DOCUMENT"
DOCUMENTO_EM_USO_CODE = "DOCUMENT_ALREADY_USED"
DOCUMENTO_EM_USO_DETAIL = (
    "Este CNPJ/CPF já tem uma conta no FiscWise. "
    "Entre com o e-mail dessa conta ou fale com o suporte."
)


def _normalizar_documento(document: Optional[str]) -> str:
    """CNPJ/CPF obrigatório e válido → só dígitos (um teste grátis por documento)."""
    digitos = re.sub(r"\D", "", document or "")
    if not validate_cpf_or_cnpj(digitos):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CNPJ ou CPF inválido. Confira os números e tente de novo.",
            headers={"X-Error-Code": DOCUMENTO_INVALIDO_CODE},
        )
    return digitos


def _documento_sem_mascara():
    """tenants.document sem pontuação, em SQL portátil (SQLite e Postgres):
    contas antigas podem ter o documento gravado com máscara."""
    return func.replace(
        func.replace(func.replace(func.replace(Tenant.document, ".", ""), "/", ""), "-", ""),
        " ", "",
    )


async def _garantir_documento_livre(
    db: AsyncSession, digitos: str, exceto_tenant_id: Optional[uuid.UUID] = None
) -> None:
    """Documento já usado por outro escritório → não ganha novo teste grátis."""
    consulta = select(Tenant.id).where(_documento_sem_mascara() == digitos)
    if exceto_tenant_id is not None:
        consulta = consulta.where(Tenant.id != exceto_tenant_id)
    if (await db.execute(consulta.limit(1))).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=DOCUMENTO_EM_USO_DETAIL,
            headers={"X-Error-Code": DOCUMENTO_EM_USO_CODE},
        )


async def _resolve_signup_plan(db: AsyncSession, plan_slug: Optional[str]) -> tuple[str, Optional[Plan]]:
    """Plano do teste grátis (validado contra os planos ativos).

    Sem plano (ou "free", de telas antigas) = teste do Premium. Todo cadastro
    ganha 14 dias de teste (TenantSubscription trialing). NUNCA concede plano
    pago sem essa janela — depois dela, só pagamento/admin mantém o plano.
    """
    chosen_slug = (plan_slug or TRIAL_PLAN_SLUG).strip().lower()
    if chosen_slug == "free":
        chosen_slug = TRIAL_PLAN_SLUG
    chosen_plan = (await db.execute(
        select(Plan).where(Plan.slug == chosen_slug, Plan.active.is_(True))
    )).scalar_one_or_none()
    if chosen_plan is None and chosen_slug == TRIAL_PLAN_SLUG and plan_slug in (None, "", "free"):
        # Banco sem o plano do teste (instalação incompleta): cria a conta sem
        # teste, com os limites mínimos — nunca ganha plano pago de graça.
        logger.error("Plano '%s' do teste grátis não encontrado; cadastro sem teste", TRIAL_PLAN_SLUG)
        return "free", None
    if chosen_plan is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plano '{chosen_slug}' inválido ou indisponível",
            headers={"X-Error-Code": "INVALID_PLAN"},
        )
    return chosen_slug, chosen_plan


def _add_trial_subscription(db: AsyncSession, tenant_id, plan: Plan, now_utc: datetime) -> None:
    db.add(TenantSubscription(
        tenant_id=tenant_id,
        plan_id=plan.id,
        status="trialing",
        trial_ends_at=now_utc + timedelta(days=TRIAL_DAYS),
        billing_provider="mercadopago",
        billing_cycle="mensal",
        amount=plan.price_monthly,
        currency="BRL",
    ))


async def _create_tenant_and_owner(
    db: AsyncSession,
    *,
    company_name: str,
    document: str,
    plan_slug: Optional[str],
    owner_email: str,
    hashed_password: str,
    owner_full_name: Optional[str],
    owner_phone: Optional[str],
) -> AuthResponse:
    """Cria escritório + dono numa transação só. Os termos já foram aceitos
    (o schema recusa terms_accepted=false). `document` já vem normalizado."""
    await _garantir_documento_livre(db, document)
    chosen_slug, chosen_plan = await _resolve_signup_plan(db, plan_slug)

    try:
        now_utc = datetime.now(timezone.utc)
        new_tenant = Tenant(
            name=company_name,
            document=document,
            subscription_status=SubscriptionStatus.TRIAL,
            plan_slug=chosen_slug,
            terms_accepted_at=now_utc,
            terms_version=TERMS_VERSION,
        )
        db.add(new_tenant)
        await db.flush()

        if chosen_plan is not None:
            _add_trial_subscription(db, new_tenant.id, chosen_plan, now_utc)

        new_owner = User(
            tenant_id=new_tenant.id,
            email=owner_email,
            hashed_password=hashed_password,
            full_name=owner_full_name,
            phone=owner_phone,
            role=UserRole.OWNER,
            is_active=True,
        )
        db.add(new_owner)
        await db.commit()
        await db.refresh(new_tenant)
        await db.refresh(new_owner)

        access_token = create_access_token(
            user_id=str(new_owner.id),
            tenant_id=str(new_tenant.id),
            role=new_owner.role.value,
        )
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            tenant_id=str(new_tenant.id),
            user=UserInfo(
                id=str(new_owner.id),
                email=new_owner.email,
                full_name=owner_full_name,
                phone=owner_phone,
                role=new_owner.role.value,
            ),
        )

    except IntegrityError:
        await db.rollback()
        logger.warning("Tenant registration failed due to integrity constraint", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration data conflicts with an existing record.",
            headers={"X-Error-Code": "REGISTRATION_CONFLICT"}
        )
    except Exception:
        await db.rollback()
        logger.error("Tenant registration failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant and owner user. Please try again.",
            headers={"X-Error-Code": "REGISTRATION_FAILED"}
        )


@router.post("/register", response_model=AuthResponse, summary="Register New Tenant")
async def register_tenant(
    registration: TenantRegistrationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """
    Public endpoint for tenant registration (onboarding).
    
    Creates a new tenant (company) and its owner user in a single atomic transaction.
    This is the entry point for new customers signing up for the platform.
    
    Process:
    1. Validates that email is not already registered
    2. Creates Tenant record with TRIAL subscription status
    3. Creates Owner User record linked to the tenant
    4. Commits both in a single transaction (atomic operation)
    
    Args:
        registration: Tenant registration data (company info + owner credentials)
        db: Database session dependency
        
    Returns:
        TenantRegistrationResponse: Success message with tenant_id and user_id
        
    Raises:
        HTTPException: 400 if email is already registered
        HTTPException: 500 if database transaction fails
    """
    
    # Cadastro público: sem limite, dava para criar escritórios em massa e
    # testar quais e-mails existem. Mesmo teto do login, por IP, em chave própria.
    rl_key = f"register:{get_client_ip(request)}"
    auth_rate_limiter.check_login_ip(rl_key)
    auth_rate_limiter.record_login_failure(rl_key)

    # Step 1: Check if email is already registered
    existing_user_query = await db.execute(
        select(User).where(User.email == registration.owner_email)
    )
    existing_user = existing_user_query.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{registration.owner_email}' is already registered",
            headers={"X-Error-Code": "EMAIL_ALREADY_EXISTS"}
        )

    documento = _normalizar_documento(registration.document)
    return await _create_tenant_and_owner(
        db,
        company_name=registration.company_name,
        document=documento,
        plan_slug=registration.plan_slug,
        owner_email=registration.owner_email,
        hashed_password=get_password_hash(registration.owner_password),
        owner_full_name=registration.owner_full_name,
        owner_phone=registration.owner_phone,
    )


@router.post("/register-google", response_model=AuthResponse, summary="Register New Tenant (Google)")
async def register_tenant_google(
    registration: GoogleTenantRegistrationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Conclui o primeiro acesso com Google: cria escritório + dono.

    O e-mail vem do signup_token (emitido por /auth/google só depois de o
    Google confirmar o e-mail), nunca do corpo da requisição.
    """
    rl_key = f"register:{get_client_ip(request)}"
    auth_rate_limiter.check_login_ip(rl_key)
    auth_rate_limiter.record_login_failure(rl_key)

    verified = verify_google_signup_token(registration.signup_token)
    if verified is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão do Google expirada. Entre com o Google novamente.",
            headers={"X-Error-Code": "GOOGLE_SIGNUP_EXPIRED"},
        )
    email, google_name = verified

    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já tem conta. Entre com o Google pela tela de login.",
            headers={"X-Error-Code": "EMAIL_ALREADY_EXISTS"},
        )

    documento = _normalizar_documento(registration.document)
    response = await _create_tenant_and_owner(
        db,
        company_name=registration.company_name,
        document=documento,
        plan_slug=registration.plan_slug,
        owner_email=email,
        # Conta Google não usa senha: hash de um valor aleatório descartado.
        hashed_password=get_password_hash(os.urandom(32).hex()),
        owner_full_name=(registration.owner_full_name or google_name or None),
        owner_phone=registration.owner_phone,
    )
    await log_audit_event(
        db=db,
        tenant_id=uuid.UUID(response.tenant_id),
        actor_user_id=uuid.UUID(response.user.id),
        actor_role=response.user.role,
        action="auth.register_google_success",
        entity_type="auth",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return response


@router.post("/complete-signup", summary="Complete signup of an existing tenant")
async def complete_signup(
    body: CompleteSignupRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Escritório criado sem cadastro completo (antigo login Google automático
    ou contas antigas): o dono informa o escritório e aceita os Termos.

    Sem assinatura, o escritório ganha o teste grátis de 14 dias.
    """
    tenant = current_user.tenant
    if signup_complete(tenant):
        return {"signup_complete": True}
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Só o responsável pelo escritório pode concluir o cadastro.",
        )

    documento = _normalizar_documento(body.document)
    await _garantir_documento_livre(db, documento, exceto_tenant_id=tenant.id)
    tenant.name = body.company_name.strip()
    tenant.document = documento
    if tenant.subscription is None:
        # Sem assinatura: começa o teste grátis (o Gratuito não existe mais).
        slug, plano = await _resolve_signup_plan(db, None)
        tenant.plan_slug = slug
        if plano is not None:
            _add_trial_subscription(db, tenant.id, plano, datetime.now(timezone.utc))
    if body.owner_full_name:
        current_user.full_name = body.owner_full_name.strip()
    if body.owner_phone:
        current_user.phone = body.owner_phone.strip()
    tenant.terms_accepted_at = datetime.now(timezone.utc)
    tenant.terms_version = TERMS_VERSION
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=DOCUMENTO_EM_USO_DETAIL,
            headers={"X-Error-Code": DOCUMENTO_EM_USO_CODE},
        )

    await log_audit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="auth.signup_completed",
        entity_type="auth",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return {"signup_complete": True}


@router.get("/health", summary="Onboarding Health Check")
async def onboarding_health():
    """
    Health check endpoint for onboarding service.
    
    Returns:
        dict: Status message
    """
    return {
        "status": "Onboarding service operational",
        "endpoint": "/api/v1/onboarding/register"
    }
