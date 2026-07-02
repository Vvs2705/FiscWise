"""Payment gateway — Mercado Pago (BR).

Ported from SessãoInk (``app/core/pagamentos.py``), adapted to the FiscWise
plan catalogue and domain vocabulary.

Payment models (per confirmed MP API behaviour):
  - Monthly card → **Preapproval** (recurring debit, frequency 1 month).
  - Monthly Pix  → **avulso** (one-off Checkout per cycle). The −10% "punctuality"
    discount is OUR backend rule, NOT a native MP feature: it is applied to the
    computed amount when we build the preference for the cycle. Pix/boleto are
    NOT MP recurring; only card recurring exists via preapproval.
  - Yearly (1st year) → **Checkout Pro** avulso with −30% off the full annual
    price; card in 6× interest-free (installments configured on the preference,
    interest absorbed by the seller); Pix/boleto paid in full.

Security & secrets:
  - ``MERCADO_PAGO_ACCESS_TOKEN`` lives only as a deploy secret (never in the
    repo/logs). Every real charge is locked behind ``settings.PAGAMENTOS_GO_LIVE``
    at the router level — this layer only builds payloads and talks to the API
    when explicitly called.
  - No card data ever transits here (Checkout Pro / hosted checkout only).

This layer does NOT import the Mercado Pago SDK: it uses httpx directly
(timeout-bounded, X-Idempotency-Key), keeping the module importable and testable
without extra dependencies.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MP_API_BASE = "https://api.mercadopago.com"
_HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Valid billing cycles accepted by checkout.
CICLOS_VALIDOS = {"mensal", "anual"}
# Cycles that are billed as a recurring card subscription (preapproval).
CICLOS_RECORRENTES = {"mensal"}

# Monthly Pix "punctuality" discount — OUR backend rule (not an MP feature).
PIX_PUNCTUALITY_DISCOUNT = 0.10
# Yearly first-year promotional discount over the full annual price.
YEARLY_FIRST_YEAR_DISCOUNT = 0.30
# Interest-free installments offered on the yearly Checkout Pro preference.
YEARLY_MAX_INSTALLMENTS = 6


class GatewayNaoConfiguradoError(RuntimeError):
    """Raised when a charge is attempted without ACCESS_TOKEN configured."""


class GatewayPagamentoError(RuntimeError):
    """Communication / business error talking to the gateway."""


# ---------------------------------------------------------------------------
# Authoritative price catalogue (server-side — never trust the client).
#
# The DB plan seed uses different slugs (free/intermediario/premium) and has no
# yearly price column, and the task forbids touching the plan seed. Billing
# prices are therefore defined here as the single source of truth, mirroring the
# owner-defined business rules. Amounts are in CENTS (BRL).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PlanoPreco:
    slug: str
    nome: str
    mensal_centavos: int  # monthly recurring / monthly avulso base price
    anual_cheio_centavos: int  # full annual price (2nd year onward, no promo)


_CATALOGO: dict[str, PlanoPreco] = {
    "escritorio": PlanoPreco(
        slug="escritorio",
        nome="Escritório",
        mensal_centavos=237_00,
        anual_cheio_centavos=2_364_00,
    ),
    "escritorio_pro": PlanoPreco(
        slug="escritorio_pro",
        nome="Escritório Pro",
        mensal_centavos=477_00,
        anual_cheio_centavos=4_764_00,
    ),
}


def get_plano_preco(plan_slug: str) -> PlanoPreco | None:
    return _CATALOGO.get(plan_slug)


def valor_venda_centavos(
    plan_slug: str, ciclo: str, *, metodo: str | None = None
) -> int:
    """Sale amount (in cents) computed ALWAYS on the server.

    - ``mensal`` (card recurring / boleto): full monthly price.
    - ``mensal`` + ``metodo="pix"``: monthly price with our −10% punctuality
      discount (backend rule, not an MP feature).
    - ``anual`` (first year): full annual price with −30% promo. Applies to all
      methods (card 6× interest-free, Pix/boleto in full).

    Never trust a value coming from the client.
    """
    plano = get_plano_preco(plan_slug)
    if plano is None:
        raise GatewayPagamentoError(f"Plano inexistente ou não cobrável: {plan_slug}")
    if ciclo not in CICLOS_VALIDOS:
        raise GatewayPagamentoError(f"Ciclo inválido: {ciclo}")

    if ciclo == "mensal":
        base = plano.mensal_centavos
        if (metodo or "").lower() == "pix":
            return int(round(base * (1 - PIX_PUNCTUALITY_DISCOUNT)))
        return base

    # anual (1º ano) — desconto promocional de 30% sobre o preço cheio.
    return int(round(plano.anual_cheio_centavos * (1 - YEARLY_FIRST_YEAR_DISCOUNT)))


def _reais(centavos: int) -> float:
    """Convert integer cents to the float BRL amount MP expects (2 decimals)."""
    return round(centavos / 100, 2)


class GatewayPagamento:
    """Thin adapter over the Mercado Pago API."""

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
            resp = await client.post(
                path, json=payload, headers=self._headers(idempotency_key)
            )
        if resp.status_code >= 400:
            logger.warning(
                "mercadopago_erro",
                extra={"extra": {"path": path, "status": resp.status_code}},
            )
            raise GatewayPagamentoError(
                f"Mercado Pago retornou {resp.status_code} em {path}"
            )
        return resp.json()

    async def _get(self, path: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=MP_API_BASE, timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(path, headers=self._headers())
        if resp.status_code >= 400:
            raise GatewayPagamentoError(
                f"Mercado Pago retornou {resp.status_code} em {path}"
            )
        return resp.json()

    # -- Payload builders (pure — testable without network) -----------------
    def _app_url(self) -> str:
        return (settings.PUBLIC_URL or "").rstrip("/")

    def _back_urls(self) -> dict[str, str]:
        app_url = self._app_url()
        return {
            "success": f"{app_url}/billing?pagamento=sucesso",
            "pending": f"{app_url}/billing?pagamento=pendente",
            "failure": f"{app_url}/billing?pagamento=falha",
        }

    def _notification_url(self) -> str:
        return f"{self._app_url()}/api/v1/billing/webhooks/mercadopago"

    def montar_preference(
        self,
        *,
        plan_slug: str,
        ciclo: str,
        amount_cents: int,
        email_pagador: str,
        referencia: str,
    ) -> dict[str, Any]:
        """Checkout Preference for an avulso payment (Pix + installment card).

        Used for the yearly first-year charge (card up to 6× interest-free,
        Pix/boleto in full) and for monthly Pix cycles. ``amount_cents`` is the
        server-computed sale price (already includes any applicable discount).
        """
        plano = get_plano_preco(plan_slug)
        if plano is None:
            raise GatewayPagamentoError(f"Plano inexistente: {plan_slug}")

        max_parcelas = YEARLY_MAX_INSTALLMENTS if ciclo == "anual" else 1
        label = "anual (1º ano)" if ciclo == "anual" else "mensal"

        return {
            "items": [
                {
                    "title": f"FiscWise {plano.nome} — {label}",
                    "description": f"Plano {plano.nome} ({ciclo})",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": _reais(amount_cents),
                }
            ],
            "payer": {"email": email_pagador},
            "payment_methods": {
                "installments": max_parcelas,
                "default_installments": 1,
            },
            "external_reference": referencia,
            "back_urls": self._back_urls(),
            "auto_return": "approved",
            "notification_url": self._notification_url(),
        }

    def montar_preapproval(
        self, *, plan_slug: str, amount_cents: int, email_pagador: str, referencia: str
    ) -> dict[str, Any]:
        """Monthly recurring card subscription (preapproval).

        The subscription webhook is configured at resource-creation time via
        ``notification_url`` (MP does not read the panel setting for
        subscriptions). Frequency is 1 month; amount is the server-computed
        monthly price.
        """
        plano = get_plano_preco(plan_slug)
        if plano is None:
            raise GatewayPagamentoError(f"Plano inexistente: {plan_slug}")
        return {
            "reason": f"FiscWise {plano.nome} (mensal)",
            "external_reference": referencia,
            "payer_email": email_pagador,
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months",
                "transaction_amount": _reais(amount_cents),
                "currency_id": "BRL",
            },
            "back_url": f"{self._app_url()}/billing?assinatura=ok",
            "notification_url": self._notification_url(),
            "status": "pending",
        }

    # -- Real calls (require token) ----------------------------------------
    async def criar_cobranca_unica(
        self,
        *,
        plan_slug: str,
        ciclo: str,
        amount_cents: int,
        email_pagador: str,
        referencia: str,
    ) -> dict[str, Any]:
        payload = self.montar_preference(
            plan_slug=plan_slug,
            ciclo=ciclo,
            amount_cents=amount_cents,
            email_pagador=email_pagador,
            referencia=referencia,
        )
        data = await self._post(
            "/checkout/preferences", payload, idempotency_key=referencia
        )
        return {
            "tipo": "cobranca_unica",
            "id": data.get("id"),
            "init_point": data.get("init_point") or data.get("sandbox_init_point"),
        }

    async def criar_assinatura(
        self, *, plan_slug: str, amount_cents: int, email_pagador: str, referencia: str
    ) -> dict[str, Any]:
        payload = self.montar_preapproval(
            plan_slug=plan_slug,
            amount_cents=amount_cents,
            email_pagador=email_pagador,
            referencia=referencia,
        )
        data = await self._post("/preapproval", payload, idempotency_key=referencia)
        return {
            "tipo": "assinatura",
            "id": data.get("id"),
            "init_point": data.get("init_point"),
        }

    async def obter_pagamento(self, pagamento_id: str) -> dict[str, Any]:
        """Query a payment's status (used by the webhook re-consult)."""
        return await self._get(f"/v1/payments/{pagamento_id}")

    async def obter_preapproval(self, preapproval_id: str) -> dict[str, Any]:
        """Query a recurring subscription (preapproval) status — used by the
        webhook to reconcile the monthly cycle."""
        return await self._get(f"/preapproval/{preapproval_id}")

    async def buscar_pagamentos_por_referencia(
        self, external_reference: str
    ) -> dict[str, Any]:
        """Search payments by external_reference — used by ACTIVE reconciliation
        (safety net when a `payment` webhook is lost)."""
        return await self._get(
            f"/v1/payments/search?external_reference={external_reference}"
        )


def validar_assinatura_webhook(
    *,
    x_signature: str | None,
    x_request_id: str | None,
    data_id: str | None,
    secret: str | None = None,
    max_idade_segundos: int | None = None,
) -> bool:
    """Validate the Mercado Pago webhook HMAC signature.

    Manifest: ``id:{data.id};request-id:{x-request-id};ts:{ts};``
    ``x-signature`` carries ``ts=<unix>,v1=<hmac sha256 hex>``.

    If no secret is configured, returns True (permissive mode for
    secret-less environments — go-live requires the secret present, enforced by
    the router refusing to go live without it). NOTE: Pix/QR notifications may
    arrive without a valid ``x-signature`` — callers must ALWAYS re-consult
    ``GET /v1/payments/{id}`` and never trust the webhook body.

    ``max_idade_segundos`` (anti-replay): when set, rejects signatures whose
    ``ts`` falls outside the window [now - window, now + window].
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
    esperado = hmac.new(
        secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(esperado, v1):
        return False

    if max_idade_segundos is not None:
        try:
            ts_val = int(ts)
        except ValueError:
            return False
        if ts_val > 10**12:  # heuristic: timestamp in milliseconds
            ts_val //= 1000
        if abs(time.time() - ts_val) > max_idade_segundos:
            return False

    return True


# Default reusable instance.
gateway = GatewayPagamento()
