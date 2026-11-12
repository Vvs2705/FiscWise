"""/api/v1/db-test atrás de DIAGNOSTICS_ENABLED e /api/v1/ready sem vazar exceção."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.deps import get_db
from app.core.middleware import _EXCLUDED_PREFIXES


def test_db_test_fora_da_allowlist_publica():
    assert "/api/v1/db-test" not in _EXCLUDED_PREFIXES


async def test_db_test_desligado_404(client_with_auth_a, monkeypatch):
    http, *_ = client_with_auth_a
    monkeypatch.setattr(settings, "DIAGNOSTICS_ENABLED", False)
    assert http.get("/api/v1/db-test").status_code == 404


async def test_db_test_ligado_exige_login(client_with_auth_a, monkeypatch):
    http, user_a, *_ = client_with_auth_a
    monkeypatch.setattr(settings, "DIAGNOSTICS_ENABLED", True)
    resp = http.get("/api/v1/db-test")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "success", "users_count": 1}

    anon = TestClient(http.app)
    anon.headers["X-Tenant-ID"] = str(user_a.tenant_id)
    assert anon.get("/api/v1/db-test").status_code in (401, 403)


def test_ready_nao_vaza_erro():
    from app.main import app

    class _Broken:
        async def execute(self, *a, **k):
            raise RuntimeError("password authentication failed for user fiscwise at 10.0.0.3")

    app.dependency_overrides[get_db] = lambda: _Broken()
    try:
        resp = TestClient(app).get("/api/v1/ready")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 503
    assert resp.json() == {"status": "not_ready"}
