import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


class FiscalMailboxMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    external_id: Optional[str]
    client_name: Optional[str]
    client_cnpj: Optional[str]
    subject: str
    summary: Optional[str]
    body: Optional[str]
    organ: Optional[str]
    received_at: Optional[datetime]
    deadline: Optional[datetime]
    risk: str
    status: str
    task_created: bool
    obligation_linked: Optional[str]
    tags: Optional[List[Any]]
    created_at: datetime


class FiscalMailboxSyncResult(BaseModel):
    synced: int
    created: int
    skipped: int
