import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Text, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


def _utcnow_naive() -> datetime:
    # ponytail: colunas sao DateTime sem timezone (asyncpg rejeita aware);
    # manter naive-UTC ate migrar as colunas para DateTime(timezone=True)
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TenantApiKey(Base):
    __tablename__ = "tenant_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    prefix = Column(String(16), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)
    last_used_at = Column(DateTime, nullable=True)


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url = Column(String(1024), nullable=False)
    secret = Column(String(255), nullable=False)
    events = Column(JSON, nullable=False)  # e.g., ["client.created", "document.uploaded"]
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)


class WebhookDeliveryLog(Base):
    __tablename__ = "webhook_delivery_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    status_code = Column(Integer, nullable=True)
    request_body = Column(Text, nullable=False)
    response_body = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)
