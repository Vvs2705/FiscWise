"""Testes da camada Mercado Pago (payload + assinatura de webhook + valor).

Não tocam rede nem DB: exercitam o caminho de dinheiro/segurança puro.
"""
import hashlib
import hmac
import time

from app.services.mercadopago import (
    GatewayMercadoPago,
    valor_centavos,
    validar_assinatura_webhook,
)


def _assinar(secret: str, data_id: str, request_id: str, ts: int) -> str:
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={v1}"


def test_valor_centavos():
    assert valor_centavos(149) == 14900
    assert valor_centavos(299.90) == 29990
    from decimal import Decimal
    assert valor_centavos(Decimal("49.00")) == 4900


def test_montar_preapproval_shape():
    gw = GatewayMercadoPago()
    payload = gw.montar_preapproval(
        plano_nome="Premium", preco_mensal=299.0,
        email_pagador="dono@escritorio.com", referencia="ref-123",
    )
    assert payload["external_reference"] == "ref-123"
    assert payload["payer_email"] == "dono@escritorio.com"
    assert payload["auto_recurring"]["transaction_amount"] == 299.0
    assert payload["auto_recurring"]["frequency_type"] == "months"
    assert payload["auto_recurring"]["currency_id"] == "BRL"
    assert "/api/v1/billing/webhook/mercadopago" in payload["notification_url"]


def test_webhook_sem_secret_permissivo():
    # Sem secret configurado → modo permissivo (dev).
    assert validar_assinatura_webhook(
        x_signature=None, x_request_id="r1", data_id="123", secret="",
    ) is True


def test_webhook_assinatura_valida_e_invalida():
    secret = "topsecret"
    ts = int(time.time())
    sig = _assinar(secret, "999", "req-1", ts)
    assert validar_assinatura_webhook(
        x_signature=sig, x_request_id="req-1", data_id="999",
        secret=secret, max_idade_segundos=600,
    ) is True
    # Payload adulterado (data_id diferente) → assinatura não casa.
    assert validar_assinatura_webhook(
        x_signature=sig, x_request_id="req-1", data_id="OUTRO",
        secret=secret, max_idade_segundos=600,
    ) is False
    # Sem x_signature com secret presente → rejeita.
    assert validar_assinatura_webhook(
        x_signature=None, x_request_id="req-1", data_id="999", secret=secret,
    ) is False


def test_webhook_anti_replay():
    secret = "topsecret"
    ts_antigo = int(time.time()) - 3600  # 1h atrás
    sig = _assinar(secret, "999", "req-1", ts_antigo)
    # Assinatura correta, mas fora da janela anti-replay → rejeita.
    assert validar_assinatura_webhook(
        x_signature=sig, x_request_id="req-1", data_id="999",
        secret=secret, max_idade_segundos=600,
    ) is False
