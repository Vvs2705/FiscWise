"""Chave de API autenticando (X-API-Key) nas rotas de operação liberadas."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import auth_rate_limiter as arl
from app.models.api_webhooks import TenantApiKey
from app.models.user import User, UserRole
from app.schemas.developer import ApiKeyCreate
from app.services import api_key_service


def _key_client(test_db, raw_key: str, tenant_id) -> TestClient:
    from app.core.deps import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: test_db
    c = TestClient(app)
    c.headers.update({"X-API-Key": raw_key, "X-Tenant-ID": str(tenant_id)})
    return c


@pytest.fixture
def _cleanup_overrides():
    yield
    from app.main import app

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_key_lists_clients_of_its_tenant(test_db, user_a, client_a, client_b, _cleanup_overrides):
    _, raw = await api_key_service.create_api_key(test_db, ApiKeyCreate(name="ERP"), user_a.tenant_id)
    c = _key_client(test_db, raw, user_a.tenant_id)

    resp = c.get("/api/v1/clients")
    assert resp.status_code == 200, resp.text
    ids = {item["id"] for item in resp.json()}
    assert str(client_a.id) in ids
    assert str(client_b.id) not in ids

    # leitura de um cliente de outro tenant não vaza
    assert c.get(f"/api/v1/clients/{client_b.id}").status_code == 404


@pytest.mark.asyncio
async def test_api_key_can_create_client(test_db, user_a, client_a, _cleanup_overrides):
    _, raw = await api_key_service.create_api_key(test_db, ApiKeyCreate(name="ERP"), user_a.tenant_id)
    c = _key_client(test_db, raw, user_a.tenant_id)
    resp = c.post("/api/v1/clients", json={
        "name": "Cliente via API", "document": "11222333000181", "entity_type": "pj",
    })
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_api_key_with_other_tenant_header_is_forbidden(test_db, user_a, user_b, client_b, _cleanup_overrides):
    _, raw = await api_key_service.create_api_key(test_db, ApiKeyCreate(name="ERP"), user_a.tenant_id)
    c = _key_client(test_db, raw, user_b.tenant_id)
    assert c.get("/api/v1/clients").status_code == 403


@pytest.mark.asyncio
async def test_key_of_other_tenant_does_not_see_clients(test_db, user_a, user_b, client_a, client_b, _cleanup_overrides):
    # tenant B não tem OWNER na fixture; cria um para a chave resolver
    owner_b = User(
        id=uuid.uuid4(), email="owner.b@firma-b.com", hashed_password="x",
        full_name="Owner B", tenant_id=user_b.tenant_id, role=UserRole.OWNER, is_active=True,
    )
    test_db.add(owner_b)
    await test_db.commit()
    _, raw_b = await api_key_service.create_api_key(test_db, ApiKeyCreate(name="ERP B"), user_b.tenant_id)
    c = _key_client(test_db, raw_b, user_b.tenant_id)
    ids = {item["id"] for item in c.get("/api/v1/clients").json()}
    assert str(client_a.id) not in ids
    assert str(client_b.id) in ids


@pytest.mark.asyncio
async def test_revoked_key_returns_401(test_db, user_a, client_a, _cleanup_overrides):
    key, raw = await api_key_service.create_api_key(test_db, ApiKeyCreate(name="ERP"), user_a.tenant_id)
    await api_key_service.revoke_api_key(test_db, key.id, user_a.tenant_id)
    c = _key_client(test_db, raw, user_a.tenant_id)
    assert c.get("/api/v1/clients").status_code == 401


@pytest.mark.asyncio
async def test_invalid_key_returns_401(test_db, user_a, _cleanup_overrides):
    c = _key_client(test_db, "fw_live_naoexiste", user_a.tenant_id)
    assert c.get("/api/v1/clients").status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/api/v1/auth/me",
    "/api/v1/developer/api-keys",
    "/api/v1/developer/webhooks",
    "/api/v1/dashboard/overview",
    "/api/v1/certificates",
])
async def test_api_key_rejected_on_jwt_only_routes(test_db, user_a, path, _cleanup_overrides):
    _, raw = await api_key_service.create_api_key(test_db, ApiKeyCreate(name="ERP"), user_a.tenant_id)
    c = _key_client(test_db, raw, user_a.tenant_id)
    assert c.get(path).status_code == 401


@pytest.mark.asyncio
async def test_api_key_cannot_create_more_keys(test_db, user_a, _cleanup_overrides):
    _, raw = await api_key_service.create_api_key(test_db, ApiKeyCreate(name="ERP"), user_a.tenant_id)
    c = _key_client(test_db, raw, user_a.tenant_id)
    assert c.post("/api/v1/developer/api-keys", json={"name": "escalada"}).status_code == 401


@pytest.mark.asyncio
async def test_api_key_routes_cover_operations(test_db, user_a, client_a, _cleanup_overrides):
    _, raw = await api_key_service.create_api_key(test_db, ApiKeyCreate(name="ERP"), user_a.tenant_id)
    c = _key_client(test_db, raw, user_a.tenant_id)
    for path in ("/api/v1/deadlines", "/api/v1/documents", "/api/v1/receivables",
                 "/api/v1/obligations/instances", "/api/v1/invoices", "/api/v1/guias"):
        assert c.get(path).status_code == 200, path


@pytest.mark.asyncio
async def test_last_used_at_is_recorded(test_db, user_a, client_a, _cleanup_overrides):
    key, raw = await api_key_service.create_api_key(test_db, ApiKeyCreate(name="ERP"), user_a.tenant_id)
    assert key.last_used_at is None
    c = _key_client(test_db, raw, user_a.tenant_id)
    c.get("/api/v1/clients")
    row = (await test_db.execute(select(TenantApiKey).where(TenantApiKey.id == key.id))).scalar_one()
    await test_db.refresh(row)
    assert row.last_used_at is not None


@pytest.mark.asyncio
async def test_rate_limit_per_key(test_db, user_a, client_a, monkeypatch, _cleanup_overrides):
    monkeypatch.setattr(arl, "API_KEY_MAX_REQUESTS", 2)
    monkeypatch.setattr(arl, "_redis", None)
    _, raw = await api_key_service.create_api_key(test_db, ApiKeyCreate(name="ERP"), user_a.tenant_id)
    c = _key_client(test_db, raw, user_a.tenant_id)
    assert c.get("/api/v1/clients").status_code == 200
    assert c.get("/api/v1/clients").status_code == 200
    resp = c.get("/api/v1/clients")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_jwt_still_works_on_principal_routes(client_with_auth_a):
    c, _, client_a, _ = client_with_auth_a
    resp = c.get("/api/v1/clients")
    assert resp.status_code == 200
    assert str(client_a.id) in {i["id"] for i in resp.json()}


@pytest.mark.asyncio
async def test_no_credentials_returns_401(test_db, user_a, _cleanup_overrides):
    from app.core.deps import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: test_db
    c = TestClient(app)
    assert c.get("/api/v1/clients", headers={"X-Tenant-ID": str(user_a.tenant_id)}).status_code == 401
