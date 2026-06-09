import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.domain.fiscal_mailbox.repository import FiscalMailboxRepository
from app.domain.fiscal_mailbox.service import FiscalMailboxService
from app.domain.fiscal_mailbox.schemas import (
    FiscalMailboxMessageResponse,
    FiscalMailboxSyncResult,
)
from app.domain.fiscal_mailbox.integrations.mock import MockFiscalMailboxProvider

router = APIRouter(prefix="/fiscal-mailbox", tags=["Fiscal Mailbox"])


def _service(db: AsyncSession) -> FiscalMailboxService:
    return FiscalMailboxService(FiscalMailboxRepository(db))


@router.get("/messages", response_model=List[FiscalMailboxMessageResponse])
async def list_messages(
    client_id: Optional[uuid.UUID] = Query(None),
    risk: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    organ: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _service(db).list_messages(
        current_user.tenant_id,
        client_id=client_id,
        risk=risk,
        status=status_filter,
        organ=organ,
    )


@router.get("/messages/{message_id}", response_model=FiscalMailboxMessageResponse)
async def get_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await _service(db).get_message(message_id, current_user.tenant_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return message


@router.post("/messages/{message_id}/read", response_model=FiscalMailboxMessageResponse)
async def mark_read(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await _service(db).set_status(message_id, current_user.tenant_id, "read")
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return message


@router.post("/messages/{message_id}/resolve", response_model=FiscalMailboxMessageResponse)
async def mark_resolved(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await _service(db).set_status(message_id, current_user.tenant_id, "resolved")
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return message


@router.post("/sync", response_model=FiscalMailboxSyncResult)
async def sync_messages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pull new fiscal mailbox messages from the provider (mock until a real
    e-CAC/DTE integration is wired) and ingest them idempotently."""
    result = await _service(db).sync_messages(current_user.tenant_id, MockFiscalMailboxProvider())
    return result
