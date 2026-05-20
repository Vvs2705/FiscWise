"""Admin endpoints for emergency database fixes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.core.deps import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Admin token for emergency fixes (should be env var in production)
ADMIN_TOKEN = "emergency-enum-fix-token-change-in-production"


async def verify_admin_token(token: str) -> bool:
    """Verify admin token for emergency operations."""
    return token == ADMIN_TOKEN


@router.post("/fix-enum-case-raw", summary="Emergency: Fix enum case mismatch (RAW asyncpg)")
async def fix_enum_case_raw(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Emergency endpoint using raw asyncpg connection to fix enum case mismatch.

    This bypasses SQLAlchemy's type system entirely, using asyncpg's raw execute().
    This should work even when SQLAlchemy's text() triggers enum errors.
    """
    if not await verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )

    try:
        # Get the raw asyncpg connection
        async_conn = await db.connection()
        raw_conn = async_conn.connection

        logger.info("Using raw asyncpg connection to fix enums")

        # Execute raw SQL without SQLAlchemy's type handling
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

        for stmt in sql_statements:
            logger.info(f"Executing: {stmt[:80]}")
            await raw_conn.execute(stmt)

        logger.info("✅ All enum fixes applied successfully")

        return {
            "status": "fixed",
            "message": "Enum case mismatch fixed successfully using raw asyncpg",
            "enums_fixed": ["user_role_enum", "subscription_status_enum"],
            "statements_executed": len(sql_statements)
        }

    except Exception as e:
        logger.error(f"❌ Raw asyncpg fix failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }


@router.post("/fix-enum-case", summary="Emergency: Fix enum case mismatch")
async def fix_enum_case(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Emergency endpoint to fix enum case mismatch.

    This is a workaround for when Alembic migrations fail to run.
    Applies the enum case conversion directly via SQL.

    Requires admin token.
    """

    if not await verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )

    try:
        # Apply fixes directly without checking - the check itself triggers enum errors
        # Fix user_role_enum: convert UPPERCASE to lowercase
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

        return {
            "status": "fixed",
            "message": "Enum case mismatch fixed successfully - enums converted to lowercase",
            "enums_fixed": ["user_role_enum", "subscription_status_enum"]
        }

    except Exception as e:
        await db.rollback()
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
            "hint": "Check that database connection is valid and user has ALTER TABLE permissions"
        }
