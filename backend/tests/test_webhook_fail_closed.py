"""Webhooks públicos sem segredo configurado são rejeitados em produção/staging."""

from app.core.config import settings
from app.services.mercadopago import validar_assinatura_webhook

WA_PAYLOAD = {"sender_phone": "+5511900000000", "body": "oi", "message_type": "text"}


def test_mp_sem_secret_rejeita_em_producao(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert not validar_assinatura_webhook(
        x_signature=None, x_request_id=None, data_id="1", secret=""
    )


def test_mp_sem_secret_aceita_em_dev(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    assert validar_assinatura_webhook(
        x_signature=None, x_request_id=None, data_id="1", secret=""
    )


async def test_whatsapp_webhook_sem_secret_em_producao(client, tenant_a, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_SECRET", "")
    resp = client.post(f"/api/v1/whatsapp/webhooks/{tenant_a.id}", json=WA_PAYLOAD)
    assert resp.status_code == 503


async def test_whatsapp_webhook_exige_header_quando_ha_secret(
    client, tenant_a, monkeypatch
):
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_SECRET", "s3gr3do-de-teste")
    url = f"/api/v1/whatsapp/webhooks/{tenant_a.id}"
    assert client.post(url, json=WA_PAYLOAD).status_code == 401
    assert (
        client.post(
            url, json=WA_PAYLOAD, headers={"X-Webhook-Secret": "errado"}
        ).status_code
        == 401
    )
    ok = client.post(
        url, json=WA_PAYLOAD, headers={"X-Webhook-Secret": "s3gr3do-de-teste"}
    )
    assert ok.status_code == 200
