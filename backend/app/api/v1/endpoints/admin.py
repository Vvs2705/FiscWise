"""Admin endpoints for operational tenant plan management."""

import hmac
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.audit import log_audit_event

router = APIRouter()
logger = logging.getLogger(__name__)

ADMIN_TOKEN = os.getenv("ADMIN_EMERGENCY_TOKEN")
ADMIN_OPERATIONS_ALLOWED = os.getenv("ADMIN_OPERATIONS_ALLOWED", "false").lower() == "true"

security = HTTPBearer(auto_error=False)


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def verify_admin_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None,
) -> str:
    """Verify admin token from Authorization header with timing-safe comparison."""
    if not ADMIN_OPERATIONS_ALLOWED:
        logger.error("Admin endpoint called but ADMIN_OPERATIONS_ALLOWED=false")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin operations are disabled",
        )

    if not credentials:
        client_ip = _get_client_ip(request) if request else "unknown"
        logger.warning("Admin endpoint called without Authorization header from %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not ADMIN_TOKEN:
        logger.error("ADMIN_EMERGENCY_TOKEN environment variable not set")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin token not configured",
        )

    provided_token = credentials.credentials
    if not hmac.compare_digest(provided_token, ADMIN_TOKEN):
        client_ip = _get_client_ip(request) if request else "unknown"
        logger.warning(
            "Invalid admin token attempted from %s. Token length: %s, Expected length: %s",
            client_ip,
            len(provided_token),
            len(ADMIN_TOKEN),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

    return provided_token


class SetPlanRequest(BaseModel):
    email: str
    plan_slug: str


@router.post("/set-plan-by-email", summary="Admin: Update tenant plan by user email")
async def set_plan_by_email(
    body: SetPlanRequest,
    request: Request,
    token: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the plan_slug of the tenant associated with the given email.

    Requires: Authorization: Bearer <ADMIN_EMERGENCY_TOKEN> header.
    Valid plan slugs: free, intermediario, premium.
    """
    valid_plans = {"free", "intermediario", "premium"}
    if body.plan_slug not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid plan_slug '{body.plan_slug}'. Valid values: {sorted(valid_plans)}",
        )

    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email '{body.email}'",
        )

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tenant found for user '{body.email}'",
        )

    old_plan = tenant.plan_slug
    tenant.plan_slug = body.plan_slug
    await db.commit()
    await db.refresh(tenant)

    await log_audit_event(
        db=db,
        tenant_id=tenant.id,
        actor_role="admin_token",
        action="admin.set_plan",
        entity_type="tenant",
        entity_id=tenant.id,
        before_data={"plan_slug": old_plan},
        after_data={"plan_slug": tenant.plan_slug},
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("User-Agent") if request else None,
    )

    client_ip = _get_client_ip(request)
    logger.info(
        "[ADMIN] plan_slug updated for %s: %r -> %r from %s",
        body.email,
        old_plan,
        body.plan_slug,
        client_ip,
    )

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
    """Fetch tenant info, including plan_slug, for a given user email."""
    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email '{email}'",
        )

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tenant found for user '{email}'",
        )

    return {
        "email": email,
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "plan_slug": tenant.plan_slug,
        "subscription_status": tenant.subscription_status.value,
    }
