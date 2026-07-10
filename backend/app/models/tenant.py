"""
Tenant Model for FiscWise

Defines the tenants table for multi-tenant SaaS architecture.
Each tenant represents an independent organization/company using the platform.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, UUID as SQLUUID, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.models.base import Base

# Import real (não TYPE_CHECKING): garante que o mapper de TenantSubscription
# esteja registrado antes da configuração do relationship `subscription` abaixo.
from app.models.billing import TenantSubscription  # noqa: F401


class SubscriptionStatus(str, enum.Enum):
    """
    Subscription status enumeration.
    
    Defines the possible states of a tenant's subscription.
    """
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Tenant(Base):
    """
    Tenant model representing an organization in the system.
    
    This is the root entity for multi-tenancy. All other tenant-scoped
    data references this table via tenant_id foreign key.
    
    Attributes:
        id: Primary key UUID
        name: Organization/company name
        document: CNPJ or CPF (Brazilian tax ID) - optional
        subscription_status: Current subscription state
        created_at: When the tenant was created
        updated_at: When the tenant was last updated
        users: Relationship to User model (one-to-many)
    """
    
    __tablename__ = "tenants"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Tenant unique identifier"
    )
    
    # Tenant Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Organization or company name"
    )
    
    document: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        unique=True,
        index=True,
        comment="CNPJ or CPF (Brazilian tax identification)"
    )

    plan_slug: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        comment="Subscription plan slug identifier"
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Tenant contact phone number"
    )

    address: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Tenant address"
    )

    website: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Tenant website URL"
    )

    # LGPD compliance
    terms_accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When the owner accepted FiscWise Terms of Service (LGPD compliance)",
    )
    terms_version: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment='Version of Terms accepted (e.g. "v1.0")',
    )
    deletion_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When a data deletion request was submitted (LGPD Art. 18)",
    )

    # Subscription Management
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus, name="subscription_status_enum", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SubscriptionStatus.TRIAL,
        index=True,
        comment="Current subscription status"
    )
    
    # Audit Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Tenant creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Tenant last update timestamp"
    )
    
    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Assinatura de billing (tenant_subscriptions) — carregada junto com o
    # tenant para o enforcement de plano (plan_access.effective_plan_slug).
    # viewonly: escrita continua passando pelos endpoints/webhooks de billing.
    subscription: Mapped[Optional["TenantSubscription"]] = relationship(
        "TenantSubscription",
        lazy="selectin",
        viewonly=True,
    )
    
    def __repr__(self) -> str:
        """String representation of the tenant."""
        return f"<Tenant(id={self.id}, name='{self.name}', status={self.subscription_status.value})>"
    
    def is_active(self) -> bool:
        """
        Check if tenant has an active subscription.
        
        Returns:
            bool: True if subscription is active or in trial
        """
        return self.subscription_status in [SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE]
