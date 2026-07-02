"""SQLAlchemy models for FiscWise billing / payment gateway integration.

Tables:
  tenant_subscriptions    — one per tenant, tracks plan + payment provider state
  billing_webhook_events  — idempotent log of all incoming webhook events
  billing_charges         — local charge intent created BEFORE calling the gateway
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text,
    UniqueConstraint, UUID as SQLUUID,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class TenantSubscription(Base):
    """
    Billing subscription for a tenant.

    Tracks the tenant's current plan, payment provider credentials,
    and subscription status. One row per tenant (unique on tenant_id).

    Status lifecycle:
      trialing → active (on first successful payment)
      active → past_due (on missed payment)
      past_due → suspended (after grace_period_days)
      past_due/suspended → active (on payment received)
      active/past_due → cancelled (on cancellation request)
    """

    __tablename__ = "tenant_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Payment provider
    billing_provider: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="asaas | iugu | manual",
    )
    provider_customer_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True,
        comment="Customer ID on billing provider",
    )
    provider_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True,
        comment="Subscription ID on billing provider",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30), server_default="trialing", nullable=False,
        comment="trialing | active | past_due | suspended | cancelled",
    )

    # Billing period
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Grace period configuration
    grace_period_days: Mapped[int] = mapped_column(
        Integer, server_default="3", nullable=False,
        comment="Days allowed after due date before suspension",
    )

    # Amount snapshot
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), server_default="BRL", nullable=False)

    # Last webhook event for idempotency
    last_event_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    last_event_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def is_active(self) -> bool:
        return self.status in ("trialing", "active")

    @property
    def is_suspended(self) -> bool:
        return self.status in ("suspended", "cancelled")

    def __repr__(self) -> str:
        return f"<TenantSubscription(tenant_id={self.tenant_id}, status='{self.status}')>"


class BillingWebhookEvent(Base):
    """
    Idempotent log of incoming billing webhook events.

    Prevents duplicate processing of the same event (provider may retry).
    Unique on (provider, event_id).
    """

    __tablename__ = "billing_webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_billing_webhook_provider_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    event_id: Mapped[str] = mapped_column(
        String(200), nullable=False,
        comment="Provider-issued event ID for idempotency",
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    processed: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<BillingWebhookEvent(provider='{self.provider}', "
            f"event_type='{self.event_type}', processed={self.processed})>"
        )


class BillingCharge(Base):
    """Local charge intent — created BEFORE calling the gateway (P0-06).

    ``external_reference`` and ``idempotency_key`` use the local charge id
    (never the tenant_id), avoiding tenant leakage and preventing distinct
    checkouts from colliding. The subscription is only activated after the
    payment/preapproval is reconciled against the gateway (webhook).
    """

    __tablename__ = "billing_charges"
    __table_args__ = (
        UniqueConstraint("external_reference",
                         name="uq_billing_charge_external_reference"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    plan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True,
        comment="Optional link to plans.id",
    )
    plan_slug: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Billing plan slug: escritorio | escritorio_pro",
    )
    ciclo: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="mensal | anual",
    )
    metodo: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Intended method hint: pix | card | boleto",
    )
    amount_cents: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Server-computed sale amount in cents (BRL)",
    )
    moeda: Mapped[str] = mapped_column(String(3), server_default="BRL", nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), server_default="CRIADA", nullable=False,
        comment="CRIADA | ENVIADA_GATEWAY | PENDENTE | PAGA | EXPIRADA | CANCELADA | FALHA",
    )
    gateway: Mapped[str] = mapped_column(
        String(40), server_default="mercadopago", nullable=False
    )
    gateway_preference_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gateway_preapproval_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    external_reference: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    init_point: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<BillingCharge(tenant_id={self.tenant_id}, plan_slug='{self.plan_slug}', "
            f"ciclo='{self.ciclo}', status='{self.status}')>"
        )
