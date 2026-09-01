"""Plan-based feature gating for FiscWise.

Plans
-----
- FREE         : Apenas números, sem IA
- INTERMEDIARIO: Recomendações IA + 20 mensagens/mês
- PREMIUM      : IA ilimitada + PDF export + benefícios fiscais
"""

from fastapi import HTTPException, status

from app.models.tenant import Tenant


# Canonical plan slugs (stored in tenants.plan_slug)
PLAN_FREE = "free"
PLAN_INTERMEDIARIO = "intermediario"
PLAN_PREMIUM = "premium"

# Ordered list for comparison (higher index = higher tier)
_PLAN_ORDER = [PLAN_FREE, PLAN_INTERMEDIARIO, PLAN_PREMIUM]

# Monthly AI chat message limits
AI_CHAT_MONTHLY_LIMIT: dict[str, int] = {
    PLAN_FREE: 0,
    PLAN_INTERMEDIARIO: 20,
    PLAN_PREMIUM: -1,  # -1 means unlimited
}


def _resolve_plan(tenant: Tenant) -> str:
    """Return the effective plan slug for a tenant.

    Falls back to FREE if plan_slug is not set or unrecognised.
    """
    slug = (tenant.plan_slug or "").lower().strip()
    if slug not in _PLAN_ORDER:
        return PLAN_FREE
    return slug


def has_ai_access(tenant: Tenant) -> bool:
    """Return True if the tenant's plan includes AI recommendations."""
    return _resolve_plan(tenant) in (PLAN_INTERMEDIARIO, PLAN_PREMIUM)


def has_pdf_export(tenant: Tenant) -> bool:
    """Return True if the tenant's plan includes PDF export."""
    return _resolve_plan(tenant) == PLAN_PREMIUM


def has_unlimited_ai_chat(tenant: Tenant) -> bool:
    """Return True if the tenant has unlimited AI chat messages."""
    return _resolve_plan(tenant) == PLAN_PREMIUM


def get_monthly_chat_limit(tenant: Tenant) -> int:
    """Return the monthly AI chat message limit for the tenant.

    Returns -1 for unlimited.
    """
    return AI_CHAT_MONTHLY_LIMIT.get(_resolve_plan(tenant), 0)


def require_ai_access(tenant: Tenant) -> None:
    """Raise HTTP 403 if the tenant's plan does not include AI.

    Usage::

        require_ai_access(current_user.tenant)
    """
    if not has_ai_access(tenant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PLAN_UPGRADE_REQUIRED",
                "message": "Recomendações com IA estão disponíveis nos planos Intermediário e Premium.",
                "required_plan": PLAN_INTERMEDIARIO,
            },
        )


def require_pdf_export(tenant: Tenant) -> None:
    """Raise HTTP 403 if the tenant's plan does not include PDF export."""
    if not has_pdf_export(tenant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PLAN_UPGRADE_REQUIRED",
                "message": "Exportação de PDF está disponível apenas no plano Premium.",
                "required_plan": PLAN_PREMIUM,
            },
        )
