"""Subscription and usage endpoints for FiscWise.

GET /api/v1/subscription/usage  — current usage vs plan limits for the authenticated tenant
GET /api/v1/subscription/plans  — list available plans (public)
"""

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.plan_access import resolve_plan
from app.models.operations import AccountingClient, ClientDocument
from app.models.plan import Plan
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PlanOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: Optional[str]
    price_monthly: Optional[float]
    max_clients: Optional[int]
    max_users: Optional[int]
    max_ai_calls_month: Optional[int]
    max_documents_per_client: Optional[int]
    features: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class UsageItem(BaseModel):
    used: int
    limit: Optional[int]  # None = unlimited
    percent: Optional[float]  # None = unlimited


class UsageResponse(BaseModel):
    plan_slug: str
    plan_name: str
    clients: UsageItem
    users: UsageItem
    ai_calls_this_month: UsageItem
    features: Dict[str, bool]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _usage_item(used: int, limit: Optional[int]) -> UsageItem:
    pct = round((used / limit) * 100, 1) if limit else None
    return UsageItem(used=used, limit=limit, percent=pct)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/plans", response_model=list[PlanOut], summary="List available subscription plans")
async def list_plans(db: AsyncSession = Depends(get_db)):
    """Return all active subscription plans (public, no auth required)."""
    result = await db.execute(
        select(Plan).where(Plan.active == True).order_by(Plan.price_monthly.nullsfirst())
    )
    return result.scalars().all()


@router.get("/usage", response_model=UsageResponse, summary="Get current usage vs plan limits")
async def get_subscription_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current tenant's usage metrics compared to their plan limits."""
    # Resolve effective plan slug
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    effective_slug = resolve_plan(tenant.plan_slug, current_user.email) or "free"

    # Load plan definition
    plan_result = await db.execute(select(Plan).where(Plan.slug == effective_slug))
    plan = plan_result.scalar_one_or_none()

    if not plan:
        # Fallback: use free plan limits if plan not found in DB
        plan_name = effective_slug.title()
        max_clients = 10
        max_users = 2
        max_ai = 0
        features: Dict[str, bool] = {"calculator": True, "ai_chat": False, "pdf_export": False}
    else:
        plan_name = plan.name
        max_clients = plan.max_clients
        max_users = plan.max_users
        max_ai = plan.max_ai_calls_month
        features = {k: bool(v) for k, v in (plan.features or {}).items()}

    # Count current usage
    clients_count_result = await db.execute(
        select(func.count()).select_from(AccountingClient).where(
            and_(
                AccountingClient.tenant_id == current_user.tenant_id,
                AccountingClient.status == "active",
            )
        )
    )
    clients_used = int(clients_count_result.scalar_one() or 0)

    users_count_result = await db.execute(
        select(func.count()).select_from(User).where(
            and_(
                User.tenant_id == current_user.tenant_id,
                User.is_active == True,
            )
        )
    )
    users_used = int(users_count_result.scalar_one() or 0)

    # AI calls this month — count from fiscal assistant messages
    ai_used = 0
    try:
        from datetime import datetime, timezone
        from app.models.calculator import FiscalAssistantMessage, AssistantRole
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ai_result = await db.execute(
            select(func.count()).select_from(FiscalAssistantMessage).where(
                and_(
                    FiscalAssistantMessage.tenant_id == current_user.tenant_id,
                    FiscalAssistantMessage.role == AssistantRole.USER,
                    FiscalAssistantMessage.created_at >= month_start,
                )
            )
        )
        ai_used = int(ai_result.scalar_one() or 0)
    except Exception:
        pass  # Calculator model may not exist in all environments

    return UsageResponse(
        plan_slug=effective_slug,
        plan_name=plan_name,
        clients=_usage_item(clients_used, max_clients),
        users=_usage_item(users_used, max_users),
        ai_calls_this_month=_usage_item(ai_used, max_ai),
        features=features,
    )


@router.get("/limits-check", summary="Check if a limit would be exceeded")
async def check_limits(
    resource: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Quick check if adding one more unit of a resource would exceed plan limits.
    resource: 'client' | 'user'
    """
    if resource not in ("client", "user"):
        raise HTTPException(status_code=422, detail="resource must be 'client' or 'user'")

    # Get usage (reuse logic from /usage)
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    effective_slug = resolve_plan(tenant.plan_slug if tenant else None, current_user.email) or "free"

    plan_result = await db.execute(select(Plan).where(Plan.slug == effective_slug))
    plan = plan_result.scalar_one_or_none()

    if resource == "client":
        if not plan or plan.max_clients is None:
            return {"allowed": True, "used": 0, "limit": None}
        count_result = await db.execute(
            select(func.count()).select_from(AccountingClient).where(
                and_(
                    AccountingClient.tenant_id == current_user.tenant_id,
                    AccountingClient.status == "active",
                )
            )
        )
        used = int(count_result.scalar_one() or 0)
        return {"allowed": used < plan.max_clients, "used": used, "limit": plan.max_clients}

    else:  # user
        if not plan or plan.max_users is None:
            return {"allowed": True, "used": 0, "limit": None}
        count_result = await db.execute(
            select(func.count()).select_from(User).where(
                and_(
                    User.tenant_id == current_user.tenant_id,
                    User.is_active == True,
                )
            )
        )
        used = int(count_result.scalar_one() or 0)
        return {"allowed": used < plan.max_users, "used": used, "limit": plan.max_users}
