"""SQLAlchemy models for the fiscal obligation engine.

Tables:
  obligation_rules            — global templates (no tenant scope)
  client_obligation_profiles  — tax profile per client
  obligation_instances        — concrete obligation per client per competence month
  document_checklist_items    — document checklist linked to obligations
"""

import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, UUID as SQLUUID,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


# ---------------------------------------------------------------------------
# ObligationRule — global (no tenant_id)
# ---------------------------------------------------------------------------

class ObligationRule(Base):
    """
    Template de obrigação fiscal (federal, estadual ou municipal).

    Represents a reusable fiscal obligation rule that can be applied
    to clients matching certain criteria (tax regime, CNAE, state).
    """

    __tablename__ = "obligation_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True,
        comment="Unique identifier (e.g. DAS, DEFIS, DCTFWEB)",
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False,
        comment="Human-readable name of the obligation",
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scope
    jurisdiction: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="federal | estadual | municipal",
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(2), nullable=True, comment="BR state code (e.g. SP) — only for estadual/municipal"
    )

    # Applicability filters (NULL = applies to all)
    applies_to_regimes: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), nullable=True,
        comment="Tax regimes this rule applies to. NULL = all regimes.",
    )
    applies_to_entity_types: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), nullable=True,
        comment="Entity types: pj, mei. NULL = all types.",
    )
    applies_to_cnaes: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), nullable=True,
        comment="CNAE codes this rule applies to. NULL = all CNAEs.",
    )

    # Scheduling
    recurrence: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="monthly | quarterly | yearly | event",
    )
    due_day: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Day of month when the obligation is due",
    )
    requires_employees: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )

    # Lifecycle
    active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False, index=True)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ObligationRule(code='{self.code}', jurisdiction='{self.jurisdiction}')>"


# ---------------------------------------------------------------------------
# ClientObligationProfile — per client tax profile
# ---------------------------------------------------------------------------

class ClientObligationProfile(Base, TenantBase):
    """
    Fiscal profile of a client — determines which obligation rules apply.

    One profile per client (unique on client_id).
    """

    __tablename__ = "client_obligation_profiles"
    __table_args__ = (
        UniqueConstraint("client_id", name="uq_client_obligation_profiles_client_id"),
    )

    # Override tenant_id with FK
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="One profile per client",
    )

    tax_regime: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True,
        comment="simples_nacional | lucro_presumido | lucro_real | mei",
    )
    cnae_main: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    cnae_secondary: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)

    has_employees: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    has_state_registration: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    has_municipal_registration: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    def __repr__(self) -> str:
        return f"<ClientObligationProfile(client_id={self.client_id}, regime='{self.tax_regime}')>"


# ---------------------------------------------------------------------------
# ObligationInstance — concrete obligation for a client in a given month
# ---------------------------------------------------------------------------

class ObligationInstance(Base, TenantBase):
    """
    A specific obligation that a client must fulfill in a competence month.

    Generated automatically by the obligation engine job (1st of each month).
    """

    __tablename__ = "obligation_instances"
    __table_args__ = (
        UniqueConstraint(
            "client_id", "rule_id", "competence_month",
            name="uq_obligation_instance_client_rule_month",
        ),
    )

    # Override tenant_id with FK
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("obligation_rules.id", ondelete="SET NULL"),
        nullable=True,
        comment="The rule that generated this instance. NULL = manual obligation.",
    )

    competence_month: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
        comment="First day of the competence month (e.g. 2026-05-01)",
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Workflow
    status: Mapped[str] = mapped_column(
        String(20), server_default="pending", nullable=False, index=True,
        comment="pending | in_progress | delivered | overdue | cancelled",
    )
    priority: Mapped[str] = mapped_column(
        String(10), server_default="medium", nullable=False,
        comment="low | medium | high | critical",
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    delivery_proof: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ObligationInstance(client_id={self.client_id}, "
            f"month={self.competence_month}, status='{self.status}')>"
        )


# ---------------------------------------------------------------------------
# DocumentChecklistItem — document checklist per client per month
# ---------------------------------------------------------------------------

class DocumentChecklistItem(Base, TenantBase):
    """
    A document that a client must provide for a given competence month.

    Can be linked to an obligation instance (automated) or be standalone (manual).
    """

    __tablename__ = "document_checklist_items"

    # Override tenant_id with FK
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    obligation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("obligation_instances.id", ondelete="SET NULL"),
        nullable=True,
    )

    competence_month: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    document_name: Mapped[str] = mapped_column(String(200), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), server_default="pending", nullable=False, index=True,
        comment="pending | received | approved | rejected",
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<DocumentChecklistItem(client_id={self.client_id}, "
            f"month={self.competence_month}, doc='{self.document_name}', status='{self.status}')>"
        )
