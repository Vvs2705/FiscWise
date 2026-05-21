#!/usr/bin/env python
"""
Run Alembic migrations.

CRITICAL: If enum mismatch causes failures, use POST /api/v1/admin/fix-enum-case
to manually fix PostgreSQL enum types post-deployment.
"""

import sys
import logging
import os
from alembic import command
from alembic.config import Config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        logger.info("Running database migrations (Alembic)...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migrations completed successfully.")
        sys.exit(0)
    except Exception as exc:
        logger.error("❌ Migration failed: %s", exc, exc_info=True)
        msg = str(exc).lower()
        if "enum" in msg or "uppercase" in msg or "'<'" in msg:
            logger.error(
                "Enum case mismatch detected. "
                "Use POST /api/v1/admin/fix-enum-case endpoint to fix."
            )
        sys.exit(1)
