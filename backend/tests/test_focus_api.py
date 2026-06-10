from datetime import date, timedelta

import pytest
from fastapi import status

from app.models.operations import DeadlineItem

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_focus_aggregates_real_sources(client_with_auth_a, test_db):
    http_client, user, client, db = client_with_auth_a
    today = date.today()

    # Seed: one overdue and one due-today deadline item for the client.
    db.add_all(
        [
            DeadlineItem(
                tenant_id=user.tenant_id,
                client_id=client.id,
                title="DCTFWeb",
                due_date=today - timedelta(days=2),
            ),
            DeadlineItem(
                tenant_id=user.tenant_id,
                client_id=client.id,
                title="DAS Simples",
                due_date=today,
            ),
        ]
    )
    await db.commit()

    # Seed: fiscal mailbox messages via the real sync endpoint (mock provider).
    response = http_client.post("/api/v1/fiscal-mailbox/sync")
    assert response.status_code == status.HTTP_200_OK

    response = http_client.get("/api/v1/focus")
    assert response.status_code == status.HTTP_200_OK
    items = response.json()["items"]
    assert len(items) > 0

    by_group = {}
    for item in items:
        by_group.setdefault(item["group"], []).append(item)

    # Overdue deadline lands in critical with the overdue suffix.
    critical_titles = [i["title"] for i in by_group.get("critical", [])]
    assert any("DCTFWeb" in t and "atraso" in t for t in critical_titles)

    # Due-today deadline lands in today.
    today_titles = [i["title"] for i in by_group.get("today", [])]
    assert any("DAS Simples" in t for t in today_titles)

    # Mock mailbox has a critical message (Malha Fina) -> critical group, type ecac.
    assert any(i["type"] == "ecac" for i in by_group.get("critical", []))

    # Every item carries an actionable primary action with an href.
    for item in items:
        assert item["primary_action"]["label"]
        assert item["primary_action"]["href"].startswith("/")
        assert item["client"]


@pytest.mark.asyncio
async def test_focus_requires_auth(client):
    response = client.get(
        "/api/v1/focus",
        headers={"X-Tenant-ID": "9df4b224-c8dc-4cdf-9bb6-40af6d206e62"},
    )
    assert response.status_code in (401, 403)
