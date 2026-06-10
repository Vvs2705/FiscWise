import pytest
from fastapi import status

pytestmark = pytest.mark.integration

COMPETENCE = "2026-06"


@pytest.mark.asyncio
async def test_portal_preview_aggregates_client_data(client_with_auth_a, test_db):
    http_client, user, client, db = client_with_auth_a

    # Generate a closing so the preview has closing data to aggregate.
    response = http_client.post("/api/v1/monthly-closing/generate", params={"competence": COMPETENCE})
    assert response.status_code == status.HTTP_200_OK

    response = http_client.get(f"/api/v1/portal/preview/{client.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["client"]["id"] == str(client.id)
    assert data["client"]["name"] == client.name

    assert data["closing"] is not None
    assert data["closing"]["competence"] == COMPETENCE
    assert data["closing"]["status"] == "not_started"
    assert data["closing"]["score"] == 0

    # Lists exist even when empty.
    assert isinstance(data["documents"], list)
    assert isinstance(data["guides"], list)
    assert isinstance(data["pendencies"], list)


@pytest.mark.asyncio
async def test_portal_preview_unknown_client_is_404(client_with_auth_a, test_db):
    http_client, user, client, db = client_with_auth_a

    response = http_client.get("/api/v1/portal/preview/00000000-0000-0000-0000-000000000000")
    assert response.status_code == status.HTTP_404_NOT_FOUND
