import asyncio
import sys
from sqlalchemy import select

# Add parent directory to path to allow importing app
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.deps import get_sessionmaker
from app.models.user import User, UserRole

async def main():
    print("Initializing session factory...")
    session_factory = get_sessionmaker()
    async with session_factory() as db:
        # Check if gisele already exists
        print("Checking if user contabil_gisele@outlook.com exists...")
        result = await db.execute(select(User).where(User.email == "contabil_gisele@outlook.com"))
        gisele = result.scalar_one_or_none()
        if gisele:
            print("User contabil_gisele@outlook.com already exists!")
            return

        # Find vsouz009@gmail.com
        print("Locating user vsouz009@gmail.com...")
        result = await db.execute(select(User).where(User.email == "vsouz009@gmail.com"))
        vsouz = result.scalar_one_or_none()
        if not vsouz:
            print("Error: User vsouz009@gmail.com not found. Cannot clone credentials.")
            return

        print(f"Found vsouz009@gmail.com (tenant_id: {vsouz.tenant_id}). Cloning credentials...")
        
        # Create Gisele's user with the same tenant_id, hashed_password, and role = OWNER
        new_user = User(
            tenant_id=vsouz.tenant_id,
            email="contabil_gisele@outlook.com",
            hashed_password=vsouz.hashed_password,
            full_name="Gisele Contadora",
            role=UserRole.OWNER,
            is_active=True
        )
        db.add(new_user)
        await db.commit()
        print("Successfully created user contabil_gisele@outlook.com with full access!")

if __name__ == "__main__":
    asyncio.run(main())
