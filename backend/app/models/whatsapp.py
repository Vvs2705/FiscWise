"""SQLAlchemy models for the WhatsApp integration.

Tables:
  whatsapp_inboxes   — chat threads grouped by remote phone number (linked to clients)
  whatsapp_messages  — individual messages within a thread (inbound / outbound)
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime, ForeignKey, String, Text,
    UUID as SQLUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBase


class WhatsAppInbox(Base, TenantBase):
    """
    Representa uma conversa do WhatsApp com um cliente ou lead.
    Uma conversa é vinculada a um tenant e opcionalmente a um AccountingClient.
    """

    __tablename__ = "whatsapp_inboxes"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Cliente contábil vinculado a esta conversa",
    )
    phone_number: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
        comment="Número de telefone do cliente remoto formatado (ex: +5511999999999)",
    )
    customer_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Nome do contato remoto (WhatsApp pushName)",
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora da última mensagem recebida ou enviada",
    )
    last_message_preview: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Texto ou descrição curta da última mensagem",
    )
    unread_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Quantidade de mensagens não lidas pelo contador",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
        comment="status: active | archived",
    )

    # Relationships
    messages = relationship("WhatsAppMessage", back_populates="inbox", cascade="all, delete-orphan")
    client = relationship("AccountingClient", foreign_keys=[client_id])


class WhatsAppMessage(Base, TenantBase):
    """
    Representa uma mensagem enviada ou recebida na conversa do WhatsApp.
    """

    __tablename__ = "whatsapp_messages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    inbox_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("whatsapp_inboxes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Conversa correspondente",
    )
    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Direção da mensagem: inbound (recebida) | outbound (enviada)",
    )
    sender_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Nome de quem enviou",
    )
    sender_phone: Mapped[Optional[str]] = mapped_column(
        String(40),
        nullable=True,
        comment="Número de telefone do remetente",
    )
    message_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="text",
        index=True,
        comment="Tipo de mensagem: text | document | image | audio",
    )
    body: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Conteúdo de texto da mensagem ou descrição/legenda de arquivo",
    )
    media_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="URL do arquivo recebido (bucket Supabase ou gateway)",
    )
    external_message_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Identificador único da mensagem no gateway do WhatsApp",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="sent",
        index=True,
        comment="status da entrega: sent | delivered | read | failed",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Mensagem de erro em caso de falha de envio",
    )

    # Relationships
    inbox = relationship("WhatsAppInbox", back_populates="messages")
