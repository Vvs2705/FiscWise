from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.v1.endpoints import admin, diagnostic
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware


def test_admin_router_does_not_expose_legacy_enum_fix_routes():
    paths = {route.path for route in admin.router.routes}

    assert "/fix-enum-case" not in paths
    assert "/fix-enum-case-raw" not in paths
    assert "/set-plan-by-email" in paths
    assert "/tenant-by-email" in paths


def test_diagnostics_return_not_found_when_feature_flag_is_disabled(monkeypatch):
    monkeypatch.setattr(diagnostic.settings, "DIAGNOSTICS_ENABLED", False)

    app = FastAPI()
    app.include_router(diagnostic.router, prefix="/diagnostic")

    response = TestClient(app).get("/diagnostic/health-detailed")

    assert response.status_code == 404
    assert response.json()["detail"] == "Diagnostic endpoints are disabled"


def test_diagnostics_still_require_authentication_when_feature_flag_is_enabled(monkeypatch):
    monkeypatch.setattr(diagnostic.settings, "DIAGNOSTICS_ENABLED", True)

    app = FastAPI()
    app.include_router(diagnostic.router, prefix="/diagnostic")

    response = TestClient(app).get("/diagnostic/health-detailed")

    assert response.status_code == 401


def test_rate_limit_strict_mode_defaults_to_settings_when_not_explicit(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_STRICT", True)

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, redis_url=None)

    @app.get("/api/v1/admin/tenant-by-email")
    async def protected_endpoint():
        return {"status": "called"}

    response = TestClient(app).get("/api/v1/admin/tenant-by-email")

    assert response.status_code == 503
    assert response.json()["error_code"] == "RATE_LIMIT_UNAVAILABLE"


def test_rate_limit_strict_mode_returns_503_when_redis_is_unavailable():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, redis_url=None, strict=True)

    @app.get("/api/v1/admin/tenant-by-email")
    async def protected_endpoint():
        return {"status": "called"}

    response = TestClient(app).get("/api/v1/admin/tenant-by-email")

    assert response.status_code == 503
    assert response.json()["error_code"] == "RATE_LIMIT_UNAVAILABLE"


def test_rate_limit_non_strict_mode_fails_open_when_redis_is_unavailable():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, redis_url=None, strict=False)

    @app.get("/api/v1/admin/tenant-by-email")
    async def protected_endpoint():
        return JSONResponse({"status": "called"})

    response = TestClient(app).get("/api/v1/admin/tenant-by-email")

    assert response.status_code == 200
    assert response.json() == {"status": "called"}
