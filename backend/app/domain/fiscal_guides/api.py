"""Fiscal Guides API endpoints (DAS, DARF, DAE, GPS, DCTFWeb)."""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.domain.fiscal_guides.models import FiscalGuide, FiscalGuideEvent, GuideStatus
from app.domain.fiscal_guides.schemas import FiscalGuideCreate, FiscalGuideOut

router = APIRouter(prefix="/fiscal-guides", tags=["Guias Fiscais"])


@router.get("", response_model=list[FiscalGuideOut])
async def list_fiscal_guides(
    client_id: Optional[uuid.UUID] = Query(None),
    guide_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    competence: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    due_before: Optional[date] = Query(None),
    due_after: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List fiscal guides with optional filters."""
    stmt = select(FiscalGuide).where(FiscalGuide.tenant_id == current_user.tenant_id)

    if client_id:
        stmt = stmt.where(FiscalGuide.client_id == client_id)
    if guide_type:
        stmt = stmt.where(FiscalGuide.guide_type == guide_type.upper())
    if status:
        stmt = stmt.where(FiscalGuide.status == status)
    if competence:
        stmt = stmt.where(FiscalGuide.competence == competence)
    if due_before:
        stmt = stmt.where(FiscalGuide.due_date <= due_before)
    if due_after:
        stmt = stmt.where(FiscalGuide.due_date >= due_after)

    stmt = stmt.order_by(FiscalGuide.due_date.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=FiscalGuideOut, status_code=201)
async def create_fiscal_guide(
    body: FiscalGuideCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new fiscal guide."""
    guide = FiscalGuide(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        status=GuideStatus.DRAFT.value,
        **body.model_dump(),
    )
    db.add(guide)

    event = FiscalGuideEvent(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        guide_id=guide.id,
        event_type="created",
        actor_user_id=current_user.id,
    )
    db.add(event)

    await db.commit()
    await db.refresh(guide)
    return guide


@router.get("/{guide_id}", response_model=FiscalGuideOut)
async def get_fiscal_guide(
    guide_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a fiscal guide by ID."""
    result = await db.execute(
        select(FiscalGuide).where(
            FiscalGuide.id == guide_id,
            FiscalGuide.tenant_id == current_user.tenant_id,
        )
    )
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Guia fiscal não encontrada.")
    return guide


@router.post("/{guide_id}/send", response_model=FiscalGuideOut)
async def send_guide_to_customer(
    guide_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a guide as sent to the customer."""
    result = await db.execute(
        select(FiscalGuide).where(
            FiscalGuide.id == guide_id,
            FiscalGuide.tenant_id == current_user.tenant_id,
        )
    )
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Guia fiscal não encontrada.")

    if guide.status not in (GuideStatus.DRAFT.value, GuideStatus.GENERATED.value):
        raise HTTPException(
            status_code=409,
            detail=f"Não é possível enviar uma guia com status '{guide.status}'.",
        )

    guide.status = GuideStatus.SENT_TO_CUSTOMER.value
    event = FiscalGuideEvent(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        guide_id=guide.id,
        event_type="sent_to_customer",
        actor_user_id=current_user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(guide)
    return guide


@router.post("/{guide_id}/mark-paid", response_model=FiscalGuideOut)
async def mark_guide_paid(
    guide_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a guide as paid."""
    from datetime import datetime, timezone

    result = await db.execute(
        select(FiscalGuide).where(
            FiscalGuide.id == guide_id,
            FiscalGuide.tenant_id == current_user.tenant_id,
        )
    )
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Guia fiscal não encontrada.")

    if guide.status == GuideStatus.PAID.value:
        raise HTTPException(status_code=409, detail="Guia já está paga.")

    guide.status = GuideStatus.PAID.value
    guide.paid_at = datetime.now(timezone.utc)

    event = FiscalGuideEvent(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        guide_id=guide.id,
        event_type="paid",
        actor_user_id=current_user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(guide)
    return guide


@router.post("/{guide_id}/cancel", response_model=FiscalGuideOut)
async def cancel_guide(
    guide_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a fiscal guide."""
    result = await db.execute(
        select(FiscalGuide).where(
            FiscalGuide.id == guide_id,
            FiscalGuide.tenant_id == current_user.tenant_id,
        )
    )
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Guia fiscal não encontrada.")

    if guide.status == GuideStatus.PAID.value:
        raise HTTPException(status_code=409, detail="Não é possível cancelar uma guia já paga.")

    guide.status = GuideStatus.CANCELLED.value
    event = FiscalGuideEvent(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        guide_id=guide.id,
        event_type="cancelled",
        actor_user_id=current_user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(guide)
    return guide


@router.get("/{guide_id}/events", response_model=list[dict])
async def list_guide_events(
    guide_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all lifecycle events for a fiscal guide."""
    # Verify guide belongs to tenant
    result = await db.execute(
        select(FiscalGuide).where(
            FiscalGuide.id == guide_id,
            FiscalGuide.tenant_id == current_user.tenant_id,
        )
    )
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Guia fiscal não encontrada.")

    events_result = await db.execute(
        select(FiscalGuideEvent)
        .where(FiscalGuideEvent.guide_id == guide_id)
        .order_by(FiscalGuideEvent.occurred_at.asc())
    )
    events = events_result.scalars().all()
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
            "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        }
        for e in events
    ]
