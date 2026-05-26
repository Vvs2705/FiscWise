"""Digital certificates domain models.

Note: The DigitalCertificate model is defined in app.models.operations (legacy location).
This module only defines supplementary models for the certificates domain.
"""
import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class CertificateUsageEvent(Base, TenantBase):
    """Trilha de uso/acesso de certificados digitais para auditoria."""

    __tablename__ = "certificate_usage_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    certificate_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("digital_certificates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    operation: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    used_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
