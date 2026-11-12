"""Link mágico do portal: envio por e-mail, modo manual e pedido público (B-03)."""

import re
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.auth_rate_limiter import LOGIN_MAX_ATTEMPTS, OTP_MAX_ATTEMPTS
from app.models.operations import AccountingClient
from app.models.user import User, UserRole
from app.services import email_service

TOKEN_RE = re.compile(r"/portal/login\?token=([A-Za-z0-9_\-]+)")


@pytest.fixture
def email_on(monkeypatch):
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    monkeypatch.setattr(email_service, "send_email", sender)
    return sender


@pytest.fixture
def email_off(monkeypatch):
    sender = AsyncMock(return_value=False)
    monkeypatch.setattr(email_service, "is_configured", lambda: False)
    monkeypatch.setattr(email_service, "send_email", sender)
    return sender


def _token_from(html: str) -> str:
    match = TOKEN_RE.search(html)
    assert match, "link do portal ausente no e-mail"
    return match.group(1)


async def test_dar_acesso_sem_email_configurado_devolve_link_manual(client_with_auth_a, email_off):
    http, _, client_a, test_db = client_with_auth_a
    resp = http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client_a.id)})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["sent"] is False and data["delivery"] == "manual"
    assert data["email"] == client_a.email
    email_off.assert_not_called()

    # Usuário CLIENT criado e vinculado ao cliente.
    await test_db.refresh(client_a)
    user = (await test_db.execute(select(User).where(User.id == client_a.portal_user_id))).scalar_one()
    assert user.role == UserRole.CLIENT

    # O link funciona de ponta a ponta e é de uso único.
    token = _token_from(data["portal_link"])
    http.headers.pop("Authorization")
    resp = http.post("/api/v1/portal/magic-link/verify", json={"token": token})
    assert resp.status_code == 200, resp.text
    http.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    assert http.get("/api/v1/portal/my-overview").status_code == 200
    assert http.post("/api/v1/portal/magic-link/verify", json={"token": token}).status_code == 401


async def test_dar_acesso_com_email_envia_e_nao_vaza_link(client_with_auth_a, email_on):
    http, _, client_a, _ = client_with_auth_a
    resp = http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client_a.id)})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data == {**data, "sent": True, "delivery": "email"}
    assert "portal_link" not in data and "token" not in resp.text

    email_on.assert_awaited_once()
    kwargs = email_on.await_args.kwargs
    assert kwargs["to"] == client_a.email
    token = _token_from(kwargs["html"])
    http.headers.pop("Authorization")
    assert http.post("/api/v1/portal/magic-link/verify", json={"token": token}).status_code == 200


async def test_novo_link_invalida_o_anterior_e_reusa_usuario(client_with_auth_a, email_on):
    http, _, client_a, test_db = client_with_auth_a
    http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client_a.id)})
    first = _token_from(email_on.await_args.kwargs["html"])
    http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client_a.id)})
    second = _token_from(email_on.await_args.kwargs["html"])
    users = (await test_db.execute(select(User).where(User.role == UserRole.CLIENT))).scalars().all()
    assert len(users) == 1
    http.headers.pop("Authorization")
    assert http.post("/api/v1/portal/magic-link/verify", json={"token": first}).status_code == 401
    assert http.post("/api/v1/portal/magic-link/verify", json={"token": second}).status_code == 200


async def test_falha_do_provedor_nao_devolve_link_e_inutiliza_token(client_with_auth_a, email_on):
    http, _, client_a, _ = client_with_auth_a
    email_on.return_value = False
    resp = http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client_a.id)})
    data = resp.json()
    assert data["sent"] is False and data["reason"] and "portal_link" not in data
    token = _token_from(email_on.await_args.kwargs["html"])
    http.headers.pop("Authorization")
    assert http.post("/api/v1/portal/magic-link/verify", json={"token": token}).status_code == 401


async def test_cliente_sem_email_exige_email(client_with_auth_a, test_db, email_on):
    http, _, client_a, _ = client_with_auth_a
    client_a.email = None
    await test_db.commit()
    resp = http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client_a.id)})
    assert resp.status_code == 422
    resp = http.post(
        "/api/v1/portal/magic-link/request",
        json={"client_id": str(client_a.id), "email": "novo@cliente.com"},
    )
    assert resp.status_code == 200 and resp.json()["email"] == "novo@cliente.com"


async def test_email_da_equipe_nao_vira_cliente(client_with_auth_a, user_a, email_on):
    http, _, client_a, _ = client_with_auth_a
    resp = http.post(
        "/api/v1/portal/magic-link/request",
        json={"client_id": str(client_a.id), "email": user_a.email},
    )
    assert resp.status_code == 409
    email_on.assert_not_called()


async def test_cliente_de_outro_escritorio_404(client_with_auth_a, client_b, email_on):
    http, *_ = client_with_auth_a
    resp = http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client_b.id)})
    assert resp.status_code == 404


async def test_membro_nao_emite_link(client_with_auth_b, email_on):
    http, _, client_b, _ = client_with_auth_b  # user_b é MEMBER
    resp = http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client_b.id)})
    assert resp.status_code == 403


# ── Pedido público na tela de login ────────────────────────────────────────


def test_self_request_sem_email_configurado_503(client, email_off):
    resp = client.post("/api/v1/portal/magic-link/self-request", json={"email": "x@y.com"})
    assert resp.status_code == 503
    assert "não configurado" in resp.json()["detail"]


async def test_self_request_desconhecido_e_conhecido_respondem_igual(client_with_auth_a, email_on):
    http, _, client_a, _ = client_with_auth_a
    http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client_a.id)})
    email_on.reset_mock()
    http.headers.pop("Authorization")

    unknown = http.post("/api/v1/portal/magic-link/self-request", json={"email": "ninguem@x.com"})
    assert unknown.status_code == 200
    email_on.assert_not_called()

    known = http.post(
        "/api/v1/portal/magic-link/self-request", json={"email": client_a.email.upper()}
    )
    assert known.status_code == 200
    assert known.json() == unknown.json()
    assert "token" not in known.text
    email_on.assert_awaited_once()
    token = _token_from(email_on.await_args.kwargs["html"])
    assert http.post("/api/v1/portal/magic-link/verify", json={"token": token}).status_code == 200


async def test_self_request_nao_envia_para_equipe(client, user_a, email_on):
    resp = client.post("/api/v1/portal/magic-link/self-request", json={"email": user_a.email})
    assert resp.status_code == 200
    email_on.assert_not_called()


def test_self_request_limite_por_ip(client, email_on):
    codes = [
        client.post(
            "/api/v1/portal/magic-link/self-request", json={"email": f"a{i}@x.com"}
        ).status_code
        for i in range(LOGIN_MAX_ATTEMPTS + 1)
    ]
    assert 429 not in codes[:LOGIN_MAX_ATTEMPTS]
    assert codes[-1] == 429


async def test_self_request_limite_por_email_e_silencioso(client_with_auth_a, email_on):
    http, _, client_a, _ = client_with_auth_a
    http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client_a.id)})
    email_on.reset_mock()
    http.headers.pop("Authorization")
    for _ in range(OTP_MAX_ATTEMPTS + 2):
        resp = http.post("/api/v1/portal/magic-link/self-request", json={"email": client_a.email})
        assert resp.status_code == 200
    assert email_on.await_count == OTP_MAX_ATTEMPTS
