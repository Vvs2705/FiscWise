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

    # 7. Get PDF and XML signed URLs
    response = http_client.get(f"/api/v1/invoices/{invoice_id}/pdf")
    assert response.status_code == status.HTTP_200_OK
    assert "url" in response.json()

    response = http_client.get(f"/api/v1/invoices/{invoice_id}/xml")
    assert response.status_code == status.HTTP_200_OK
    assert "url" in response.json()

    # 8. Cancel Invoice
    response = http_client.post(f"/api/v1/invoices/{invoice_id}/cancel", json={"reason": "Erro no preenchimento"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "cancelled"

    # 9. List Events
    response = http_client.get(f"/api/v1/invoices/{invoice_id}/events")
    assert response.status_code == status.HTTP_200_OK
    events = response.json()
    assert len(events) >= 1
