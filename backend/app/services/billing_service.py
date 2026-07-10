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

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import BillingWebhookEvent, TenantSubscription
from app.models.plan import Plan
from app.models.tenant import Tenant, SubscriptionStatus

logger = logging.getLogger(__name__)

_BILLING_PROVIDER = os.getenv("BILLING_PROVIDER", "").lower().strip()
_WEBHOOK_SECRET = os.getenv("BILLING_WEBHOOK_SECRET", "")
_ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "")
_ASAAS_API_URL = os.getenv("ASAAS_API_URL", "https://sandbox.asaas.com/api/v3")
_IUGU_API_KEY = os.getenv("IUGU_API_KEY", "")
_ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower().strip()


# ─── Webhook signature verification ───────────────────────────────────────────

def verify_asaas_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """Verify HMAC-SHA256 signature from Asaas webhook.

    Fail-closed: sem BILLING_WEBHOOK_SECRET, aceita só em ambiente de dev.
    Em produção/staging um webhook sem secret é rejeitado (evita webhook aberto,
    onde qualquer POST forjaria confirmação de pagamento).
    """
    if not _WEBHOOK_SECRET:
        if _ENVIRONMENT in ("production", "prod", "staging"):
            logger.error(
                "BILLING_WEBHOOK_SECRET ausente em %s — rejeitando webhook de pagamento",
                _ENVIRONMENT,
            )
            return False
        logger.warning("BILLING_WEBHOOK_SECRET não configurado — aceitando webhook (dev)")
        return True
    expected = hmac.new(
        _WEBHOOK_SECRET.encode(),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header or "")


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

    # Also update tenant's subscription_status + plan_slug (paywall lê o tenant)
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == sub.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if tenant:
        tenant.subscription_status = SubscriptionStatus.ACTIVE
        plan_slug = (
            await db.execute(select(Plan.slug).where(Plan.id == sub.plan_id))
        ).scalar_one_or_none()
        if plan_slug:
            tenant.plan_slug = plan_slug

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
