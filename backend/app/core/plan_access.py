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
      - subscription.status == trialing E trial_ends_at já passou.

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
