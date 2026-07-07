"""Billing Service for FiscWise

Handles payment gateway integration (Asaas / Iugu) and subscription lifecycle.

Environment variables:
  BILLING_PROVIDER    — 'asaas' | 'iugu' | (unset = manual mode)
  ASAAS_API_KEY       — Asaas sandbox/production API key
  ASAAS_API_URL       — Asaas API base URL (default sandbox)
  IUGU_API_KEY        — Iugu API key
  BILLING_WEBHOOK_SECRET — HMAC secret for webhook signature verification

Status transitions:
  trialing  → active      (first successful payment)
  active    → past_due    (payment missed / failed)
  past_due  → active      (payment received)
  past_due  → suspended   (after grace_period_days)
  suspended → active      (payment received after suspension)
  any       → cancelled   (explicit cancellation)
"""

import hmac
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import BillingWebhookEvent, TenantSubscription
from app.models.plan import Plan
from app.models.tenant import Tenant, SubscriptionStatus

logger = logging.getLogger(__name__)

# Env vars are read at call time (not import time) so tests and Fly secrets
# rotation work without process restart tricks.


class BillingUnavailableError(RuntimeError):
    """Billing gateway not configured / unreachable. Endpoints convert to 503."""


def _env() -> str:
    return os.getenv("ENVIRONMENT", "development").lower().strip()


def asaas_enabled() -> bool:
    """True when the Asaas gateway is fully configured."""
    return (
        os.getenv("BILLING_PROVIDER", "").lower().strip() == "asaas"
        and bool(os.getenv("ASAAS_API_KEY", ""))
    )


def require_billing_gateway() -> None:
    """Fail-closed: outside development, a real gateway is mandatory.

    Never activate a subscription without real billing in production.
    """
    if not asaas_enabled() and _env() != "development":
        raise BillingUnavailableError(
            "Gateway de cobrança não configurado (BILLING_PROVIDER=asaas + ASAAS_API_KEY)"
        )


# ─── Webhook token verification ───────────────────────────────────────────────

def verify_asaas_signature(signature_header: str) -> bool:
    """Verify the Asaas webhook auth token.

    Asaas sends the configured token verbatim in the `asaas-access-token`
    header (no HMAC — see https://docs.asaas.com/docs/webhooks).
    Fail-closed: missing secret outside development raises (endpoint → 503).
    """
    secret = os.getenv("BILLING_WEBHOOK_SECRET", "")
    if not secret:
        if _env() != "development":
            raise BillingUnavailableError("BILLING_WEBHOOK_SECRET não configurado")
        logger.warning("BILLING_WEBHOOK_SECRET not configured — skipping check (dev only)")
        return True
    return hmac.compare_digest(secret.encode(), (signature_header or "").encode())


# ─── Asaas REST client ────────────────────────────────────────────────────────

async def _asaas_request(
    method: str,
    path: str,
    json: Optional[Dict[str, Any]] = None,
    allow_404: bool = False,
) -> Dict[str, Any]:
    """Single seam for all Asaas HTTP calls (tests monkeypatch this)."""
    base = os.getenv("ASAAS_API_URL", "https://sandbox.asaas.com/api/v3").rstrip("/")
    headers = {"access_token": os.getenv("ASAAS_API_KEY", "")}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.request(method, f"{base}{path}", json=json, headers=headers)
    except httpx.HTTPError as exc:
        logger.error("Asaas API unreachable: %s %s — %s", method, path, exc)
        raise BillingUnavailableError("Asaas API inacessível") from exc

    if resp.status_code == 404 and allow_404:
        return {}
    if resp.status_code >= 400:
        logger.error(
            "Asaas API error: %s %s → %s %s", method, path, resp.status_code, resp.text[:500]
        )
        raise BillingUnavailableError(f"Asaas API retornou {resp.status_code}")
    return resp.json()


async def create_asaas_customer(name: str, email: str, cpf_cnpj: str) -> str:
    """Create a customer on Asaas. Returns the Asaas customer id."""
    data = await _asaas_request(
        "POST", "/customers",
        json={"name": name, "email": email, "cpfCnpj": cpf_cnpj},
    )
    return data["id"]


async def create_asaas_subscription(customer_id: str, plan: Plan) -> Dict[str, Any]:
    """Create a monthly subscription on Asaas (hosted checkout — card never touches us).

    billingType UNDEFINED lets the customer pick pix/boleto/card on the
    Asaas invoice page. Returns {'id', 'checkout_url'} where checkout_url is
    the invoiceUrl of the first payment.
    """
    sub = await _asaas_request(
        "POST", "/subscriptions",
        json={
            "customer": customer_id,
            "billingType": "UNDEFINED",
            "value": float(plan.price_monthly or 0),
            "cycle": "MONTHLY",
            "description": f"FiscWise — Plano {plan.name}",
            "nextDueDate": (date.today() + timedelta(days=1)).isoformat(),
        },
    )
    checkout_url = None
    payments = await _asaas_request("GET", f"/subscriptions/{sub['id']}/payments")
    items = payments.get("data") or []
    if items:
        checkout_url = items[0].get("invoiceUrl")
    return {"id": sub["id"], "checkout_url": checkout_url}


async def cancel_asaas_subscription(subscription_id: str) -> None:
    """Cancel a subscription on Asaas (404 tolerated — already gone)."""
    await _asaas_request("DELETE", f"/subscriptions/{subscription_id}", allow_404=True)


# ─── Subscription state machine ───────────────────────────────────────────────

_PROVIDER_TO_TENANT_STATUS: Dict[str, SubscriptionStatus] = {
    # Asaas payment statuses
    "CONFIRMED": SubscriptionStatus.ACTIVE,
    "RECEIVED": SubscriptionStatus.ACTIVE,
    "REFUND_REQUESTED": SubscriptionStatus.ACTIVE,  # Keep active until confirmed
    "OVERDUE": SubscriptionStatus.ACTIVE,  # Handled by grace period logic
    "PENDING": SubscriptionStatus.TRIAL,
    "AWAITING_RISK_ANALYSIS": SubscriptionStatus.TRIAL,
}


async def handle_payment_confirmed(
    db: AsyncSession,
    provider_subscription_id: str,
    event_data: Dict[str, Any],
) -> bool:
    """
    Mark tenant subscription as active after confirmed payment.

    Returns True if subscription was updated, False if not found.
    """
    result = await db.execute(
        select(TenantSubscription).where(
            TenantSubscription.provider_subscription_id == provider_subscription_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        logger.warning("No subscription found for provider_subscription_id=%s", provider_subscription_id)
        return False

    old_status = sub.status
    sub.status = "active"
    sub.last_event_at = datetime.now(timezone.utc)

    # Also update tenant's subscription_status
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == sub.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if tenant:
        tenant.subscription_status = SubscriptionStatus.ACTIVE
        # Apply the paid plan to the tenant (plan changes only take effect
        # after real payment — never on checkout intent).
        plan_result = await db.execute(select(Plan).where(Plan.id == sub.plan_id))
        plan = plan_result.scalar_one_or_none()
        if plan:
            tenant.plan_slug = plan.slug

    await db.commit()
    logger.info(
        "Subscription activated: tenant=%s, old_status=%s → active",
        sub.tenant_id, old_status,
    )
    return True


async def handle_payment_overdue(
    db: AsyncSession,
    provider_subscription_id: str,
) -> bool:
    """Mark tenant subscription as past_due after missed payment."""
    result = await db.execute(
        select(TenantSubscription).where(
            TenantSubscription.provider_subscription_id == provider_subscription_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return False

    sub.status = "past_due"
    sub.last_event_at = datetime.now(timezone.utc)

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == sub.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant:
        tenant.subscription_status = SubscriptionStatus.SUSPENDED

    await db.commit()
    logger.info("Subscription past_due: tenant=%s", sub.tenant_id)
    return True


async def handle_subscription_cancelled(
    db: AsyncSession,
    provider_subscription_id: str,
) -> bool:
    """Cancel a subscription."""
    result = await db.execute(
        select(TenantSubscription).where(
            TenantSubscription.provider_subscription_id == provider_subscription_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return False

    sub.status = "cancelled"
    sub.cancelled_at = datetime.now(timezone.utc)
    sub.last_event_at = datetime.now(timezone.utc)

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == sub.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant:
        tenant.subscription_status = SubscriptionStatus.CANCELLED

    await db.commit()
    logger.info("Subscription cancelled: tenant=%s", sub.tenant_id)
    return True


# ─── Idempotent webhook event logging ─────────────────────────────────────────

async def record_webhook_event(
    db: AsyncSession,
    provider: str,
    event_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> Optional[BillingWebhookEvent]:
    """
    Record a webhook event. Returns None if already processed (duplicate).
    """
    # Check for duplicate
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
    """Mark a webhook event as processed (with optional error)."""
    event.processed = True
    event.processed_at = datetime.now(timezone.utc)
    event.error_message = error
    await db.commit()


# ─── Asaas webhook dispatcher ─────────────────────────────────────────────────

async def dispatch_asaas_event(
    db: AsyncSession,
    event_type: str,
    payload: Dict[str, Any],
) -> str:
    """
    Dispatch an Asaas webhook event to the appropriate handler.

    Returns: 'processed' | 'skipped' | 'unknown'
    """
    payment = payload.get("payment", {})
    subscription_id = payment.get("subscription") or payload.get("subscription", {}).get("id")

    if not subscription_id:
        logger.warning("Asaas event %s has no subscription_id", event_type)
        return "skipped"

    if event_type in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"):
        updated = await handle_payment_confirmed(db, subscription_id, payment)
        return "processed" if updated else "skipped"

    if event_type in ("PAYMENT_OVERDUE",):
        updated = await handle_payment_overdue(db, subscription_id)
        return "processed" if updated else "skipped"

    if event_type in ("SUBSCRIPTION_DELETED",):
        updated = await handle_subscription_cancelled(db, subscription_id)
        return "processed" if updated else "skipped"

    logger.info("Unhandled Asaas event type: %s", event_type)
    return "unknown"
