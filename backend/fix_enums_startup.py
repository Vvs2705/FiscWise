#!/usr/bin/env python
"""
Fix PostgreSQL enum case mismatch before app startup.

This script runs BEFORE SQLAlchemy models are loaded, using raw asyncpg
to execute enum fixes without triggering type system errors.

Usage: python fix_enums_startup.py <DATABASE_URL>
"""

import asyncio
import sys
import logging
import asyncpg
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sanitize_database_url(url: str) -> str:
    """Convert DATABASE_URL to raw asyncpg format (without sslmode)."""
    parsed = urlparse(url)

    if parsed.scheme == "postgres":
        parsed = parsed._replace(scheme="postgresql")

    params = parse_qs(parsed.query, keep_blank_values=True)

    # Remove sslmode (asyncpg will use ssl=require)
    if "sslmode" in params:
        del params["sslmode"]

    params["ssl"] = ["require"]

    new_query = urlencode(params, doseq=True)

    fixed_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

    return fixed_url


async def fix_enums(database_url: str) -> bool:
    """Connect and fix enum case mismatch."""
    try:
        # Sanitize the URL
        db_url = sanitize_database_url(database_url)
        logger.info(f"Connecting to database: {db_url[:60]}...")

        # Connect with raw asyncpg
        conn = await asyncpg.connect(db_url)

        try:
            # Test connection
            result = await conn.fetchval("SELECT 1")
            logger.info(f"✅ Database connected: {result}")

            # List of SQL statements to fix enums
            statements = [
                # Fix user_role_enum
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS _role_tmp VARCHAR(50)",
                "UPDATE users SET _role_tmp = LOWER(role::text) WHERE _role_tmp IS NULL",
                "ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_tenant_email",
                "ALTER TABLE users DROP COLUMN IF EXISTS role",
                "DROP TYPE IF EXISTS user_role_enum CASCADE",
                "CREATE TYPE user_role_enum AS ENUM ('owner', 'admin', 'member')",
                "ALTER TABLE users ADD COLUMN role user_role_enum NOT NULL DEFAULT 'member'::user_role_enum",
                "UPDATE users SET role = _role_tmp::user_role_enum",
                "ALTER TABLE users DROP COLUMN IF EXISTS _role_tmp",
                "CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)",
                "ALTER TABLE users ADD CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email)",

                # Fix subscription_status_enum
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS _sub_tmp VARCHAR(50)",
                "UPDATE tenants SET _sub_tmp = LOWER(subscription_status::text) WHERE _sub_tmp IS NULL",
                "ALTER TABLE tenants DROP COLUMN IF EXISTS subscription_status",
                "DROP TYPE IF EXISTS subscription_status_enum CASCADE",
                "CREATE TYPE subscription_status_enum AS ENUM ('trial', 'active', 'suspended', 'cancelled', 'expired')",
                "ALTER TABLE tenants ADD COLUMN subscription_status subscription_status_enum NOT NULL DEFAULT 'trial'::subscription_status_enum",
                "UPDATE tenants SET subscription_status = _sub_tmp::subscription_status_enum",
                "ALTER TABLE tenants DROP COLUMN IF EXISTS _sub_tmp",
                "CREATE INDEX IF NOT EXISTS ix_tenants_subscription_status ON tenants(subscription_status)",
            ]

            for i, stmt in enumerate(statements, 1):
                try:
                    logger.info(f"[{i}/{len(statements)}] Executing: {stmt[:70]}...")
                    await conn.execute(stmt)
                except Exception as e:
                    if "already exists" in str(e) or "does not exist" in str(e):
                        logger.info(f"  → Skipped (already fixed): {str(e)[:60]}")
                    else:
                        logger.error(f"  ❌ FAILED: {str(e)}")
                        raise

            logger.info("✅ All enum fixes applied successfully!")
            return True

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ Enum fix failed: {str(e)}", exc_info=True)
        return False


async def main():
    """Entry point."""
    if len(sys.argv) < 2:
        logger.error("Usage: python fix_enums_startup.py <DATABASE_URL>")
        sys.exit(1)

    database_url = sys.argv[1]

    success = await fix_enums(database_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
