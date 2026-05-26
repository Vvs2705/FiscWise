"""Fiscal Mailbox API endpoints — caixa postal fiscal."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.domain.fiscal_mailbox.models import (
    FiscalMailboxMessage,
    MailboxMessageStatus,
)
from app.domain.fiscal_mailbox.schemas import (
    FiscalMailboxMessageOut,
    FiscalMailboxMessagePatch,
)

router = APIRouter(prefix="/fiscal-mailbox", tags=["Caixa Postal Fiscal"])


@router.get("", response_model=list[FiscalMailboxMessageOut])
async def list_messages(
    client_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    message_type: Optional[str] = Query(None),
    is_urgent: Optional[bool] = Query(None),
    provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all fiscal mailbox messages for the tenant."""
    stmt = select(FiscalMailboxMessage).where(
        FiscalMailboxMessage.tenant_id == current_user.tenant_id
    )

    if client_id:
        stmt = stmt.where(FiscalMailboxMessage.client_id == client_id)
    if status:
        stmt = stmt.where(FiscalMailboxMessage.status == status)
    if message_type:
        stmt = stmt.where(FiscalMailboxMessage.message_type == message_type)
    if is_urgent is not None:
        stmt = stmt.where(FiscalMailboxMessage.is_urgent == is_urgent)
    if provider:
        stmt = stmt.where(FiscalMailboxMessage.provider == provider)

    stmt = stmt.order_by(FiscalMailboxMessage.received_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/unread-count")
async def unread_count(
    client_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return count of unread messages."""
    from sqlalchemy import func

    stmt = select(func.count()).select_from(FiscalMailboxMessage).where(
        FiscalMailboxMessage.tenant_id == current_user.tenant_id,
        FiscalMailboxMessage.status == MailboxMessageStatus.UNREAD.value,
    )
    if client_id:
        stmt = stmt.where(FiscalMailboxMessage.client_id == client_id)

    result = await db.execute(stmt)
    count = result.scalar_one()
    return {"unread_count": count}


@router.get("/{message_id}", response_model=FiscalMailboxMessageOut)
async def get_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific mailbox message (auto-marks as read)."""
    result = await db.execute(
        select(FiscalMailboxMessage).where(
            FiscalMailboxMessage.id == message_id,
            FiscalMailboxMessage.tenant_id == current_user.tenant_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

    # Auto-mark as read on first access
    if msg.status == MailboxMessageStatus.UNREAD.value:
        msg.status = MailboxMessageStatus.READ.value
        msg.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(msg)

    return msg


@router.patch("/{message_id}", response_model=FiscalMailboxMessageOut)
async def patch_message(
    message_id: uuid.UUID,
    body: FiscalMailboxMessagePatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update message status or urgency flag."""
    result = await db.execute(
        select(FiscalMailboxMessage).where(
            FiscalMailboxMessage.id == message_id,
            FiscalMailboxMessage.tenant_id == current_user.tenant_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(msg, field, val)

    await db.commit()
    await db.refresh(msg)
    return msg


@router.post("/{message_id}/archive", response_model=FiscalMailboxMessageOut)
async def archive_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive a fiscal mailbox message."""
    result = await db.execute(
        select(FiscalMailboxMessage).where(
            FiscalMailboxMessage.id == message_id,
            FiscalMailboxMessage.tenant_id == current_user.tenant_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

    msg.status = MailboxMessageStatus.ARCHIVED.value
    await db.commit()
    await db.refresh(msg)
    return msg


@router.post("/{message_id}/flag", response_model=FiscalMailboxMessageOut)
async def flag_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Flag a fiscal mailbox message for follow-up."""
    result = await db.execute(
        select(FiscalMailboxMessage).where(
            FiscalMailboxMessage.id == message_id,
            FiscalMailboxMessage.tenant_id == current_user.tenant_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

    msg.status = MailboxMessageStatus.FLAGGED.value
    await db.commit()
    await db.refresh(msg)
    return msg
