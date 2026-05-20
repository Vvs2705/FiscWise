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
        logger.info("Starting database migrations...")
        alembic_cfg = Config("alembic.ini")

        # Run migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migrations completed successfully!")
        return True
    except Exception as e:
        logger.error("❌ Migration failed: %s", str(e), exc_info=True)
        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
