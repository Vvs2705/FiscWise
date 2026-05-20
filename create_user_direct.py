#!/usr/bin/env python3
"""
Create user directly in database using asyncpg.
Workaround for enum migration issue on Fly.io.
"""
import asyncio
import os
import uuid
import sys
from datetime import datetime
from getpass import getpass

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

async def create_user():
    """Create user directly in database."""
    import asyncpg
    from app.core.security import get_password_hash
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found. Check .env file")
        return

    # Sanitize DATABASE_URL for asyncpg
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://")
    if "?sslmode=" in db_url:
        db_url = db_url.split("?sslmode=")[0]

    print(f"📍 Database: {db_url.split('@')[1] if '@' in db_url else 'hidden'}")

    try:
        conn = await asyncpg.connect(db_url)
        print("✓ Connected to database")

        # Create tenant
        tenant_id = str(uuid.uuid4())
        company_name = "ContaFlow Test"
        subscription_status = "trial"  # lowercase after migration

        await conn.execute("""
            INSERT INTO tenants (id, name, subscription_status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5)
        """, tenant_id, company_name, subscription_status, datetime.utcnow(), datetime.utcnow())
        print(f"✓ Tenant created: {tenant_id}")

        # Create user
        user_id = str(uuid.uuid4())
        email = "vsouz009@gmail.com"
        password = "Pq267@gtr417#"
        full_name = "Vinicius Souza"
        role = "owner"  # lowercase after migration
        hashed_password = get_password_hash(password)

        await conn.execute("""
            INSERT INTO users (id, tenant_id, email, hashed_password, full_name, role, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, user_id, tenant_id, email, hashed_password, full_name, role, True, datetime.utcnow(), datetime.utcnow())
        print(f"✓ User created: {email}")

        print("\n✅ User created successfully!")
        print(f"  Tenant ID: {tenant_id}")
        print(f"  User ID: {user_id}")
        print(f"  Email: {email}")
        print(f"  Password: {password}")

        await conn.close()

    except asyncpg.PostgresError as e:
        print(f"❌ Database error: {e}")
        print(f"   This likely means the enum migration hasn't run yet.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_user())
