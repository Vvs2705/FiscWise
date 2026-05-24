"""Model for tracking audit logs and tenant activities."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class AuditEvent(Base, TenantBase):
    """
    Audit log events to track data mutations and actions within a tenant context.
    
    Logs key events like client creation/updates, document upload/download,
    plan updates, and authentication events (login, logout, failures).
    """

    __tablename__ = "audit_events"

    # Override tenant_id to add ForeignKey constraint
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )

    # Actor information
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who performed the action",
    )
    actor_role: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Role of the user at the time of the action",
    )

    # Action details
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="The type of action performed (e.g. client.create, auth.login)",
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="The type of entity affected (e.g. client, document, auth)",
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID of the affected entity",
    )

    # Payloads for diffing changes
    before_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="State of the entity before modification",
    )
    after_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="State of the entity after modification",
    )

    # Metadata
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address of the client",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User agent of the client browser",
    )

    def __repr__(self) -> str:
        return f"<AuditEvent(id={self.id}, action='{self.action}', tenant_id={self.tenant_id})>"
