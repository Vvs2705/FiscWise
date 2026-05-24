"""Billing endpoints for FiscWise

Handles payment gateway webhooks and subscription management.
Supports Asaas (primary) with Iugu stub for future.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.billing import TenantSubscription
from app.models.plan import Plan
from app.models.user import User

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
    billing_provider: Optional[str] = None  # 'asaas' | 'iugu' | 'manual'


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


# ─── Subscription endpoints ───────────────────────────────────────────────────

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


@router.post("/subscription", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
async def create_or_update_subscription(
    body: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    """
    Create or update the billing subscription for this tenant.

    Owner only. In production, this also calls the billing provider API.
    """
    if current_user.role.value != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o proprietário pode gerenciar assinaturas",
        )

    plan_result = await db.execute(select(Plan).where(Plan.id == body.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado")

    existing_result = await db.execute(
        select(TenantSubscription).where(
            TenantSubscription.tenant_id == current_user.tenant_id
        )
    )
    sub = existing_result.scalar_one_or_none()

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


# ─── Webhook endpoints ────────────────────────────────────────────────────────

@router.post("/webhooks/asaas", status_code=status.HTTP_200_OK)
async def asaas_webhook(
    request: Request,
    asaas_access_token: Optional[str] = Header(default=None, alias="asaas-access-token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Receive Asaas webhook events (public — no JWT).

    Idempotent: duplicate events return 200 silently.
    Configure BILLING_WEBHOOK_SECRET for signature verification.
    """
    from app.services.billing_service import (
        verify_asaas_signature,
        record_webhook_event,
        mark_event_processed,
        dispatch_asaas_event,
    )

    raw_body = await request.body()

    if not verify_asaas_signature(raw_body, asaas_access_token or ""):
        logger.warning("Asaas webhook signature mismatch")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event_type = payload.get("event", "UNKNOWN")
    payment = payload.get("payment", {})
    event_id = payment.get("id") or str(uuid.uuid4())

    event = await record_webhook_event(db, "asaas", event_id, event_type, payload)
    if event is None:
        return {"status": "already_processed"}

    try:
        result = await dispatch_asaas_event(db, event_type, payload)
        await mark_event_processed(db, event)
    except Exception as exc:
        await mark_event_processed(db, event, error=str(exc))
        logger.error("Asaas event %s error: %s", event_id, exc, exc_info=True)
        return {"status": "error_logged"}

    return {"status": result, "event_type": event_type}
