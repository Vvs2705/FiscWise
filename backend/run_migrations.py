#!/usr/bin/env python
"""Run Alembic migrations with proper error handling for asyncpg.

Pre-flight enum case fix to prevent migration failures due to
UPPERCASE/lowercase enum value mismatches.
"""

import sys
import logging
import os
import asyncio
from alembic import command
from alembic.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def try_fix_enums_preflight():
    """Try to fix enum case before migrations run.

    This prevents Alembic from failing on enum comparisons.
    Runs only if DATABASE_URL is available.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.info("DATABASE_URL not available - skipping preflight enum fix")
        return True

    try:
        # Import and run the startup fix script
        from fix_enums_startup import fix_enums
        logger.info("🔧 Running preflight enum case fix...")
        success = await fix_enums(database_url)
        if success:
            logger.info("✅ Preflight enum fix completed")
            return True
        else:
            logger.warning("⚠️  Preflight enum fix failed - continuing anyway")
            return True  # Don't fail - Alembic migration might still work
    except Exception as e:
        logger.warning(f"⚠️  Preflight enum fix exception (continuing): {str(e)}")
        return True  # Don't fail the whole startup


def run_migrations():
    """Run Alembic migrations."""
    try:
        logger.info("Starting database migrations with enum case fix...")

        # Step 1: Try preflight enum fix (async)
        try:
            asyncio.run(try_fix_enums_preflight())
        except Exception as e:
            logger.warning(f"Preflight fix failed, continuing: {e}")

        # Step 2: Run Alembic migrations
        alembic_cfg = Config("alembic.ini")

        logger.info("Connecting to database...")
        logger.info("Running: alembic upgrade head")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migrations completed successfully!")
        return True

    except Exception as e:
        logger.error("❌ Migration failed with error:", exc_info=True)
        logger.error("Error type: %s", type(e).__name__)
        logger.error("Error message: %s", str(e))

        if "enum" in str(e).lower():
            logger.error("   → Enum-related error detected. Try manual fix: POST /api/v1/admin/fix-enum-case-raw")
        if "already exists" in str(e).lower():
            logger.error("   → Schema object already exists. Check migration history.")
        if "no such table" in str(e).lower():
            logger.error("   → Table not found. Check database connectivity.")

        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
