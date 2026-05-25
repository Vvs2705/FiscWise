"""Notification endpoints for FiscWise

Provides API access to notification messages and manual trigger for pending
document notifications.
"""

import uuid
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.notification import NotificationMessage
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class NotificationMessageOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    channel: str
    recipient: str
    subject: Optional[str]
    status: str
    provider: Optional[str]
    sent_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class TriggerNotificationRequest(BaseModel):
    """Manual trigger: notify pending documents for this tenant."""
    competence_month: Optional[str] = None  # "2026-05" format; defaults to current month


class TriggerNotificationResponse(BaseModel):
    sent: int
    skipped: int
    failed: int
    clients_notified: int
    competence_month: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _require_admin_or_owner(user: User) -> None:
    if user.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can access notifications",
        )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[NotificationMessageOut])
async def list_notifications(
    channel: Optional[str] = Query(default=None, max_length=20),
    status_filter: Optional[str] = Query(default=None, alias="status", max_length=20),
    client_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationMessageOut]:
    """
    List recent notification messages for this tenant.

    Supports filtering by channel, status, and client_id.
    Owner/admin only.
    """
    _require_admin_or_owner(current_user)

    stmt = (
        select(NotificationMessage)
        .where(NotificationMessage.tenant_id == current_user.tenant_id)
        .order_by(desc(NotificationMessage.created_at))
        .limit(limit)
    )

    if channel:
        stmt = stmt.where(NotificationMessage.channel == channel)
    if status_filter:
        stmt = stmt.where(NotificationMessage.status == status_filter)
    if client_id:
        stmt = stmt.where(NotificationMessage.client_id == client_id)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [
        NotificationMessageOut(
            id=m.id,
            tenant_id=m.tenant_id,
            client_id=m.client_id,
            channel=m.channel,
            recipient=m.recipient,
            subject=m.subject,
            status=m.status,
            provider=m.provider,
            sent_at=m.sent_at.isoformat() if m.sent_at else None,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@router.post("/trigger-pending-docs", response_model=TriggerNotificationResponse)
async def trigger_pending_document_notifications(
    body: TriggerNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TriggerNotificationResponse:
    """
    Manually trigger pending document notifications for this tenant.

    Useful for immediate dispatch or testing. The weekly scheduler also
    calls this job automatically every Monday at 09:00.

    Owner/admin only.
    """
    from app.services.notification_engine import notify_pending_documents_for_tenant

    _require_admin_or_owner(current_user)

    # Parse competence_month from "YYYY-MM" string or default to current month
    today = date.today()
    if body.competence_month:
        try:
            year_s, month_s = body.competence_month.split("-")
            comp_month = date(int(year_s), int(month_s), 1)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="competence_month must be in YYYY-MM format",
            )
    else:
        comp_month = date(today.year, today.month, 1)

    result = await notify_pending_documents_for_tenant(
        db,
        tenant_id=current_user.tenant_id,
        competence_month=comp_month,
    )

    logger.info(
        "Manual notification trigger by %s (tenant %s): %s",
        current_user.email, current_user.tenant_id, result,
    )

    return TriggerNotificationResponse(
        sent=result.get("sent", 0),
        skipped=result.get("skipped", 0),
        failed=result.get("failed", 0),
        clients_notified=result.get("clients_notified", 0),
        competence_month=comp_month.strftime("%Y-%m"),
    )


@router.get("/stats")
async def notification_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Quick stats: total sent / failed / pending in the last 30 days.

    Owner/admin only.
    """
    from sqlalchemy import func
    from datetime import datetime, timedelta, timezone

    _require_admin_or_owner(current_user)

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    result = await db.execute(
        select(
            NotificationMessage.status,
            func.count().label("cnt"),
        )
        .where(
            NotificationMessage.tenant_id == current_user.tenant_id,
            NotificationMessage.created_at >= thirty_days_ago,
        )
        .group_by(NotificationMessage.status)
    )

    stats: dict[str, int] = {}
    for row in result.all():
        stats[row.status] = int(row.cnt)

    return {
        "period": "last_30_days",
        "sent": stats.get("sent", 0),
        "skipped": stats.get("skipped", 0),
        "failed": stats.get("failed", 0),
        "pending": stats.get("pending", 0),
        "total": sum(stats.values()),
    }
