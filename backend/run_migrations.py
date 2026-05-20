#!/usr/bin/env python
"""
Run Alembic migrations with a synchronous psycopg preflight enum fix.

Order of operations:
  1. fix_enums_startup.fix_enums()  — psycopg3 sync, no asyncpg type-cache issues
  2. alembic upgrade head            — standard Alembic migration
"""

import sys
import logging
import os

from alembic import command
from alembic.config import Config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_migrations() -> bool:
    """Run Alembic upgrade head."""
    try:
        logger.info("Running database migrations...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully.")
        return True

    except Exception as exc:
        logger.error("Migration failed: %s", exc, exc_info=True)

        msg = str(exc).lower()
        if "enum" in msg or "'<'" in msg:
            logger.error(
                "Enum-related error detected. "
                "The preflight fix may not have run or the enum still has old values. "
                "Check DATABASE_URL is set and psycopg[binary] is installed."
            )
        elif "already exists" in msg:
            logger.error("Schema object already exists — check migration history.")
        elif "no such table" in msg or "relation" in msg:
            logger.error("Table not found — check database connectivity.")

        return False


if __name__ == "__main__":
    # Step 1: Alembic migrations only
    # Note: Preflight enum fix disabled for now (removed psycopg[binary] complexity)
    # If enum mismatch occurs, use POST /api/v1/admin/fix-enum-case endpoint
    logger.info("Running database migrations (enum preflight fix disabled)...")
    success = run_migrations()
    sys.exit(0 if success else 1)
