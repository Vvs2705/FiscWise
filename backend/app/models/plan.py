"""Plan model — defines subscription tiers and feature limits."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, UUID as SQLUUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class Plan(Base):
    """
    Subscription plan definition.

    Stores feature limits and pricing for each plan tier.
    Plans are global (no tenant_id) — they are defined by the platform operator.
    Limits of NULL mean unlimited.
    """

    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True,
        comment="Plan identifier: free | intermediario | premium",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Pricing
    price_monthly: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True,
        comment="Monthly price in BRL. NULL = custom pricing.",
    )

    # Limits (NULL = unlimited)
    max_clients: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Max active accounting clients"
    )
    max_users: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Max users (staff) per tenant"
    )
    max_ai_calls_month: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Max AI chat messages per month"
    )
    max_documents_per_client: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Max documents stored per client"
    )

    # Feature flags (arbitrary JSON for flexibility)
    features: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="Feature flags as JSON: {calculator, ai_chat, pdf_export, ...}",
    )

    active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Plan(slug='{self.slug}', max_clients={self.max_clients})>"
