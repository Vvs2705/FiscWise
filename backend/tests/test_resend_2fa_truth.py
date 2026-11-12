"""/auth/login/resend-2fa devolve o resultado real do envio (B-02).

Antes respondia sent=True mesmo quando o e-mail não saía.
"""

import pytest

from app.api.v1.endpoints import auth as auth_ep
from app.core.auth_rate_limiter import auth_rate_limiter
from app.core.security import create_mfa_token


@pytest.mark.parametrize("ok", [True, False])
async def test_resend_reflete_envio(client_with_auth_a, monkeypatch, ok):
    http, user, _, db = client_with_auth_a
    user.two_factor_method = "email"
    await db.commit()

    async def fake_send(to, subject, html, idempotency_key=None):
        return ok

    monkeypatch.setattr(auth_ep, "send_email", fake_send)
    try:
        r = http.post("/api/v1/auth/login/resend-2fa", json={"mfa_token": create_mfa_token(str(user.id))})
        assert r.status_code == 200, r.text
        assert r.json()["sent"] is ok
    finally:
        auth_rate_limiter._otp_store.pop(str(user.id), None)
