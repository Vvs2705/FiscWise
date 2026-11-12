import pytest
import uuid
from datetime import date
from decimal import Decimal
from fastapi import status
from app.domain.invoices.models import Invoice, InvoiceIssuer

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_invoice_api_workflow(client_with_auth_a):
    http_client, user, client, db = client_with_auth_a
    tenant_id = user.tenant_id

    # 1. Create Invoice Issuer Profile
    issuer_payload = {
        "cnpj": "10000000000145",
        "inscricao_municipal": "12345",
        "regime_tributario": "simples",
        "municipio_ibge": "3550308",
        "cod_servico_lc116": "01.01",
        "aliquota_iss": 0.02,
        "retencao_iss": False
    }
    response = http_client.post("/api/v1/invoices/issuers", json=issuer_payload)
    assert response.status_code == status.HTTP_201_CREATED
    issuer_data = response.json()
    assert issuer_data["cnpj"] == "10000000000145"
    issuer_id = issuer_data["id"]

    # 2. Get Issuers list
    response = http_client.get("/api/v1/invoices/issuers")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1

    # 3. Create Invoice Draft
    invoice_payload = {
        "issuer_id": issuer_id,
        "client_id": str(client.id),
        "competencia": date.today().isoformat(),
        "valor_servico": 500.00,
        "valor_deducoes": 0.00,
        "descricao_servico": "Servico de Consultoria Tributaria de Teste",
        "tomador_nome": "Empresa Cliente Teste",
        "tomador_cpf_cnpj": "10000000019"
    }
    response = http_client.post("/api/v1/invoices", json=invoice_payload)
    assert response.status_code == status.HTTP_201_CREATED
    invoice_data = response.json()
    assert invoice_data["status"] == "draft"
    invoice_id = invoice_data["id"]

    # 4. Get Invoice details
    response = http_client.get(f"/api/v1/invoices/{invoice_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "draft"

    # 5. List Invoices
    response = http_client.get("/api/v1/invoices")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1

    # 6. Emit Invoice (async with BackgroundTasks)
    response = http_client.post(f"/api/v1/invoices/{invoice_id}/emit")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "queued"

    # In TestClient, BackgroundTasks run within the request block synchronously
    # so by the time the request completes, the status will have transitioned to issued.
    response = http_client.get(f"/api/v1/invoices/{invoice_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "issued"
    assert data["numero"] == "1"

    assert data["simulated"] is True
    assert data["pdf_storage_path"] is None

    # 7. PDF (DANFSe gerado sob demanda) e XML servido do banco
    response = http_client.get(f"/api/v1/invoices/{invoice_id}/pdf")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert 'filename="nfse-1.pdf"' in response.headers["content-disposition"]

    response = http_client.get(f"/api/v1/invoices/{invoice_id}/xml")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("application/xml")
    assert response.text == data["xml_content"]
    assert 'filename="nfse-1.xml"' in response.headers["content-disposition"]

    # 8. Cancel Invoice
    response = http_client.post(f"/api/v1/invoices/{invoice_id}/cancel", json={"reason": "Erro no preenchimento"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "cancelled"

    # 9. List Events
    response = http_client.get(f"/api/v1/invoices/{invoice_id}/events")
    assert response.status_code == status.HTTP_200_OK
    events = response.json()
    assert len(events) >= 1


async def _draft_invoice(http_client, client) -> str:
    issuer = http_client.post("/api/v1/invoices/issuers", json={
        "cnpj": "10000000000145", "inscricao_municipal": "12345", "regime_tributario": "simples",
        "municipio_ibge": "3550308", "cod_servico_lc116": "01.01", "aliquota_iss": 0.02,
        "retencao_iss": False,
    }).json()
    inv = http_client.post("/api/v1/invoices", json={
        "issuer_id": issuer["id"], "client_id": str(client.id),
        "competencia": date.today().isoformat(), "valor_servico": 500.00,
        "valor_deducoes": 0.00, "descricao_servico": "Consultoria",
    }).json()
    return inv["id"]


@pytest.mark.asyncio
async def test_emit_with_mock_in_production_returns_503_and_keeps_draft(
    client_with_auth_a, test_db, monkeypatch
):
    from sqlalchemy import select
    from app.core.config import settings
    from app.domain.invoices.models import InvoiceEvent

    http_client, _, client, _ = client_with_auth_a
    invoice_id = await _draft_invoice(http_client, client)
    monkeypatch.setattr(settings, "NFSE_PROVIDER", "mock")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    response = http_client.post(f"/api/v1/invoices/{invoice_id}/emit")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == (
        "Emissão de NFS-e não configurada (exige certificado A1 e homologação)"
    )
    data = http_client.get(f"/api/v1/invoices/{invoice_id}").json()
    assert data["status"] == "draft"

    # G2: nenhuma nota vira "issued" em produção com mock.
    issued = (await test_db.execute(select(Invoice).where(Invoice.status == "issued"))).scalars().all()
    assert issued == []
    events = (await test_db.execute(select(InvoiceEvent))).scalars().all()
    assert [e.event_type for e in events] == ["created"]

    response = http_client.post(f"/api/v1/invoices/{invoice_id}/cancel", json={"reason": "Erro no preenchimento"})
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert http_client.get(f"/api/v1/invoices/{invoice_id}").json()["status"] == "draft"


@pytest.mark.asyncio
async def test_pdf_and_xml_before_emission_return_404(client_with_auth_a):
    http_client, _, client, _ = client_with_auth_a
    invoice_id = await _draft_invoice(http_client, client)
    r = http_client.get(f"/api/v1/invoices/{invoice_id}/pdf")
    assert r.status_code == 404 and "PDF ainda não gerado" in r.json()["detail"]
    r = http_client.get(f"/api/v1/invoices/{invoice_id}/xml")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_background_failure_is_logged_and_recorded(client_with_auth_a, test_db, monkeypatch):
    from sqlalchemy import select
    from app.domain.invoices.models import InvoiceRejection
    from app.domain.invoices.service import InvoiceService

    http_client, _, client, _ = client_with_auth_a
    invoice_id = await _draft_invoice(http_client, client)

    async def boom(self, *args, **kwargs):
        raise RuntimeError("falha inesperada")

    monkeypatch.setattr(InvoiceService, "process_emission_sync", boom)
    assert http_client.post(f"/api/v1/invoices/{invoice_id}/emit").status_code == 200
    data = http_client.get(f"/api/v1/invoices/{invoice_id}").json()
    assert data["status"] == "failed"
    rejections = (await test_db.execute(select(InvoiceRejection))).scalars().all()
    assert rejections and rejections[0].codigo_rejeicao == "BACKGROUND"
