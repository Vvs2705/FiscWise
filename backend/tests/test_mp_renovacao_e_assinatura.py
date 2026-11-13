"""Mercado Pago: regras da assinatura HMAC, renovação mensal e fim do pré-pago.

- O manifesto assinado usa o `data.id` da query string, em minúsculas, e
  omite partes ausentes (documentação do MP).
- `subscription_authorized_payment` (cobrança do mês) empurra o fim do período
  sem somar 30 dias em dobro na 1ª cobrança.
- Ciclo pré-pago vencido volta para o Gratuito.
"""

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core.plan_access import PLAN_FREE, effective_plan_slug
from app.models.billing import TenantSubscription
from app.services.mercadopago import montar_manifesto_webhook, validar_assinatura_webhook
from tests.test_plan_enforcement import premium_setup, register_client  # noqa: F401


def _assinar(secret: str, manifesto: str, ts: int) -> str:
    v1 = hmac.new(secret.encode(), manifesto.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={v1}"


def test_manifesto_minusculas_e_partes_ausentes():
    assert montar_manifesto_webhook(data_id="ABC123", x_request_id="r-1", ts="10") == (
        "id:abc123;request-id:r-1;ts:10;"
    )
    assert montar_manifesto_webhook(data_id=None, x_request_id=None, ts="10") == "ts:10;"
    assert montar_manifesto_webhook(data_id="9", x_request_id=None, ts="10") == "id:9;ts:10;"


def test_assinatura_com_id_alfanumerico_maiusculo():
    secret = "s3gredo"
    ts = int(time.time())
    sig = _assinar(secret, f"id:2c938084abc;request-id:req-9;ts:{ts};", ts)
    assert validar_assinatura_webhook(
        x_signature=sig, x_request_id="req-9", data_id="2C938084ABC",
        secret=secret, max_idade_segundos=600,
    ) is True


@pytest.mark.asyncio
async def test_webhook_assinado_usa_data_id_da_query(register_client, monkeypatch):  # noqa: F811
    from app.api.v1.endpoints import billing as billing_ep
    from app.core.config import settings

    secret = "s3gredo"
    monkeypatch.setattr(settings, "MERCADO_PAGO_WEBHOOK_SECRET", secret, raising=False)
    monkeypatch.setattr(billing_ep.gateway, "configurado", lambda: False)
    ts = int(time.time())
    sig = _assinar(secret, f"id:123;request-id:req-q;ts:{ts};", ts)

    ok = register_client.post(
        "/api/v1/billing/webhook/mercadopago?data.id=123&type=payment",
        json={"id": "n-1", "type": "payment", "data": {"id": "123"}},
        headers={"x-signature": sig, "x-request-id": "req-q"},
    )
    assert ok.status_code == 200, ok.text

    # Corpo adulterado não muda o id assinado (vem da query) → 401 se a query mudar.
    ruim = register_client.post(
        "/api/v1/billing/webhook/mercadopago?data.id=999&type=payment",
        json={"id": "n-2", "type": "payment", "data": {"id": "123"}},
        headers={"x-signature": sig, "x-request-id": "req-q"},
    )
    assert ruim.status_code == 401


class _FakeGatewayAutorizado:
    def __init__(self, valor: float, preapproval_id: str, status: str = "approved"):
        self.valor = valor
        self.preapproval_id = preapproval_id
        self.status = status

    def configurado(self) -> bool:
        return True

    async def obter_pagamento_autorizado(self, recurso_id: str) -> dict:
        return {
            "preapproval_id": self.preapproval_id,
            "status": "processed",
            "transaction_amount": self.valor,
            "payment": {"status": self.status},
        }


@pytest.mark.asyncio
async def test_cobranca_do_mes_renova_periodo(test_db, premium_setup, register_client, monkeypatch):  # noqa: F811
    from app.api.v1.endpoints import billing as billing_ep
    from app.core.config import settings

    plan, tenant, _ = premium_setup
    agora = datetime.now(timezone.utc)
    sub = TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="active",
        billing_cycle="mensal", amount=plan.price_monthly,
        provider_subscription_id="pre_renova", billing_provider="mercadopago",
        current_period_start=agora - timedelta(days=30),
        current_period_end=agora - timedelta(hours=1),
    )
    test_db.add(sub)
    await test_db.commit()

    monkeypatch.setattr(settings, "MERCADO_PAGO_WEBHOOK_SECRET", "", raising=False)
    monkeypatch.setattr(billing_ep, "gateway", _FakeGatewayAutorizado(299.0, "pre_renova"))
    resp = register_client.post(
        "/api/v1/billing/webhook/mercadopago",
        json={"id": "evt-mes-2", "type": "subscription_authorized_payment", "data": {"id": "7001"}},
    )
    assert resp.status_code == 200, resp.text
    await test_db.refresh(sub)
    fim = sub.current_period_end
    if fim.tzinfo is None:
        fim = fim.replace(tzinfo=timezone.utc)
    assert fim > agora + timedelta(days=29)
    assert sub.status == "active"

    # 1ª cobrança chegando logo após a autorização não vira 60 dias.
    fim_antes = fim
    resp = register_client.post(
        "/api/v1/billing/webhook/mercadopago",
        json={"id": "evt-mes-2b", "type": "subscription_authorized_payment", "data": {"id": "7002"}},
    )
    assert resp.status_code == 200
    await test_db.refresh(sub)
    fim2 = sub.current_period_end
    if fim2.tzinfo is None:
        fim2 = fim2.replace(tzinfo=timezone.utc)
    assert fim2 - fim_antes < timedelta(minutes=5)


@pytest.mark.asyncio
async def test_cobranca_do_mes_valor_errado_nao_renova(test_db, premium_setup, register_client, monkeypatch):  # noqa: F811
    from app.api.v1.endpoints import billing as billing_ep
    from app.core.config import settings

    plan, tenant, _ = premium_setup
    fim_original = datetime.now(timezone.utc) + timedelta(days=2)
    sub = TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="active",
        billing_cycle="mensal", amount=plan.price_monthly,
        provider_subscription_id="pre_valor", billing_provider="mercadopago",
        current_period_end=fim_original,
    )
    test_db.add(sub)
    await test_db.commit()

    monkeypatch.setattr(settings, "MERCADO_PAGO_WEBHOOK_SECRET", "", raising=False)
    monkeypatch.setattr(billing_ep, "gateway", _FakeGatewayAutorizado(1.0, "pre_valor"))
    resp = register_client.post(
        "/api/v1/billing/webhook/mercadopago",
        json={"id": "evt-valor", "type": "subscription_authorized_payment", "data": {"id": "7003"}},
    )
    assert resp.status_code == 200
    await test_db.refresh(sub)
    fim = sub.current_period_end
    if fim.tzinfo is None:
        fim = fim.replace(tzinfo=timezone.utc)
    assert abs((fim - fim_original).total_seconds()) < 5


def test_prepago_vencido_volta_para_gratuito():
    tenant = SimpleNamespace(plan_slug="premium")
    vencido = SimpleNamespace(
        status="active", billing_provider="mercadopago", billing_cycle="trimestral",
        current_period_end=datetime.now(timezone.utc) - timedelta(minutes=1),
        cancelled_at=None, trial_ends_at=None,
    )
    assert effective_plan_slug(tenant, vencido) == PLAN_FREE

    em_dia = SimpleNamespace(**{**vencido.__dict__, "current_period_end": datetime.now(timezone.utc) + timedelta(days=3)})
    assert effective_plan_slug(tenant, em_dia) == "premium"

    # Mensal recorrente: quem encerra é o MP (não vence sozinho aqui).
    mensal = SimpleNamespace(**{**vencido.__dict__, "billing_cycle": "mensal"})
    assert effective_plan_slug(tenant, mensal) == "premium"
