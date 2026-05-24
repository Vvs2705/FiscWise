"""SQLAlchemy models for the notification system.

Tables:
  notification_templates  — reusable message templates (global or per-tenant)
  notification_messages   — sent/queued notification records
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, String, Text,
    UUID as SQLUUID,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class NotificationTemplate(Base):
    """
    Reusable message template (email / whatsapp / sms).

    tenant_id = NULL means it's a global system template available to all tenants.
    Tenants can create their own templates (tenant_id = their UUID) to override defaults.
    """

    __tablename__ = "notification_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="NULL = global system template",
    )

    channel: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="email | whatsapp | sms",
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Template body with {{variable}} placeholders",
    )
    variables: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="Declared variables and their descriptions",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def render(self, context: Dict[str, str]) -> tuple[str, str]:
        """Return (rendered_subject, rendered_body) after substituting context vars."""
        subject = self.subject or ""
        body = self.body or ""
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            subject = subject.replace(placeholder, value)
            body = body.replace(placeholder, value)
        return subject, body

    def __repr__(self) -> str:
        return f"<NotificationTemplate(name='{self.name}', channel='{self.channel}')>"


class NotificationMessage(Base):
    """
    A concrete notification sent (or queued) to a client.

    Records every outbound message for audit and deduplication purposes.
    """

    __tablename__ = "notification_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
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
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("notification_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    channel: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="email | whatsapp | sms",
    )
    recipient: Mapped[str] = mapped_column(
        String(500), nullable=False,
        comment="Email address or phone number",
    )
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), server_default="pending", nullable=False,
        comment="pending | sent | delivered | failed | skipped",
    )
    provider: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="sendgrid | resend | smtp",
    )
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationMessage(channel='{self.channel}', "
            f"recipient='{self.recipient}', status='{self.status}')>"
        )
