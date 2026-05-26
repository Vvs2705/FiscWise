"""Tests for Digital Certificates domain — security and cross-tenant isolation."""
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.models.operations import DigitalCertificate, AccountingClient


# ─── Helpers ─────────────��──────────────────────────────���─────────────────────


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
    tenant = Tenant(id=uuid.uuid4(), name=f"Cert_{suffix}", subscription_status=SubscriptionStatus.TRIAL)
    db.add(tenant)
    await db.flush()
    user = User(
        id=uuid.uuid4(), email=f"cert_{suffix}@test.com",
        hashed_password=get_password_hash("Pw123456!"),
        full_name=f"Cert {suffix}", tenant_id=tenant.id,
        role=UserRole.OWNER, is_active=True,
    )
    db.add(user)
    client = AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant.id,
        name=f"Cert Client {suffix}", document="76069336914468",
        entity_type="pj", status="active",
    )
    db.add(client)
    await db.commit()
    return tenant, user, client


def _make_cert(tenant_id: uuid.UUID, client_id: uuid.UUID, days_until: int = 90) -> DigitalCertificate:
    return DigitalCertificate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        label="Cert Test",
        certificate_type="a1",
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=days_until),
        status="valid",
    )


# ─── Tests ────────────────────────────────────────────────���───────────────────


class TestCertificateAccess:
    @pytest.mark.asyncio
    async def test_list_certificates_requires_auth(self, test_db: AsyncSession):
        from app.main import app
        from app.core.deps import get_db
        app.dependency_overrides[get_db] = lambda: test_db
        c = TestClient(app, raise_server_exceptions=False)
        # Send X-Tenant-ID but no Authorization token
        c.headers.update({"X-Tenant-ID": str(uuid.uuid4())})
        resp = c.get("/api/v1/certificates")
        app.dependency_overrides.clear()
        # Should be 401/403 without valid auth token
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_certificates_returns_only_own(self, test_db: AsyncSession):
        from app.main import app
        tenant_a, user_a, client_a = await _bootstrap(test_db, "la")
        tenant_b, user_b, client_b = await _bootstrap(test_db, "lb")

        cert_a = _make_cert(tenant_a.id, client_a.id)
        test_db.add(cert_a)
        await test_db.commit()

        http_b = _auth_client(app, test_db, user_b)
        resp = http_b.get("/api/v1/certificates")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_expiring_filter_returns_expiring_certs(self, test_db: AsyncSession):
        from app.main import app
        from datetime import date as _date
        tenant, user, client = await _bootstrap(test_db, "ex")

        cert_near = _make_cert(tenant.id, client.id, days_until=10)
        cert_near.label = "Near"
        test_db.add(cert_near)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        # Filter for certs expiring within 30 days — cert_near (10 days) must appear
        resp = http.get("/api/v1/certificates?expiring_days=30")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        # All returned certs must have valid_until ≤ today + 30 days
        from datetime import timedelta
        threshold = (_date.today() + timedelta(days=30)).isoformat()
        for cert in data:
            assert cert["valid_until"] <= threshold, f"{cert['label']} should not appear"
        labels = [c["label"] for c in data]
        assert "Near" in labels

    @pytest.mark.asyncio
    async def test_get_cert_from_other_tenant_returns_404(self, test_db: AsyncSession):
        from app.main import app
        tenant_a, _, client_a = await _bootstrap(test_db, "ctA")
        _, user_b, _ = await _bootstrap(test_db, "ctB")

        cert_a = _make_cert(tenant_a.id, client_a.id)
        test_db.add(cert_a)
        await test_db.commit()

        http_b = _auth_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/certificates/{cert_a.id}")
        app.dependency_overrides.clear()

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_validate_cert_returns_expiry_info(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "val")
        cert = _make_cert(tenant.id, client.id, days_until=45)
        test_db.add(cert)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.post(f"/api/v1/certificates/{cert.id}/validate")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["expired"] is False
        assert data["valid"] is True
