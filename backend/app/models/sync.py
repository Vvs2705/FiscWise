"""Sincronização offline-first (Frente G, docs/arquitetura/OFFLINE_SYNC.md seção 4).

- `SyncDevice`: dispositivo registrado (id gerado no cliente); revogação derruba o token.
- `SyncEvent`: log de cada evento recebido no push (applied | rejected), chave
  de idempotência `<device_id>:<event_id>`. Retenção de 90 dias (scheduler).
- `SyncConflict`: histórico do LWW por campo (nada é perdido em silêncio).

Também registra o listener que incrementa `version` em qualquer UPDATE das
entidades offline (API REST, sync, rotinas agendadas).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UUID as SQLUUID,
    FetchedValue,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, object_session
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.operations import (
    AccountReceivable,
    AccountingClient,
    DeadlineItem,
    DigitalCertificate,
)

# BIGSERIAL no Postgres; no SQLite dos testes BigInteger não autoincrementa fora da PK.
_SEQUENCE_TYPE = BigInteger().with_variant(Integer(), "sqlite")


class SyncDevice(Base):
    __tablename__ = "sync_devices"

    id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    app_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SyncEvent(Base):
    __tablename__ = "sync_events"
    __table_args__ = (
        Index("idx_sync_events_tenant_sequence", "tenant_id", "sequence"),
        Index("idx_sync_events_tenant_entity", "tenant_id", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Preenchido pelo banco (identity no Postgres); só para ordenação/auditoria.
    # FetchedValue: o ORM não manda NULL explícito no INSERT. No SQLite dos testes fica nulo.
    sequence: Mapped[Optional[int]] = mapped_column(
        _SEQUENCE_TYPE, nullable=True, unique=True, server_default=FetchedValue()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("sync_devices.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SyncConflict(Base):
    __tablename__ = "sync_conflicts"
    __table_args__ = (Index("idx_sync_conflicts_tenant_resolved", "tenant_id", "resolved_at"),)

    id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    base_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    server_version: Mapped[int] = mapped_column(Integer, nullable=False)
    fields_overwritten: Mapped[dict] = mapped_column(JSON, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


VERSIONED_MODELS = (AccountingClient, DeadlineItem, DigitalCertificate, AccountReceivable)


def _bump_version(mapper, connection, target) -> None:
    session = object_session(target)
    if session is not None and not session.is_modified(target, include_collections=False):
        return
    target.version = (target.version or 0) + 1


for _model in VERSIONED_MODELS:
    event.listen(_model, "before_update", _bump_version)
