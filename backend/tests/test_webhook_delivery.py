"""Webhooks verificáveis: HMAC com o segredo cru, retry, sessão própria e eventos."""

import hashlib
import hmac
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy import select

from app.models.api_webhooks import WebhookDeliveryLog, WebhookSubscription
from app.schemas.developer import WebhookSubscriptionCreate
from app.services import webhook_service


class _FakeHttp:
    """Substitui httpx.AsyncClient: devolve as respostas na ordem e guarda as chamadas."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.kwargs = kwargs
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, content=None, headers=None):
        self.calls.append({"url": url, "content": content, "headers": headers})
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        resp = MagicMock()
        resp.status_code = r
        resp.text = "ok"
        return resp


@pytest.fixture
def no_sleep(monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(webhook_service, "_sleep", fake_sleep)
    return sleeps


async def _subscribe(db, tenant_id, events=("client.created",)):
    return await webhook_service.create_webhook_subscription(
        db, WebhookSubscriptionCreate(url="https://example.com/hook", events=list(events)), tenant_id
    )


async def _logs(db):
    db.expire_all()
    return list((await db.execute(select(WebhookDeliveryLog))).scalars().all())


@pytest.mark.asyncio
async def test_secret_is_stored_encrypted_not_plain(test_db, tenant_a):
    sub, raw = await _subscribe(test_db, tenant_a.id)
    assert raw not in sub.secret
    assert sub.secret.startswith("enc:v1:")
    assert webhook_service.decrypt_secret(sub.secret) == raw
    assert sub.signature_scheme == "hmac-sha256-v1"


@pytest.mark.asyncio
async def test_signature_is_verifiable_with_raw_secret(test_db, tenant_a, no_sleep, monkeypatch):
    sub, raw_secret = await _subscribe(test_db, tenant_a.id)
    fake = _FakeHttp([200])
    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", fake)

    await webhook_service.dispatch_event(test_db, tenant_a.id, "client.created", {"id": "c1"})
    await webhook_service.wait_for_deliveries()

    assert len(fake.calls) == 1
    call = fake.calls[0]
    headers, body = call["headers"], call["content"]
    assert headers["X-FiscWise-Event"] == "client.created"
    uuid.UUID(headers["X-FiscWise-Delivery"])
    parts = dict(p.split("=", 1) for p in headers["X-FiscWise-Signature"].split(","))
    expected = hmac.new(raw_secret.encode(), f"{parts['t']}.".encode() + body, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(parts["v1"], expected)
    payload = json.loads(body)
    assert payload["event"] == "client.created"
    assert payload["id"] == headers["X-FiscWise-Delivery"]
    assert fake.kwargs["timeout"] == 10


@pytest.mark.asyncio
async def test_retry_with_backoff_then_success(test_db, tenant_a, no_sleep, monkeypatch):
    await _subscribe(test_db, tenant_a.id)
    fake = _FakeHttp([httpx.ConnectError("down"), 503, 200])
    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", fake)

    await webhook_service.dispatch_event(test_db, tenant_a.id, "client.created", {"id": "c1"})
    await webhook_service.wait_for_deliveries()

    assert len(fake.calls) == 3
    assert no_sleep == [1, 5]
    delivery_ids = {c["headers"]["X-FiscWise-Delivery"] for c in fake.calls}
    assert len(delivery_ids) == 1  # mesma entrega em todas as tentativas
    logs = await _logs(test_db)
    assert [l.success for l in sorted(logs, key=lambda l: l.created_at)].count(True) == 1
    assert len(logs) == 3
    assert any(l.status_code is None and "ConnectError" in (l.response_body or "") for l in logs)
    assert any(l.status_code == 503 for l in logs)


@pytest.mark.asyncio
async def test_retry_gives_up_after_three_retries(test_db, tenant_a, no_sleep, monkeypatch):
    await _subscribe(test_db, tenant_a.id)
    fake = _FakeHttp([500, 500, 500, 500])
    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", fake)
    await webhook_service.dispatch_event(test_db, tenant_a.id, "client.created", {})
    await webhook_service.wait_for_deliveries()
    assert len(fake.calls) == 4
    assert no_sleep == [1, 5, 25]
    assert all(not l.success for l in await _logs(test_db))


@pytest.mark.asyncio
async def test_client_error_is_not_retried(test_db, tenant_a, no_sleep, monkeypatch):
    await _subscribe(test_db, tenant_a.id)
    fake = _FakeHttp([400])
    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", fake)
    await webhook_service.dispatch_event(test_db, tenant_a.id, "client.created", {})
    await webhook_service.wait_for_deliveries()
    assert len(fake.calls) == 1 and no_sleep == []


@pytest.mark.asyncio
async def test_delivery_uses_own_session_not_request_session(test_db, tenant_a, no_sleep, monkeypatch):
    sub, _ = await _subscribe(test_db, tenant_a.id)
    fake = _FakeHttp([200])
    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", fake)

    request_db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [sub]
    request_db.execute = AsyncMock(return_value=result)
    request_db.commit = AsyncMock()

    await webhook_service.dispatch_event(request_db, tenant_a.id, "client.created", {"id": "x"})
    await webhook_service.wait_for_deliveries()

    request_db.add.assert_not_called()
    request_db.commit.assert_not_awaited()
    logs = await _logs(test_db)
    assert len(logs) == 1 and logs[0].success


@pytest.mark.asyncio
async def test_tasks_are_tracked_until_done(test_db, tenant_a, no_sleep, monkeypatch):
    await _subscribe(test_db, tenant_a.id)
    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", _FakeHttp([200]))
    await webhook_service.dispatch_event(test_db, tenant_a.id, "client.created", {})
    assert len(webhook_service._background_tasks) == 1
    await webhook_service.wait_for_deliveries()
    assert not webhook_service._background_tasks


@pytest.mark.asyncio
async def test_dispatch_failure_never_raises(tenant_a):
    broken = MagicMock()
    broken.execute = AsyncMock(side_effect=RuntimeError("db fora"))
    await webhook_service.dispatch_event(broken, tenant_a.id, "client.created", {})


@pytest.mark.asyncio
async def test_legacy_hash_subscription_still_delivers_and_is_flagged(test_db, tenant_a, no_sleep, monkeypatch):
    legacy = WebhookSubscription(
        id=uuid.uuid4(), tenant_id=tenant_a.id, url="https://example.com/old",
        secret=hashlib.sha256(b"whsec_old").hexdigest(), events=["client.created"], is_active=True,
    )
    test_db.add(legacy)
    await test_db.commit()
    assert legacy.signature_scheme == "legacy"
    fake = _FakeHttp([200])
    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", fake)
    await webhook_service.dispatch_event(test_db, tenant_a.id, "client.created", {})
    await webhook_service.wait_for_deliveries()
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_rotate_secret_endpoint(client_with_auth_a):
    c, _, _, _ = client_with_auth_a
    created = c.post("/api/v1/developer/webhooks", json={
        "url": "https://example.com/r", "events": ["client.created"],
    }).json()
    assert created["signature_scheme"] == "hmac-sha256-v1"
    assert created["signature_header"] == "X-FiscWise-Signature"
    rotated = c.post(f"/api/v1/developer/webhooks/{created['id']}/rotate-secret")
    assert rotated.status_code == 200
    assert rotated.json()["signing_secret"] != created["signing_secret"]
    assert c.post(f"/api/v1/developer/webhooks/{uuid.uuid4()}/rotate-secret").status_code == 404


# ── eventos disparados pelos endpoints ───────────────────────────────────────

@pytest.fixture
def dispatched(monkeypatch):
    calls = []

    async def fake_dispatch(db, tenant_id, event, data):
        calls.append((event, data))

    monkeypatch.setattr(webhook_service, "dispatch_event", fake_dispatch)
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["patch", "put"])
async def test_client_update_fires_client_updated(client_with_auth_a, dispatched, method):
    c, _, client_a, _ = client_with_auth_a
    resp = getattr(c, method)(f"/api/v1/clients/{client_a.id}", json={"name": "Nome Novo"})
    assert resp.status_code == 200, resp.text
    events = [e for e, _ in dispatched]
    assert events == ["client.updated"]
    assert dispatched[0][1]["id"] == str(client_a.id)
    assert dispatched[0][1]["name"] == "Nome Novo"
    assert "name" in dispatched[0][1]["changed_fields"]


@pytest.mark.asyncio
async def test_obligation_delivered_fires_once(client_with_auth_a, dispatched):
    from datetime import date

    from app.models.obligation import ObligationInstance

    c, user_a, client_a, db = client_with_auth_a
    inst = ObligationInstance(
        id=uuid.uuid4(), tenant_id=user_a.tenant_id, client_id=client_a.id,
        competence_month=date(2026, 10, 1), due_date=date(2026, 11, 20), status="pending",
    )
    db.add(inst)
    await db.commit()

    assert c.patch(f"/api/v1/obligations/instances/{inst.id}", json={"notes": "x"}).status_code == 200
    assert dispatched == []
    assert c.patch(f"/api/v1/obligations/instances/{inst.id}", json={"status": "delivered"}).status_code == 200
    assert [e for e, _ in dispatched] == ["obligation.completed"]
    # repetir "delivered" é idempotente: não dispara de novo
    assert c.patch(f"/api/v1/obligations/instances/{inst.id}", json={"status": "delivered"}).status_code == 200
    assert len(dispatched) == 1


@pytest.mark.asyncio
async def test_client_document_upload_fires_document_uploaded(client_with_auth_a, dispatched, monkeypatch):
    from app.api.v1.endpoints import operations

    c, _, client_a, _ = client_with_auth_a

    async def fake_upload(bucket, path, data, content_type="application/octet-stream", **kw):
        return path

    monkeypatch.setattr("app.core.storage.upload_bytes", fake_upload)
    monkeypatch.setattr(operations, "_parse_document_background", lambda *a, **k: None)
    resp = c.post(
        f"/api/v1/clients/{client_a.id}/documents?document_type=contract",
        files={"file": ("contrato.pdf", b"%PDF-1.7 teste")},
    )
    assert resp.status_code == 200, resp.text
    assert [e for e, _ in dispatched] == ["document.uploaded"]
    assert dispatched[0][1]["id"] == resp.json()["id"]
    assert dispatched[0][1]["client_id"] == str(client_a.id)
