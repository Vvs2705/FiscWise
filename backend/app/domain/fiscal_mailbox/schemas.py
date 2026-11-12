import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, model_validator


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
    # Provider configurado e se ESTA mensagem veio do simulador (ids "mock-...").
    provider: str = "mock"
    simulated: bool = False

    @model_validator(mode="after")
    def _mark_simulated(self) -> "FiscalMailboxMessageResponse":
        from app.domain.fiscal_mailbox.integrations.factory import current_provider_name

        self.provider = current_provider_name()
        self.simulated = (self.external_id or "").startswith("mock-")
        return self


class FiscalMailboxProviderStatus(BaseModel):
    provider: str
    simulated: bool
    sync_available: bool
    message: Optional[str] = None


class FiscalMailboxSyncResult(BaseModel):
    synced: int
    created: int
    skipped: int
