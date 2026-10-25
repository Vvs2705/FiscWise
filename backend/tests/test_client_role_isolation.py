"""Usuário CLIENT (portal) não pode usar rotas de equipe do escritório.

Antes: o JWT do portal valia em /operations/clients, /reports etc. e o cliente
via os dados de todos os outros clientes do mesmo escritório (TEN-1).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole


@pytest.fixture
async def portal_client_http(test_db, tenant_a, client_a):
    from app.core.deps import get_db
    from app.main import app

    user = User(
        id=uuid.uuid4(),
        email="cliente.portal@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Cliente Portal",
        tenant_id=tenant_a.id,
        role=UserRole.CLIENT,
        is_active=True,
    )
    test_db.add(user)
    client_a.portal_user_id = user.id
    await test_db.commit()

    app.dependency_overrides[get_db] = lambda: test_db
    http = TestClient(app)
    token = create_access_token(
        user_id=str(user.id), tenant_id=str(tenant_a.id), role=UserRole.CLIENT.value
    )
    http.headers.update(
        {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_a.id)}
    )
    yield http
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/clients",
        "/api/v1/receivables",
        "/api/v1/reports/summary",
        "/api/v1/guias",
        "/api/v1/invoices",
    ],
)
async def test_client_role_blocked_from_staff_routes(portal_client_http, path):
    resp = portal_client_http.get(path)
    assert resp.status_code == 403, f"{path} -> {resp.status_code}"


async def test_client_role_keeps_portal_and_own_account(portal_client_http):
    assert portal_client_http.get("/api/v1/portal/my-data").status_code != 403
    assert portal_client_http.get("/api/v1/auth/me").status_code == 200
