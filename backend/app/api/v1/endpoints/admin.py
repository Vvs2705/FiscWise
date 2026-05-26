"""Admin endpoints for FiscWise — plan management and tenant operations.

Auth: JWT-based superuser (is_superuser=True on the user record).
The static ADMIN_EMERGENCY_TOKEN is kept as an emergency fallback but
is disabled by default (ADMIN_OPERATIONS_ALLOWED=false).
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

from app.core.deps import get_db, get_current_user, require_superuser
from app.models.tenant import Tenant
from app.models.user import User as UserModel

router = APIRouter()
logger = logging.getLogger(__name__)

# Emergency static token — kept for break-glass scenarios only
ADMIN_TOKEN: str | None = os.getenv("ADMIN_EMERGENCY_TOKEN")
ADMIN_OPERATIONS_ALLOWED: bool = os.getenv("ADMIN_OPERATIONS_ALLOWED", "false").lower() == "true"

security = HTTPBearer(auto_error=False)


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def verify_admin_access(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """
    Primary: validate JWT token with is_superuser=True.
    Fallback (emergency only): static ADMIN_EMERGENCY_TOKEN when ADMIN_OPERATIONS_ALLOWED=true.
    """
    # Try JWT superuser auth first (preferred path)
    if credentials and credentials.credentials:
        try:
            from app.core.deps import get_current_user as _get_user
            from fastapi.security import OAuth2PasswordBearer
            user = await _get_user(request=request, token=credentials.credentials, db=db)
            if getattr(user, "is_superuser", False):
                logger.info(
                    "Admin access via JWT superuser: user=%s ip=%s",
                    user.email, _get_client_ip(request),
                )
                return user
        except HTTPException:
            pass  # Fall through to emergency token check

    # Emergency static token fallback
    if not ADMIN_OPERATIONS_ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso admin requer usuário com is_superuser=True ou token de emergência habilitado.",
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency admin token not configured.",
        )

    if not hmac.compare_digest(credentials.credentials, ADMIN_TOKEN):
        logger.warning("Invalid emergency admin token from %s", _get_client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

    logger.warning(
        "Admin access via EMERGENCY TOKEN from %s — migrate to JWT superuser ASAP.",
        _get_client_ip(request),
    )
    # Return a synthetic "admin user" sentinel when using emergency token
    return None


async def verify_admin_token(
    credentials: Optional[HTTPAuthorizationCredentials],
    request: Request,
) -> None:
    """Legacy emergency-token-only check (no DB). Used by tests and backwards-compat callers."""
    if not ADMIN_OPERATIONS_ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin operations are disabled",
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not ADMIN_TOKEN or not hmac.compare_digest(credentials.credentials, ADMIN_TOKEN):
        logger.warning("Invalid emergency admin token from %s", _get_client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

    logger.warning(
        "Admin access via EMERGENCY TOKEN from %s — migrate to JWT superuser ASAP.",
        _get_client_ip(request),
    )


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
    token=Depends(verify_admin_access),
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


@router.get("/tenant-by-email", summary="Admin: Get tenant info by user email")
async def get_tenant_by_email(
    email: str,
    request: Request,
    token=Depends(verify_admin_access),
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
