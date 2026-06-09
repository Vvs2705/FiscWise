"""Security foundation tests for tenant middleware boundaries."""

import uuid


def test_health_endpoints_are_public_without_tenant_header(client):
    root_response = client.get("/health")
    api_response = client.get("/api/v1/health")

    assert root_response.status_code == 200
    assert api_response.status_code == 200
    assert api_response.json()["status"] == "healthy"


def test_root_probes_are_public_without_tenant_header(client):
    """Root liveness/readiness probes (used by the Fly.io health check) must not
    be blocked by the tenant middleware. They may return 200/503 depending on DB
    state, but never 400 TENANT_ID_REQUIRED."""
    live_response = client.get("/live")
    ready_response = client.get("/ready")

    assert live_response.status_code == 200
    assert ready_response.status_code != 400
    assert ready_response.json().get("error_code") != "TENANT_ID_REQUIRED"


def test_protected_route_requires_tenant_header(client):
    response = client.get("/api/v1/clients")

    assert response.status_code == 400
    assert response.json()["error_code"] == "TENANT_ID_REQUIRED"


def test_protected_route_rejects_invalid_tenant_uuid(client):
    response = client.get("/api/v1/clients", headers={"X-Tenant-ID": "not-a-uuid"})

    assert response.status_code == 400
    assert response.json()["error_code"] == "TENANT_ID_INVALID"


def test_auth_routes_are_public_without_tenant_header(client):
    logout_response = client.post("/api/v1/auth/logout")
    login_validation_response = client.post("/api/v1/auth/login", data={})

    assert logout_response.status_code == 200
    assert login_validation_response.status_code == 422
    assert login_validation_response.json().get("error_code") != "TENANT_ID_REQUIRED"


def test_onboarding_routes_are_public_without_tenant_header(client):
    response = client.get("/api/v1/onboarding/health")

    assert response.status_code == 200
    assert response.json()["endpoint"] == "/api/v1/onboarding/register"


def test_unknown_route_with_valid_tenant_reaches_router(client):
    response = client.get(
        "/api/v1/does-not-exist",
        headers={"X-Tenant-ID": str(uuid.uuid4())},
    )

    assert response.status_code == 404
