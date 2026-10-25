"""/auth/2fa/confirm-email bloqueia após 5 códigos errados (SEC-7)."""

from app.core.auth_rate_limiter import auth_rate_limiter


async def test_confirm_email_bloqueia_forca_bruta(client_with_auth_a):
    http, user, _, _ = client_with_auth_a
    auth_rate_limiter._otp_store.pop(str(user.id), None)
    try:
        codes = [
            http.post(
                "/api/v1/auth/2fa/confirm-email", json={"otp_code": "000000"}
            ).status_code
            for _ in range(6)
        ]
        assert codes[:5] == [400] * 5
        assert codes[5] == 429
    finally:
        auth_rate_limiter._otp_store.pop(str(user.id), None)
