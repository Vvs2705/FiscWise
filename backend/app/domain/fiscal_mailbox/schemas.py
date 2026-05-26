"""Fiscal Mailbox schemas."""
import uuid
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FiscalMailboxMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    subject_id: Optional[uuid.UUID]
    provider: str
    provider_message_id: Optional[str]
    message_type: str
    status: str
    sender: Optional[str]
    subject: str
    body_text: Optional[str]
    received_at: datetime
    read_at: Optional[datetime]
    due_date: Optional[datetime]
    has_attachment: bool
    is_urgent: bool
    created_at: datetime


class FiscalMailboxMessagePatch(BaseModel):
    status: Optional[str] = None
    is_urgent: Optional[bool] = None
