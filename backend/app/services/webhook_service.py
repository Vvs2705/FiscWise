"""
Webhook Service for FiscWise — Phase 12: Public API & Webhooks.

Handles subscription management, event dispatching (async fire-and-forget),
HMAC-SHA256 payload signing, and delivery logging.
"""

import uuid
import json
import hmac
import hashlib
import logging
import asyncio
import time
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_webhooks import WebhookSubscription, WebhookDeliveryLog
from app.schemas.developer import WebhookSubscriptionCreate, WebhookSubscriptionUpdate, VALID_EVENTS

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 10
WEBHOOK_SECRET_BYTES = 32  # 64 hex chars


# ──────────────────────────────────────────────────────────
# Subscription Management
# ──────────────────────────────────────────────────────────

def _generate_signing_secret() -> str:
    """Generate a cryptographically secure webhook signing secret."""
    return f"whsec_{secrets.token_hex(WEBHOOK_SECRET_BYTES)}"


async def create_webhook_subscription(
    db: AsyncSession,
    payload: WebhookSubscriptionCreate,
    tenant_id: uuid.UUID,
) -> tuple[WebhookSubscription, str]:
    """
    Create a new webhook subscription.
    Returns (WebhookSubscription ORM object, signing_secret).
    The signing secret is shown once and never stored in plain text.
    """
    # Validate events
    invalid_events = [e for e in payload.events if e not in VALID_EVENTS]
    if invalid_events:
        raise ValueError(f"Eventos inválidos: {invalid_events}. Permitidos: {VALID_EVENTS}")

    signing_secret = _generate_signing_secret()
    # Store hash of secret so we can validate delivered payloads server-side
    secret_hash = hashlib.sha256(signing_secret.encode()).hexdigest()

    sub = WebhookSubscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        url=payload.url,
        secret=secret_hash,
        events=payload.events,
        is_active=True,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    logger.info("Webhook subscription created: tenant=%s url=%s", tenant_id, payload.url)
    return sub, signing_secret


async def list_webhook_subscriptions(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> List[WebhookSubscription]:
    """List all webhook subscriptions for a tenant."""
    stmt = select(WebhookSubscription).where(
        WebhookSubscription.tenant_id == tenant_id
    ).order_by(WebhookSubscription.created_at)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_webhook_subscription(
    db: AsyncSession,
    sub_id: uuid.UUID,
    tenant_id: uuid.UUID,
    payload: WebhookSubscriptionUpdate,
) -> Optional[WebhookSubscription]:
    """Update an existing webhook subscription."""
    stmt = select(WebhookSubscription).where(
        (WebhookSubscription.id == sub_id) & (WebhookSubscription.tenant_id == tenant_id)
    )
    result = await db.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        return None

    if payload.url is not None:
        sub.url = payload.url
    if payload.events is not None:
        invalid_events = [e for e in payload.events if e not in VALID_EVENTS]
        if invalid_events:
            raise ValueError(f"Eventos inválidos: {invalid_events}")
        sub.events = payload.events
    if payload.is_active is not None:
        sub.is_active = payload.is_active

    await db.commit()
    await db.refresh(sub)
    return sub


async def delete_webhook_subscription(
    db: AsyncSession,
    sub_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> bool:
    """Delete a webhook subscription."""
    stmt = select(WebhookSubscription).where(
        (WebhookSubscription.id == sub_id) & (WebhookSubscription.tenant_id == tenant_id)
    )
    result = await db.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        return False
    await db.delete(sub)
    await db.commit()
    return True


async def list_delivery_logs(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    subscription_id: Optional[uuid.UUID] = None,
    limit: int = 50,
) -> List[WebhookDeliveryLog]:
    """List webhook delivery logs for a tenant."""
    stmt = select(WebhookDeliveryLog).where(
        WebhookDeliveryLog.tenant_id == tenant_id
    ).order_by(WebhookDeliveryLog.created_at.desc()).limit(limit)
    if subscription_id:
        stmt = stmt.where(WebhookDeliveryLog.subscription_id == subscription_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ──────────────────────────────────────────────────────────
# Event Dispatching
# ──────────────────────────────────────────────────────────

def _sign_payload(secret_hash: str, payload_bytes: bytes, timestamp: int) -> str:
    """
    Compute HMAC-SHA256 signature.
    Signature covers: timestamp.payload_body (same as Stripe webhook style).
    """
    signed_content = f"{timestamp}.".encode() + payload_bytes
    return hmac.new(secret_hash.encode(), signed_content, hashlib.sha256).hexdigest()


async def _dispatch_single(
    db: AsyncSession,
    subscription: WebhookSubscription,
    event: str,
    data: Dict[str, Any],
) -> None:
    """Fire a webhook to a single subscription endpoint and log result."""
    timestamp = int(time.time())
    payload = {
        "event": event,
        "timestamp": timestamp,
        "data": data,
    }
    payload_bytes = json.dumps(payload, default=str).encode()
    signature = _sign_payload(subscription.secret, payload_bytes, timestamp)

    headers = {
        "Content-Type": "application/json",
        "X-FiscWise-Event": event,
        "X-FiscWise-Signature": f"t={timestamp},v1={signature}",
        "X-FiscWise-Delivery": str(uuid.uuid4()),
    }

    status_code: Optional[int] = None
    response_body: Optional[str] = None
    success = False
    start = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                subscription.url,
                content=payload_bytes,
                headers=headers,
            )
        status_code = resp.status_code
        response_body = resp.text[:4096]
        success = 200 <= status_code < 300
    except Exception as exc:
        logger.warning("Webhook delivery failed: sub=%s event=%s error=%s", subscription.id, event, exc)
        response_body = str(exc)[:4096]

    duration_ms = int((time.monotonic() - start) * 1000)

    log = WebhookDeliveryLog(
        id=uuid.uuid4(),
        tenant_id=subscription.tenant_id,
        subscription_id=subscription.id,
        event=event,
        url=subscription.url,
        status_code=status_code,
        request_body=payload_bytes.decode(),
        response_body=response_body,
        duration_ms=duration_ms,
        success=success,
    )
    db.add(log)
    await db.commit()


async def dispatch_event(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    event: str,
    data: Dict[str, Any],
) -> None:
    """
    Dispatch a webhook event to all active subscriptions for a tenant.
    Fire-and-forget: runs in background without blocking the caller.
    """
    stmt = select(WebhookSubscription).where(
        (WebhookSubscription.tenant_id == tenant_id)
        & (WebhookSubscription.is_active == True)  # noqa: E712
    )
    result = await db.execute(stmt)
    subscriptions = result.scalars().all()

    matching = [s for s in subscriptions if event in (s.events or [])]
    if not matching:
        return

    tasks = [
        asyncio.create_task(_dispatch_single(db, sub, event, data))
        for sub in matching
    ]
    logger.info(
        "Dispatching event=%s to %d webhook(s) for tenant=%s",
        event, len(tasks), tenant_id
    )
    # Non-blocking: we schedule the tasks but don't await them here
    # The caller receives a response immediately
    for task in tasks:
        asyncio.ensure_future(task)
