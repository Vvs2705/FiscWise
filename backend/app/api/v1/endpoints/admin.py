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

from app.core.deps import get_db
from app.models.tenant import Tenant
from app.models.user import User as UserModel

router = APIRouter()
logger = logging.getLogger(__name__)

ADMIN_TOKEN = os.getenv("ADMIN_EMERGENCY_TOKEN")
ADMIN_OPERATIONS_ALLOWED = os.getenv("ADMIN_OPERATIONS_ALLOWED", "false").lower() == "true"

security = HTTPBearer(auto_error=False)


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
