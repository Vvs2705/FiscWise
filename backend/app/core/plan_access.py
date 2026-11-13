"""
Plan Access Control for FiscWise - Feature #7

Defines which features each subscription plan can access.
Raises HTTPException with clear error messages when access is denied.

Plan slugs (stored in tenants.plan_slug):
  - None / "free"    → FREE plan
  - "intermediario"  → INTERMEDIARIO plan
  - "premium"        → PREMIUM plan

Feature matrix:
  Calculator basic simulations  → all plans
  AI recommendations            → intermediario + premium
  Chat assistant                → intermediario (20/month) + premium (unlimited)
  PDF export                    → premium only
  Fiscal benefits listing       → premium only

Superuser override:
  Emails listed in TEST_SUPERUSER_EMAILS always receive PREMIUM access
  regardless of the plan stored in the database. Intended for explicit
  operator-controlled test/admin accounts only.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Superuser override: these emails always get PREMIUM regardless of DB value
# Add more via TEST_SUPERUSER_EMAILS env var (comma-separated)
# ---------------------------------------------------------------------------

_SUPERUSER_EMAILS: frozenset[str] = frozenset(
    e.strip().lower()
    for e in os.getenv("TEST_SUPERUSER_EMAILS", "").split(",")
    if e.strip()
)


def resolve_plan(plan_slug: Optional[str], user_email: Optional[str] = None) -> Optional[str]:
    """
    Resolve the effective plan for a user.

    If the user's email is in _SUPERUSER_EMAILS, always returns PREMIUM.
    Otherwise returns plan_slug as stored in the database.
    """
    if user_email and user_email.lower() in _SUPERUSER_EMAILS:
        return PLAN_PREMIUM
    return plan_slug


def effective_plan_slug(tenant: object, subscription: object = None) -> Optional[str]:
    """
    Plano efetivo do tenant considerando o estado da assinatura (enforcement).

    Degrada para FREE quando:
      - subscription.status ∈ {suspended, cancelled}; OU
      - subscription.status == trialing E trial_ends_at já passou; OU
      - o dono cancelou (cancelled_at) e o período pago já terminou; OU
      - ciclo pré-pago do Mercado Pago (não mensal) com o período vencido.

    Tenants SEM linha em tenant_subscriptions (legado) mantêm o plan_slug
    gravado — nunca degradam. Se `subscription` não for passada, é lida de
    `tenant.subscription` (relationship selectin em Tenant).
    """
    plan_slug = getattr(tenant, "plan_slug", None) if tenant is not None else None
    if subscription is None:
        subscription = getattr(tenant, "subscription", None) if tenant is not None else None
    if subscription is None:
        return plan_slug

    sub_status = getattr(subscription, "status", None)
    if sub_status in ("suspended", "cancelled"):
        return PLAN_FREE

    # Cancelamento pedido pelo dono: vale o período pago; depois, Gratuito.
    if getattr(subscription, "cancelled_at", None) is not None:
        period_end = getattr(subscription, "current_period_end", None)
        if period_end is None:
            return PLAN_FREE
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        if period_end <= datetime.now(timezone.utc):
            return PLAN_FREE

    # Ciclo pré-pago (trimestral/semestral/anual, pagamento único): acabou o
    # período, volta para o Gratuito até pagar de novo. O mensal recorrente não
    # entra aqui: quem encerra é o Mercado Pago (preapproval cancelado → suspenso).
    if (
        sub_status == "active"
        and getattr(subscription, "billing_provider", None) == "mercadopago"
        and (getattr(subscription, "billing_cycle", None) or "mensal") != "mensal"
    ):
        period_end = getattr(subscription, "current_period_end", None)
        if period_end is not None:
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)
            if period_end <= datetime.now(timezone.utc):
                return PLAN_FREE

    if sub_status == "trialing":
        trial_ends_at = getattr(subscription, "trial_ends_at", None)
        if trial_ends_at is not None:
            if trial_ends_at.tzinfo is None:  # SQLite devolve datetimes naive
                trial_ends_at = trial_ends_at.replace(tzinfo=timezone.utc)
            if trial_ends_at < datetime.now(timezone.utc):
                return PLAN_FREE

    return plan_slug


def resolve_tenant_plan(tenant: object, user_email: Optional[str] = None) -> Optional[str]:
    """
    Plano efetivo de um tenant: enforcement de assinatura + override de superuser.

    RAIZ do paywall — todo ponto que resolve o plano a partir de um Tenant deve
    passar por aqui (não por tenant.plan_slug direto).
    """
    return resolve_plan(effective_plan_slug(tenant), user_email)


def resolve_user_plan(current_user: object) -> Optional[str]:
    """Resolve the effective plan for the current authenticated user."""
    tenant = getattr(current_user, "tenant", None)
    return resolve_tenant_plan(tenant, getattr(current_user, "email", None))


# ---------------------------------------------------------------------------
# Teste grátis e conta só leitura (13/11/2026: o plano Gratuito permanente
# deixou de existir; todo cadastro começa com 14 dias de teste do Premium).
# ---------------------------------------------------------------------------

TRIAL_DAYS = 14
# Depois de vencer, os dados ficam disponíveis para consulta e exportação.
RETENCAO_APOS_VENCER_DIAS = 60


def acesso_expirado(tenant: object, user_email: Optional[str] = None) -> bool:
    """Conta sem plano pago nem teste vigente → só leitura.

    É o mesmo critério que antes "caía para o Gratuito" (effective_plan_slug):
    teste vencido, assinatura suspensa/cancelada, período pago encerrado ou
    pré-pago vencido. Tenant None (rotas sem escritório) nunca bloqueia.

    Escritório SEM linha de assinatura nunca vence (mesma regra do
    effective_plan_slug para contas antigas, ex.: plano liberado pelo admin).
    Todo cadastro novo nasce com o teste, e a migração r4t5teste14d deu o teste
    a quem estava no Gratuito sem assinatura.
    """
    if tenant is None or getattr(tenant, "subscription", None) is None:
        return False
    return _rank(resolve_tenant_plan(tenant, user_email)) == 0


def info_teste(tenant: object, user_email: Optional[str] = None) -> dict:
    """Situação do teste grátis para a tela (faixa de dias restantes)."""
    sub = getattr(tenant, "subscription", None) if tenant is not None else None
    expirado = acesso_expirado(tenant, user_email)
    fim = getattr(sub, "trial_ends_at", None) if sub is not None else None
    if fim is not None and fim.tzinfo is None:
        fim = fim.replace(tzinfo=timezone.utc)
    em_teste = (
        sub is not None and getattr(sub, "status", None) == "trialing"
        and fim is not None and not expirado
    )
    dias = None
    if em_teste:
        # Dias de calendário em Brasília: 14 no cadastro, 0 = acaba hoje.
        import pytz  # imagem slim pode não ter tzdata; o scheduler já usa pytz

        br = pytz.timezone("America/Sao_Paulo")
        dias = max((fim.astimezone(br).date() - datetime.now(br).date()).days, 0)
    return {
        "em_teste": em_teste,
        "trial_ends_at": fim.isoformat() if fim is not None else None,
        "trial_dias_restantes": dias,
        "acesso_expirado": expirado,
    }


# ---------------------------------------------------------------------------
# Plan constants
# ---------------------------------------------------------------------------

PLAN_FREE = "free"
PLAN_INTERMEDIARIO = "intermediario"
PLAN_PREMIUM = "premium"

_PLAN_RANK: dict[Optional[str], int] = {
    None: 0,
    PLAN_FREE: 0,
    PLAN_INTERMEDIARIO: 1,
    PLAN_PREMIUM: 2,
}

# Monthly chat message quota per plan (None = unlimited)
_CHAT_QUOTA: dict[Optional[str], Optional[int]] = {
    None: 0,
    PLAN_FREE: 0,
    PLAN_INTERMEDIARIO: 20,
    PLAN_PREMIUM: None,
}


def _rank(plan_slug: Optional[str]) -> int:
    return _PLAN_RANK.get(plan_slug, 0)


def require_plan(
    current_plan: Optional[str],
    required_plan: str,
    feature_name: str,
) -> None:
    """
    Raise HTTPException(403) if current_plan is below the required tier.

    Args:
        current_plan: plan_slug from tenants.plan_slug
        required_plan: minimum plan slug required (e.g. PLAN_INTERMEDIARIO)
        feature_name: human-readable name for the error message
    """
    if _rank(current_plan) < _rank(required_plan):
        plan_labels = {
            PLAN_INTERMEDIARIO: "Intermediário",
            PLAN_PREMIUM: "Premium",
        }
        required_label = plan_labels.get(required_plan, required_plan.title())
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"O recurso '{feature_name}' requer o plano {required_label} ou superior. "
                f"Faça upgrade em fiscwise.com.br/planos."
            ),
        )


AI_NOT_CONFIGURED_DETAIL = "Assistente de IA não configurado nesta instalação."


def require_ai_configured() -> None:
    """
    Fail fast with 503 when no AI key is configured.

    Must run BEFORE anything that consumes chat quota (persisting the user
    message), so an installation without OPENAI_API_KEY never burns the
    tenant's monthly messages on answers that cannot be produced.
    """
    from app.core.config import settings

    if not (settings.OPENAI_API_KEY or "").strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=AI_NOT_CONFIGURED_DETAIL,
        )


def has_plan(current_plan: Optional[str], required_plan: str) -> bool:
    """Return True if current_plan meets the required minimum tier."""
    return _rank(current_plan) >= _rank(required_plan)


async def check_chat_quota(
    tenant_id,
    plan_slug: Optional[str],
    db: AsyncSession,
) -> tuple[bool, Optional[int]]:
    """
    Check whether a tenant has remaining chat quota for the current month.

    Returns (has_quota: bool, remaining: Optional[int]).
    remaining is None when the plan has unlimited quota.
    """
    quota = _CHAT_QUOTA.get(plan_slug, 0)

    if quota == 0:
        # FREE plan — no chat access at all
        return False, 0

    if quota is None:
        # PREMIUM plan — unlimited
        return True, None

    # INTERMEDIARIO plan — count messages sent this calendar month
    from app.models.calculator import FiscalAssistantMessage, AssistantRole

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count())
        .select_from(FiscalAssistantMessage)
        .where(
            FiscalAssistantMessage.tenant_id == tenant_id,
            FiscalAssistantMessage.role == AssistantRole.USER,
            FiscalAssistantMessage.created_at >= month_start,
        )
    )
    used = int(result.scalar_one() or 0)
    remaining = max(quota - used, 0)
    return remaining > 0, remaining


# ---------------------------------------------------------------------------
# Limites e recursos da tabela `plans` aplicados no backend (não só na tela).
#
# Sempre pelo plano EFETIVO (resolve_tenant_plan): teste vencido ou assinatura
# suspensa caem para a linha "free". Os limites só barram o que é NOVO: quem
# já passou do limite mantém tudo o que tem (nada é apagado nem desativado).
#
# Falha fechada: se não der para conferir o plano (erro de banco), a criação é
# recusada com 503 PLANO_INDISPONIVEL em vez de passar sem limite.
# Plano gravado sem linha na tabela usa os limites da linha "free"; se nem ela
# existir (instalação sem catálogo, ex.: testes), não há limite configurado.
# ---------------------------------------------------------------------------

LIMITE_CLIENTES_CODE = "LIMITE_CLIENTES"
LIMITE_USUARIOS_CODE = "LIMITE_USUARIOS"
LIMITE_DOCUMENTOS_CODE = "LIMITE_DOCUMENTOS"
RECURSO_FORA_DO_PLANO_CODE = "RECURSO_FORA_DO_PLANO"
PLANO_INDISPONIVEL_CODE = "PLANO_INDISPONIVEL"

FEATURE_PORTAL_CLIENTE = "portal_cliente"
FEATURE_OBRIGACOES = "obrigacoes"

_FEATURE_LABELS = {
    FEATURE_PORTAL_CLIENTE: "Portal do cliente",
    FEATURE_OBRIGACOES: "Motor de obrigações",
}

_UPGRADE_HINT = "Faça upgrade em fiscwise.com.br/planos."


def _forbidden(detail: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
        headers={"X-Error-Code": code},
    )


def _plan_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Não foi possível conferir os limites do seu plano agora. "
            "Tente de novo em instantes."
        ),
        headers={"X-Error-Code": PLANO_INDISPONIVEL_CODE},
    )


async def load_tenant_plan(db: AsyncSession, tenant_id, user_email: Optional[str] = None):
    """(slug efetivo, PlanSnapshot | None) do escritório. Erros sobem crus."""
    from app.models.tenant import Tenant
    from app.services.catalog_cache import get_plan_by_slug

    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    slug = resolve_tenant_plan(tenant, user_email) or PLAN_FREE
    plan = await get_plan_by_slug(db, slug)
    if plan is None and slug != PLAN_FREE:
        logger.warning("Plano '%s' sem linha na tabela plans: usando limites do Gratuito", slug)
        plan = await get_plan_by_slug(db, PLAN_FREE)
    return slug, plan


def _plan_label(plan) -> str:
    return getattr(plan, "name", None) or "atual"


async def ensure_can_add_client(db: AsyncSession, tenant_id, user_email: Optional[str] = None) -> None:
    """Barra cliente ATIVO novo (cadastro ou reativação) acima de max_clients."""
    from app.models.operations import AccountingClient

    try:
        _, plan = await load_tenant_plan(db, tenant_id, user_email)
        limit = getattr(plan, "max_clients", None)
        if limit is None:
            return
        used = int(
            await db.scalar(
                select(func.count()).select_from(AccountingClient).where(
                    AccountingClient.tenant_id == tenant_id,
                    AccountingClient.status == "active",
                )
            )
            or 0
        )
    except Exception as exc:
        logger.exception("Checagem do limite de clientes falhou (tenant %s)", tenant_id)
        raise _plan_unavailable() from exc
    if used >= limit:
        raise _forbidden(
            f"Limite de clientes atingido para o plano {_plan_label(plan)} "
            f"({limit} clientes ativos). {_UPGRADE_HINT}",
            LIMITE_CLIENTES_CODE,
        )


def team_member_filter(tenant_id):
    """Quem conta como usuário da equipe: ativo e não é cliente do portal."""
    from app.models.user import User, UserRole

    return (
        User.tenant_id == tenant_id,
        User.is_active == True,  # noqa: E712
        User.role != UserRole.CLIENT,
    )


async def count_team_members(db: AsyncSession, tenant_id) -> int:
    from app.models.user import User

    return int(
        await db.scalar(select(func.count()).select_from(User).where(*team_member_filter(tenant_id)))
        or 0
    )


async def ensure_can_add_team_member(db: AsyncSession, tenant_id, user_email: Optional[str] = None) -> None:
    """Barra membro da equipe novo (convite, criação ou reativação) acima de max_users.

    Usuários do portal do cliente (role client) não contam: são do cliente final.
    Toda rota que criar ou reativar alguém da equipe deve chamar esta função.
    """
    try:
        _, plan = await load_tenant_plan(db, tenant_id, user_email)
        limit = getattr(plan, "max_users", None)
        if limit is None:
            return
        used = await count_team_members(db, tenant_id)
    except Exception as exc:
        logger.exception("Checagem do limite de usuários falhou (tenant %s)", tenant_id)
        raise _plan_unavailable() from exc
    if used >= limit:
        raise _forbidden(
            f"Limite de usuários atingido para o plano {_plan_label(plan)} "
            f"({limit} usuários na equipe). {_UPGRADE_HINT}",
            LIMITE_USUARIOS_CODE,
        )


async def ensure_can_add_document(
    db: AsyncSession, tenant_id, client_id, user_email: Optional[str] = None
) -> None:
    """Barra documento novo de um cliente acima de max_documents_per_client."""
    from app.models.operations import ClientDocument

    try:
        _, plan = await load_tenant_plan(db, tenant_id, user_email)
        limit = getattr(plan, "max_documents_per_client", None)
        if limit is None:
            return
        used = int(
            await db.scalar(
                select(func.count()).select_from(ClientDocument).where(
                    ClientDocument.tenant_id == tenant_id,
                    ClientDocument.client_id == client_id,
                )
            )
            or 0
        )
    except Exception as exc:
        logger.exception("Checagem do limite de documentos falhou (tenant %s)", tenant_id)
        raise _plan_unavailable() from exc
    if used >= limit:
        raise _forbidden(
            f"Limite de documentos atingido para este cliente no plano {_plan_label(plan)} "
            f"({limit} documentos por cliente). Apague documentos antigos ou faça upgrade "
            f"em fiscwise.com.br/planos.",
            LIMITE_DOCUMENTOS_CODE,
        )


def plan_has_feature(plan, feature: str) -> bool:
    """Sem catálogo configurado (plan None) o recurso fica liberado."""
    if plan is None:
        return True
    return bool((getattr(plan, "features", None) or {}).get(feature))


async def ensure_feature(
    db: AsyncSession, tenant_id, feature: str, user_email: Optional[str] = None
) -> None:
    """403 RECURSO_FORA_DO_PLANO quando o plano efetivo não tem o recurso."""
    try:
        _, plan = await load_tenant_plan(db, tenant_id, user_email)
    except Exception as exc:
        logger.exception("Checagem do recurso '%s' falhou (tenant %s)", feature, tenant_id)
        raise _plan_unavailable() from exc
    if not plan_has_feature(plan, feature):
        label = _FEATURE_LABELS.get(feature, feature)
        raise _forbidden(
            f"O recurso '{label}' não faz parte do plano {_plan_label(plan)}. {_UPGRADE_HINT}",
            RECURSO_FORA_DO_PLANO_CODE,
        )


# ---------------------------------------------------------------------------
# Uso de IA no mês = mensagens ao assistente (inclui resumos por IA) +
# documentos classificados por IA. Mesmo saldo de plans.max_ai_calls_month.
# O chat continua contando só as mensagens (o plano promete "N mensagens/mês");
# a classificação automática usa o que sobra do saldo do mês.
# ---------------------------------------------------------------------------


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def count_ai_calls_this_month(db: AsyncSession, tenant_id) -> int:
    from app.models.calculator import AssistantRole, FiscalAssistantMessage
    from app.models.operations import ClientDocument

    start = _month_start()
    chat = await db.scalar(
        select(func.count()).select_from(FiscalAssistantMessage).where(
            FiscalAssistantMessage.tenant_id == tenant_id,
            FiscalAssistantMessage.role == AssistantRole.USER,
            FiscalAssistantMessage.created_at >= start,
        )
    )
    docs = await db.scalar(
        select(func.count()).select_from(ClientDocument).where(
            ClientDocument.tenant_id == tenant_id,
            ClientDocument.ai_classified_at >= start,
        )
    )
    return int(chat or 0) + int(docs or 0)


async def ai_classification_allowed(db: AsyncSession, tenant_id) -> tuple[bool, Optional[str]]:
    """Pode classificar mais um documento por IA? (permitido, motivo quando não).

    Roda em segundo plano (fila de leitura de documentos), então nunca levanta.
    Falha fechada: sem conseguir conferir, não chama a IA. O documento é lido
    normalmente, só fica sem a classificação.
    """
    try:
        _, plan = await load_tenant_plan(db, tenant_id)
        limit = getattr(plan, "max_ai_calls_month", None)
        if plan is None or limit is None:
            return True, None
        if limit <= 0:
            return False, (
                f"A classificação por IA não faz parte do plano {_plan_label(plan)}. {_UPGRADE_HINT}"
            )
        used = await count_ai_calls_this_month(db, tenant_id)
    except Exception:
        logger.exception("Checagem da cota de IA falhou (tenant %s)", tenant_id)
        return False, "Não foi possível conferir a cota de IA do plano; classificação não feita."
    if used >= limit:
        return False, (
            f"A cota mensal de IA do plano {_plan_label(plan)} acabou ({limit} usos por mês). "
            f"{_UPGRADE_HINT}"
        )
    return True, None
