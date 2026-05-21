"""
Tenant Model for ContaFlow

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
