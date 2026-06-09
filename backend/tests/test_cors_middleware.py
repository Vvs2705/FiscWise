"""Regression tests for CORS middleware ordering (CORRECOES.md C1).

CORSMiddleware must be the OUTERMOST middleware so that every response —
including error responses produced by the inner Tenant/RateLimit
middlewares — carries the Access-Control-Allow-Origin header.

If CORS were inner (the bug these tests guard against), a 400 from the
tenant middleware would reach the browser without CORS headers and surface
as a misleading "CORS policy / ERR_FAILED" network error, which is what made
login appear broken in production.
"""

ALLOWED_ORIGIN = "http://localhost:3000"


def test_preflight_on_login_is_allowed(client):
    """The browser preflight (OPTIONS) for login must be answered with CORS headers."""
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


def test_cors_header_present_on_successful_public_response(client):
    """A normal public response carries the Access-Control-Allow-Origin header."""
    response = client.get("/api/v1/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


def test_cors_header_present_on_inner_middleware_error(client):
    """A 400 produced by the INNER tenant middleware must still carry CORS headers.

    This is the core regression: with CORS as the outermost layer the error
    response from TenantMiddleware is wrapped by CORS on the way out. With the
    old ordering (CORS innermost) this header would be absent.
    """
    response = client.get(
        "/api/v1/clients",
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "TENANT_ID_REQUIRED"
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
