"""Pydantic schemas for Public API Keys and Webhook Subscriptions (Phase 12)."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# ──────────────────────────────────────────────────────────
# API Key Schemas
# ──────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Friendly label for this key")


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned once after creation — includes the raw key. Never shown again."""
    raw_key: str


# ──────────────────────────────────────────────────────────
# Webhook Subscription Schemas
# ──────────────────────────────────────────────────────────

VALID_EVENTS = [
    "client.created",
    "client.updated",
    "document.uploaded",
    "das.paid",
    "obligation.completed",
]


class WebhookSubscriptionCreate(BaseModel):
    url: str = Field(..., max_length=1024, description="HTTPS endpoint that will receive events")
    events: List[str] = Field(..., min_length=1, description="List of event types to subscribe to")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "url": "https://example.com/webhooks/fiscwise",
            "events": ["client.created", "das.paid"]
        }
    })


class WebhookSubscriptionUpdate(BaseModel):
    url: Optional[str] = Field(None, max_length=1024)
    events: Optional[List[str]] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class WebhookSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime


class WebhookSubscriptionCreatedResponse(WebhookSubscriptionResponse):
    """Returned once after creation — includes the signing secret. Never shown again."""
    signing_secret: str


# ──────────────────────────────────────────────────────────
# Webhook Delivery Log Schemas
# ──────────────────────────────────────────────────────────

class WebhookDeliveryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subscription_id: uuid.UUID
    event: str
    url: str
    status_code: Optional[int]
    success: bool
    duration_ms: int
    created_at: datetime
