"""GET /portal/my-overview: tela do cliente final no portal.

O cliente só pode ver o próprio agregado. Outro cliente do MESMO escritório
não pode aparecer, e equipe do escritório não usa esta rota (usa /preview).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.models.operations import AccountingClient, ClientDocument
from app.models.user import User, UserRole

pytestmark = pytest.mark.integration


@pytest.fixture
async def portal_http(test_db, tenant_a, client_a):
    from app.core.deps import get_db
    from app.main import app

    user = User(
        id=uuid.uuid4(),
        email="cliente.overview@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Cliente Overview",
        tenant_id=tenant_a.id,
        role=UserRole.CLIENT,
        is_active=True,
    )
    test_db.add(user)
    client_a.portal_user_id = user.id

    # Outro cliente do mesmo escritório, com documento próprio.
    neighbor = AccountingClient(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        name="Vizinho do Mesmo Escritorio",
        document="11222333000181",
        entity_type="pj",
        status="active",
    )
    test_db.add(neighbor)
    test_db.add(ClientDocument(tenant_id=tenant_a.id, client_id=client_a.id, name="Extrato proprio"))
    test_db.add(ClientDocument(tenant_id=tenant_a.id, client_id=neighbor.id, name="Extrato do vizinho"))
    await test_db.commit()

    app.dependency_overrides[get_db] = lambda: test_db
    http = TestClient(app)
    token = create_access_token(
        user_id=str(user.id), tenant_id=str(tenant_a.id), role=UserRole.CLIENT.value
    )
    http.headers.update({"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_a.id)})
    yield http, client_a, neighbor
    app.dependency_overrides.clear()


async def test_client_sees_own_overview(portal_http):
    http, client, _ = portal_http

    resp = http.get("/api/v1/portal/my-overview")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["client"]["id"] == str(client.id)
    assert data["closing"] is None
    assert [d["name"] for d in data["documents"]] == ["Extrato proprio"]
    assert isinstance(data["guides"], list)
    assert isinstance(data["pendencies"], list)


async def test_client_overview_never_shows_neighbor_data(portal_http):
    http, _, neighbor = portal_http

    body = http.get("/api/v1/portal/my-overview").text
    assert str(neighbor.id) not in body
    assert "Extrato do vizinho" not in body


async def test_client_still_blocked_from_staff_preview(portal_http):
    http, _, neighbor = portal_http

    assert http.get(f"/api/v1/portal/preview/{neighbor.id}").status_code == 403


async def test_staff_cannot_use_client_overview(client_with_auth_a):
    http, *_ = client_with_auth_a

    assert http.get("/api/v1/portal/my-overview").status_code == 403


async def test_client_user_without_linked_client_is_404(test_db, tenant_a):
    from app.core.deps import get_db
    from app.main import app

    orphan = User(
        id=uuid.uuid4(),
        email="sem.vinculo@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Sem Vinculo",
        tenant_id=tenant_a.id,
        role=UserRole.CLIENT,
        is_active=True,
    )
    test_db.add(orphan)
    await test_db.commit()

    app.dependency_overrides[get_db] = lambda: test_db
    try:
        http = TestClient(app)
        token = create_access_token(
            user_id=str(orphan.id), tenant_id=str(tenant_a.id), role=UserRole.CLIENT.value
        )
        http.headers.update({"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_a.id)})
        assert http.get("/api/v1/portal/my-overview").status_code == 404
    finally:
        app.dependency_overrides.clear()
