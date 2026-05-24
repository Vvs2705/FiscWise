#!/usr/bin/env python
"""
Run Alembic migrations.
"""

import sys
import logging
import os
from alembic import command
from alembic.config import Config

# Use print() for critical startup messages — fileConfig in alembic/env.py
# resets the logging configuration, which can swallow logger output to stdout.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        print("INFO Running database migrations (Alembic)...", flush=True)
        print(f"INFO Current working directory: {os.getcwd()}", flush=True)
        print(f"INFO alembic.ini exists: {os.path.exists('alembic.ini')}", flush=True)

        alembic_cfg = Config("alembic.ini")

        command.upgrade(alembic_cfg, "head")
        print("INFO Migrations completed successfully.", flush=True)
        sys.exit(0)
    except Exception as exc:
        print(f"ERROR Migration failed: {type(exc).__name__}: {exc}", flush=True)
        import traceback
        traceback.print_exc()
        msg = str(exc).lower()
        if "enum" in msg or "uppercase" in msg or "'<'" in msg:
            print(
                "ERROR Enum case mismatch detected. "
                "Check Alembic migration history and run the enum-case migration path.",
                flush=True,
            )
        sys.exit(1)
