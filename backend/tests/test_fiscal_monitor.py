"""Integration tests for Fiscal Monitor endpoints, service, and isolation."""

import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select
import httpx

from app.core.config import settings
from app.models.audit import AuditEvent
from app.services import fiscal_monitor_service

from app.models.fiscal_monitor import FiscalMonitorSummary, FiscalNFe
from app.models.operations import DeadlineItem, ClientDocument


def _brasilapi_payload(situacao: str) -> dict:
    return {
        "cnpj": "12345678000101",
        "razao_social": "EMPRESA REAL LTDA",
        "descricao_situacao_cadastral": situacao,
        "data_situacao_cadastral": "2019-05-10",
        "cnae_fiscal": 6201501,
        "cnae_fiscal_descricao": "Desenvolvimento de programas de computador sob encomenda",
        "natureza_juridica": "Sociedade Empresária Limitada",
        "opcao_pelo_simples": True,
        "opcao_pelo_mei": False,
        "data_inicio_atividade": "2015-03-01",
        "qsa": [{"nome_socio": "NAO GUARDAR"}],
    }


def _install_transport(monkeypatch, handler):
    calls = []

    def wrapped(request: httpx.Request):
        calls.append(str(request.url))
        return handler(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(wrapped))
    monkeypatch.setattr(fiscal_monitor_service, "_http_client_override", client)
    monkeypatch.setattr(fiscal_monitor_service.asyncio, "sleep", _no_sleep)
    monkeypatch.setattr(settings, "FISCAL_MONITOR_PROVIDER", "brasilapi")
    return calls


async def _no_sleep(_seconds):
    return None


@pytest.fixture
def brasilapi_ok(monkeypatch):
    return _install_transport(
        monkeypatch, lambda req: httpx.Response(200, json=_brasilapi_payload("ATIVA"))
    )


class TestFiscalMonitorSync:
    @pytest.mark.asyncio
    async def test_sync_active_cnpj_uses_real_registry_and_invents_nothing(
        self, client_with_auth_a, test_db, brasilapi_ok
    ):
        client, user_a, client_a, _ = client_with_auth_a
        client_a.document = "12.345.678/0001-01"
        test_db.add(client_a)
        await test_db.commit()

        response = client.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        summary = data["summary"]
        assert summary["cnpj_status"] == "ATIVA"
        assert summary["registry_source"] == "brasilapi"
        details = summary["situation_details"]
        assert details["razao_social"] == "EMPRESA REAL LTDA"
        assert details["cnae_fiscal"] == 6201501
        assert details["opcao_pelo_simples"] is True
        assert "qsa" not in details
        assert summary["debts"] is None and summary["cnd"] is None and summary["nfes"] == []
        assert summary["source"] == "unavailable"
        assert "SERPRO" in summary["message"]
        assert brasilapi_ok == ["https://brasilapi.com.br/api/cnpj/v1/12345678000101"]

        # Nada inventado: nenhum prazo, CND ou NF-e gravado.
        assert (await test_db.execute(select(DeadlineItem))).scalars().all() == []
        assert (await test_db.execute(select(ClientDocument))).scalars().all() == []
        assert (await test_db.execute(select(FiscalNFe))).scalars().all() == []

    @pytest.mark.asyncio
    async def test_sync_baixada(self, client_with_auth_a, test_db, monkeypatch):
        _install_transport(
            monkeypatch, lambda req: httpx.Response(200, json=_brasilapi_payload("BAIXADA"))
        )
        client, _, client_a, _ = client_with_auth_a
        client_a.document = "12345678000101"
        test_db.add(client_a)
        await test_db.commit()

        data = client.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}").json()
        assert data["summary"]["cnpj_status"] == "BAIXADA"

    @pytest.mark.asyncio
    async def test_network_error_retries_once_and_records_error(
        self, client_with_auth_a, test_db, monkeypatch
    ):
        def boom(request):
            raise httpx.ConnectError("sem rede", request=request)

        calls = _install_transport(monkeypatch, boom)
        client, _, client_a, _ = client_with_auth_a
        client_a.document = "12345678000101"
        test_db.add(client_a)
        await test_db.commit()

        response = client.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert len(calls) == 2  # 1 tentativa + 1 retry
        summary = data["summary"]
        assert summary["cnpj_status"] == "ERRO_CONSULTA"
        assert summary["situation_details"]["status"] == "error"
        assert summary["registry_source"] is None
        assert (await test_db.execute(select(DeadlineItem))).scalars().all() == []

    @pytest.mark.asyncio
    async def test_error_keeps_previous_real_status(self, client_with_auth_a, test_db, monkeypatch):
        client, _, client_a, _ = client_with_auth_a
        client_a.document = "12345678000101"
        test_db.add(client_a)
        await test_db.commit()
        _install_transport(monkeypatch, lambda req: httpx.Response(200, json=_brasilapi_payload("ATIVA")))
        client.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}")
        _install_transport(monkeypatch, lambda req: httpx.Response(503))
        data = client.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}").json()
        assert data["status"] == "error"
        assert data["summary"]["cnpj_status"] == "ATIVA"
        assert data["summary"]["situation_details"]["last_error"]

    @pytest.mark.asyncio
    async def test_mock_provider_in_production_returns_503(
        self, client_with_auth_a, test_db, monkeypatch
    ):
        monkeypatch.setattr(settings, "FISCAL_MONITOR_PROVIDER", "mock")
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        client, _, client_a, _ = client_with_auth_a
        response = client.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}")
        assert response.status_code == 503
        assert "não configurada" in response.json()["detail"]
        assert (await test_db.execute(select(FiscalMonitorSummary))).scalars().all() == []

    @pytest.mark.asyncio
    async def test_resync_retires_legacy_fake_records(
        self, client_with_auth_a, test_db, brasilapi_ok
    ):
        client, user_a, client_a, _ = client_with_auth_a
        client_a.document = "12345678000101"
        tenant_id = user_a.tenant_id
        fake_task = DeadlineItem(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_a.id,
            title="Regularizar DAS Simples Nacional - Competência 03/2026",
            category="fiscal", due_date=date.today(), status="pending", priority="high",
            description="Alerta automático de irregularidade identificado na Receita Federal.\n\n- Tipo: FEDERAL",
        )
        real_task = DeadlineItem(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_a.id,
            title="Regularizar DAS Simples Nacional - Competência 05/2026",
            category="fiscal", due_date=date.today(), status="pending", priority="high",
            description="Criado pelo contador",
        )
        fake_cnd = ClientDocument(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_a.id,
            name="Certidao Negativa de Debitos Federais - 20260101.pdf",
            document_type="certidao_negativa", status="available",
            file_url="https://fiscwise.storage/cnd/federal-x.pdf",
        )
        legacy = FiscalMonitorSummary(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_a.id,
            cnpj_status="REGULAR", cnd_status="COM_PENDENCIAS", has_debts=True,
            debt_count=2, total_debt_value=Decimal("762.50"),
            debts_list={"debts": [{"value": 350.0}]},
            situation_details={"situacao_cadastral": "ATIVA"},
        )
        test_db.add_all([client_a, fake_task, real_task, fake_cnd, legacy])
        await test_db.commit()

        # Antes de sincronizar, o resumo legado não é exibido como real.
        before = client.get(f"/api/v1/fiscal-monitor/status/{client_a.id}").json()
        assert before["cnpj_status"] == "PENDENTE"
        assert before["has_debts"] is False and before["debts"] is None

        assert client.post(f"/api/v1/fiscal-monitor/sync/{client_a.id}").status_code == 200

        await test_db.refresh(fake_task)
        await test_db.refresh(real_task)
        await test_db.refresh(fake_cnd)
        await test_db.refresh(legacy)
        assert fake_task.status == "cancelled"
        assert real_task.status == "pending"
        assert fake_cnd.status == "missing" and fake_cnd.file_url is None
        assert legacy.debts_list is None and legacy.has_debts is False
        assert legacy.cnd_status == "NAO_CONSULTADO"
        events = (await test_db.execute(
            select(AuditEvent).where(AuditEvent.action == "fiscal_monitor.sync")
        )).scalars().all()
        assert events and events[0].after_data["cancelled_tasks"] == 1


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
        assert data["cnd_status"] == "NAO_CONSULTADO"
        assert data["debts"] is None and data["cnd"] is None and data["nfes"] == []
        assert data["source"] == "unavailable"
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
    async def test_import_nfe_returns_501_without_writing(self, client_with_auth_a, test_db):
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
            "issued_at": datetime.now().isoformat(),
        }
        response = client.post("/api/v1/fiscal-monitor/nfes/import", json=payload)
        assert response.status_code == 501
        res = await test_db.execute(select(FiscalNFe))
        assert res.scalars().all() == []

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, client_with_auth_b, client_with_auth_a, test_db, brasilapi_ok):
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
