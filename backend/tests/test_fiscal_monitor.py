"""Integration tests for Fiscal Monitor endpoints, service, and isolation."""

import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select

from app.models.fiscal_monitor import FiscalMonitorSummary, FiscalNFe
from app.models.operations import DeadlineItem, ClientDocument


class TestFiscalMonitorAPI:
    """Tests for the Fiscal Monitor endpoints and service layer."""

    @pytest.mark.asyncio
    async def test_get_client_status_blank_default(self, client_with_auth_a):
        """GET /api/v1/fiscal-monitor/status/{client_id} returns default un-synced status if client exists but has never been synced."""
        client, _, client_a, _ = client_with_auth_a

        response = client.get(f"/api/v1/fiscal-monitor/status/{client_a.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["cnpj_status"] == "PENDENTE"
        assert data["cnd_status"] == "PENDENTE"
        assert data["has_debts"] is False
        assert data["debt_count"] == 0
        assert data["total_debt_value"] == "0.00"

    @pytest.mark.asyncio
    async def test_get_client_status_not_found(self, client_with_auth_a):
        """GET /api/v1/fiscal-monitor/status/{client_id} returns 404 if client doesn't exist."""
        client, _, _, _ = client_with_auth_a
        random_id = uuid.uuid4()

        response = client.get(f"/api/v1/fiscal-monitor/status/{random_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_sync_client_status_success(self, client_with_auth_a, test_db):
        """POST /api/v1/fiscal-monitor/sync/{client_id} successfully triggers sync, creating summary, CND doc, and NF-es."""
        client, user_a, client_a, _ = client_with_auth_a

        # CNPJ ending with "1" will simulate REGULAR status, no debts
        client_a.document = "12345678000101"
        test_db.add(client_a)
        await test_db.commit()

        response = client.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["nfes_fetched"] > 0
        assert data["summary"]["cnpj_status"] == "REGULAR"
        assert data["summary"]["cnd_status"] == "REGULAR"
        assert data["summary"]["has_debts"] is False

        # Verify summary exists in DB
        stmt_summary = select(FiscalMonitorSummary).where(FiscalMonitorSummary.client_id == client_a.id)
        res_summary = await test_db.execute(stmt_summary)
        summary = res_summary.scalar_one_or_none()
        assert summary is not None
        assert summary.cnpj_status == "REGULAR"

        # Verify CND ClientDocument is created
        stmt_doc = select(ClientDocument).where(
            (ClientDocument.client_id == client_a.id) &
            (ClientDocument.document_type == "certidao_negativa")
        )
        res_doc = await test_db.execute(stmt_doc)
        docs = res_doc.scalars().all()
        assert len(docs) == 1
        assert "Certidao Negativa" in docs[0].name
        assert docs[0].status == "available"

    @pytest.mark.asyncio
    async def test_sync_client_status_with_debts(self, client_with_auth_a, test_db):
        """POST /api/v1/fiscal-monitor/sync/{client_id} creates tasks/deadlines when debts are found (CNPJ ending in 5)."""
        client, user_a, client_a, _ = client_with_auth_a

        # CNPJ ending with "5" triggers simulated debts
        client_a.document = "12345678000105"
        test_db.add(client_a)
        await test_db.commit()

        response = client.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["has_debts"] is True
        assert data["summary"]["debt_count"] == 2
        assert float(data["summary"]["total_debt_value"]) > 0
        assert data["summary"]["cnd_status"] == "COM_PENDENCIAS"

        # Verify automated DeadlineItems are created in database
        stmt_tasks = select(DeadlineItem).where(
            (DeadlineItem.client_id == client_a.id) &
            (DeadlineItem.category == "fiscal")
        )
        res_tasks = await test_db.execute(stmt_tasks)
        tasks = res_tasks.scalars().all()
        assert len(tasks) == 2
        assert any("Competência 03/2026" in t.description for t in tasks)
        assert any("Competência 04/2026" in t.description for t in tasks)

    @pytest.mark.asyncio
    async def test_list_client_nfes(self, client_with_auth_a, test_db):
        """GET /api/v1/fiscal-monitor/nfes/{client_id} returns list of retrieved NF-e invoices."""
        client, user_a, client_a, _ = client_with_auth_a

        # Create one mock NF-e
        nfe = FiscalNFe(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            access_key="352605" + "1" * 38,
            nfe_number="00123",
            nfe_type="ENTRADA",
            issuer_name="Fornecedor ABC",
            issuer_document="09876543000199",
            recipient_name=client_a.name,
            recipient_document="12345678000101",
            value=Decimal("1500.50"),
            issued_at=datetime.now(),
            retrieved_at=datetime.now(),
            status="AUTORIZADA"
        )
        test_db.add(nfe)
        await test_db.commit()

        response = client.get(f"/api/v1/fiscal-monitor/nfes/{client_a.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["access_key"] == "352605" + "1" * 38
        assert data[0]["nfe_number"] == "00123"
        assert data[0]["value"] == "1500.50"

    @pytest.mark.asyncio
    async def test_import_nfe_webhook(self, client_with_auth_a, test_db):
        """POST /api/v1/fiscal-monitor/nfes/import webhook successfully registers a new NF-e invoice."""
        client, user_a, client_a, _ = client_with_auth_a

        payload = {
            "client_id": str(client_a.id),
            "access_key": "352605" + "9" * 38,
            "nfe_number": "54321",
            "nfe_type": "SAIDA",
            "issuer_name": client_a.name,
            "issuer_document": "12345678000101",
            "recipient_name": "Cliente Destinatário S/A",
            "recipient_document": "55443322000188",
            "value": "7890.99",
            "issued_at": datetime.now().isoformat()
        }

        response = client.post("/api/v1/fiscal-monitor/nfes/import", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["access_key"] == "352605" + "9" * 38
        assert data["nfe_number"] == "54321"
        assert data["value"] == "7890.99"

        # Verify key exists in DB
        stmt_nfe = select(FiscalNFe).where(FiscalNFe.access_key == "352605" + "9" * 38)
        res_nfe = await test_db.execute(stmt_nfe)
        nfe = res_nfe.scalar_one_or_none()
        assert nfe is not None
        assert nfe.nfe_number == "54321"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, client_with_auth_b, client_with_auth_a, test_db):
        """User B cannot access or trigger sync for User A's client fiscal status."""
        client_a_http, user_a, client_a, _ = client_with_auth_a
        client_b_http, user_b, client_b, _ = client_with_auth_b

        # Sync client_a first so it has an existing summary under Tenant A
        response = client_a_http.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}")
        assert response.status_code == 200

        # Try to query Client A status using User B (returns 404 because client is isolated by tenant)
        response = client_b_http.get(f"/api/v1/fiscal-monitor/status/{client_a.id}")
        assert response.status_code == 404

        # Try to trigger sync for Client A using User B (returns 404)
        response = client_b_http.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}")
        assert response.status_code == 404
