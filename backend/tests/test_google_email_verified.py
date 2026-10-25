"""Login Google exige e-mail verificado (SEC-16): o login casa pela conta com o mesmo e-mail."""

from app.api.v1.endpoints import auth
from app.core.config import settings


async def test_google_sem_email_verificado_recusa(client, user_a, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(
        auth.google_id_token,
        "verify_oauth2_token",
        lambda *a, **k: {"email": user_a.email, "name": "x", "email_verified": False},
    )
    resp = client.post("/api/v1/auth/google", json={"credential": "fake"})
    assert resp.status_code == 401
