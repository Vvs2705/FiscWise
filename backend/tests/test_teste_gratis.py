"""Teste grátis de 14 dias no lugar do plano Gratuito (decisão de 13/11/2026).

- Conta com o teste vigente usa tudo; /auth/tenant mostra os dias restantes.
- Teste vencido = só leitura: GET funciona, escrita responde 402
  ACESSO_EXPIRADO; assinar, exportar e excluir continuam liberados.
- Escritório antigo sem assinatura nunca vence.
- Avisos por e-mail (3 dias, 1 dia, no dia, vencido) saem uma vez cada.
- A exportação LGPD traz os dados do escritório, sem colunas sensíveis.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.core.plan_access import acesso_expirado, info_teste
from app.models.billing import TenantSubscription
from app.models.operations import AccountingClient
from tests.test_plan_enforcement import authed_client, premium_setup  # noqa: F401


def _sub_teste(plan, tenant, dias: float) -> TenantSubscription:
    return TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="trialing",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=dias),
        billing_cycle="mensal", amount=plan.price_monthly, billing_provider="mercadopago",
    )


@pytest.mark.asyncio
async def test_teste_vigente_escreve_e_mostra_dias(test_db, premium_setup, authed_client):  # noqa: F811
    plan, tenant, user = premium_setup
    test_db.add(_sub_teste(plan, tenant, 14))
    await test_db.commit()
    client = authed_client(user)

    info = client.get("/api/v1/auth/tenant").json()
    assert info["em_teste"] is True
    assert info["acesso_expirado"] is False
    assert info["trial_dias_restantes"] in (13, 14)
    assert info["plan_slug"] == "premium"

    resp = client.post("/api/v1/clients", json={"name": "Cliente Teste", "document": "11222333000181"})
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_teste_vencido_fica_so_leitura(test_db, premium_setup, authed_client):  # noqa: F811
    plan, tenant, user = premium_setup
    test_db.add(_sub_teste(plan, tenant, -1))
    test_db.add(AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant.id, name="Cliente Antigo",
        document="11222333000181", status="active",
    ))
    await test_db.commit()
    client = authed_client(user)

    info = client.get("/api/v1/auth/tenant").json()
    assert info["acesso_expirado"] is True
    assert info["em_teste"] is False
    assert info["plan_slug"] == "free"

    # Ler continua funcionando.
    assert client.get("/api/v1/clients").status_code == 200

    # Escrever não.
    resp = client.post("/api/v1/clients", json={"name": "Novo", "document": "99888777000161"})
    assert resp.status_code == 402
    assert resp.headers.get("X-Error-Code") == "ACESSO_EXPIRADO"
    assert "teste grátis acabou" in resp.json()["detail"]

    # Exportar os dados continua liberado e traz o que existe.
    exp = client.get("/api/v1/account/export")
    assert exp.status_code == 200, exp.text
    clientes = exp.json()["dados"]["clientes"]
    assert [c["name"] for c in clientes] == ["Cliente Antigo"]

    # Assinar continua liberado (não é barrado pela trava; 503 = cobrança desligada no teste).
    resp = client.post("/api/v1/billing/checkout", json={"plan_slug": "premium", "ciclo": "mensal", "metodo": "cartao"})
    assert resp.status_code != 402, resp.text


def test_escritorio_sem_assinatura_nunca_vence():
    class T:
        plan_slug = "free"
        subscription = None

    assert acesso_expirado(T()) is False
    assert acesso_expirado(None) is False


def test_info_teste_dias_em_brasilia():
    class Sub:
        status = "trialing"
        trial_ends_at = datetime.now(timezone.utc) + timedelta(days=3, hours=1)

    class T:
        plan_slug = "premium"
        subscription = Sub()

    info = info_teste(T())
    assert info["em_teste"] is True
    assert info["trial_dias_restantes"] in (3, 4)


def test_exportacao_tira_colunas_sensiveis():
    from app.api.v1.endpoints.account import _COLUNAS_SENSIVEIS

    for nome in ("hashed_password", "token_hash", "pfx_encrypted", "senha_certificado", "webhook_secret"):
        assert _COLUNAS_SENSIVEIS.search(nome), nome
    for nome in ("name", "document", "file_url", "access_key", "amount"):
        assert not _COLUNAS_SENSIVEIS.search(nome), nome


@pytest.mark.asyncio
async def test_avisos_do_teste_saem_uma_vez(test_db, premium_setup, monkeypatch):  # noqa: F811
    from app.services import email_service
    from app.services.scheduler import avisar_fim_do_teste_scheduled

    plan, tenant, user = premium_setup
    agora = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)  # 09h em Brasília
    sub = _sub_teste(plan, tenant, 0)
    sub.trial_ends_at = agora + timedelta(days=3)
    test_db.add(sub)
    await test_db.commit()

    enviados = []

    async def fake_send(to, subject, html, idempotency_key=None):
        enviados.append((to, subject))
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send)

    r1 = await avisar_fim_do_teste_scheduled(now=agora)
    assert r1["sent"] == 1
    assert enviados == [(user.email, "Seu teste grátis do FiscWise acaba em 3 dias")]

    # Tick repetido no mesmo dia: não manda de novo.
    r2 = await avisar_fim_do_teste_scheduled(now=agora + timedelta(minutes=30))
    assert r2["sent"] == 0 and r2["duplicate"] == 1

    # Dois dias depois: aviso de "amanhã".
    r3 = await avisar_fim_do_teste_scheduled(now=agora + timedelta(days=2))
    assert r3["sent"] == 1
    assert enviados[-1][1] == "Seu teste grátis do FiscWise acaba amanhã"

    # Um dia depois do fim: aviso de vencido.
    r4 = await avisar_fim_do_teste_scheduled(now=agora + timedelta(days=4))
    assert r4["sent"] == 1
    assert enviados[-1][1] == "Seu teste grátis do FiscWise acabou"
