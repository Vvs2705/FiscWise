"""Admin endpoints for FiscWise — plan management and tenant operations.

NOTE: Emergency enum-fix endpoints (fix-enum-case, fix-enum-case-raw) were
removed in cleanup sprint 24/05/2026 — the underlying enum bug was fully
resolved by migration 20260520_fix_enum_case and those endpoints were dead
code with unnecessary attack surface.
"""

import os
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select as sa_select

from app.core.auth_rate_limiter import get_client_ip
from app.core.deps import get_db
from app.models.tenant import Tenant
from app.models.user import User as UserModel

router = APIRouter()
logger = logging.getLogger(__name__)

ADMIN_TOKEN = os.getenv("ADMIN_EMERGENCY_TOKEN")
ADMIN_OPERATIONS_ALLOWED = os.getenv("ADMIN_OPERATIONS_ALLOWED", "false").lower() == "true"

security = HTTPBearer(auto_error=False)


def _get_client_ip(request: Request) -> str:
    # Mesmo IP confiável do limitador de login (última entrada do
    # X-Forwarded-For, que o Cloud Run acrescenta): a primeira é escolhida
    # pelo cliente e deixava forjar o IP registrado nos alertas de admin.
    return get_client_ip(request)


async def verify_admin_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    if not ADMIN_OPERATIONS_ALLOWED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin operations are disabled")

    if not credentials:
        logger.warning(f"Admin endpoint called without Authorization from {_get_client_ip(request) if request else 'unknown'}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header", headers={"WWW-Authenticate": "Bearer"})

    if not ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin token not configured")

    if not hmac.compare_digest(credentials.credentials, ADMIN_TOKEN):
        logger.warning(f"Invalid admin token from {_get_client_ip(request) if request else 'unknown'}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")

    return credentials.credentials


# ---------------------------------------------------------------------------
# Plan management
# ---------------------------------------------------------------------------

class SetPlanRequest(PydanticBaseModel):
    email: str
    plan_slug: str  # "free" | "intermediario" | "premium"


@router.post("/set-plan-by-email", summary="Admin: Update tenant plan by user email")
async def set_plan_by_email(
    body: SetPlanRequest,
    request: Request,
    token: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Update the plan_slug of the tenant associated with the given email."""
    VALID_PLANS = {"free", "intermediario", "premium"}
    if body.plan_slug not in VALID_PLANS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid plan_slug '{body.plan_slug}'. Valid values: {sorted(VALID_PLANS)}",
        )

    user_result = await db.execute(sa_select(UserModel).where(UserModel.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"No user found with email '{body.email}'")

    tenant_result = await db.execute(sa_select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"No tenant found for user '{body.email}'")

    old_plan = tenant.plan_slug
    tenant.plan_slug = body.plan_slug
    await db.commit()
    await db.refresh(tenant)

    logger.info(f"[ADMIN] plan_slug updated for {body.email}: {old_plan!r} -> {body.plan_slug!r} from {_get_client_ip(request)}")

    return {
        "status": "updated",
        "email": body.email,
        "tenant_id": str(tenant.id),
        "old_plan": old_plan,
        "new_plan": tenant.plan_slug,
    }


@router.post("/cache/invalidate", summary="Admin: limpa o cache de planos e regras")
async def invalidate_catalog_cache(
    request: Request,
    token: str = Depends(verify_admin_token),
):
    """Use depois de alterar `plans` ou `obligation_rules` direto no banco (seed,
    SQL manual). Sem isso, a mudança aparece em até 5 minutos."""
    from app.core.ttl_cache import invalidate_all

    invalidate_all()
    logger.info("[ADMIN] cache de catálogo invalidado por %s", _get_client_ip(request))
    return {"status": "invalidated", "caches": ["plans", "obligation_rules"]}


@router.get("/tenant-by-email", summary="Admin: Get tenant info by user email")
async def get_tenant_by_email(
    email: str,
    request: Request,
    token: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Fetch tenant info (including plan_slug) for a given user email."""
    user_result = await db.execute(sa_select(UserModel).where(UserModel.email == email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"No user found with email '{email}'")

    tenant_result = await db.execute(sa_select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"No tenant found for user '{email}'")

    return {
        "email": email,
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "plan_slug": tenant.plan_slug,
        "subscription_status": tenant.subscription_status.value,
    }


# ---------------------------------------------------------------------------
# LGPD: executar o pedido de exclusão do dono (POST /account/delete)
# ---------------------------------------------------------------------------

class ExclusaoLgpdRequest(PydanticBaseModel):
    tenant_id: str
    # Nome do escritório digitado de novo: evita apagar o escritório errado.
    confirmar_nome: str
    # False (padrão) = só a prévia, com a contagem por tabela.
    executar: bool = False


@router.post("/lgpd/exclusao", summary="Admin: executa o pedido LGPD de exclusão de um escritório")
async def executar_exclusao_lgpd(
    body: ExclusaoLgpdRequest,
    request: Request,
    token: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Exclui os dados de um escritório que pediu exclusão (LGPD art. 18, VI).

    Mesma exclusão da rotina de contas vencidas (services/exclusao_dados):
    apaga linhas e arquivos do escritório, anonimiza os usuários, mantém o
    histórico de cobrança e os registros de acesso por 6 meses.

    Só vale para escritório com `deletion_requested_at` (pedido feito pelo
    dono). Sem `executar=true` devolve só a prévia. Não tem volta: antes de
    executar, confirme que o escritório exportou o que precisa guardar.
    """
    import uuid as _uuid
    from datetime import datetime, timezone

    from app.services import exclusao_dados

    try:
        tenant_id = _uuid.UUID(body.tenant_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="tenant_id inválido")
    tenant = (await db.execute(sa_select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Escritório não encontrado")
    if tenant.deletion_requested_at is None:
        raise HTTPException(status_code=409, detail="Este escritório não pediu exclusão.")
    if tenant.dados_excluidos_em is not None:
        return {"status": "ja_excluido", "excluido_em": tenant.dados_excluidos_em.isoformat()}
    if body.confirmar_nome.strip() != (tenant.name or "").strip():
        raise HTTPException(status_code=400, detail="O nome digitado não confere com o do escritório.")

    if not body.executar:
        return {
            "status": "previa",
            "tenant_id": str(tenant.id),
            "pedido_em": tenant.deletion_requested_at.isoformat(),
            "linhas_por_tabela": await exclusao_dados.contar_linhas(db, tenant.id),
        }

    resumo = await exclusao_dados.excluir(db, tenant, datetime.now(timezone.utc))
    await db.commit()
    logger.warning("[ADMIN] exclusao_lgpd tenant=%s ip=%s resumo=%s", tenant.id, _get_client_ip(request), resumo)
    from app.services.audit import log_audit_event

    await log_audit_event(
        db=db, tenant_id=tenant.id, action="lgpd.exclusao_a_pedido", entity_type="tenant",
        entity_id=tenant.id, actor_role="admin", after_data=resumo,
    )
    return {"status": "excluido", "tenant_id": str(tenant.id), "resumo": resumo}
