import pytest
import uuid
from datetime import date, timedelta
from fastapi import status
from app.domain.ecac.models import EcacProxy, EcacFiscalSituation

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_ecac_api_workflow(client_with_auth_a, test_db):
    http_client, user, client, db = client_with_auth_a
    tenant_id = user.tenant_id

    # 1. Create a proxy expiring in 15 days (should trigger expiring filter)
    expiring_date = date.today() + timedelta(days=15)
    proxy_payload = {
        "client_id": str(client.id),
        "outorgante_cpf_cnpj": "10000000000145",
        "outorgante_nome": "Outorgante Teste",
        "procurador_cpf": "10000000019",
        "tipo": "e-CAC",
        "servicos_autorizados": ["sit-fiscal", "nfs-e"],
        "data_inicio": date.today().isoformat(),
        "data_validade": expiring_date.isoformat()
    }
    response = http_client.post("/api/v1/ecac/proxies", json=proxy_payload)
    assert response.status_code == status.HTTP_201_CREATED
    proxy_data = response.json()
    assert proxy_data["outorgante_nome"] == "Outorgante Teste"
    proxy_id = proxy_data["id"]

    # 2. Get proxies list
    response = http_client.get("/api/v1/ecac/proxies")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1

    # 3. Get expiring proxies
    response = http_client.get("/api/v1/ecac/proxies/expiring")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1
    assert response.json()[0]["id"] == proxy_id

    # 4. Get detailed proxy
    response = http_client.get(f"/api/v1/ecac/proxies/{proxy_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ativa"

    # 5. Update proxy
    response = http_client.put(f"/api/v1/ecac/proxies/{proxy_id}", json={"status": "revogada"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "revogada"

    # 6. Clients without proxy (client has a proxy but it is now 'revogada', so it should appear in clients-without-proxy!)
    response = http_client.get("/api/v1/ecac/clients-without-proxy")
    assert response.status_code == status.HTTP_200_OK
    matched = [c for c in response.json() if c["id"] == str(client.id)]
    assert len(matched) == 1

    # 7. Post refresh fiscal situation
    response = http_client.post(f"/api/v1/ecac/fiscal-situation/{client.id}/refresh")
    print("REFRESH RESPONSE:", response.status_code, response.text)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "queued"

    # In TestClient, BackgroundTasks run synchronously before response returns
    # So the fiscal situation should be populated now! Let's check.
    response = http_client.get(f"/api/v1/ecac/fiscal-situation/{client.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status_geral"] == "regular"
