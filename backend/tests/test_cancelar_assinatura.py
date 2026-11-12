"""Cancelar assinatura em um clique (POST /billing/subscription/cancel).

Regras: para a cobrança no Mercado Pago, mantém o período pago até o fim e
depois o plano efetivo volta para o Gratuito.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.plan_access import PLAN_FREE, effective_plan_slug
from app.models.billing import TenantSubscription
from app.models.plan import Plan

pytestmark = pytest.mark.integration


async def _criar_sub(db, tenant_id, **kw):
    plan = Plan(id=uuid.uuid4(), slug=f"premium-{uuid.uuid4().hex[:6]}", name="Premium",
                price_monthly=Decimal("349.00"), features={})
    db.add(plan)
    await db.flush()
    sub = TenantSubscription(tenant_id=tenant_id, plan_id=plan.id, currency="BRL",
                             amount=Decimal("349.00"), **kw)
    db.add(sub)
    await db.commit()
    return sub


@pytest.mark.asyncio
async def test_cancelar_mensal_para_cobranca_e_mantem_periodo(client_with_auth_a, monkeypatch):
    http, user, _client, db = client_with_auth_a
    fim = datetime.now(timezone.utc) + timedelta(days=20)
    await _criar_sub(db, user.tenant_id, status="active", billing_provider="mercadopago",
                     provider_subscription_id="pre-123", billing_cycle="mensal",
                     current_period_end=fim)

    chamadas = []

    async def fake_cancelar(pid):
        chamadas.append(pid)
        return {"id": pid, "status": "cancelled"}

    from app.services.mercadopago import gateway
    monkeypatch.setattr(gateway, "cancelar_assinatura", fake_cancelar)

    r = http.post("/api/v1/billing/subscription/cancel")
    assert r.status_code == 200, r.text
    data = r.json()
    assert chamadas == ["pre-123"]
    assert data["status"] == "active"          # período pago continua
    assert data["cancelled_at"] is not None

    # Idempotente: não chama o gateway de novo.
    r2 = http.post("/api/v1/billing/subscription/cancel")
    assert r2.status_code == 200
    assert chamadas == ["pre-123"]


@pytest.mark.asyncio
async def test_cancelar_sem_periodo_pago_encerra_na_hora(client_with_auth_a):
    http, user, _client, db = client_with_auth_a
    await _criar_sub(db, user.tenant_id, status="trialing", billing_cycle="anual")

    r = http.post("/api/v1/billing/subscription/cancel")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_falha_no_gateway_nao_marca_cancelado(client_with_auth_a, monkeypatch):
    http, user, _client, db = client_with_auth_a
    sub = await _criar_sub(db, user.tenant_id, status="active", billing_provider="mercadopago",
                           provider_subscription_id="pre-9", billing_cycle="mensal",
                           current_period_end=datetime.now(timezone.utc) + timedelta(days=5))

    from app.services.mercadopago import GatewayPagamentoError, gateway

    async def falha(pid):
        raise GatewayPagamentoError("fora do ar")

    monkeypatch.setattr(gateway, "cancelar_assinatura", falha)
    r = http.post("/api/v1/billing/subscription/cancel")
    assert r.status_code == 502
    await db.refresh(sub)
    assert sub.cancelled_at is None


@pytest.mark.asyncio
async def test_sem_assinatura_responde_400(client_with_auth_a):
    http, *_ = client_with_auth_a
    r = http.post("/api/v1/billing/subscription/cancel")
    assert r.status_code == 400


def test_plano_efetivo_apos_cancelamento():
    tenant = SimpleNamespace(plan_slug="premium")
    agora = datetime.now(timezone.utc)
    vigente = SimpleNamespace(status="active", cancelled_at=agora,
                              current_period_end=agora + timedelta(days=3), trial_ends_at=None)
    vencido = SimpleNamespace(status="active", cancelled_at=agora - timedelta(days=40),
                              current_period_end=agora - timedelta(days=1), trial_ends_at=None)
    assert effective_plan_slug(tenant, vigente) == "premium"
    assert effective_plan_slug(tenant, vencido) == PLAN_FREE
