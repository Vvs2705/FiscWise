"""Tests for Powers of Attorney domain — procurações eletrônicas."""
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.domain.powers_of_attorney.models import PowerOfAttorney, PoaStatus


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _auth_client(app, db: AsyncSession, user: User) -> TestClient:
    from app.core.deps import get_db
    app.dependency_overrides[get_db] = lambda: db
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value,
    )
    c = TestClient(app, raise_server_exceptions=False)
    c.headers.update({
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(user.tenant_id),
    })
    return c


async def _bootstrap(db: AsyncSession, suffix: str):
    tenant = Tenant(id=uuid.uuid4(), name=f"POA_{suffix}", subscription_status=SubscriptionStatus.TRIAL)
    db.add(tenant)
    await db.flush()
    user = User(
        id=uuid.uuid4(), email=f"poa_{suffix}@test.com",
        hashed_password=get_password_hash("Pw123456!"),
        full_name=f"POA {suffix}", tenant_id=tenant.id,
        role=UserRole.OWNER, is_active=True,
    )
    db.add(user)
    await db.commit()
    return tenant, user


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestPoaCRUD:
    @pytest.mark.asyncio
    async def test_create_poa_returns_201(self, test_db: AsyncSession):
        from app.main import app
        _, user = await _bootstrap(test_db, "c1")
        http = _auth_client(app, test_db, user)

        payload = {
            "grantor_document": "12.345.678/0001-99",
            "attorney_document": "123.456.789-00",
            "provider": "ecac",
            "services": ["DECLARACOES", "PARCELAMENTO"],
            "valid_from": "2026-01-01",
            "valid_until": "2026-12-31",
        }
        resp = http.post("/api/v1/powers-of-attorney", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == PoaStatus.PENDING.value
        assert data["provider"] == "ecac"

    @pytest.mark.asyncio
    async def test_list_poas_returns_only_own_tenant(self, test_db: AsyncSession):
        from app.main import app
        tenant_a, user_a = await _bootstrap(test_db, "la")
        tenant_b, user_b = await _bootstrap(test_db, "lb")

        # Create one POA for tenant A
        test_db.add(PowerOfAttorney(
            id=uuid.uuid4(), tenant_id=tenant_a.id,
            grantor_document="11.222.333/0001-81",
            attorney_document="111.222.333-44",
            provider="gov_br", status=PoaStatus.ACTIVE.value,
        ))
        await test_db.commit()

        http_b = _auth_client(app, test_db, user_b)
        resp = http_b.get("/api/v1/powers-of-attorney")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        # Tenant B should see zero POAs
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_check_poa_transitions_pending_to_active(self, test_db: AsyncSession):
        from app.main import app
        tenant, user = await _bootstrap(test_db, "ch1")
        poa = PowerOfAttorney(
            id=uuid.uuid4(), tenant_id=tenant.id,
            grantor_document="99.888.777/0001-66",
            attorney_document="999.888.777-55",
            provider="ecac", status=PoaStatus.PENDING.value,
            valid_until=date.today() + timedelta(days=365),
        )
        test_db.add(poa)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.post(f"/api/v1/powers-of-attorney/{poa.id}/check")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == PoaStatus.ACTIVE.value
        assert data["last_checked_at"] is not None

    @pytest.mark.asyncio
    async def test_check_poa_transitions_expired(self, test_db: AsyncSession):
        from app.main import app
        tenant, user = await _bootstrap(test_db, "ch2")
        poa = PowerOfAttorney(
            id=uuid.uuid4(), tenant_id=tenant.id,
            grantor_document="55.444.333/0001-22",
            attorney_document="554.443.330-11",
            provider="ecac", status=PoaStatus.ACTIVE.value,
            valid_until=date(2020, 12, 31),  # past date
        )
        test_db.add(poa)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.post(f"/api/v1/powers-of-attorney/{poa.id}/check")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["status"] == PoaStatus.EXPIRED.value

    @pytest.mark.asyncio
    async def test_get_poa_from_other_tenant_returns_404(self, test_db: AsyncSession):
        from app.main import app
        tenant_a, _ = await _bootstrap(test_db, "ctA")
        _, user_b = await _bootstrap(test_db, "ctB")

        poa = PowerOfAttorney(
            id=uuid.uuid4(), tenant_id=tenant_a.id,
            grantor_document="77.666.555/0001-44",
            attorney_document="776.665.550-33",
            provider="ecac", status=PoaStatus.ACTIVE.value,
        )
        test_db.add(poa)
        await test_db.commit()

        http_b = _auth_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/powers-of-attorney/{poa.id}")
        app.dependency_overrides.clear()

        assert resp.status_code == 404
