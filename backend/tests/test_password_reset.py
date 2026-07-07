"""Tests for POST /api/v1/auth/forgot-password and /api/v1/auth/reset-password.

Contract (frontend depends on this exactly):
  POST /api/v1/auth/forgot-password {"email"}                → 202 always
  POST /api/v1/auth/reset-password  {"token","new_password"} → 200 ok / 400 erro

E-mail dispatch is monkeypatched — no network calls.
"""

import re
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.security import verify_password
from app.models.user import User

import app.api.v1.endpoints.auth as auth_module


@pytest_asyncio.fixture
async def api_client(test_db):
    """TestClient with get_db overridden (no auth needed — public endpoints)."""
    from app.main import app
    from app.core.deps import get_db

    app.dependency_overrides[get_db] = lambda: test_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def sent_emails(monkeypatch):
    """Capture e-mails instead of sending; returns the capture list."""
    captured = []

    async def fake_send_email(to: str, subject: str, html: str) -> bool:
        captured.append({"to": to, "subject": subject, "html": html})
        return True

    monkeypatch.setattr(auth_module, "send_email", fake_send_email)
    return captured


def _extract_token(html: str) -> str:
    match = re.search(r"reset-password\?token=([\w\-.]+)", html)
    assert match, f"reset link not found in email html: {html}"
    return match.group(1)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forgot_and_reset_password_happy_path(api_client, sent_emails, user_a: User, test_db):
    resp = api_client.post("/api/v1/auth/forgot-password", json={"email": user_a.email})
    assert resp.status_code == 202, resp.text
    assert resp.json() == {"message": "Se o e-mail existir, enviaremos instruções."}

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == user_a.email
    token = _extract_token(sent_emails[0]["html"])

    resp = api_client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NovaSenhaForte123"},
    )
    assert resp.status_code == 200, resp.text

    await test_db.refresh(user_a)
    assert verify_password("NovaSenhaForte123", user_a.hashed_password)


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_still_202_and_no_email(api_client, sent_emails, test_db):
    resp = api_client.post("/api/v1/auth/forgot-password", json={"email": "naoexiste@nada.com"})
    assert resp.status_code == 202
    assert resp.json() == {"message": "Se o e-mail existir, enviaremos instruções."}
    assert sent_emails == []


# ---------------------------------------------------------------------------
# Invalid / expired tokens
# ---------------------------------------------------------------------------


def test_reset_password_invalid_token_returns_400(api_client):
    resp = api_client.post(
        "/api/v1/auth/reset-password",
        json={"token": "lixo-invalido", "new_password": "SenhaValida123"},
    )
    assert resp.status_code == 400
    assert "inválido ou expirado" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_reset_password_expired_token_returns_400(api_client, user_a: User):
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired_token = jwt.encode(
        {"sub": str(user_a.id), "purpose": "pwd_reset", "exp": past},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    resp = api_client.post(
        "/api/v1/auth/reset-password",
        json={"token": expired_token, "new_password": "SenhaValida123"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_wrong_purpose_token_returns_400(api_client, user_a: User):
    """A regular access token (no purpose=pwd_reset) must be rejected."""
    from app.core.security import create_access_token

    access_token = create_access_token(
        user_id=str(user_a.id), tenant_id=str(user_a.tenant_id), role="owner"
    )
    resp = api_client.post(
        "/api/v1/auth/reset-password",
        json={"token": access_token, "new_password": "SenhaValida123"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Weak password
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_password_weak_password_returns_422(api_client, sent_emails, user_a: User):
    api_client.post("/api/v1/auth/forgot-password", json={"email": user_a.email})
    token = _extract_token(sent_emails[0]["html"])

    resp = api_client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "curta"},  # < 8 chars
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forgot_password_rate_limited_after_5(api_client, sent_emails, user_a: User):
    for _ in range(5):
        resp = api_client.post("/api/v1/auth/forgot-password", json={"email": user_a.email})
        assert resp.status_code == 202
    resp = api_client.post("/api/v1/auth/forgot-password", json={"email": user_a.email})
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_register_rate_limited_after_5(api_client, test_db):
    payload = {
        "company_name": "Empresa Spam",
        "owner_password": "SenhaValida123",
        "terms_accepted": True,
    }
    for i in range(5):
        resp = api_client.post(
            "/api/v1/onboarding/register",
            json={**payload, "owner_email": f"spam{i}@empresa.com"},
        )
        assert resp.status_code == 200, resp.text
    resp = api_client.post(
        "/api/v1/onboarding/register",
        json={**payload, "owner_email": "spam99@empresa.com"},
    )
    assert resp.status_code == 429
