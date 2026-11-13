"""Primeiro login Google NÃO entra no sistema sem cadastro.

Antes, POST /auth/google com e-mail novo criava escritório + dono na hora
(sem nome do escritório, sem aceite dos Termos, sem plano) e devolvia o
access token: a pessoa caía direto no sistema. Agora:

  - /auth/google com e-mail novo devolve requires_signup e não grava nada;
  - /onboarding/register-google conclui o cadastro (termos obrigatórios,
    plano Gratuito por padrão);
  - escritório sem aceite dos Termos (contas antigas) recebe 403
    SIGNUP_INCOMPLETE em todo o sistema, até concluir o cadastro.
"""

import uuid

import pytest_asyncio
from sqlalchemy import func, select

from app.api.v1.endpoints import auth
from app.api.v1.endpoints.onboarding import TERMS_VERSION
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.tenant import SubscriptionStatus, Tenant
from app.models.user import User, UserRole

NEW_EMAIL = "novo.contador@gmail.com"


def _fake_google(monkeypatch, email=NEW_EMAIL, name="Novo Contador"):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(
        auth.google_id_token,
        "verify_oauth2_token",
        lambda *a, **k: {"email": email, "name": name, "email_verified": True},
    )


async def _count(db, model):
    return int((await db.execute(select(func.count()).select_from(model))).scalar_one())


async def test_google_email_novo_nao_cria_conta_nem_da_acesso(client, test_db, monkeypatch):
    _fake_google(monkeypatch)
    tenants_antes = await _count(test_db, Tenant)

    resp = client.post("/api/v1/auth/google", json={"credential": "fake"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "requires_signup"
    assert body["email"] == NEW_EMAIL
    assert body["signup_token"]
    assert "access_token" not in body
    assert await _count(test_db, Tenant) == tenants_antes
    assert (await test_db.execute(select(User).where(User.email == NEW_EMAIL))).scalar_one_or_none() is None


async def test_signup_token_nao_serve_como_access_token(client, monkeypatch):
    _fake_google(monkeypatch)
    token = client.post("/api/v1/auth/google", json={"credential": "fake"}).json()["signup_token"]

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(uuid.uuid4())})
    assert resp.status_code == 401


async def test_register_google_exige_termos(client, monkeypatch):
    _fake_google(monkeypatch)
    token = client.post("/api/v1/auth/google", json={"credential": "fake"}).json()["signup_token"]

    resp = client.post(
        "/api/v1/onboarding/register-google",
        json={"signup_token": token, "company_name": "Escritório Novo", "terms_accepted": False},
    )
    assert resp.status_code == 422


async def test_register_google_cria_escritorio_no_gratuito(client, test_db, monkeypatch):
    _fake_google(monkeypatch)
    token = client.post("/api/v1/auth/google", json={"credential": "fake"}).json()["signup_token"]

    resp = client.post(
        "/api/v1/onboarding/register-google",
        json={"signup_token": token, "company_name": "Escritório Novo", "terms_accepted": True},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["user"]["email"] == NEW_EMAIL
    assert data["user"]["full_name"] == "Novo Contador"

    tenant = (await test_db.execute(select(Tenant).where(Tenant.id == uuid.UUID(data["tenant_id"])))).scalar_one()
    assert tenant.name == "Escritório Novo"
    assert tenant.plan_slug == "free"
    assert tenant.terms_accepted_at is not None
    assert tenant.terms_version == TERMS_VERSION  # prova do aceite: qual versão

    headers = {"Authorization": f"Bearer {data['access_token']}", "X-Tenant-ID": data["tenant_id"]}
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["signup_complete"] is True
    assert client.get("/api/v1/clients", headers=headers).status_code == 200

    # Segundo login Google do mesmo e-mail entra direto (conta já existe).
    again = client.post("/api/v1/auth/google", json={"credential": "fake"}).json()
    assert "access_token" in again


async def test_register_google_token_invalido(client):
    resp = client.post(
        "/api/v1/onboarding/register-google",
        json={"signup_token": "x" * 40, "company_name": "Escritório", "terms_accepted": True},
    )
    assert resp.status_code == 401


async def test_register_google_ignora_email_do_corpo(client, test_db, monkeypatch, user_a):
    """O e-mail vem do token; não dá para tomar o e-mail de outra pessoa."""
    _fake_google(monkeypatch)
    token = client.post("/api/v1/auth/google", json={"credential": "fake"}).json()["signup_token"]
    resp = client.post(
        "/api/v1/onboarding/register-google",
        json={
            "signup_token": token, "company_name": "Escritório", "terms_accepted": True,
            "owner_email": user_a.email,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == NEW_EMAIL


# ── Contas antigas sem cadastro concluído ──────────────────────────────────


@pytest_asyncio.fixture
async def incomplete_owner(test_db):
    tenant = Tenant(
        id=uuid.uuid4(), name="Conta Google Antiga",
        subscription_status=SubscriptionStatus.TRIAL, plan_slug=None,
    )
    test_db.add(tenant)
    await test_db.flush()
    user = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email="antiga@gmail.com",
        hashed_password=get_password_hash("Password123!"), full_name="Antiga",
        role=UserRole.OWNER, is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    return user


def _headers(user):
    token = create_access_token(user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role.value)
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(user.tenant_id)}


async def test_conta_sem_cadastro_bloqueada_no_sistema(client, incomplete_owner):
    h = _headers(incomplete_owner)
    resp = client.get("/api/v1/clients", headers=h)
    assert resp.status_code == 403
    assert resp.headers.get("X-Error-Code") == "SIGNUP_INCOMPLETE"

    # A própria conta continua acessível (para o site saber que falta concluir).
    me = client.get("/api/v1/auth/me", headers=h)
    assert me.status_code == 200
    assert me.json()["signup_complete"] is False


async def test_concluir_cadastro_libera_no_gratuito(client, test_db, incomplete_owner):
    h = _headers(incomplete_owner)
    bad = client.post(
        "/api/v1/onboarding/complete-signup", headers=h,
        json={"company_name": "Meu Escritório", "terms_accepted": False},
    )
    assert bad.status_code == 422

    ok = client.post(
        "/api/v1/onboarding/complete-signup", headers=h,
        json={"company_name": "Meu Escritório", "terms_accepted": True},
    )
    assert ok.status_code == 200, ok.text

    tenant = (await test_db.execute(select(Tenant).where(Tenant.id == incomplete_owner.tenant_id))).scalar_one()
    await test_db.refresh(tenant)
    assert tenant.name == "Meu Escritório"
    assert tenant.plan_slug == "free"
    assert tenant.terms_accepted_at is not None
    assert tenant.terms_version == TERMS_VERSION  # prova do aceite: qual versão
    assert client.get("/api/v1/clients", headers=h).status_code == 200


async def test_concluir_cadastro_so_o_dono(client, test_db, incomplete_owner):
    staff = User(
        id=uuid.uuid4(), tenant_id=incomplete_owner.tenant_id, email="equipe@gmail.com",
        hashed_password=get_password_hash("Password123!"), role=UserRole.MEMBER, is_active=True,
    )
    test_db.add(staff)
    await test_db.commit()
    resp = client.post(
        "/api/v1/onboarding/complete-signup", headers=_headers(staff),
        json={"company_name": "Outro Nome", "terms_accepted": True},
    )
    assert resp.status_code == 403
