"""Mercado Pago: pontos achados na homologação do sandbox (13/11/2026).

1. Abrir um checkout não muda o que está pago (ciclo, valor, id da recorrência);
   o pedido viaja no external_reference e só vale com o pagamento confirmado.
   Trocar o mensal por um pré-pago para a cobrança do mensal.
2. O mesmo pagamento avisado em dois formatos é aplicado uma vez só; um
   estorno posterior (outro status) ainda é processado.
3. Simulação do painel com id inexistente (404, live_mode false) responde 200;
   notificação real com 404 continua em 503 para o MP repetir.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.api.v1.endpoints import billing as billing_ep
from app.api.v1.endpoints.billing import ler_referencia, montar_referencia
from app.core.config import settings
from app.core.pricing import valores_aceitos
from app.models.billing import TenantSubscription
from app.services.mercadopago import GatewayPagamentoError
from tests.test_plan_enforcement import authed_client, premium_setup, register_client  # noqa: F401


def _aware(dt):
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


class _FakeGateway:
    """Gateway falso: checkout grava a referência, consultas devolvem o combinado."""

    def __init__(self):
        self.referencias: list[str] = []
        self.cancelados: list[str] = []
        self.pagamento: dict = {}
        self.preapproval: dict = {}

    def configurado(self) -> bool:
        return True

    async def criar_assinatura(self, *, referencia, **_):
        self.referencias.append(referencia)
        return {"tipo": "assinatura", "id": "pre_novo", "init_point": "https://mp/pre"}

    async def criar_cobranca_unica(self, *, referencia, **_):
        self.referencias.append(referencia)
        return {"tipo": "cobranca_unica", "id": "pref_1", "init_point": "https://mp/pref"}

    async def cancelar_assinatura(self, preapproval_id):
        self.cancelados.append(preapproval_id)
        return {"status": "cancelled"}

    async def obter_pagamento(self, _id):
        return self.pagamento

    async def obter_preapproval(self, _id):
        return self.preapproval


@pytest.fixture
def fake(monkeypatch):
    gw = _FakeGateway()
    monkeypatch.setattr(billing_ep, "gateway", gw)
    monkeypatch.setattr(settings, "MERCADO_PAGO_WEBHOOK_SECRET", "", raising=False)
    monkeypatch.setattr(settings, "PAGAMENTOS_GO_LIVE", True, raising=False)
    return gw


async def _mensal_ativo(test_db, plan, tenant, dias=20):
    agora = datetime.now(timezone.utc)
    sub = TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="active",
        billing_cycle="mensal", amount=plan.price_monthly,
        provider_subscription_id="pre_antigo", billing_provider="mercadopago",
        current_period_start=agora - timedelta(days=30 - dias),
        current_period_end=agora + timedelta(days=dias),
    )
    test_db.add(sub)
    await test_db.commit()
    return sub


def test_referencia_ida_e_volta_e_formato_antigo():
    import uuid

    sid = uuid.uuid4()
    assert ler_referencia(montar_referencia(sid, "premium", "trimestral")) == (sid, "premium", "trimestral")
    assert ler_referencia(str(sid)) == (sid, None, None)  # checkouts antigos
    assert ler_referencia(f"{sid}|premium|ciclo-falso") == (sid, "premium", None)
    assert ler_referencia("lixo") == (None, None, None)
    assert ler_referencia(None) == (None, None, None)


@pytest.mark.asyncio
async def test_checkout_nao_muda_o_que_esta_pago(test_db, premium_setup, authed_client, fake):  # noqa: F811
    plan, tenant, user = premium_setup
    sub = await _mensal_ativo(test_db, plan, tenant)
    client = authed_client(user)

    resp = client.post("/api/v1/billing/checkout", json={
        "plan_slug": "premium", "ciclo": "trimestral", "metodo": "pix",
    })
    assert resp.status_code == 201, resp.text
    await test_db.refresh(sub)
    assert sub.billing_cycle == "mensal"
    assert sub.provider_subscription_id == "pre_antigo"
    assert fake.referencias == [f"{sub.id}|premium|trimestral"]

    resp = client.post("/api/v1/billing/checkout", json={
        "plan_slug": "premium", "ciclo": "mensal", "metodo": "cartao",
    })
    assert resp.status_code == 201, resp.text
    await test_db.refresh(sub)
    assert sub.provider_subscription_id == "pre_antigo"  # só troca quando autorizar


@pytest.mark.asyncio
async def test_prepago_pago_troca_ciclo_e_para_o_mensal(test_db, premium_setup, register_client, fake):  # noqa: F811
    plan, tenant, _ = premium_setup
    sub = await _mensal_ativo(test_db, plan, tenant)
    valor = sorted(valores_aceitos(plan.price_monthly, "trimestral"))[0]
    fake.pagamento = {
        "status": "approved", "transaction_amount": valor,
        "external_reference": montar_referencia(sub.id, "premium", "trimestral"),
    }

    resp = register_client.post(
        "/api/v1/billing/webhook/mercadopago?data.id=555&type=payment",
        json={"id": "n-a", "type": "payment", "data": {"id": "555"}},
    )
    assert resp.status_code == 200, resp.text
    await test_db.refresh(sub)
    assert sub.billing_cycle == "trimestral"
    assert sub.provider_subscription_id is None
    assert fake.cancelados == ["pre_antigo"]
    assert _aware(sub.current_period_end) > datetime.now(timezone.utc) + timedelta(days=89)


@pytest.mark.asyncio
async def test_mesmo_pagamento_em_dois_formatos_aplica_uma_vez(test_db, premium_setup, register_client, fake):  # noqa: F811
    plan, tenant, _ = premium_setup
    sub = TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="trialing",
        billing_cycle="mensal", amount=plan.price_monthly, billing_provider="mercadopago",
    )
    test_db.add(sub)
    await test_db.commit()
    valor = sorted(valores_aceitos(plan.price_monthly, "trimestral"))[0]
    fake.pagamento = {
        "status": "approved", "transaction_amount": valor,
        "external_reference": montar_referencia(sub.id, "premium", "trimestral"),
    }

    r1 = register_client.post(
        "/api/v1/billing/webhook/mercadopago?data.id=777&type=payment",
        json={"id": "n-1", "type": "payment", "data": {"id": "777"}},
    )
    assert r1.status_code == 200, r1.text
    await test_db.refresh(sub)
    assert sub.status == "active"

    # Marca o fim do período: o 2º aviso do mesmo pagamento não pode recalcular.
    marcado = datetime(2030, 1, 1, tzinfo=timezone.utc)
    sub.current_period_end = marcado
    await test_db.commit()
    r2 = register_client.post(
        "/api/v1/billing/webhook/mercadopago?id=777&topic=payment",
        json={"resource": "777", "topic": "payment"},
        headers={"x-request-id": "outro-formato"},
    )
    assert r2.status_code == 200, r2.text
    await test_db.refresh(sub)
    assert _aware(sub.current_period_end) == marcado

    # Estorno do mesmo pagamento (outro status) ainda é processado.
    fake.pagamento = {**fake.pagamento, "status": "refunded"}
    r3 = register_client.post(
        "/api/v1/billing/webhook/mercadopago?data.id=777&type=payment",
        json={"id": "n-3", "type": "payment", "data": {"id": "777"}},
    )
    assert r3.status_code == 200, r3.text
    await test_db.refresh(sub)
    assert sub.status == "suspended"


@pytest.mark.asyncio
async def test_preapproval_novo_achado_pela_referencia(test_db, premium_setup, register_client, fake):  # noqa: F811
    plan, tenant, _ = premium_setup
    sub = TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="trialing",
        billing_cycle="trimestral", amount=plan.price_monthly, billing_provider="mercadopago",
    )
    test_db.add(sub)
    await test_db.commit()
    fake.preapproval = {
        "status": "authorized",
        "auto_recurring": {"transaction_amount": float(plan.price_monthly)},
        "external_reference": montar_referencia(sub.id, "premium", "mensal"),
    }

    resp = register_client.post(
        "/api/v1/billing/webhook/mercadopago?data.id=pre_novo&type=subscription_preapproval",
        json={"id": "n-pre", "type": "subscription_preapproval", "data": {"id": "pre_novo"}},
    )
    assert resp.status_code == 200, resp.text
    await test_db.refresh(sub)
    assert sub.status == "active"
    assert sub.provider_subscription_id == "pre_novo"
    assert sub.billing_cycle == "mensal"


@pytest.mark.asyncio
async def test_cancelamento_de_recorrencia_trocada_nao_suspende(test_db, premium_setup, register_client, fake):  # noqa: F811
    plan, tenant, _ = premium_setup
    sub = await _mensal_ativo(test_db, plan, tenant)
    sub.provider_subscription_id = "pre_atual"
    await test_db.commit()
    fake.preapproval = {
        "status": "cancelled",
        "auto_recurring": {"transaction_amount": float(plan.price_monthly)},
        "external_reference": montar_referencia(sub.id, "premium", "mensal"),
    }

    resp = register_client.post(
        "/api/v1/billing/webhook/mercadopago?data.id=pre_velho&type=subscription_preapproval",
        json={"id": "n-velho", "type": "subscription_preapproval", "data": {"id": "pre_velho"}},
    )
    assert resp.status_code == 200, resp.text
    await test_db.refresh(sub)
    assert sub.status == "active"
    assert sub.cancelled_at is None


@pytest.mark.asyncio
async def test_404_de_simulacao_responde_200_e_real_continua_503(register_client, fake, monkeypatch):  # noqa: F811
    async def nao_existe(_id):
        raise GatewayPagamentoError("Mercado Pago retornou 404", status_code=404)

    monkeypatch.setattr(fake, "obter_pagamento", nao_existe)

    teste = register_client.post(
        "/api/v1/billing/webhook/mercadopago?data.id=123456&type=payment",
        json={"id": "123456", "type": "payment", "live_mode": False, "data": {"id": "123456"}},
    )
    assert teste.status_code == 200, teste.text
    assert teste.json() == {"status": "ignorado"}

    real = register_client.post(
        "/api/v1/billing/webhook/mercadopago?data.id=654321&type=payment",
        json={"id": "n-real", "type": "payment", "live_mode": True, "data": {"id": "654321"}},
    )
    assert real.status_code == 503
