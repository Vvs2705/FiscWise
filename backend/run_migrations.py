#!/usr/bin/env python
"""Run Alembic migrations with proper error handling for asyncpg."""

import sys
import logging
from alembic import command
from alembic.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run Alembic migrations."""
    try:
        logger.info("Starting database migrations with enum case fix...")
        alembic_cfg = Config("alembic.ini")

        # Run migrations with verbose output
        logger.info("Connecting to database...")
        logger.info("Running: alembic upgrade head")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migrations completed successfully!")
        return True
    except Exception as e:
        logger.error("❌ Migration failed with error:", exc_info=True)
        logger.error("Error type: %s", type(e).__name__)
        logger.error("Error message: %s", str(e))

        # Try to give more context
        if "enum" in str(e).lower():
            logger.error("   → Enum-related error detected. Check if enums need case conversion.")
        if "already exists" in str(e).lower():
            logger.error("   → Schema object already exists. Check migration history.")
        if "no such table" in str(e).lower():
            logger.error("   → Table not found. Check database connectivity.")

        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
