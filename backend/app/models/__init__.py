"""
Models Package for FiscWise

This module registers all SQLAlchemy models for the application.
Import this module to ensure all models are loaded for Alembic migrations.
"""

from app.models.base import Base, TenantBase
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.models.audit import AuditEvent
from app.models.operations import (
    AccountReceivable,
    AccountingClient,
    ClientDocument,
    DeadlineItem,
    DigitalCertificate,
)
from app.models.obligation import (
    ObligationRule,
    ClientObligationProfile,
    ObligationInstance,
    DocumentChecklistItem,
)

# Export all models and enums for easy importing
__all__ = [
    "Base",
    "TenantBase",
    "Tenant",
    "SubscriptionStatus",
    "User",
    "UserRole",
    "AuditEvent",
    "AccountingClient",
    "DeadlineItem",
    "ClientDocument",
    "DigitalCertificate",
    "AccountReceivable",
    "ObligationRule",
    "ClientObligationProfile",
    "ObligationInstance",
    "DocumentChecklistItem",
]
