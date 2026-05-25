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
from app.models.plan import Plan
from app.models.portal import PortalMagicToken
from app.models.notification import NotificationTemplate, NotificationMessage
from app.models.billing import TenantSubscription, BillingWebhookEvent
from app.models.whatsapp import WhatsAppInbox, WhatsAppMessage
from app.models.fiscal_monitor import FiscalMonitorSummary, FiscalNFe
from app.models.rag_fiscal import RagDocument
from app.models.api_webhooks import TenantApiKey, WebhookSubscription, WebhookDeliveryLog

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
    "Plan",
    "PortalMagicToken",
    "NotificationTemplate",
    "NotificationMessage",
    "TenantSubscription",
    "BillingWebhookEvent",
    "WhatsAppInbox",
    "WhatsAppMessage",
    "FiscalMonitorSummary",
    "FiscalNFe",
    "RagDocument",
    "TenantApiKey",
    "WebhookSubscription",
    "WebhookDeliveryLog",
]
