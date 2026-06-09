import uuid
from datetime import datetime
from typing import Optional, Any, List

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UUID as SQLUUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBase


class FiscalMailboxMessage(Base, TenantBase):
    """A message pulled from the e-CAC fiscal mailbox / DTE for a tenant.

    Messages are ingested from an integration provider (see
    domain/fiscal_mailbox/integrations) and deduplicated per tenant by
    ``external_id`` (the provider's message identifier).
    """

    __tablename__ = "fiscal_mailbox_messages"

    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Provider message id — used for idempotent ingestion (unique per tenant).
    external_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)

    # Denormalised snapshot of the subject taxpayer (from the provider message).
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_cnpj: Mapped[Optional[str]] = mapped_column(String(18), nullable=True)

    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    organ: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # RFB, PGFN, SEFAZ...

    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    risk: Mapped[str] = mapped_column(String(20), default="none", server_default="none", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unread", server_default="unread", nullable=False)

    task_created: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    obligation_linked: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    tags: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True, default=list)

    # Relationship (optional link to a client in the portfolio).
    client = relationship("AccountingClient", lazy="joined")
