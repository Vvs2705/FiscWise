#!/usr/bin/env python
"""
Fix PostgreSQL enum case mismatch using psycopg (sync, no type-cache issues).

psycopg3 does NOT cache PostgreSQL types the way asyncpg does, so it safely
executes DDL that recreates enum types without the
"'<' not supported between instances of 'str' and 'int'" error.

Strategy:
  - Each DDL statement runs in its own transaction (autocommit=True).
  - Errors that mean "already done or not applicable" are silently skipped.
  - Only unexpected errors abort the fix.
  - Tables/enums are checked first; if they don't exist we skip cleanly.

This script runs BEFORE SQLAlchemy / Alembic so no model is imported.

Usage: python fix_enums_startup.py [DATABASE_URL]
       DATABASE_URL env var is also accepted.
"""

import sys
import logging
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _sanitize_url_for_logging(database_url: str) -> str:
    """Return URL with password redacted for safe logging."""
    parsed = urlparse(database_url)
    if parsed.password:
        safe_netloc = f"{parsed.username}:***@{parsed.hostname}"
        if parsed.port:
            safe_netloc += f":{parsed.port}"
        parsed = parsed._replace(netloc=safe_netloc)
    return urlunparse(parsed)

# Substrings in an error message that mean "this step is already done or
# not needed" — we log a warning and continue.
_BENIGN_ERROR_PATTERNS = (
    "already exists",
    "does not exist",
    "undefined column",
    "no such column",
)


def _build_dsn(database_url: str) -> str:
    """
    Normalise DATABASE_URL for psycopg3.

    - postgres:// -> postgresql://
    - ?ssl=require (asyncpg style) -> ?sslmode=require (libpq style)
    """
    parsed = urlparse(database_url)
    scheme = "postgresql" if parsed.scheme == "postgres" else parsed.scheme

    params = parse_qs(parsed.query, keep_blank_values=True)

    # asyncpg-style ?ssl=require -> libpq-style ?sslmode=require
    if "ssl" in params:
        ssl_val = params.pop("ssl")[0]
        if ssl_val in ("require", "true", "1"):
            params.setdefault("sslmode", ["require"])

    new_query = urlencode(params, doseq=True)
    return urlunparse((scheme, parsed.netloc, parsed.path,
                       parsed.params, new_query, parsed.fragment))


def _exec(cur, stmt: str, label: str) -> bool:
    """
    Execute one DDL statement.  Returns True on success or benign skip,
    False on a real error that should abort the fix.
    """
    try:
        cur.execute(stmt)
        return True
    except Exception as exc:
        msg = str(exc).lower()
        if any(p in msg for p in _BENIGN_ERROR_PATTERNS):
            logger.info("  -> skipped (already done / not applicable): %s", str(exc)[:120])
            return True
        logger.error("  -> FATAL on [%s]: %s", label, exc)
        return False


def _check_tables(conn) -> tuple[bool, bool]:
    """Return (users_exists, tenants_exists)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                EXISTS(SELECT 1 FROM information_schema.tables
                       WHERE table_schema='public' AND table_name='users'),
                EXISTS(SELECT 1 FROM information_schema.tables
                       WHERE table_schema='public' AND table_name='tenants')
            """
        )
        row = cur.fetchone()
    return bool(row[0]), bool(row[1])


def _enum_has_uppercase(conn, enum_name: str) -> bool:
    """Return True if the enum exists and has any uppercase label."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT enumlabel
            FROM pg_enum e
            JOIN pg_type t ON t.oid = e.enumtypid
            WHERE t.typname = %s
            ORDER BY e.enumsortorder
            """,
            (enum_name,),
        )
        rows = cur.fetchall()

    if not rows:
        return False  # doesn't exist — Alembic will create it correctly
    return any(r[0] != r[0].lower() for r in rows)


def fix_enums(database_url: str) -> bool:
    """
    Connect and fix enum case.  Returns True on success (or no-op),
    False only on hard failures.
    """
    try:
        import psycopg  # psycopg3 sync
    except ImportError:
        logger.error(
            "psycopg[binary] not installed. "
            "Add 'psycopg[binary]>=3.2' to requirements.txt."
        )
        return False

    dsn = _build_dsn(database_url)
    safe_dsn = _sanitize_url_for_logging(dsn)
    logger.info(f"Connecting for enum preflight check: {safe_dsn}...")

    try:
        # autocommit=True so each statement is its own transaction;
        # DDL errors don't leave a broken transaction block.
        with psycopg.connect(dsn, autocommit=True) as conn:
            # Connectivity check
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                assert cur.fetchone()[0] == 1
            logger.info("Connected to PostgreSQL.")

            users_exist, tenants_exist = _check_tables(conn)

            if not users_exist and not tenants_exist:
                logger.info("Tables absent (first deploy) — skipping enum fix.")
                return True

            role_fix = users_exist and _enum_has_uppercase(conn, "user_role_enum")
            sub_fix = tenants_exist and _enum_has_uppercase(conn, "subscription_status_enum")

            if not role_fix and not sub_fix:
                logger.info("Enums already have lowercase values — no fix needed.")
                return True

            logger.info(
                "Will fix: user_role_enum=%s  subscription_status_enum=%s",
                role_fix, sub_fix,
            )

            with conn.cursor() as cur:

                # ---------------------------------------------- users table
                if role_fix:
                    logger.info("--- Fixing user_role_enum ---")
                    steps = [
                        ("save-role",
                         "ALTER TABLE users ADD COLUMN IF NOT EXISTS _role_tmp VARCHAR(50)"),
                        ("copy-role",
                         "UPDATE users SET _role_tmp = LOWER(role::text) "
                         "WHERE _role_tmp IS NULL OR _role_tmp = ''"),
                        ("drop-uq",
                         "ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_tenant_email"),
                        ("drop-role-col",
                         "ALTER TABLE users DROP COLUMN IF EXISTS role"),
                        ("drop-role-type",
                         "DROP TYPE IF EXISTS user_role_enum CASCADE"),
                        ("create-role-type",
                         "CREATE TYPE user_role_enum AS ENUM ('owner', 'admin', 'member')"),
                        ("add-role-col",
                         "ALTER TABLE users ADD COLUMN role user_role_enum "
                         "NOT NULL DEFAULT 'member'::user_role_enum"),
                        ("restore-role",
                         "UPDATE users SET role = _role_tmp::user_role_enum "
                         "WHERE _role_tmp IS NOT NULL"),
                        ("drop-tmp-role",
                         "ALTER TABLE users DROP COLUMN IF EXISTS _role_tmp"),
                        ("idx-role",
                         "CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)"),
                        ("uq-tenant-email",
                         "ALTER TABLE users ADD CONSTRAINT uq_users_tenant_email "
                         "UNIQUE (tenant_id, email)"),
                    ]
                    for label, stmt in steps:
                        logger.info("[users/%s] %s", label, stmt[:80])
                        if not _exec(cur, stmt, label):
                            return False

                # ------------------------------------------- tenants table
                if sub_fix:
                    logger.info("--- Fixing subscription_status_enum ---")
                    steps = [
                        ("save-sub",
                         "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS _sub_tmp VARCHAR(50)"),
                        ("copy-sub",
                         "UPDATE tenants SET _sub_tmp = LOWER(subscription_status::text) "
                         "WHERE _sub_tmp IS NULL OR _sub_tmp = ''"),
                        ("drop-sub-col",
                         "ALTER TABLE tenants DROP COLUMN IF EXISTS subscription_status"),
                        ("drop-sub-type",
                         "DROP TYPE IF EXISTS subscription_status_enum CASCADE"),
                        ("create-sub-type",
                         "CREATE TYPE subscription_status_enum AS ENUM "
                         "('trial', 'active', 'suspended', 'cancelled', 'expired')"),
                        ("add-sub-col",
                         "ALTER TABLE tenants ADD COLUMN subscription_status "
                         "subscription_status_enum NOT NULL DEFAULT 'trial'::subscription_status_enum"),
                        ("restore-sub",
                         "UPDATE tenants SET subscription_status = _sub_tmp::subscription_status_enum "
                         "WHERE _sub_tmp IS NOT NULL"),
                        ("drop-tmp-sub",
                         "ALTER TABLE tenants DROP COLUMN IF EXISTS _sub_tmp"),
                        ("idx-sub",
                         "CREATE INDEX IF NOT EXISTS ix_tenants_subscription_status "
                         "ON tenants(subscription_status)"),
                    ]
                    for label, stmt in steps:
                        logger.info("[tenants/%s] %s", label, stmt[:80])
                        if not _exec(cur, stmt, label):
                            return False

        logger.info("Enum fix completed successfully.")
        return True

    except Exception as exc:
        logger.error("Enum fix connection failed: %s", exc, exc_info=True)
        return False


def main() -> None:
    """CLI entry point."""
    database_url = (sys.argv[1] if len(sys.argv) > 1
                    else os.getenv("DATABASE_URL", ""))
    if not database_url:
        logger.error("Usage: python fix_enums_startup.py <DATABASE_URL>")
        sys.exit(1)

    success = fix_enums(database_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
