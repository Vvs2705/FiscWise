"""Billing Service for FiscWise — Mercado Pago (BR gateway).

Handles the Mercado Pago webhook lifecycle and subscription state machine.

Security model (mirrors SessãoInk P0-05/06/07):
  - Real charges are locked behind ``settings.PAGAMENTOS_GO_LIVE`` at the router.
  - The webhook NEVER trusts the request body: it validates the HMAC signature
    (``validar_assinatura_webhook``), then re-consults the gateway
    (``GET /v1/payments/{id}`` or ``/preapproval/{id}``), matches the local
    charge by ``external_reference`` (the local charge UUID), validates the paid
    amount == expected, and only then activates.
  - Idempotent inbox: ``record_webhook_event`` dedups on (provider, event_id).

Subscription status transitions (TenantSubscription.status + Tenant.subscription_status):
  trialing  → active      (payment approved / preapproval authorized, amount matches)
  active    → suspended   (refund / chargeback / preapproval cancelled|paused)
  any       → cancelled   (explicit cancellation)

Webhook topics handled: ``payment``, ``preapproval`` /
``subscription_preapproval``, ``subscription_authorized_payment``.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import BillingCharge, BillingWebhookEvent, TenantSubscription
from app.models.tenant import SubscriptionStatus, Tenant
from app.services.mercadopago_gateway import (
    GatewayPagamentoError,
    gateway,
)

logger = logging.getLogger(__name__)


# ─── Idempotent webhook event logging ─────────────────────────────────────────

async def record_webhook_event(
    db: AsyncSession,
    provider: str,
    event_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> Optional[BillingWebhookEvent]:
    """Record a webhook event. Returns None if already processed (duplicate)."""
    existing = await db.execute(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.provider == provider,
            BillingWebhookEvent.event_id == event_id,
        )
    )
    if existing.scalar_one_or_none():
        logger.info("Duplicate webhook event: provider=%s, event_id=%s", provider, event_id)
        return None

    event = BillingWebhookEvent(
        provider=provider,
        event_id=event_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(event)
    await db.flush()  # Get ID without committing
    return event


async def mark_event_processed(
    db: AsyncSession,
    event: BillingWebhookEvent,
    error: Optional[str] = None,
) -> None:
    """Mark a webhook event as processed (with optional error). Commits."""
    event.processed = True
    event.processed_at = datetime.now(timezone.utc)
    event.error_message = error
    await db.commit()


# ─── Subscription state machine ───────────────────────────────────────────────

async def _get_charge_by_external_reference(
    db: AsyncSession, external_reference: Optional[str]
) -> Optional[BillingCharge]:
    if not external_reference:
        return None
    result = await db.execute(
        select(BillingCharge).where(
            BillingCharge.external_reference == str(external_reference)
        )
    )
    return result.scalar_one_or_none()


async def _get_subscription(
    db: AsyncSession, tenant_id: uuid.UUID
) -> Optional[TenantSubscription]:
    result = await db.execute(
        select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def _activate_from_charge(
    db: AsyncSession, charge: BillingCharge, *, via: str
) -> bool:
    """Mark the charge PAID and move the tenant subscription to ACTIVE.

    Idempotent — safe to call repeatedly. Never activates from the front-end,
    only from a reconciled gateway event. Returns True when activation ran.
    """
    charge.status = "PAGA"

    sub = await _get_subscription(db, charge.tenant_id)
    if sub is not None:
        sub.billing_provider = "mercadopago"
        sub.status = "active"
        sub.last_event_at = datetime.now(timezone.utc)

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == charge.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is not None:
        tenant.subscription_status = SubscriptionStatus.ACTIVE
        # Keep the tenant's effective plan slug in sync with what was purchased.
        tenant.plan_slug = charge.plan_slug

    logger.info(
        "billing_subscription_activated tenant=%s plan=%s ciclo=%s via=%s charge=%s",
        charge.tenant_id, charge.plan_slug, charge.ciclo, via, charge.id,
    )
    return True


async def _suspend_from_charge(
    db: AsyncSession, charge: BillingCharge, *, reason: str
) -> bool:
    """Revenue protection: suspend an active subscription on refund/chargeback
    or a cancelled/paused recurring subscription."""
    sub = await _get_subscription(db, charge.tenant_id)
    changed = False
    if sub is not None and sub.status == "active":
        sub.status = "suspended"
        sub.last_event_at = datetime.now(timezone.utc)
        changed = True

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == charge.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is not None and tenant.subscription_status == SubscriptionStatus.ACTIVE:
        tenant.subscription_status = SubscriptionStatus.SUSPENDED
        changed = True

    if changed:
        logger.warning(
            "billing_subscription_suspended tenant=%s reason=%s charge=%s",
            charge.tenant_id, reason, charge.id,
        )
    return changed


# ─── Gateway re-consult handlers (never trust the webhook body) ────────────────

async def _handle_payment(db: AsyncSession, resource_id: str) -> str:
    """Re-consult a `payment` at the gateway, match the local charge, validate
    the amount and activate/suspend accordingly. Used for avulso charges
    (yearly first-year Checkout Pro, monthly Pix) and recurring-payment events."""
    mp = await gateway.obter_pagamento(resource_id)
    mp_status = (mp.get("status") or "").lower()
    external_ref = mp.get("external_reference")
    paid_cents = int(round(float(mp.get("transaction_amount") or 0) * 100))

    charge = await _get_charge_by_external_reference(db, external_ref)
    if charge is None:
        logger.warning("payment %s: no local charge for external_reference=%s",
                       resource_id, external_ref)
        return "no_charge"

    if mp_status == "approved":
        if paid_cents and paid_cents != charge.amount_cents:
            logger.warning(
                "billing_amount_mismatch charge=%s expected_cents=%s paid_cents=%s",
                charge.id, charge.amount_cents, paid_cents,
            )
            return "amount_mismatch"
        await _activate_from_charge(db, charge, via="payment")
        return "activated"

    if mp_status in ("refunded", "charged_back"):
        await _suspend_from_charge(db, charge, reason=mp_status)
        return "suspended"

    # pending / in_process / rejected / cancelled → keep charge open, no activation.
    charge.status = "PENDENTE" if mp_status in ("pending", "in_process") else charge.status
    return f"noop_{mp_status or 'sem_status'}"


async def _handle_preapproval(db: AsyncSession, resource_id: str) -> str:
    """Re-consult a `preapproval` (monthly recurring card subscription) at the
    gateway, match the local charge, validate the monthly amount and
    activate/suspend accordingly."""
    pre = await gateway.obter_preapproval(resource_id)
    pre_status = (pre.get("status") or "").lower()
    external_ref = pre.get("external_reference")
    monthly_cents = int(
        round(float((pre.get("auto_recurring") or {}).get("transaction_amount") or 0) * 100)
    )

    charge = await _get_charge_by_external_reference(db, external_ref)
    if charge is None:
        logger.warning("preapproval %s: no local charge for external_reference=%s",
                       resource_id, external_ref)
        return "no_charge"

    if pre_status == "authorized":
        if monthly_cents and monthly_cents != charge.amount_cents:
            logger.warning(
                "billing_amount_mismatch charge=%s expected_cents=%s paid_cents=%s via=preapproval",
                charge.id, charge.amount_cents, monthly_cents,
            )
            return "amount_mismatch"
        await _activate_from_charge(db, charge, via="preapproval")
        return "activated"

    if pre_status in ("cancelled", "paused"):
        await _suspend_from_charge(db, charge, reason=f"preapproval_{pre_status}")
        return "suspended"

    return f"noop_{pre_status or 'sem_status'}"


# ─── Mercado Pago webhook dispatcher ──────────────────────────────────────────

async def dispatch_mercadopago_event(
    db: AsyncSession,
    topic: str,
    resource_id: str,
) -> str:
    """Dispatch a Mercado Pago webhook to the right re-consult handler.

    ``topic`` is normalised (``type``/``topic`` from the body). ``resource_id``
    is the ``data.id``. Every handler re-consults the gateway and never trusts
    the webhook body. Returns a short status string for logging/response.

    Note: Pix/QR notifications may arrive without a valid signature and with a
    bare id — the payment handler re-consults ``GET /v1/payments/{id}`` anyway,
    so a valid approval is still reconciled.
    """
    if not gateway.configurado():
        return "gateway_off"
    if not resource_id:
        return "no_resource"

    topic = (topic or "").lower()
    try:
        if topic in ("payment", "subscription_authorized_payment"):
            # subscription_authorized_payment carries a payment id (the charge
            # generated by a preapproval cycle); resolve it as a payment.
            return await _handle_payment(db, resource_id)
        if topic in ("preapproval", "subscription_preapproval"):
            return await _handle_preapproval(db, resource_id)
    except GatewayPagamentoError as exc:
        logger.warning("mercadopago_reconcile_failed topic=%s error=%s", topic, exc)
        return "reconcile_error"

    logger.info("Unhandled Mercado Pago topic: %s", topic)
    return "unknown"


# ─── Active reconciliation (safety net when a webhook is lost) ─────────────────

async def reconcile_pending_charges(
    db: AsyncSession, tenant_id: uuid.UUID, *, limit: int = 5
) -> bool:
    """Consult Mercado Pago and reconcile the tenant's open charges (in case a
    webhook was lost). Same anti-fraud rules as the webhook: match by the local
    charge and validate the amount. Idempotent and safe to call repeatedly.
    Returns True if any charge was activated."""
    if not gateway.configurado():
        return False

    result = await db.execute(
        select(BillingCharge)
        .where(
            BillingCharge.tenant_id == tenant_id,
            BillingCharge.status.in_(["CRIADA", "ENVIADA_GATEWAY", "PENDENTE"]),
        )
        .order_by(BillingCharge.created_at.desc())
        .limit(limit)
    )
    charges = result.scalars().all()

    activated = False
    for charge in charges:
        try:
            outcome = await _reconcile_one_charge(db, charge)
            if outcome == "activated":
                activated = True
        except GatewayPagamentoError as exc:
            logger.warning("active_reconcile_failed charge=%s error=%s", charge.id, exc)

    await db.commit()
    return activated


async def _reconcile_one_charge(db: AsyncSession, charge: BillingCharge) -> str:
    """Active reconciliation of a single charge (recurring vs avulso)."""
    # Monthly → recurring subscription (preapproval).
    if charge.ciclo == "mensal" and charge.gateway_preapproval_id:
        pre = await gateway.obter_preapproval(charge.gateway_preapproval_id)
        pre_status = (pre.get("status") or "").lower()
        monthly_cents = int(
            round(float((pre.get("auto_recurring") or {}).get("transaction_amount") or 0) * 100)
        )
        if pre_status != "authorized":
            return f"preapproval_{pre_status or 'sem_status'}"
        if monthly_cents and monthly_cents != charge.amount_cents:
            return "amount_mismatch"
        await _activate_from_charge(db, charge, via="reconcile_active")
        return "activated"

    # Avulso → find the approved payment by external_reference.
    data = await gateway.buscar_pagamentos_por_referencia(charge.external_reference or "")
    results = data.get("results") or []
    approved = next(
        (r for r in results if (r.get("status") or "").lower() == "approved"), None
    )
    if not approved:
        return "no_approved_payment"
    paid_cents = int(round(float(approved.get("transaction_amount") or 0) * 100))
    if paid_cents != charge.amount_cents:
        return "amount_mismatch"
    await _activate_from_charge(db, charge, via="reconcile_active")
    return "activated"
