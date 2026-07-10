"""Camada de pagamento — Mercado Pago (gateway BR).

Modelo do FiscWise: assinatura mensal recorrente (preapproval) por plano
(Intermediário / Premium). Portado do padrão já em produção no SessãoInk.

Segurança:
- O ACCESS_TOKEN vive só como secret (nunca no repo/logs).
- Toda cobrança real é trancada por `settings.PAGAMENTOS_GO_LIVE` no router — esta
  camada só monta payloads e fala com a API quando chamada.
- Não importa o SDK do Mercado Pago: usa httpx direto (timeout-bounded,
  idempotency key), mantendo o módulo importável e testável sem dependências extras.
- Valor SEMPRE calculado no servidor (nunca confiar em valor vindo do cliente).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import settings
from app.core.pricing import linha_preco

logger = logging.getLogger(__name__)

MP_API_BASE = "https://api.mercadopago.com"
_HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class GatewayNaoConfiguradoError(RuntimeError):
    """Levantada quando se tenta cobrar sem ACCESS_TOKEN configurado."""


class GatewayPagamentoError(RuntimeError):
    """Erro de comunicação/negócio com o gateway."""


def valor_centavos(preco_mensal: Decimal | float | int | None) -> int:
    """Preço mensal (reais) → centavos. Calculado sempre no servidor."""
    if preco_mensal is None:
        raise GatewayPagamentoError("Plano sem preço mensal definido")
    return int(round(float(preco_mensal) * 100))


class GatewayMercadoPago:
    """Adaptador fino sobre a API do Mercado Pago (assinatura mensal)."""

    def __init__(self) -> None:
        self._token = settings.MERCADO_PAGO_ACCESS_TOKEN

    def configurado(self) -> bool:
        return bool(self._token)

    def _exigir_token(self) -> str:
        if not self._token:
            raise GatewayNaoConfiguradoError(
                "MERCADO_PAGO_ACCESS_TOKEN não configurado — cobrança indisponível."
            )
        return self._token

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._exigir_token()}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        return headers

    async def _post(
        self, path: str, payload: dict[str, Any], idempotency_key: str | None = None
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=MP_API_BASE, timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(path, json=payload, headers=self._headers(idempotency_key))
        if resp.status_code >= 400:
            logger.warning("mercadopago_erro path=%s status=%s", path, resp.status_code)
            raise GatewayPagamentoError(f"Mercado Pago retornou {resp.status_code} em {path}")
        return resp.json()

    async def _get(self, path: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=MP_API_BASE, timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(path, headers=self._headers())
        if resp.status_code >= 400:
            raise GatewayPagamentoError(f"Mercado Pago retornou {resp.status_code} em {path}")
        return resp.json()

    # -- Montagem de payload (puro — testável sem rede) ------------------------
    def montar_preapproval(
        self, *, plano_nome: str, preco_mensal: Decimal | float, email_pagador: str, referencia: str
    ) -> dict[str, Any]:
        """Assinatura recorrente mensal (preapproval) cobrada no cartão."""
        app_url = settings.APP_URL.rstrip("/")
        api_url = settings.PUBLIC_URL.rstrip("/")
        return {
            "reason": f"FiscWise {plano_nome} (mensal)",
            "external_reference": referencia,
            "payer_email": email_pagador,
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months",
                "transaction_amount": float(preco_mensal),
                "currency_id": "BRL",
            },
            "back_url": f"{app_url}/configuracoes?assinatura=ok",
            "notification_url": f"{api_url}/api/v1/billing/webhook/mercadopago",
            "status": "pending",
        }

    def montar_preference(
        self, *, plano_nome: str, preco_mensal: Decimal | float, ciclo: str,
        metodo: str, email_pagador: str, referencia: str,
    ) -> dict[str, Any]:
        """Checkout Preference para ciclos pré-pagos (trimestral/semestral/anual).

        metodo="pix": valor com desconto Pix (15%) embutido; cartão/boleto excluídos.
        metodo="cartao": valor do cartão (anual tem 15%); até N parcelas SEM JUROS
        para o cliente (nós absorvemos a taxa); Pix/boleto excluídos.
        """
        linha = linha_preco(preco_mensal, ciclo)
        app_url = settings.APP_URL.rstrip("/")
        api_url = settings.PUBLIC_URL.rstrip("/")
        if metodo == "pix":
            valor = linha["pix_total"]
            payment_methods: dict[str, Any] = {
                "excluded_payment_types": [
                    {"id": "credit_card"}, {"id": "debit_card"}, {"id": "ticket"},
                ],
                "installments": 1,
            }
        else:
            valor = linha["cartao_total"]
            payment_methods = {
                "excluded_payment_types": [{"id": "bank_transfer"}, {"id": "ticket"}],
                "installments": linha["cartao_max_parcelas"],
                "default_installments": 1,
            }
        return {
            "items": [{
                "title": f"FiscWise {plano_nome} — {linha['label']}",
                "description": f"Plano {plano_nome} ({ciclo})",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": valor,
            }],
            "payer": {"email": email_pagador},
            "payment_methods": payment_methods,
            "external_reference": referencia,
            "back_urls": {
                "success": f"{app_url}/configuracoes?pagamento=sucesso",
                "pending": f"{app_url}/configuracoes?pagamento=pendente",
                "failure": f"{app_url}/configuracoes?pagamento=falha",
            },
            "auto_return": "approved",
            "notification_url": f"{api_url}/api/v1/billing/webhook/mercadopago",
        }

    # -- Chamadas reais (exigem token) ----------------------------------------
    async def criar_cobranca_unica(
        self, *, plano_nome: str, preco_mensal: Decimal | float, ciclo: str,
        metodo: str, email_pagador: str, referencia: str,
    ) -> dict[str, Any]:
        """Cria a Checkout Preference (ciclos pré-pagos) e devolve o init_point."""
        payload = self.montar_preference(
            plano_nome=plano_nome, preco_mensal=preco_mensal, ciclo=ciclo,
            metodo=metodo, email_pagador=email_pagador, referencia=referencia,
        )
        data = await self._post(
            "/checkout/preferences", payload,
            idempotency_key=f"{referencia}:{ciclo}:{metodo}",
        )
        return {
            "tipo": "cobranca_unica",
            "id": data.get("id"),
            "init_point": data.get("init_point") or data.get("sandbox_init_point"),
        }

    async def criar_assinatura(
        self, *, plano_nome: str, preco_mensal: Decimal | float, email_pagador: str, referencia: str
    ) -> dict[str, Any]:
        payload = self.montar_preapproval(
            plano_nome=plano_nome, preco_mensal=preco_mensal,
            email_pagador=email_pagador, referencia=referencia,
        )
        data = await self._post("/preapproval", payload, idempotency_key=referencia)
        return {
            "tipo": "assinatura",
            "id": data.get("id"),
            "init_point": data.get("init_point") or data.get("sandbox_init_point"),
        }

    async def obter_preapproval(self, preapproval_id: str) -> dict[str, Any]:
        """Status de uma assinatura recorrente (usado pelo webhook)."""
        return await self._get(f"/preapproval/{preapproval_id}")

    async def obter_pagamento(self, pagamento_id: str) -> dict[str, Any]:
        """Status de um pagamento avulso (usado pelo webhook)."""
        return await self._get(f"/v1/payments/{pagamento_id}")


def validar_assinatura_webhook(
    *,
    x_signature: str | None,
    x_request_id: str | None,
    data_id: str | None,
    secret: str | None = None,
    max_idade_segundos: int | None = None,
) -> bool:
    """Valida a assinatura HMAC do webhook do Mercado Pago.

    Manifesto: `id:{data.id};request-id:{x-request-id};ts:{ts};`
    `x-signature` traz `ts=<unix>,v1=<hmac sha256 hex>`.
    Sem secret configurado → True (modo permissivo em dev; o go-live exige o secret).
    `max_idade_segundos` (anti-replay): rejeita `ts` fora da janela.
    """
    secret = secret if secret is not None else settings.MERCADO_PAGO_WEBHOOK_SECRET
    if not secret:
        return True
    if not x_signature:
        return False

    partes = dict(p.split("=", 1) for p in x_signature.split(",") if "=" in p)
    ts = partes.get("ts", "").strip()
    v1 = partes.get("v1", "").strip()
    if not ts or not v1:
        return False

    manifest = f"id:{data_id or ''};request-id:{x_request_id or ''};ts:{ts};"
    esperado = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(esperado, v1):
        return False

    if max_idade_segundos is not None:
        try:
            ts_val = int(ts)
        except ValueError:
            return False
        if ts_val > 10**12:  # timestamp em milissegundos
            ts_val //= 1000
        if abs(time.time() - ts_val) > max_idade_segundos:
            return False

    return True


# Instância padrão reutilizável.
gateway = GatewayMercadoPago()
