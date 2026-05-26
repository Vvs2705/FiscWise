import pytest
import io
import uuid
from datetime import date, timedelta
from fastapi import status
from app.domain.guias.models import TaxGuide

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_guias_api_workflow(client_with_auth_a, test_db):
    http_client, user, client, db = client_with_auth_a
    tenant_id = user.tenant_id

    # 1. Create a guide
    vencimento_futuro = date.today() + timedelta(days=20)
    guide_payload = {
        "client_id": str(client.id),
        "tipo": "DAS",
        "competencia": date.today().isoformat(),
        "valor": 450.00,
        "vencimento": vencimento_futuro.isoformat()
    }
    response = http_client.post("/api/v1/guias", json=guide_payload)
    assert response.status_code == status.HTTP_201_CREATED
    guide_data = response.json()
    assert guide_data["tipo"] == "DAS"
    assert guide_data["status"] == "pendente"
    guide_id = guide_data["id"]

    # 2. Upload PDF
    pdf_file = (io.BytesIO(b"%PDF-1.4..."), "guide.pdf")
    response = http_client.post(
        f"/api/v1/guias/{guide_id}/upload-pdf",
        files={"file": (pdf_file[1], pdf_file[0], "application/pdf")}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "enviada"
    assert response.json()["pdf_storage_path"] is not None

    # 3. Get PDF url
    response = http_client.get(f"/api/v1/guias/{guide_id}/pdf")
    assert response.status_code == status.HTTP_200_OK
    assert "url" in response.json()

    # 4. Upload Comprovante (marks as paga)
    receipt_file = (io.BytesIO(b"image data"), "receipt.png")
    response = http_client.post(
        f"/api/v1/guias/{guide_id}/upload-comprovante",
        files={"file": (receipt_file[1], receipt_file[0], "image/png")}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "paga"
    assert response.json()["comprovante_storage_path"] is not None

    # 5. Get Comprovante url
    response = http_client.get(f"/api/v1/guias/{guide_id}/comprovante")
    assert response.status_code == status.HTTP_200_OK
    assert "url" in response.json()

    # 6. List Guias
    response = http_client.get("/api/v1/guias")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1

    # 7. Test overdue guide auto-transition
    past_date = date.today() - timedelta(days=5)
    overdue_guide = TaxGuide(
        tenant_id=tenant_id,
        client_id=client.id,
        tipo="DARF",
        competencia=date.today(),
        valor=100.00,
        vencimento=past_date,
        status="pendente"
    )
    db.add(overdue_guide)
    await db.commit()

    # Querying should auto-update status to 'atrasada'
    response = http_client.get(f"/api/v1/guias/{overdue_guide.id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "atrasada"

    # 8. Test pending receipt alert
    # Mark as 'paga' but without a comprovante
    response = http_client.put(f"/api/v1/guias/{overdue_guide.id}/mark-paid")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "paga"
    assert response.json()["comprovante_storage_path"] is None

    # Fetch from pending-receipt report
    response = http_client.get("/api/v1/guias/pending-receipt")
    assert response.status_code == status.HTTP_200_OK
    matched = [g for g in response.json() if g["id"] == str(overdue_guide.id)]
    assert len(matched) == 1
