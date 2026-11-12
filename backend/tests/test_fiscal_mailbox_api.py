import pytest
from fastapi import status

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_fiscal_mailbox_workflow(client_with_auth_a, test_db):
    http_client, user, client, db = client_with_auth_a

    # 1. Empty before any sync
    response = http_client.get("/api/v1/fiscal-mailbox/messages")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    # 2. Sync pulls messages from the (mock) provider
    response = http_client.post("/api/v1/fiscal-mailbox/sync")
    assert response.status_code == status.HTTP_200_OK
    sync = response.json()
    assert sync["created"] == 3
    assert sync["skipped"] == 0

    # 3. Sync again is idempotent (deduped by external_id)
    response = http_client.post("/api/v1/fiscal-mailbox/sync")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["created"] == 0
    assert response.json()["skipped"] == 3

    # 4. List returns the ingested messages, all unread
    response = http_client.get("/api/v1/fiscal-mailbox/messages")
    assert response.status_code == status.HTTP_200_OK
    messages = response.json()
    assert len(messages) == 3
    assert all(m["status"] == "unread" for m in messages)

    # 5. Filter by risk
    response = http_client.get("/api/v1/fiscal-mailbox/messages", params={"risk": "critical"})
    assert response.status_code == status.HTTP_200_OK
    critical = response.json()
    assert len(critical) == 1
    assert critical[0]["risk"] == "critical"

    # 6. Opening a message marks it read (unread -> read)
    target_id = critical[0]["id"]
    response = http_client.get(f"/api/v1/fiscal-mailbox/messages/{target_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "read"

    # 7. Resolve a message
    response = http_client.post(f"/api/v1/fiscal-mailbox/messages/{target_id}/resolve")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "resolved"

    # 8. Filter by status reflects the change
    response = http_client.get("/api/v1/fiscal-mailbox/messages", params={"status": "resolved"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1

    # 9. Unknown message id -> 404
    response = http_client.get("/api/v1/fiscal-mailbox/messages/00000000-0000-0000-0000-000000000000")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_fiscal_mailbox_requires_auth(client):
    """Without auth the endpoint must not return data."""
    response = client.get(
        "/api/v1/fiscal-mailbox/messages",
        headers={"X-Tenant-ID": "9df4b224-c8dc-4cdf-9bb6-40af6d206e62"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_mock_mailbox_in_production_returns_503_without_writing(
    client_with_auth_a, test_db, monkeypatch
):
    from sqlalchemy import select
    from app.core.config import settings
    from app.domain.fiscal_mailbox.models import FiscalMailboxMessage

    http_client, _, _, _ = client_with_auth_a
    monkeypatch.setattr(settings, "FISCAL_MAILBOX_PROVIDER", "mock")
    for env in ("production", "staging"):
        monkeypatch.setattr(settings, "ENVIRONMENT", env)
        response = http_client.post("/api/v1/fiscal-mailbox/sync")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["detail"] == "Caixa postal exige SERPRO (não configurado)"
    assert (await test_db.execute(select(FiscalMailboxMessage))).scalars().all() == []

    st = http_client.get("/api/v1/fiscal-mailbox/provider-status").json()
    assert st == {
        "provider": "mock",
        "simulated": True,
        "sync_available": False,
        "message": "Caixa postal exige SERPRO (não configurado)",
    }


@pytest.mark.asyncio
async def test_messages_flag_simulated_in_dev(client_with_auth_a):
    http_client, _, _, _ = client_with_auth_a
    assert http_client.post("/api/v1/fiscal-mailbox/sync").status_code == 200
    messages = http_client.get("/api/v1/fiscal-mailbox/messages").json()
    assert messages and all(m["simulated"] is True and m["provider"] == "mock" for m in messages)
    st = http_client.get("/api/v1/fiscal-mailbox/provider-status").json()
    assert st["simulated"] is True and st["sync_available"] is True
