"""Falha na consulta ao Mercado Pago não pode "queimar" o evento do webhook.

Antes: o evento era gravado mesmo com o gateway fora; o reenvio do MP caía em
already_processed e o pagamento nunca ativava o plano (SEC-5).
"""

from sqlalchemy import select

from app.api.v1.endpoints import billing
from app.core.config import settings
from app.models.billing import BillingWebhookEvent
from app.services.mercadopago import GatewayPagamentoError

BODY = {"id": "evt-1", "type": "payment", "data": {"id": "pay-1"}}


async def test_falha_no_gateway_permite_reenvio(client, test_db, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "MERCADO_PAGO_WEBHOOK_SECRET", "")
    monkeypatch.setattr(billing.gateway, "configurado", lambda: True)

    async def fora_do_ar(_id):
        raise GatewayPagamentoError("timeout")

    monkeypatch.setattr(billing.gateway, "obter_pagamento", fora_do_ar)
    resp = client.post("/api/v1/billing/webhook/mercadopago", json=BODY)
    assert resp.status_code == 503
    eventos = (await test_db.execute(select(BillingWebhookEvent))).scalars().all()
    assert eventos == []

    async def aprovado(_id):
        return {"status": "approved", "external_reference": "", "transaction_amount": 0}

    monkeypatch.setattr(billing.gateway, "obter_pagamento", aprovado)
    resp = client.post("/api/v1/billing/webhook/mercadopago", json=BODY)
    assert resp.json() == {"status": "ok"}
