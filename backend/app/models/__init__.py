"""
Models Package for ContaFlow

This module registers all SQLAlchemy models for the application.
Import this module to ensure all models are loaded for Alembic migrations.
"""

from app.models.base import Base, TenantBase
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.models.knowledge import Document, DocumentChunk, DocumentStatus
from app.models.chat import ChatSession, ChatMessage, TokenUsageLog
from app.models.analytics import DailyUsageMetrics

# Export all models and enums for easy importing
__all__ = [
    "Base",
    "TenantBase",
    "Tenant",
    "SubscriptionStatus",
    "User",
    "UserRole",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "ChatSession",
    "ChatMessage",
    "TokenUsageLog",
    "DailyUsageMetrics",
]
