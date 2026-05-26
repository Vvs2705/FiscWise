"""Monthly Closing API — fechamento mensal e dossiê fiscal."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.domain.monthly_closing.models import (
    MonthlyClosing,
    MonthlyClosingItem,
    FiscalDossier,
    ClosingStatus,
    ClosingItemStatus,
)
from app.domain.monthly_closing.schemas import (
    MonthlyClosingCreate,
    MonthlyClosingPatch,
    MonthlyClosingOut,
    ClosingItemCreate,
    ClosingItemPatch,
    ClosingItemOut,
    FiscalDossierOut,
)

router = APIRouter(prefix="/monthly-closings", tags=["Fechamento Mensal"])


# ─── Monthly Closings ────────────────────────────────────────────────────────

@router.get("", response_model=list[MonthlyClosingOut])
async def list_closings(
    client_id: Optional[uuid.UUID] = Query(None),
    competence: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MonthlyClosing).where(
        MonthlyClosing.tenant_id == current_user.tenant_id
    )
    if client_id:
        stmt = stmt.where(MonthlyClosing.client_id == client_id)
    if competence:
        stmt = stmt.where(MonthlyClosing.competence == competence)
    if status:
        stmt = stmt.where(MonthlyClosing.status == status)

    stmt = stmt.order_by(MonthlyClosing.competence.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=MonthlyClosingOut, status_code=201)
async def create_closing(
    body: MonthlyClosingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check for duplicate competence per client
    existing = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.tenant_id == current_user.tenant_id,
            MonthlyClosing.client_id == body.client_id,
            MonthlyClosing.competence == body.competence,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Já existe um fechamento para {body.competence} deste cliente.",
        )

    closing = MonthlyClosing(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        status=ClosingStatus.OPEN.value,
        **body.model_dump(),
    )
    db.add(closing)
    await db.commit()
    await db.refresh(closing)
    return closing


@router.get("/{closing_id}", response_model=MonthlyClosingOut)
async def get_closing(
    closing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.id == closing_id,
            MonthlyClosing.tenant_id == current_user.tenant_id,
        )
    )
    closing = result.scalar_one_or_none()
    if not closing:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")
    return closing


@router.patch("/{closing_id}", response_model=MonthlyClosingOut)
async def patch_closing(
    closing_id: uuid.UUID,
    body: MonthlyClosingPatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.id == closing_id,
            MonthlyClosing.tenant_id == current_user.tenant_id,
        )
    )
    closing = result.scalar_one_or_none()
    if not closing:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")

    if closing.status == ClosingStatus.CLOSED.value and body.status != ClosingStatus.REOPENED.value:
        raise HTTPException(
            status_code=409, detail="Fechamento encerrado. Reabra antes de editar."
        )

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(closing, field, val)

    await db.commit()
    await db.refresh(closing)
    return closing


@router.post("/{closing_id}/close", response_model=MonthlyClosingOut)
async def close_closing(
    closing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Finalize/close a monthly closing."""
    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.id == closing_id,
            MonthlyClosing.tenant_id == current_user.tenant_id,
        )
    )
    closing = result.scalar_one_or_none()
    if not closing:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")

    if closing.status == ClosingStatus.CLOSED.value:
        raise HTTPException(status_code=409, detail="Fechamento já está encerrado.")

    # Check for pending required items
    pending = await db.execute(
        select(MonthlyClosingItem).where(
            MonthlyClosingItem.closing_id == closing_id,
            MonthlyClosingItem.item_status == ClosingItemStatus.PENDING.value,
            MonthlyClosingItem.is_required == True,  # noqa: E712
        )
    )
    pending_items = pending.scalars().all()
    if pending_items:
        raise HTTPException(
            status_code=409,
            detail=f"Existem {len(pending_items)} itens obrigatórios pendentes.",
        )

    closing.status = ClosingStatus.CLOSED.value
    closing.closed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(closing)
    return closing


@router.post("/{closing_id}/reopen", response_model=MonthlyClosingOut)
async def reopen_closing(
    closing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reopen a closed monthly closing."""
    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.id == closing_id,
            MonthlyClosing.tenant_id == current_user.tenant_id,
        )
    )
    closing = result.scalar_one_or_none()
    if not closing:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")

    if closing.status != ClosingStatus.CLOSED.value:
        raise HTTPException(status_code=409, detail="Apenas fechamentos encerrados podem ser reabertos.")

    closing.status = ClosingStatus.REOPENED.value
    closing.closed_at = None
    await db.commit()
    await db.refresh(closing)
    return closing


# ─── Closing Items ────────────────────────────────────────────────────────────

@router.get("/{closing_id}/items", response_model=list[ClosingItemOut])
async def list_closing_items(
    closing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify closing ownership
    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.id == closing_id,
            MonthlyClosing.tenant_id == current_user.tenant_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")

    items_result = await db.execute(
        select(MonthlyClosingItem)
        .where(MonthlyClosingItem.closing_id == closing_id)
        .order_by(MonthlyClosingItem.created_at.asc())
    )
    return list(items_result.scalars().all())


@router.post("/{closing_id}/items", response_model=ClosingItemOut, status_code=201)
async def add_closing_item(
    closing_id: uuid.UUID,
    body: ClosingItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.id == closing_id,
            MonthlyClosing.tenant_id == current_user.tenant_id,
        )
    )
    closing = result.scalar_one_or_none()
    if not closing:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")

    if closing.status == ClosingStatus.CLOSED.value:
        raise HTTPException(
            status_code=409, detail="Não é possível adicionar itens a um fechamento encerrado."
        )

    item = MonthlyClosingItem(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        closing_id=closing_id,
        item_status=ClosingItemStatus.PENDING.value,
        **body.model_dump(),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/{closing_id}/items/{item_id}", response_model=ClosingItemOut)
async def patch_closing_item(
    closing_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ClosingItemPatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify closing ownership
    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.id == closing_id,
            MonthlyClosing.tenant_id == current_user.tenant_id,
        )
    )
    closing = result.scalar_one_or_none()
    if not closing:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")

    item_result = await db.execute(
        select(MonthlyClosingItem).where(
            MonthlyClosingItem.id == item_id,
            MonthlyClosingItem.closing_id == closing_id,
        )
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado.")

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(item, field, val)

    await db.commit()
    await db.refresh(item)
    return item


# ─── Dossier ──────────────────────────────────────────────────────────────────

@router.get("/{closing_id}/dossier", response_model=FiscalDossierOut)
async def get_dossier(
    closing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the fiscal dossier for a closing."""
    # Verify closing ownership
    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.id == closing_id,
            MonthlyClosing.tenant_id == current_user.tenant_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")

    dossier_result = await db.execute(
        select(FiscalDossier).where(FiscalDossier.closing_id == closing_id)
    )
    dossier = dossier_result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossiê ainda não gerado para este fechamento.")
    return dossier


@router.post("/{closing_id}/dossier/generate", response_model=FiscalDossierOut)
async def generate_dossier(
    closing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate or regenerate the fiscal dossier for a closing."""
    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.id == closing_id,
            MonthlyClosing.tenant_id == current_user.tenant_id,
        )
    )
    closing = result.scalar_one_or_none()
    if not closing:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")

    # Check if dossier already exists
    existing_result = await db.execute(
        select(FiscalDossier).where(FiscalDossier.closing_id == closing_id)
    )
    dossier = existing_result.scalar_one_or_none()

    if dossier is None:
        dossier = FiscalDossier(
            id=uuid.uuid4(),
            tenant_id=current_user.tenant_id,
            closing_id=closing_id,
            client_id=closing.client_id,
            competence=closing.competence,
            sent_to_client=False,
        )
        db.add(dossier)

    # TODO: trigger async PDF generation job
    await db.commit()
    await db.refresh(dossier)
    return dossier
