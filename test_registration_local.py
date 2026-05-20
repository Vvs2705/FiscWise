#!/usr/bin/env python3
"""
Local test script para debug do endpoint de registro.
Simula a request de registro sem precisar do HTTP.
"""
import asyncio
import os
import uuid
from datetime import datetime

# Mock a criação da tenandencia sem dependência de HTTP
async def test_tenant_registration():
    """Test tenant registration logic locally."""

    # Imports
    from app.models.tenant import Tenant, SubscriptionStatus
    from app.models.user import User, UserRole
    from app.core.security import get_password_hash

    print("✓ Imports successful")
    print(f"SubscriptionStatus.TRIAL value: {SubscriptionStatus.TRIAL}")
    print(f"SubscriptionStatus.TRIAL value type: {type(SubscriptionStatus.TRIAL)}")
    print(f"UserRole.OWNER value: {UserRole.OWNER}")
    print(f"UserRole.OWNER value type: {type(UserRole.OWNER)}")

    # Create instances (no DB yet, just validation)
    try:
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Test Organization",
            subscription_status=SubscriptionStatus.TRIAL,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        print(f"✓ Tenant created: {tenant.name}")
        print(f"  - subscription_status: {tenant.subscription_status} (type: {type(tenant.subscription_status)})")

        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="vsouz009@gmail.com",
            hashed_password=get_password_hash("Pq267@gtr417#"),
            full_name="Vinicius Souza",
            role=UserRole.OWNER,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        print(f"✓ User created: {user.email}")
        print(f"  - role: {user.role} (type: {type(user.role)})")
        print(f"  - is_admin_or_owner: {user.is_admin_or_owner()}")

        print("\n✅ All model validations PASSED")

    except Exception as e:
        print(f"\n❌ Model creation FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tenant_registration())
