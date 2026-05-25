"""
Base Model Configuration for FiscWise

This module defines the base SQLAlchemy declarative base and mixins
for multi-tenant architecture with SQLAlchemy 2.0 typed mappings.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, UUID as SQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    Uses SQLAlchemy 2.0 DeclarativeBase for modern ORM patterns.
    All models should inherit from this base or use TenantBase mixin.
    """
    pass


class TenantBase:
    """
    Mixin for multi-tenant tables.
    
    Enforces tenant isolation by requiring a tenant_id column on all tables.
    This ensures data segregation at the database level for SaaS multi-tenancy.
    
    Attributes:
        id: Primary key UUID for the record
        tenant_id: Foreign key to tenants table (indexed for performance)
        created_at: Timestamp when record was created (auto-generated)
        updated_at: Timestamp when record was last updated (auto-updated)
    """
    
    # Primary Key - UUID for distributed systems and security
    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary key UUID"
    )
    
    # Tenant Isolation - Critical for multi-tenancy
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation"
    )
    
    # Audit Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp"
    )
    
    def __repr__(self) -> str:
        """String representation of the model instance."""
        return f"<{self.__class__.__name__}(id={self.id}, tenant_id={self.tenant_id})>"
