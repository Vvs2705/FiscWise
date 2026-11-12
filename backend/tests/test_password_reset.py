"""Esqueci minha senha (B-07): pedido genérico, token de propósito único,
uso único, invalidação de sessões, rate limit e guardas do 2FA por e-mail."""

import re
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from jose import jwt

from app.core.auth_rate_limiter import LOGIN_MAX_ATTEMPTS
from app.core.config import settings
from app.core.security import create_password_reset_token

AUTH = "app.api.v1.endpoints.auth"
REQ = "/api/v1/auth/password-reset/request"
CONFIRM = "/api/v1/auth/password-reset/confirm"


def _token_from(mock_send: AsyncMock) -> str:
    html = mock_send.await_args.kwargs["html"]
    match = re.search(r"/redefinir-senha\?token=([^\"&<\s]+)", html)
    assert match, "link de redefinição ausente no e-mail"
    return match.group(1)


def _request_token(http, email: str) -> str:
    with patch(f"{AUTH}.send_email", new=AsyncMock(return_value=True)) as mock_send:
        resp = http.post(REQ, json={"email": email})
    assert resp.status_code == 200, resp.text
    mock_send.assert_awaited_once()
    return _token_from(mock_send)


async def test_email_inexistente_responde_200_generico_sem_enviar(client, user_a):
    with patch(f"{AUTH}.send_email", new=AsyncMock(return_value=True)) as mock_send:
        ghost = client.post(REQ, json={"email": "ninguem@nada.com"})
        real = client.post(REQ, json={"email": user_a.email})
    assert ghost.status_code == 200
    assert ghost.json() == real.json()  # mesma resposta: sem enumeração
    assert mock_send.await_count == 1  # só o e-mail real recebeu
    assert mock_send.await_args.kwargs["to"] == user_a.email


async def test_email_existente_recebe_link_com_token(client, user_a):
    token = _request_token(client, user_a.email.upper())  # e-mail sem diferenciar caixa
    assert token.count(".") == 2  # JWT


async def test_confirm_troca_senha_e_derruba_sessoes(client_with_auth_a):
    http, user, _, _ = client_with_auth_a
    assert http.get("/api/v1/auth/me").status_code == 200
    token = _request_token(http, user.email)
    time.sleep(1.1)  # iat tem resolução de segundos
    resp = http.post(CONFIRM, json={"token": token, "new_password": "NovaSenha!2026"})
    assert resp.status_code == 200, resp.text

    assert http.get("/api/v1/auth/me").status_code == 401  # access token antigo morreu
    ok = http.post("/api/v1/auth/login", data={"username": user.email, "password": "NovaSenha!2026"})
    assert ok.status_code == 200, ok.text
    old = http.post("/api/v1/auth/login", data={"username": user.email, "password": "password123"})
    assert old.status_code == 401


async def test_segundo_uso_do_mesmo_token_falha(client, user_a):
    token = _request_token(client, user_a.email)
    first = client.post(CONFIRM, json={"token": token, "new_password": "NovaSenha!2026"})
    assert first.status_code == 200, first.text
    # Mesmo segundo: só a impressão da senha já impede o reuso.
    again = client.post(CONFIRM, json={"token": token, "new_password": "OutraSenha!2026"})
    assert again.status_code == 400


async def test_token_de_reset_nao_serve_como_bearer(client, user_a):
    token = create_password_reset_token(str(user_a.id), user_a.hashed_password)
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(user_a.tenant_id)},
    )
    assert resp.status_code == 401


async def test_token_mfa_nao_serve_como_bearer(client, user_a):
    from app.core.security import create_mfa_token

    resp = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {create_mfa_token(str(user_a.id))}",
            "X-Tenant-ID": str(user_a.tenant_id),
        },
    )
    assert resp.status_code == 401


async def test_token_expirado_ou_alterado_400(client, user_a):
    good = create_password_reset_token(str(user_a.id), user_a.hashed_password)
    claims = jwt.get_unverified_claims(good)
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    claims.update({"iat": int(past.timestamp()), "exp": int((past + timedelta(hours=1)).timestamp())})
    expired = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    head, body, sig = good.split(".")
    tampered = f"{head}.{body}.{sig[:-3]}{'AAA' if sig[-3:] != 'AAA' else 'BBB'}"
    access_like = jwt.encode(
        {**jwt.get_unverified_claims(good), "purpose": "access"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    for bad in (expired, tampered, access_like, "lixo"):
        resp = client.post(CONFIRM, json={"token": bad, "new_password": "NovaSenha!2026"})
        assert resp.status_code == 400, bad
    # Senha continua a antiga.
    ok = client.post("/api/v1/auth/login", data={"username": user_a.email, "password": "password123"})
    assert ok.status_code == 200


async def test_confirm_aplica_politica_de_senha(client, user_a):
    token = create_password_reset_token(str(user_a.id), user_a.hashed_password)
    assert client.post(CONFIRM, json={"token": token, "new_password": "curta"}).status_code == 422
    longa = "ç" * 40  # 80 bytes > limite do bcrypt
    assert client.post(CONFIRM, json={"token": token, "new_password": longa}).status_code == 400


async def test_rate_limit_por_ip(client, user_a):
    with patch(f"{AUTH}.send_email", new=AsyncMock(return_value=True)):
        codes = [
            client.post(REQ, json={"email": f"x{i}@nada.com"}).status_code
            for i in range(LOGIN_MAX_ATTEMPTS + 1)
        ]
    assert 429 not in codes[:LOGIN_MAX_ATTEMPTS]
    assert codes[-1] == 429


async def test_rate_limit_por_email(client, user_a):
    with patch(f"{AUTH}.send_email", new=AsyncMock(return_value=True)) as mock_send:
        codes = [
            client.post(
                REQ, json={"email": user_a.email}, headers={"X-Forwarded-For": f"10.0.0.{i}"}
            ).status_code
            for i in range(LOGIN_MAX_ATTEMPTS + 1)
        ]
    assert codes[-1] == 429
    assert mock_send.await_count == LOGIN_MAX_ATTEMPTS


async def test_available_reflete_configuracao(client):
    with patch(f"{AUTH}.email_delivery_available", return_value=False):
        assert client.get("/api/v1/auth/password-reset/available").json() == {"available": False}
    with patch(f"{AUTH}.email_delivery_available", return_value=True):
        assert client.get("/api/v1/auth/password-reset/available").json() == {"available": True}


# ─── Guardas do 2FA por e-mail ────────────────────────────────────────────────


async def test_ativar_2fa_email_sem_resend_400(client_with_auth_a):
    http, *_ = client_with_auth_a
    with patch(f"{AUTH}.email_delivery_available", return_value=False), patch(
        f"{AUTH}.send_email", new=AsyncMock(return_value=False)
    ) as mock_send:
        resp = http.post("/api/v1/auth/2fa/enable", json={"method": "email", "otp_code": "000000"})
    assert resp.status_code == 400
    assert "indisponível" in resp.json()["detail"]
    mock_send.assert_not_awaited()


async def _enable_email_2fa(db, user):
    user.two_factor_enabled = True
    user.two_factor_method = "email"
    await db.commit()


async def test_login_2fa_email_com_envio_falho_503(client, user_a, test_db):
    await _enable_email_2fa(test_db, user_a)
    with patch(f"{AUTH}.send_email", new=AsyncMock(return_value=False)):
        resp = client.post("/api/v1/auth/login", data={"username": user_a.email, "password": "password123"})
    assert resp.status_code == 503
    with patch(f"{AUTH}.send_email", new=AsyncMock(return_value=True)):
        resp = client.post("/api/v1/auth/login", data={"username": user_a.email, "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "requires_2fa"


async def test_resend_2fa_reporta_envio_real(client, user_a, test_db):
    from app.core.security import create_mfa_token

    await _enable_email_2fa(test_db, user_a)
    mfa = create_mfa_token(str(user_a.id))
    with patch(f"{AUTH}.send_email", new=AsyncMock(return_value=False)):
        resp = client.post("/api/v1/auth/login/resend-2fa", json={"mfa_token": mfa})
    assert resp.status_code == 200
    assert resp.json()["sent"] is False
    with patch(f"{AUTH}.send_email", new=AsyncMock(return_value=True)):
        assert client.post("/api/v1/auth/login/resend-2fa", json={"mfa_token": mfa}).json()["sent"] is True


def test_verify_2fa_dispensa_x_tenant_id(client):
    # Navegador limpo ainda não tem tenant_id: o 2º passo precisa chegar ao endpoint.
    resp = client.post("/api/v1/auth/login/verify-2fa", json={"mfa_token": "x", "otp_code": "123456"})
    assert resp.status_code == 401
