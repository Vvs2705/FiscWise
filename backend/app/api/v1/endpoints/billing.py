"""Billing endpoints for FiscWise — Mercado Pago (BR gateway).

Security lock: real charge creation requires ``settings.PAGAMENTOS_GO_LIVE`` to
be enabled. Until then ``POST /billing/checkout`` returns 503 — the code is
ready but NOBODY is charged before an explicit go-live.

PCI: no card data may reach this API (Checkout Pro / hosted checkout only).
Any card data in the request body is rejected with 400 BEFORE the go-live gate.

Endpoints:
  GET  /billing/config                  — public key + go_live flag (frontend)
  GET  /billing/subscription            — current tenant subscription
  POST /billing/checkout                — create local charge + gateway checkout
  POST /billing/reconcile               — active reconciliation safety net
  POST /billing/webhooks/mercadopago    — gateway notifications (public, no JWT)
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.pci import card_data_reason, redact_sensitive
from app.models.billing import BillingCharge, TenantSubscription
from app.models.plan import Plan
from app.models.user import User, UserRole
from app.services.mercadopago_gateway import (
    CICLOS_VALIDOS,
    GatewayNaoConfiguradoError,
    GatewayPagamentoError,
    gateway,
    get_plano_preco,
    valor_venda_centavos,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SubscriptionOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    plan_id: uuid.UUID
    billing_provider: Optional[str]
    status: str
    current_period_end: Optional[str]
    trial_ends_at: Optional[str]
    amount: Optional[str]
    currency: str
    created_at: str


class CreateSubscriptionRequest(BaseModel):
    plan_id: uuid.UUID
    billing_provider: Optional[str] = None  # 'mercadopago' | 'manual'


class CheckoutRequest(BaseModel):
    plan_slug: str
    ciclo: str = "mensal"
    # Optional method hint. For monthly, "pix" applies our −10% punctuality
    # discount and forces an avulso Pix checkout; anything else = recurring card.
    metodo: Optional[str] = None


class CheckoutResponse(BaseModel):
    tipo: str
    id: Optional[str]
    init_point: Optional[str]


class BillingConfigResponse(BaseModel):
    gateway: str = "mercadopago"
    public_key: str
    go_live: bool


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _sub_out(sub: TenantSubscription) -> SubscriptionOut:
    return SubscriptionOut(
        id=sub.id,
        tenant_id=sub.tenant_id,
        plan_id=sub.plan_id,
        billing_provider=sub.billing_provider,
        status=sub.status,
        current_period_end=_fmt(sub.current_period_end),
        trial_ends_at=_fmt(sub.trial_ends_at),
        amount=str(sub.amount) if sub.amount else None,
        currency=sub.currency,
        created_at=sub.created_at.isoformat(),
    )


# ─── Config / subscription (read) ─────────────────────────────────────────────

@router.get("/config", response_model=BillingConfigResponse)
async def billing_config(current_user: User = Depends(get_current_user)) -> BillingConfigResponse:
    """Public gateway data for the frontend (public key is safe to expose)."""
    return BillingConfigResponse(
        public_key=settings.MERCADO_PAGO_PUBLIC_KEY,
        go_live=settings.PAGAMENTOS_GO_LIVE,
    )


@router.get("/subscription", response_model=SubscriptionOut)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    """Get the current tenant's subscription details."""
    result = await db.execute(
        select(TenantSubscription).where(
            TenantSubscription.tenant_id == current_user.tenant_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma assinatura encontrada para este tenant",
        )
    return _sub_out(sub)


@router.post(
    "/subscription", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED
)
async def create_or_update_subscription(
    body: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    """Create or update the tenant's billing subscription record (owner only).

    This is the local subscription bookkeeping (plan selection / trial). It does
    NOT create a real charge — real charging goes through ``/billing/checkout``
    and is gated by ``PAGAMENTOS_GO_LIVE``. Kept for frontend backward
    compatibility.
    """
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o proprietário pode gerenciar assinaturas",
        )

    plan_result = await db.execute(select(Plan).where(Plan.id == body.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado"
        )

    existing = await db.execute(
        select(TenantSubscription).where(
            TenantSubscription.tenant_id == current_user.tenant_id
        )
    )
    sub = existing.scalar_one_or_none()

    if sub:
        sub.plan_id = body.plan_id
        if body.billing_provider:
            sub.billing_provider = body.billing_provider
        sub.amount = plan.price_monthly
    else:
        sub = TenantSubscription(
            tenant_id=current_user.tenant_id,
            plan_id=body.plan_id,
            billing_provider=body.billing_provider,
            status="trialing",
            amount=plan.price_monthly,
            currency="BRL",
        )
        db.add(sub)

    await db.commit()
    await db.refresh(sub)
    logger.info("Subscription upserted: tenant=%s plan=%s", current_user.tenant_id, plan.slug)
    return _sub_out(sub)


# ─── Checkout ─────────────────────────────────────────────────────────────────

@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def create_checkout(
    body: CheckoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Create the charge (monthly recurring card, monthly Pix avulso, or yearly
    first-year Checkout Pro).

    - 400 if the body carries card data (PCI) — checked BEFORE the go-live gate.
    - 503 while ``PAGAMENTOS_GO_LIVE`` is off (charging not enabled).
    - Owner only (billing is owner-scoped).
    """
    # PCI — no card data may reach this endpoint. Reject BEFORE the go-live gate
    # so it always returns 400 (even when charging is disabled).
    try:
        raw_body = await request.json()
    except Exception:
        raw_body = {}
    reason = card_data_reason(raw_body)
    if reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dados de cartão não são aceitos neste endpoint ({reason}).",
        )

    # Guardrail — no real charge until the product owner flips go-live.
    if not settings.PAGAMENTOS_GO_LIVE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pagamentos em configuração — cobrança ainda não habilitada.",
        )

    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o proprietário pode gerenciar assinaturas",
        )

    if body.ciclo not in CICLOS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ciclo inválido: {body.ciclo}"
        )
    plano = get_plano_preco(body.plan_slug)
    if plano is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plano inexistente ou não cobrável: {body.plan_slug}",
        )

    email = current_user.email
    now = datetime.now(timezone.utc)
    # Monthly card = recurring (preapproval); monthly Pix and yearly = avulso.
    metodo = (body.metodo or "").lower() or None
    is_recurring = body.ciclo == "mensal" and metodo != "pix"
    tipo_checkout = "assinatura" if is_recurring else "cobranca_unica"

    # Amount computed on the server (never trust the client).
    amount_cents = valor_venda_centavos(body.plan_slug, body.ciclo, metodo=metodo)

    # Local charge created BEFORE the gateway. Pre-generated id → used as
    # external_reference AND idempotency_key (never the tenant_id: avoids
    # leaking the tenant and collapsing distinct checkouts).
    charge_id = uuid.uuid4()
    charge = BillingCharge(
        id=charge_id,
        tenant_id=current_user.tenant_id,
        plan_slug=body.plan_slug,
        ciclo=body.ciclo,
        metodo=metodo,
        amount_cents=amount_cents,
        status="CRIADA",
        gateway="mercadopago",
        external_reference=str(charge_id),
        idempotency_key=str(charge_id),
        expires_at=now + timedelta(hours=24),
        created_by_user_id=current_user.id,
    )
    db.add(charge)
    await db.flush()

    try:
        if is_recurring:
            resultado = await gateway.criar_assinatura(
                plan_slug=body.plan_slug,
                amount_cents=amount_cents,
                email_pagador=email,
                referencia=str(charge_id),
            )
            charge.gateway_preapproval_id = (
                str(resultado["id"]) if resultado.get("id") else None
            )
        else:
            resultado = await gateway.criar_cobranca_unica(
                plan_slug=body.plan_slug,
                ciclo=body.ciclo,
                amount_cents=amount_cents,
                email_pagador=email,
                referencia=str(charge_id),
            )
            charge.gateway_preference_id = (
                str(resultado["id"]) if resultado.get("id") else None
            )
    except GatewayNaoConfiguradoError as exc:
        charge.status = "FALHA"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except GatewayPagamentoError as exc:
        charge.status = "FALHA"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    charge.init_point = resultado.get("init_point")
    charge.status = "ENVIADA_GATEWAY"
    await db.commit()

    logger.info(
        "billing_checkout_created tenant=%s plan=%s ciclo=%s tipo=%s charge=%s",
        current_user.tenant_id, body.plan_slug, body.ciclo, tipo_checkout, charge_id,
    )
    return CheckoutResponse(
        tipo=tipo_checkout,
        id=str(resultado.get("id")) if resultado.get("id") else None,
        init_point=resultado.get("init_point"),
    )


# ─── Active reconciliation (safety net) ───────────────────────────────────────

@router.post("/reconcile", status_code=status.HTTP_200_OK)
async def reconcile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Safety net: consult Mercado Pago and reconcile this tenant's pending
    charges (in case a payment webhook was lost). Called by the frontend when
    returning from checkout. Idempotent and safe to call repeatedly."""
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o proprietário pode gerenciar assinaturas",
        )
    from app.services.billing_service import reconcile_pending_charges

    activated = await reconcile_pending_charges(db, current_user.tenant_id)
    return {"activated": activated}


# ─── Webhook ──────────────────────────────────────────────────────────────────

@router.post("/webhooks/mercadopago", status_code=status.HTTP_200_OK)
async def mercadopago_webhook(
    request: Request,
    x_signature: Optional[str] = Header(default=None),
    x_request_id: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Receive Mercado Pago notifications (public — no JWT). Idempotent.

    Validates the HMAC signature (when the webhook secret is configured), then
    re-consults the gateway (never trusts the body), matches the local charge by
    external_reference, validates the amount and activates/suspends. Always
    responds 200 quickly so the gateway does not re-enqueue.
    """
    from app.services.billing_service import (
        dispatch_mercadopago_event,
        mark_event_processed,
        record_webhook_event,
    )
    from app.services.mercadopago_gateway import validar_assinatura_webhook

    try:
        body = await request.json()
    except Exception:
        body = {}

    topic = body.get("type") or body.get("topic") or "desconhecido"
    data = body.get("data") or {}
    resource_id = str(
        data.get("id") or body.get("id") or request.query_params.get("data.id") or ""
    )

    # Anti-replay window of 10 min. Pix/QR may lack a valid signature — the
    # dispatcher re-consults the gateway anyway, so a lost signature does not
    # block a real approval, but a configured secret still rejects forgeries.
    if not validar_assinatura_webhook(
        x_signature=x_signature,
        x_request_id=x_request_id,
        data_id=resource_id,
        max_idade_segundos=600,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida."
        )

    if not resource_id:
        return {"status": "ignored"}

    # Idempotent inbox — dedup on (provider, event_id). Redact secrets/card data
    # before persisting the payload.
    event_id = f"{topic}:{resource_id}"
    event = await record_webhook_event(
        db, "mercadopago", event_id, str(topic), redact_sensitive(body)
    )
    if event is None:
        return {"status": "already_processed"}

    try:
        result = await dispatch_mercadopago_event(db, str(topic), resource_id)
        await mark_event_processed(db, event)
    except Exception as exc:  # noqa: BLE001 — never let the gateway retry-storm us
        await mark_event_processed(db, event, error=str(exc))
        logger.error("mercadopago webhook %s error: %s", event_id, exc, exc_info=True)
        return {"status": "error_logged"}

    return {"status": result, "topic": topic}
