import pytest
from fastapi import status

pytestmark = pytest.mark.integration

COMPETENCE = "2026-06"


@pytest.mark.asyncio
async def test_monthly_closing_workflow(client_with_auth_a, test_db):
    http_client, user, client, db = client_with_auth_a

    # 1. Empty before generation
    response = http_client.get("/api/v1/monthly-closing", params={"competence": COMPETENCE})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    # 2. Generate creates one closing per active client
    response = http_client.post("/api/v1/monthly-closing/generate", params={"competence": COMPETENCE})
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["created"] >= 1
    assert result["skipped"] == 0

    # 3. Idempotent: generating again skips existing closings
    response = http_client.post("/api/v1/monthly-closing/generate", params={"competence": COMPETENCE})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["created"] == 0

    # 4. List returns the closing with client info and a fresh checklist
    response = http_client.get("/api/v1/monthly-closing", params={"competence": COMPETENCE})
    assert response.status_code == status.HTTP_200_OK
    closings = response.json()
    assert len(closings) >= 1
    closing = next(c for c in closings if c["client_id"] == str(client.id))
    assert closing["status"] == "not_started"
    assert closing["score"] == 0
    assert closing["client_name"] == client.name
    assert len(closing["checklist"]) == 8
    closing_id = closing["id"]

    # 5. Completing a checklist item moves the closing to in_progress
    response = http_client.patch(
        f"/api/v1/monthly-closing/{closing_id}/checklist/ck-01",
        json={"status": "done"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["score"] > 0
    item = next(i for i in data["checklist"] if i["id"] == "ck-01")
    assert item["status"] == "done"
    assert item["completed_at"] is not None

    # 6. A blocked item flags the whole closing as blocked, with the blocker listed
    response = http_client.patch(
        f"/api/v1/monthly-closing/{closing_id}/checklist/ck-07",
        json={"status": "blocked", "notes": "Aguardando cliente"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "blocked"
    assert "Pendências fiscais verificadas" in data["blockers"]

    # 7. Unblock and generate the dossier (also completes the ck-08 item)
    response = http_client.patch(
        f"/api/v1/monthly-closing/{closing_id}/checklist/ck-07",
        json={"status": "done"},
    )
    assert response.status_code == status.HTTP_200_OK

    response = http_client.post(f"/api/v1/monthly-closing/{closing_id}/dossier")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["generated_at"] is not None

    response = http_client.get(f"/api/v1/monthly-closing/{closing_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["dossier_generated_at"] is not None
    ck08 = next(i for i in data["checklist"] if i["id"] == "ck-08")
    assert ck08["status"] == "done"

    # 8. Unknown checklist item / closing -> 404
    response = http_client.patch(
        f"/api/v1/monthly-closing/{closing_id}/checklist/ck-99",
        json={"status": "done"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = http_client.get("/api/v1/monthly-closing/00000000-0000-0000-0000-000000000000")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # 9. Invalid competence format -> 422
    response = http_client.post("/api/v1/monthly-closing/generate", params={"competence": "junho"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_monthly_closing_requires_auth(client):
    response = client.get(
        "/api/v1/monthly-closing",
        headers={"X-Tenant-ID": "9df4b224-c8dc-4cdf-9bb6-40af6d206e62"},
    )
    assert response.status_code in (401, 403)
