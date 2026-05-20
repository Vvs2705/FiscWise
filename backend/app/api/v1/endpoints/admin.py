"""Admin endpoints for emergency database fixes."""

import os
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.deps import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Admin token from environment variable (CRITICAL SECURITY FIX)
ADMIN_TOKEN = os.getenv("ADMIN_EMERGENCY_TOKEN")
ADMIN_OPERATIONS_ALLOWED = os.getenv("ADMIN_OPERATIONS_ALLOWED", "false").lower() == "true"

# HTTP Bearer token scheme for Authorization header
security = HTTPBearer(auto_error=False)


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def verify_admin_token(
    credentials: Optional[HTTPAuthCredentials] = Depends(security),
    request: Request = None
) -> str:
    """
    Verify admin token from Authorization header with timing-safe comparison.

    Expected header: Authorization: Bearer <TOKEN>
    Uses hmac.compare_digest() to prevent timing attacks.

    Raises:
        HTTPException: 401 if token missing or invalid
        HTTPException: 403 if admin operations not enabled
    """
    # Check if admin operations are enabled
    if not ADMIN_OPERATIONS_ALLOWED:
        logger.error("Admin endpoint called but ADMIN_OPERATIONS_ALLOWED=false")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin operations are disabled"
        )

    # Check if token is provided in Authorization header
    if not credentials:
        client_ip = _get_client_ip(request) if request else "unknown"
        logger.warning(f"Admin endpoint called without Authorization header from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if ADMIN_TOKEN is configured
    if not ADMIN_TOKEN:
        logger.error("ADMIN_EMERGENCY_TOKEN environment variable not set")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin token not configured"
        )

    # Timing-safe token comparison (prevents timing attacks)
    provided_token = credentials.credentials
    is_valid = hmac.compare_digest(provided_token, ADMIN_TOKEN)

    if not is_valid:
        client_ip = _get_client_ip(request) if request else "unknown"
        logger.warning(
            f"Invalid admin token attempted from {client_ip}. "
            f"Token length: {len(provided_token)}, Expected length: {len(ADMIN_TOKEN)}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )

    return provided_token


@router.post("/fix-enum-case-raw", summary="Emergency: Fix enum case mismatch (RAW asyncpg)")
async def fix_enum_case_raw(
    request: Request,
    token: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Emergency endpoint using raw asyncpg connection to fix enum case mismatch.

    This bypasses SQLAlchemy's type system entirely, using asyncpg's raw execute().
    This should work even when SQLAlchemy's text() triggers enum errors.

    Requires: Authorization: Bearer <ADMIN_EMERGENCY_TOKEN> header
    """
    client_ip = _get_client_ip(request)

    try:
        # Get the raw asyncpg connection
        async_conn = await db.connection()
        raw_conn = async_conn.connection

        logger.info(f"[ADMIN] Raw asyncpg enum fix started from {client_ip}")

        # Execute raw SQL without SQLAlchemy's type handling
        # CRITICAL: Use explicit transaction to prevent partial updates
        sql_statements = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS _role_tmp VARCHAR(50)",
            "UPDATE users SET _role_tmp = LOWER(role::text) WHERE _role_tmp IS NULL",
            "ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_tenant_email",
            "ALTER TABLE users DROP COLUMN IF EXISTS role",
            "DROP TYPE IF EXISTS user_role_enum CASCADE",
            "CREATE TYPE user_role_enum AS ENUM ('owner', 'admin', 'member')",
            "ALTER TABLE users ADD COLUMN role user_role_enum NOT NULL DEFAULT 'member'::user_role_enum",
            "UPDATE users SET role = _role_tmp::user_role_enum",
            "ALTER TABLE users DROP COLUMN IF EXISTS _role_tmp",
            "CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)",
            "ALTER TABLE users ADD CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email)",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS _sub_tmp VARCHAR(50)",
            "UPDATE tenants SET _sub_tmp = LOWER(subscription_status::text) WHERE _sub_tmp IS NULL",
            "ALTER TABLE tenants DROP COLUMN IF EXISTS subscription_status",
            "DROP TYPE IF EXISTS subscription_status_enum CASCADE",
            "CREATE TYPE subscription_status_enum AS ENUM ('trial', 'active', 'suspended', 'cancelled', 'expired')",
            "ALTER TABLE tenants ADD COLUMN subscription_status subscription_status_enum NOT NULL DEFAULT 'trial'::subscription_status_enum",
            "UPDATE tenants SET subscription_status = _sub_tmp::subscription_status_enum",
            "ALTER TABLE tenants DROP COLUMN IF EXISTS _sub_tmp",
            "CREATE INDEX IF NOT EXISTS ix_tenants_subscription_status ON tenants(subscription_status)",
        ]

        # Execute all statements within a transaction
        async with raw_conn.transaction():
            for stmt in sql_statements:
                logger.debug(f"[ADMIN] Executing: {stmt[:80]}")
                await raw_conn.execute(stmt)

        logger.info(
            f"[ADMIN] ✅ Enum fix completed successfully from {client_ip} - "
            f"{len(sql_statements)} statements executed"
        )

        return {
            "status": "fixed",
            "message": "Enum case mismatch fixed successfully using raw asyncpg",
            "enums_fixed": ["user_role_enum", "subscription_status_enum"],
            "statements_executed": len(sql_statements)
        }

    except Exception as e:
        logger.error(
            f"[ADMIN] ❌ Raw asyncpg fix FAILED from {client_ip}: {str(e)}",
            exc_info=True
        )
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }


@router.post("/fix-enum-case", summary="Emergency: Fix enum case mismatch")
async def fix_enum_case(
    request: Request,
    token: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Emergency endpoint to fix enum case mismatch.

    This is a workaround for when Alembic migrations fail to run.
    Applies the enum case conversion directly via SQL.

    Requires: Authorization: Bearer <ADMIN_EMERGENCY_TOKEN> header
    """
    client_ip = _get_client_ip(request)

    try:
        logger.info(f"[ADMIN] Enum fix started from {client_ip}")

        # Apply fixes within a transaction for atomicity
        await db.execute(text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS _role_tmp VARCHAR(50);
        """))

        await db.execute(text("""
            UPDATE users SET _role_tmp = LOWER(role::text) WHERE _role_tmp IS NULL;
        """))

        await db.execute(text("""
            ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_tenant_email;
        """))

        await db.execute(text("""
            ALTER TABLE users DROP COLUMN IF EXISTS role;
        """))

        await db.execute(text("""
            DROP TYPE IF EXISTS user_role_enum CASCADE;
        """))

        await db.execute(text("""
            CREATE TYPE user_role_enum AS ENUM ('owner', 'admin', 'member');
        """))

        await db.execute(text("""
            ALTER TABLE users ADD COLUMN role user_role_enum NOT NULL DEFAULT 'member'::user_role_enum;
        """))

        await db.execute(text("""
            UPDATE users SET role = _role_tmp::user_role_enum;
        """))

        await db.execute(text("""
            ALTER TABLE users DROP COLUMN IF EXISTS _role_tmp;
        """))

        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);
        """))

        await db.execute(text("""
            ALTER TABLE users ADD CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email);
        """))

        # Fix subscription_status_enum: convert UPPERCASE to lowercase
        await db.execute(text("""
            ALTER TABLE tenants ADD COLUMN IF NOT EXISTS _sub_tmp VARCHAR(50);
        """))

        await db.execute(text("""
            UPDATE tenants SET _sub_tmp = LOWER(subscription_status::text) WHERE _sub_tmp IS NULL;
        """))

        await db.execute(text("""
            ALTER TABLE tenants DROP COLUMN IF EXISTS subscription_status;
        """))

        await db.execute(text("""
            DROP TYPE IF EXISTS subscription_status_enum CASCADE;
        """))

        await db.execute(text("""
            CREATE TYPE subscription_status_enum AS ENUM ('trial', 'active', 'suspended', 'cancelled', 'expired');
        """))

        await db.execute(text("""
            ALTER TABLE tenants ADD COLUMN subscription_status subscription_status_enum NOT NULL DEFAULT 'trial'::subscription_status_enum;
        """))

        await db.execute(text("""
            UPDATE tenants SET subscription_status = _sub_tmp::subscription_status_enum;
        """))

        await db.execute(text("""
            ALTER TABLE tenants DROP COLUMN IF EXISTS _sub_tmp;
        """))

        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_tenants_subscription_status ON tenants(subscription_status);
        """))

        await db.commit()

        logger.info(f"[ADMIN] ✅ Enum fix completed successfully from {client_ip}")

        return {
            "status": "fixed",
            "message": "Enum case mismatch fixed successfully - enums converted to lowercase",
            "enums_fixed": ["user_role_enum", "subscription_status_enum"]
        }

    except Exception as e:
        await db.rollback()
        logger.error(
            f"[ADMIN] ❌ Enum fix FAILED from {client_ip}: {str(e)}",
            exc_info=True
        )
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
            "hint": "Check that database connection is valid and user has ALTER TABLE permissions"
        }
