#!/usr/bin/env python3
"""Check migration status and apply enum fix if needed."""

import asyncio
import os
import sys
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

async def check_enum_status():
    """Check if enums are uppercase or lowercase."""
    try:
        import asyncpg
        from dotenv import load_dotenv

        # Load env vars
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)

        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not found")
            return

        # Sanitize URL
        parsed = urlparse(db_url)
        if parsed.scheme == "postgres":
            parsed = parsed._replace(scheme="postgresql+asyncpg")

        params = parse_qs(parsed.query, keep_blank_values=True)
        if "sslmode" in params:
            del params["sslmode"]
        params["ssl"] = ["require"]

        new_query = urlencode(params, doseq=True)
        db_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

        conn = await asyncpg.connect(db_url)

        # Check user_role_enum values
        result = await conn.fetch("""
            SELECT enumlabel FROM pg_enum
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role_enum')
            ORDER BY enumsortorder;
        """)

        if not result:
            print("⚠️  user_role_enum not found in database")
            await conn.close()
            return

        enum_values = [r['enumlabel'] for r in result]
        print(f"Found user_role_enum values: {enum_values}")

        if enum_values == ['owner', 'admin', 'member']:
            print("✅ Enum is already lowercase (migration applied)")
        elif enum_values == ['OWNER', 'ADMIN', 'MEMBER']:
            print("❌ Enum is still UPPERCASE (migration NOT applied)")
            print("   Need to run: alembic upgrade head")
        else:
            print(f"⚠️  Unexpected enum values: {enum_values}")

        # Check migration table
        migrations = await conn.fetch("""
            SELECT version FROM alembic_version ORDER BY version;
        """)

        print(f"\nApplied migrations:")
        for m in migrations:
            print(f"  - {m['version']}")

        await conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_enum_status())
