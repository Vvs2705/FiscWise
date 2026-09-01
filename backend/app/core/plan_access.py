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
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

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
