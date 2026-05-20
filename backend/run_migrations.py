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
    database_url = os.getenv("DATABASE_URL", "")

    # Step 1: Preflight enum fix (psycopg3 sync — avoids asyncpg type-cache issues)
    if database_url:
        from fix_enums_startup import fix_enums
        logger.info("Running database migrations (with enum preflight fix)...")
        enum_ok = fix_enums(database_url)
        if not enum_ok:
            logger.error(
                "Preflight enum fix failed. Aborting to prevent partial DB state. "
                "Check: (1) DATABASE_URL is valid and accessible, "
                "(2) psycopg[binary] is installed, (3) network/firewall allows connection"
            )
            sys.exit(1)
    else:
        logger.warning("DATABASE_URL not set — skipping preflight enum fix.")

    # Step 2: Alembic migrations
    success = run_migrations()
    sys.exit(0 if success else 1)
