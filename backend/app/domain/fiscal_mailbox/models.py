"""Fiscal Mailbox domain models — caixa postal fiscal dos órgãos."""
import uuid
from typing import Optional
from enum import Enum

from sqlalchemy import ForeignKey, String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class MailboxMessageType(str, Enum):
    NOTICE = "notice"           # Intimação / notificação
    DEBT_NOTICE = "debt_notice" # Aviso de débito
    FISCAL_INFO = "fiscal_info" # Informativo fiscal
    SUMMONS = "summons"         # Citação
    DECISION = "decision"       # Decisão administrativa
    RECEIPT = "receipt"         # Recibo / confirmação
    OTHER = "other"


class MailboxMessageStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"
    FLAGGED = "flagged"


class FiscalMailboxMessage(Base, TenantBase):
    """Mensagem recebida na caixa postal fiscal (e-CAC, DTE, etc.)."""

    __tablename__ = "fiscal_mailbox_messages"

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
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, unique=True
    )
    message_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=MailboxMessageType.OTHER.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MailboxMessageStatus.UNREAD.value, index=True
    )
    sender: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    read_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
    has_attachment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attachment_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
