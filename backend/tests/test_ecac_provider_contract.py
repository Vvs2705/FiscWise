"""Tests for e-CAC provider contract and fiscal subject management."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.domain.ecac.models import FiscalSubject, EcacCredential


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
    tenant = Tenant(id=uuid.uuid4(), name=f"ECAC_{suffix}", subscription_status=SubscriptionStatus.TRIAL)
    db.add(tenant)
    await db.flush()
    user = User(
        id=uuid.uuid4(), email=f"ecac_{suffix}@test.com",
        hashed_password=get_password_hash("Pw123456!"),
        full_name=f"ECAC {suffix}", tenant_id=tenant.id,
        role=UserRole.OWNER, is_active=True,
    )
    db.add(user)
    await db.commit()
    return tenant, user


# ─── Provider Protocol Tests ──────────────────────────────────────────────────


class TestEcacProviderContract:
    """Validate the EcacProvider Protocol is correctly implemented by MockEcacProvider."""

    def test_mock_provider_implements_protocol(self):
        from app.domain.ecac.providers.mock import MockEcacProvider
        from app.domain.ecac.providers.base import EcacProvider
        provider = MockEcacProvider()
        # Runtime check via @runtime_checkable Protocol
        assert isinstance(provider, EcacProvider)

    def test_mock_provider_has_all_protocol_methods(self):
        from app.domain.ecac.providers.mock import MockEcacProvider
        provider = MockEcacProvider()
        for method in ("get_tax_status", "get_pgdas", "generate_das",
                       "get_dctfweb", "get_mailbox_messages",
                       "get_certidao_status", "get_procuracoes"):
            assert callable(getattr(provider, method, None)), f"Missing method: {method}"

    @pytest.mark.asyncio
    async def test_mock_provider_tax_status_returns_dict(self):
        from app.domain.ecac.providers.mock import MockEcacProvider
        provider = MockEcacProvider()
        result = await provider.get_tax_status(type("S", (), {"document": "12.345.678/0001-99"})())
        assert isinstance(result, dict)
        assert "regularized" in result

    @pytest.mark.asyncio
    async def test_mock_provider_mailbox_messages(self):
        from app.domain.ecac.providers.mock import MockEcacProvider
        provider = MockEcacProvider()
        result = await provider.get_mailbox_messages(type("S", (), {"document": "12.345.678/0001-99"})())
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "external_id" in result[0]

    @pytest.mark.asyncio
    async def test_mock_provider_generate_das(self):
        from app.domain.ecac.providers.mock import MockEcacProvider
        provider = MockEcacProvider()
        subject = type("S", (), {"document": "12.345.678/0001-99"})()
        result = await provider.generate_das(subject, "2026-01")
        assert isinstance(result, dict)
        assert "barcode" in result
        assert "amount" in result


# ─── Fiscal Subject CRUD Tests ────────────────────────────────────────────────


class TestFiscalSubjectCRUD:
    @pytest.mark.asyncio
    async def test_create_subject_returns_201(self, test_db: AsyncSession):
        from app.main import app
        _, user = await _bootstrap(test_db, "cs1")
        http = _auth_client(app, test_db, user)

        payload = {
            "document": "12.345.678/0001-99",
            "legal_name": "Empresa ABC",
            "subject_type": "pj",
            "tax_regime": "simples_nacional",
        }
        resp = http.post("/api/v1/ecac/subjects", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        data = resp.json()
        assert data["document"] == "12.345.678/0001-99"

    @pytest.mark.asyncio
    async def test_list_subjects_only_own_tenant(self, test_db: AsyncSession):
        from app.main import app
        tenant_a, _ = await _bootstrap(test_db, "la")
        _, user_b = await _bootstrap(test_db, "lb")

        test_db.add(FiscalSubject(
            id=uuid.uuid4(), tenant_id=tenant_a.id,
            document="11.222.333/0001-44", legal_name="Empresa LA", subject_type="pj", active=True,
        ))
        await test_db.commit()

        http_b = _auth_client(app, test_db, user_b)
        resp = http_b.get("/api/v1/ecac/subjects")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_subject_404_other_tenant(self, test_db: AsyncSession):
        from app.main import app
        tenant_a, _ = await _bootstrap(test_db, "ctA")
        _, user_b = await _bootstrap(test_db, "ctB")

        subject = FiscalSubject(
            id=uuid.uuid4(), tenant_id=tenant_a.id,
            document="55.666.777/0001-88", legal_name="Empresa CTA", subject_type="pj", active=True,
        )
        test_db.add(subject)
        await test_db.commit()

        http_b = _auth_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/ecac/subjects/{subject.id}")
        app.dependency_overrides.clear()

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_sync_subject_returns_result(self, test_db: AsyncSession):
        from app.main import app
        tenant, user = await _bootstrap(test_db, "sync1")

        subject = FiscalSubject(
            id=uuid.uuid4(), tenant_id=tenant.id,
            document="99.888.777/0001-66", legal_name="Empresa Sync", subject_type="pj", active=True,
        )
        test_db.add(subject)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.post(f"/api/v1/ecac/subjects/{subject.id}/sync")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
