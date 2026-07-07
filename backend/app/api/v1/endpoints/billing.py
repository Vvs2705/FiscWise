"""Billing endpoints for FiscWise

Handles payment gateway webhooks and subscription management.
Supports Asaas (primary) with Iugu stub for future.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.billing import TenantSubscription
from app.models.plan import Plan
from app.models.tenant import Tenant
from app.models.user import User
from app.services import billing_service
from app.services.billing_service import BillingUnavailableError

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
    checkout_url: Optional[str] = None  # Asaas hosted checkout (invoiceUrl)


class CreateSubscriptionRequest(BaseModel):
    plan_id: uuid.UUID
    billing_provider: Optional[str] = None  # 'asaas' | 'manual'
    # Billing profile for the Asaas customer (fallback: tenant/user data)
    cpf_cnpj: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _sub_out(sub: TenantSubscription, checkout_url: Optional[str] = None) -> SubscriptionOut:
    return SubscriptionOut(
        checkout_url=checkout_url,
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

    Owner only. With Asaas configured, creates customer + subscription on
    the gateway and returns `checkout_url` (hosted checkout — card data
    never touches FiscWise). Fail-closed: outside development, no gateway
    means 503 — a subscription is never activated without real billing.
    """
    if current_user.role.value != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o proprietário pode gerenciar assinaturas",
        )

    try:
        billing_service.require_billing_gateway()
    except BillingUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cobrança temporariamente indisponível",
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

    checkout_url: Optional[str] = None
    provider_customer_id: Optional[str] = sub.provider_customer_id if sub else None
    provider_subscription_id: Optional[str] = None

    if billing_service.asaas_enabled():
        tenant = await db.get(Tenant, current_user.tenant_id)
        cpf_cnpj = body.cpf_cnpj or (tenant.document if tenant else None)
        if not cpf_cnpj:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="CPF/CNPJ é obrigatório para ativar a cobrança",
            )
        try:
            if not provider_customer_id:
                provider_customer_id = await billing_service.create_asaas_customer(
                    name=body.name or (tenant.name if tenant else current_user.full_name),
                    email=body.email or current_user.email,
                    cpf_cnpj=cpf_cnpj,
                )
            if sub and sub.provider_subscription_id:
                # Plan change: stop billing the old subscription before creating the new one
                await billing_service.cancel_asaas_subscription(sub.provider_subscription_id)
            asaas_sub = await billing_service.create_asaas_subscription(
                provider_customer_id, plan
            )
        except BillingUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cobrança temporariamente indisponível",
            )
        provider_subscription_id = asaas_sub["id"]
        checkout_url = asaas_sub.get("checkout_url")

    if sub:
        sub.plan_id = body.plan_id
        sub.amount = plan.price_monthly
    else:
        sub = TenantSubscription(
            tenant_id=current_user.tenant_id,
            plan_id=body.plan_id,
            status="trialing",
            amount=plan.price_monthly,
            currency="BRL",
        )
        db.add(sub)

    if provider_subscription_id:
        sub.billing_provider = "asaas"
        sub.provider_customer_id = provider_customer_id
        sub.provider_subscription_id = provider_subscription_id
    elif body.billing_provider:
        sub.billing_provider = body.billing_provider

    await db.commit()
    await db.refresh(sub)
    logger.info("Subscription upserted: tenant=%s plan=%s", current_user.tenant_id, plan.slug)
    return _sub_out(sub, checkout_url=checkout_url)


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
    Auth: Asaas sends the configured token in the `asaas-access-token`
    header. Fail-closed: missing BILLING_WEBHOOK_SECRET outside dev → 503.
    """
    from app.services.billing_service import (
        verify_asaas_signature,
        record_webhook_event,
        mark_event_processed,
        dispatch_asaas_event,
    )

    try:
        token_ok = verify_asaas_signature(asaas_access_token or "")
    except BillingUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook de cobrança não configurado",
        )
    if not token_ok:
        logger.warning("Asaas webhook token mismatch")
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
