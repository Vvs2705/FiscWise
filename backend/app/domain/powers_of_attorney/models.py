"""Powers of Attorney domain models."""
import uuid
from typing import Optional
from enum import Enum

from sqlalchemy import ForeignKey, String, Text, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class PoaStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class PowerOfAttorney(Base, TenantBase):
    """Procuração eletrônica perante órgãos fiscais."""

    __tablename__ = "powers_of_attorney"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    grantor_document: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    attorney_document: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    services: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    valid_from: Mapped[Optional[object]] = mapped_column(Date, nullable=True)
    valid_until: Mapped[Optional[object]] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PoaStatus.PENDING.value, index=True
    )
    last_checked_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
