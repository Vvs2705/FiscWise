"""Admin endpoints for emergency database fixes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.deps import get_db

router = APIRouter()

# Admin token for emergency fixes (should be env var in production)
ADMIN_TOKEN = "emergency-enum-fix-token-change-in-production"


async def verify_admin_token(token: str) -> bool:
    """Verify admin token for emergency operations."""
    return token == ADMIN_TOKEN


@router.post("/admin/fix-enum-case", summary="Emergency: Fix enum case mismatch")
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
        conn = await db.connection()

        # Step 1: Check if already fixed
        result = await db.execute(text("""
            SELECT enumlabel FROM pg_enum
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role_enum')
            LIMIT 1
        """))
        row = result.first()

        if row and row[0] == 'owner':
            return {
                "status": "already_fixed",
                "message": "Enums are already lowercase"
            }

        # Step 2: Apply fixes

        # Fix user_role_enum
        await db.execute(text("""
            ALTER TABLE users ADD COLUMN _role_tmp VARCHAR(50);
            UPDATE users SET _role_tmp = LOWER(role::text);
            ALTER TABLE users ALTER COLUMN _role_tmp SET NOT NULL;
            ALTER TABLE users DROP COLUMN role;
            DROP TYPE user_role_enum;
            CREATE TYPE user_role_enum AS ENUM ('owner', 'admin', 'member');
            ALTER TABLE users ADD COLUMN role user_role_enum NOT NULL DEFAULT 'member'::user_role_enum;
            UPDATE users SET role = _role_tmp::user_role_enum;
            ALTER TABLE users DROP COLUMN _role_tmp;
            CREATE INDEX ix_users_role ON users(role);
        """))

        # Fix subscription_status_enum
        await db.execute(text("""
            ALTER TABLE tenants ADD COLUMN _sub_tmp VARCHAR(50);
            UPDATE tenants SET _sub_tmp = LOWER(subscription_status::text);
            ALTER TABLE tenants ALTER COLUMN _sub_tmp SET NOT NULL;
            ALTER TABLE tenants DROP COLUMN subscription_status;
            DROP TYPE subscription_status_enum;
            CREATE TYPE subscription_status_enum AS ENUM ('trial', 'active', 'suspended', 'cancelled', 'expired');
            ALTER TABLE tenants ADD COLUMN subscription_status subscription_status_enum NOT NULL DEFAULT 'trial'::subscription_status_enum;
            UPDATE tenants SET subscription_status = _sub_tmp::subscription_status_enum;
            ALTER TABLE tenants DROP COLUMN _sub_tmp;
            CREATE INDEX ix_tenants_subscription_status ON tenants(subscription_status);
        """))

        await db.commit()

        return {
            "status": "fixed",
            "message": "Enum case mismatch fixed successfully",
            "enums_fixed": ["user_role_enum", "subscription_status_enum"]
        }

    except Exception as e:
        await db.rollback()
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }
