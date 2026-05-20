"""Diagnostic endpoints for debugging migration and database issues."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.deps import get_db

router = APIRouter()


@router.get("/enums", summary="Check enum status in database")
async def check_enums(db: AsyncSession = Depends(get_db)):
    """Check if enums are uppercase or lowercase in the database."""
    try:
        # Check user_role_enum
        result = await db.execute(text("""
            SELECT enumlabel FROM pg_enum
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role_enum')
            ORDER BY enumsortorder;
        """))
        role_enums = [row[0] for row in result.fetchall()]

        # Check subscription_status_enum
        result = await db.execute(text("""
            SELECT enumlabel FROM pg_enum
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subscription_status_enum')
            ORDER BY enumsortorder;
        """))
        status_enums = [row[0] for row in result.fetchall()]

        # Check migration status
        result = await db.execute(text("""
            SELECT version FROM alembic_version ORDER BY version;
        """))
        applied_migrations = [row[0] for row in result.fetchall()]

        return {
            "status": "ok",
            "user_role_enum": {
                "values": role_enums,
                "is_lowercase": role_enums == ['owner', 'admin', 'member'],
                "needs_migration": role_enums != ['owner', 'admin', 'member']
            },
            "subscription_status_enum": {
                "values": status_enums,
                "is_lowercase": status_enums == ['trial', 'active', 'suspended', 'cancelled', 'expired'],
                "needs_migration": status_enums != ['trial', 'active', 'suspended', 'cancelled', 'expired']
            },
            "applied_migrations": applied_migrations,
            "migration_fix_applied": "20260520_fix_enum_case" in applied_migrations,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "message": "Failed to check enums - database may not be initialized"
        }


@router.get("/health-detailed", summary="Detailed health check")
async def health_detailed(db: AsyncSession = Depends(get_db)):
    """Return detailed health status."""
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
            "message": "All systems operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
