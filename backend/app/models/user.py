"""
User Model for FiscWise

Defines the users table with multi-tenant isolation.
Each user belongs to a single tenant and has a specific role within that organization.

2FA Fields:
- two_factor_enabled: Whether 2FA is active for this user
- two_factor_secret: Base32 TOTP secret (for Google Authenticator / Microsoft Authenticator)
- two_factor_method: Active method — 'none' | 'totp' | 'email'
"""

import uuid
from typing import Optional
import enum

from sqlalchemy import String, UUID as SQLUUID, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBase
from app.models.tenant import Tenant


class UserRole(str, enum.Enum):
    """
    User role enumeration for RBAC (Role-Based Access Control).

    Defines the hierarchy of permissions within a tenant:
    - OWNER: Full control, can manage billing and delete tenant
    - ADMIN: Can manage users and all resources within tenant
    - MEMBER: Standard user with limited permissions
    - CLIENT: External client with portal access to own client data
    """
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    CLIENT = "client"


class User(Base, TenantBase):
    """
    User model with multi-tenant isolation.
    
    Represents a user account within a specific tenant organization.
    Email uniqueness is enforced per tenant (not globally).
    
    Attributes:
        id: Primary key UUID (inherited from TenantBase)
        tenant_id: Foreign key to tenants table (inherited from TenantBase)
        email: User email address (unique per tenant)
        hashed_password: Bcrypt hashed password
        role: User role within the tenant (owner/admin/member)
        is_active: Whether the user account is active
        created_at: Account creation timestamp (inherited from TenantBase)
        updated_at: Last update timestamp (inherited from TenantBase)
        tenant: Relationship to Tenant model (many-to-one)
    """
    
    __tablename__ = "users"
    
    # Override tenant_id to add ForeignKey constraint
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation"
    )
    
    # User Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="User email address (unique per tenant)"
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password"
    )

    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User full name"
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="User phone number"
    )

    # User Authorization
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.MEMBER,
        index=True,
        comment="User role for RBAC"
    )
    
    # Account Status
    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        index=True,
        comment="Whether the user account is active"
    )

    # Superuser flag — cross-tenant admin access (replaces static ADMIN_EMERGENCY_TOKEN)
    is_superuser: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        comment="Cross-tenant superuser access for platform administration"
    )

    # ── Two-Factor Authentication (2FA) ──────────────────────────────────────
    two_factor_enabled: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether 2FA is enabled for this user"
    )

    two_factor_secret: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Base32 TOTP secret for Google/Microsoft Authenticator"
    )

    two_factor_method: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="none",
        server_default="none",
        comment="Active 2FA method: none | totp | email"
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="users",
        lazy="selectin"
    )
    
    # Table-level constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    
    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User(id={self.id}, email='{self.email}', role={self.role.value}, tenant_id={self.tenant_id})>"
    
    def is_owner(self) -> bool:
        """Check if user has owner role."""
        return self.role == UserRole.OWNER
    
    def is_admin_or_owner(self) -> bool:
        """Check if user has admin or owner role."""
        return self.role in [UserRole.OWNER, UserRole.ADMIN]
    
    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.is_admin_or_owner()
