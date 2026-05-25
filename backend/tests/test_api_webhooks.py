"""Integration tests for Phase 12 — Public API Keys & Webhook Subscriptions."""

import uuid
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from app.models.api_webhooks import TenantApiKey, WebhookSubscription, WebhookDeliveryLog
from app.services import api_key_service, webhook_service


class TestApiKeysCRUD:
    """Tests for API key creation, listing, and revocation."""

    @pytest.mark.asyncio
    async def test_create_api_key_returns_raw_key_once(self, client_with_auth_a, test_db):
        """Creating a key returns the raw key in the response exactly once."""
        client, user_a, _, _ = client_with_auth_a

        response = client.post(
            "/api/v1/developer/api-keys",
            json={"name": "Chave de Integração ERP"}
        )
        assert response.status_code == 201
        data = response.json()
        assert "raw_key" in data
        assert data["raw_key"].startswith("fw_live_")
        assert data["name"] == "Chave de Integração ERP"
        assert data["is_active"] is True
        assert "prefix" in data
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_api_keys(self, client_with_auth_a, test_db):
        """Listing keys shows all active/inactive keys but never raw keys."""
        client, user_a, _, _ = client_with_auth_a

        # Create two keys
        client.post("/api/v1/developer/api-keys", json={"name": "Chave 1"})
        client.post("/api/v1/developer/api-keys", json={"name": "Chave 2"})

        response = client.get("/api/v1/developer/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for key_item in data:
            assert "raw_key" not in key_item
            assert "key_hash" not in key_item

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, client_with_auth_a, test_db):
        """Revoking a key sets is_active=False."""
        client, user_a, _, _ = client_with_auth_a

        create_resp = client.post(
            "/api/v1/developer/api-keys",
            json={"name": "Chave Temporária"}
        )
        assert create_resp.status_code == 201
        key_id = create_resp.json()["id"]

        # Revoke
        revoke_resp = client.delete(f"/api/v1/developer/api-keys/{key_id}")
        assert revoke_resp.status_code == 204

        # Verify DB state
        stmt = select(TenantApiKey).where(TenantApiKey.id == uuid.UUID(key_id))
        result = await test_db.execute(stmt)
        db_key = result.scalar_one_or_none()
        assert db_key is not None
        assert db_key.is_active is False

    @pytest.mark.asyncio
    async def test_revoke_unknown_key_returns_404(self, client_with_auth_a, test_db):
        """Revoking a non-existent key returns 404."""
        client, _, _, _ = client_with_auth_a
        response = client.delete(f"/api/v1/developer/api-keys/{uuid.uuid4()}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_tenant_isolation_api_keys(self, client_with_auth_a, client_with_auth_b, test_db):
        """Tenant A cannot see or revoke Tenant B's keys."""
        client_a, user_a, _, _ = client_with_auth_a
        client_b, user_b, _, _ = client_with_auth_b

        # Create a key for Tenant A
        resp_a = client_a.post("/api/v1/developer/api-keys", json={"name": "Chave A"})
        key_id_a = resp_a.json()["id"]

        # Tenant B listing should not include Tenant A's key
        resp_b_list = client_b.get("/api/v1/developer/api-keys")
        assert resp_b_list.status_code == 200
        ids_b = [k["id"] for k in resp_b_list.json()]
        assert key_id_a not in ids_b

        # Tenant B cannot revoke Tenant A's key
        resp_b_revoke = client_b.delete(f"/api/v1/developer/api-keys/{key_id_a}")
        assert resp_b_revoke.status_code == 404


class TestApiKeyService:
    """Unit tests for api_key_service helpers."""

    @pytest.mark.asyncio
    async def test_key_hash_verification(self, test_db, tenant_a):
        """Raw key can be re-hashed to verify against stored hash."""
        from app.schemas.developer import ApiKeyCreate
        payload = ApiKeyCreate(name="Test Verification Key")
        key_obj, raw_key = await api_key_service.create_api_key(test_db, payload, tenant_a.id)

        # Verify returns the key and updates last_used_at
        verified = await api_key_service.verify_api_key(test_db, raw_key)
        assert verified is not None
        assert verified.id == key_obj.id
        assert verified.last_used_at is not None

    @pytest.mark.asyncio
    async def test_verify_invalid_key_returns_none(self, test_db, tenant_a):
        """Verifying a fake raw key returns None."""
        result = await api_key_service.verify_api_key(test_db, "fw_live_invalidkey000000000000000000000000000000")
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_revoked_key_returns_none(self, test_db, tenant_a):
        """Verifying a revoked key returns None."""
        from app.schemas.developer import ApiKeyCreate
        payload = ApiKeyCreate(name="Revoked Key Test")
        key_obj, raw_key = await api_key_service.create_api_key(test_db, payload, tenant_a.id)
        await api_key_service.revoke_api_key(test_db, key_obj.id, tenant_a.id)
        result = await api_key_service.verify_api_key(test_db, raw_key)
        assert result is None


class TestWebhookSubscriptionCRUD:
    """Tests for webhook subscription management."""

    @pytest.mark.asyncio
    async def test_create_webhook_subscription_returns_secret_once(self, client_with_auth_a, test_db):
        """Creating a subscription returns the signing secret exactly once."""
        client, _, _, _ = client_with_auth_a
        payload = {
            "url": "https://example.com/webhook/receive",
            "events": ["client.created", "das.paid"]
        }
        response = client.post("/api/v1/developer/webhooks", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "signing_secret" in data
        assert data["signing_secret"].startswith("whsec_")
        assert data["url"] == payload["url"]
        assert "client.created" in data["events"]
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_webhooks(self, client_with_auth_a, test_db):
        """Listing subscriptions hides the signing secret."""
        client, _, _, _ = client_with_auth_a
        client.post("/api/v1/developer/webhooks", json={
            "url": "https://example.com/wh1",
            "events": ["client.created"]
        })
        response = client.get("/api/v1/developer/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        for item in data:
            assert "signing_secret" not in item

    @pytest.mark.asyncio
    async def test_update_webhook(self, client_with_auth_a, test_db):
        """Updating a webhook changes its URL/events/status."""
        client, _, _, _ = client_with_auth_a
        create_resp = client.post("/api/v1/developer/webhooks", json={
            "url": "https://example.com/old-webhook",
            "events": ["client.created"]
        })
        sub_id = create_resp.json()["id"]

        update_resp = client.put(f"/api/v1/developer/webhooks/{sub_id}", json={
            "url": "https://example.com/new-webhook",
            "events": ["das.paid"],
            "is_active": False
        })
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["url"] == "https://example.com/new-webhook"
        assert updated["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_webhook(self, client_with_auth_a, test_db):
        """Deleting a webhook removes it from the DB."""
        client, _, _, _ = client_with_auth_a
        create_resp = client.post("/api/v1/developer/webhooks", json={
            "url": "https://example.com/deletable",
            "events": ["document.uploaded"]
        })
        sub_id = create_resp.json()["id"]

        delete_resp = client.delete(f"/api/v1/developer/webhooks/{sub_id}")
        assert delete_resp.status_code == 204

        stmt = select(WebhookSubscription).where(WebhookSubscription.id == uuid.UUID(sub_id))
        res = await test_db.execute(stmt)
        assert res.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_create_webhook_invalid_event_returns_422(self, client_with_auth_a, test_db):
        """Creating a subscription with an invalid event type returns 422."""
        client, _, _, _ = client_with_auth_a
        response = client.post("/api/v1/developer/webhooks", json={
            "url": "https://example.com/wh",
            "events": ["invalid.event.type"]
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_available_events_endpoint(self, client_with_auth_a):
        """GET /developer/webhooks/events returns the valid event list."""
        client, _, _, _ = client_with_auth_a
        response = client.get("/api/v1/developer/webhooks/events")
        assert response.status_code == 200
        events = response.json()
        assert "client.created" in events
        assert "das.paid" in events


class TestWebhookDispatch:
    """Tests for the webhook dispatch service logic."""

    @pytest.mark.asyncio
    async def test_dispatch_event_fires_to_matching_subscriptions(self, test_db, tenant_a):
        """dispatch_event creates asyncio tasks for matching active subscriptions."""
        from app.schemas.developer import WebhookSubscriptionCreate

        payload = WebhookSubscriptionCreate(
            url="https://example.com/target",
            events=["client.created"]
        )
        sub, _ = await webhook_service.create_webhook_subscription(test_db, payload, tenant_a.id)
        assert sub.id is not None

        # Patch the HTTP client to avoid real HTTP requests
        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client_cls:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.text = '{"ok": true}'
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_cls.return_value)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value.post = AsyncMock(return_value=mock_resp)

            await webhook_service.dispatch_event(
                db=test_db,
                tenant_id=tenant_a.id,
                event="client.created",
                data={"id": str(uuid.uuid4()), "name": "Empresa Teste"}
            )

    @pytest.mark.asyncio
    async def test_dispatch_event_skips_inactive_subscriptions(self, test_db, tenant_a):
        """dispatch_event does not fire for inactive subscriptions."""
        from app.schemas.developer import WebhookSubscriptionCreate, WebhookSubscriptionUpdate

        payload = WebhookSubscriptionCreate(
            url="https://example.com/inactive",
            events=["client.created"]
        )
        sub, _ = await webhook_service.create_webhook_subscription(test_db, payload, tenant_a.id)
        # Deactivate
        await webhook_service.update_webhook_subscription(
            test_db, sub.id, tenant_a.id,
            WebhookSubscriptionUpdate(is_active=False)
        )

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.post = AsyncMock()
            await webhook_service.dispatch_event(
                db=test_db,
                tenant_id=tenant_a.id,
                event="client.created",
                data={"id": "xxx"}
            )
            # post should NOT have been called
            mock_client_cls.return_value.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_event_skips_non_subscribed_events(self, test_db, tenant_a):
        """dispatch_event does not fire if event is not in subscription.events list."""
        from app.schemas.developer import WebhookSubscriptionCreate

        payload = WebhookSubscriptionCreate(
            url="https://example.com/narrow",
            events=["das.paid"]  # Does NOT subscribe to client.created
        )
        await webhook_service.create_webhook_subscription(test_db, payload, tenant_a.id)

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.post = AsyncMock()
            await webhook_service.dispatch_event(
                db=test_db,
                tenant_id=tenant_a.id,
                event="client.created",  # Not in subscription events
                data={}
            )
            mock_client_cls.return_value.post.assert_not_called()
