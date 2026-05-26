import pytest
import uuid
from datetime import date, timedelta
from fastapi import status
from app.models.operations import DigitalCertificate

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_certificates_evolution_endpoints(client_with_auth_a):
    http_client, user, client, db = client_with_auth_a
    tenant_id = user.tenant_id

    # 1. Create a certificate that is expiring soon (e.g. in 45 days)
    expiring_date = date.today() + timedelta(days=45)
    cert1 = DigitalCertificate(
        tenant_id=tenant_id,
        client_id=client.id,
        label="Expiring Cert A",
        certificate_type="a1",
        valid_until=expiring_date,
        status="valid",
        bloqueado=False
    )
    db.add(cert1)
    
    # 2. Create another certificate that is NOT expiring soon (e.g. in 90 days)
    ok_date = date.today() + timedelta(days=90)
    cert2 = DigitalCertificate(
        tenant_id=tenant_id,
        client_id=client.id,
        label="Long Term Cert A",
        certificate_type="a1",
        valid_until=ok_date,
        status="valid",
        bloqueado=False
    )
    db.add(cert2)
    await db.commit()

    # 3. Test GET /api/v1/certificates/expiring -> should find cert1 but not cert2
    response = http_client.get("/api/v1/certificates/expiring")
    print("GET RESPONSE:", response.status_code, response.text)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["label"] == "Expiring Cert A"

    # 4. Test POST /api/v1/certificates/{id}/block -> should block cert1
    response = http_client.post(f"/api/v1/certificates/{cert1.id}/block?reason=compromised")
    print("POST RESPONSE:", response.status_code, response.text)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["bloqueado"] is True
    assert data["motivo_bloqueio"] == "compromised"
    assert data["status"] == "revoked"

    # 5. Test GET /api/v1/certificates/{id}/usage-trail -> should list the block audit event
    response = http_client.get(f"/api/v1/certificates/{cert1.id}/usage-trail")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert data[0]["action"] == "certificate.blocked"
    assert data[0]["details"]["motivo_bloqueio"] == "compromised"
