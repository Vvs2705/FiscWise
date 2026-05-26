"""Tests for Invoice/NFS-e domain — emission flow and provider contract."""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.models.operations import AccountingClient
from app.domain.invoices.models import (
    Invoice, InvoiceIssuer, InvoiceStatus, InvoiceType, IssuerType
)


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
    tenant = Tenant(id=uuid.uuid4(), name=f"INV_{suffix}", subscription_status=SubscriptionStatus.TRIAL)
    db.add(tenant)
    await db.flush()
    user = User(
        id=uuid.uuid4(), email=f"inv_{suffix}@test.com",
        hashed_password=get_password_hash("Pw123456!"),
        full_name=f"Inv {suffix}", tenant_id=tenant.id,
        role=UserRole.OWNER, is_active=True,
    )
    db.add(user)
    client = AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant.id,
        name=f"Client {suffix}", document="76069336914468",
        entity_type="pj", status="active",
    )
    db.add(client)
    await db.commit()
    return tenant, user, client


async def _make_issuer(db: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID) -> InvoiceIssuer:
    issuer = InvoiceIssuer(
        id=uuid.uuid4(), tenant_id=tenant_id,
        client_id=client_id, issuer_type=IssuerType.ACCOUNTANT.value,
        document="76.069.336/9144-68",
        legal_name="Empresa Test LTDA",
        city_code="3550308",  # São Paulo
        tax_regime="simples_nacional",
        provider="mock",
        active=True,
    )
    db.add(issuer)
    await db.commit()
    return issuer


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestInvoiceIssuers:
    @pytest.mark.asyncio
    async def test_create_issuer_returns_201(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "iss1")
        http = _auth_client(app, test_db, user)

        payload = {
            "client_id": str(client.id),
            "issuer_type": "accountant",
            "document": "76.069.336/9144-68",
            "legal_name": "Empresa Teste LTDA",
            "city_code": "3550308",
            "tax_regime": "simples_nacional",
            "provider": "mock",
        }
        resp = http.post("/api/v1/invoice-issuers", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        data = resp.json()
        assert data["legal_name"] == "Empresa Teste LTDA"
        assert data["active"] is True

    @pytest.mark.asyncio
    async def test_list_issuers_only_own_tenant(self, test_db: AsyncSession):
        from app.main import app
        tenant_a, user_a, client_a = await _bootstrap(test_db, "ia")
        _, user_b, _ = await _bootstrap(test_db, "ib")

        await _make_issuer(test_db, tenant_a.id, client_a.id)

        http_b = _auth_client(app, test_db, user_b)
        resp = http_b.get("/api/v1/invoice-issuers")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json() == []


class TestInvoiceDraft:
    @pytest.mark.asyncio
    async def test_create_draft_invoice(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "dr1")
        issuer = await _make_issuer(test_db, tenant.id, client.id)
        http = _auth_client(app, test_db, user)

        payload = {
            "issuer_id": str(issuer.id),
            "invoice_type": InvoiceType.HONORARIOS.value,
            "competence": "2026-01",
            "service_description": "Serviços de consultoria contábil",
            "amount": "1500.00",
            "provider": "mock",
        }
        resp = http.post("/api/v1/invoices", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == InvoiceStatus.DRAFT.value
        assert data["competence"] == "2026-01"

    @pytest.mark.asyncio
    async def test_cancel_draft_invoice(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "cn1")
        issuer = await _make_issuer(test_db, tenant.id, client.id)

        invoice = Invoice(
            id=uuid.uuid4(), tenant_id=tenant.id, issuer_id=issuer.id,
            invoice_type=InvoiceType.HONORARIOS.value, status=InvoiceStatus.DRAFT.value,
            competence="2026-02", service_description="Serviços",
            amount=Decimal("800.00"), provider="mock",
        )
        test_db.add(invoice)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        payload = {"reason": "Erro nos dados do tomador"}
        resp = http.post(f"/api/v1/invoices/{invoice.id}/cancel", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["status"] == InvoiceStatus.CANCELLED.value

    @pytest.mark.asyncio
    async def test_invoice_cross_tenant_isolation(self, test_db: AsyncSession):
        from app.main import app
        tenant_a, _, client_a = await _bootstrap(test_db, "ctA")
        _, user_b, _ = await _bootstrap(test_db, "ctB")
        issuer_a = await _make_issuer(test_db, tenant_a.id, client_a.id)

        invoice = Invoice(
            id=uuid.uuid4(), tenant_id=tenant_a.id, issuer_id=issuer_a.id,
            invoice_type=InvoiceType.HONORARIOS.value, status=InvoiceStatus.DRAFT.value,
            competence="2026-03", service_description="Serviços",
            amount=Decimal("500.00"), provider="mock",
        )
        test_db.add(invoice)
        await test_db.commit()

        http_b = _auth_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/invoices/{invoice.id}")
        app.dependency_overrides.clear()

        assert resp.status_code == 404


class TestInvoiceProviderMock:
    """Tests using the mock provider — validates provider protocol contract."""

    @pytest.mark.asyncio
    async def test_mock_provider_validate_issuer(self):
        from app.domain.invoices.providers.mock import MockInvoiceProvider
        provider = MockInvoiceProvider()
        issuer = type("I", (), {"document": "12.345.678/0001-99", "city_code": "3550308"})()
        result = await provider.validate_issuer(issuer)
        assert result.get("valid") is True

    @pytest.mark.asyncio
    async def test_mock_provider_issue_nfse(self):
        from app.domain.invoices.providers.mock import MockInvoiceProvider
        provider = MockInvoiceProvider()
        invoice = type("Inv", (), {"amount": 1000, "service_description": "Test", "provider_invoice_id": None})()
        result = await provider.issue_nfse(invoice)
        assert "provider_invoice_id" in result
        assert result.get("status") in ("issued", "processing")

    @pytest.mark.asyncio
    async def test_mock_provider_cancel(self):
        from app.domain.invoices.providers.mock import MockInvoiceProvider
        provider = MockInvoiceProvider()
        invoice = type("Inv", (), {"provider_invoice_id": "mock-123"})()
        result = await provider.cancel_nfse(invoice, reason="Test cancel")
        assert result.get("status") == "cancelled"
