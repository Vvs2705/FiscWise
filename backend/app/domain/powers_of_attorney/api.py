"""Powers of Attorney API endpoints."""
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.domain.powers_of_attorney.models import PowerOfAttorney, PoaStatus
from app.domain.powers_of_attorney.schemas import PoaCreate, PoaPatch, PoaOut

router = APIRouter(prefix="/powers-of-attorney", tags=["Procurações"])


@router.get("", response_model=list[PoaOut])
async def list_poas(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PowerOfAttorney).where(PowerOfAttorney.tenant_id == current_user.tenant_id)
        .order_by(PowerOfAttorney.valid_until.asc())
    )
    return list(result.scalars().all())


@router.post("", response_model=PoaOut, status_code=201)
async def create_poa(
    body: PoaCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    poa = PowerOfAttorney(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        status=PoaStatus.PENDING.value,
        **body.model_dump(),
    )
    db.add(poa)
    await db.commit()
    await db.refresh(poa)
    return poa


@router.get("/{poa_id}", response_model=PoaOut)
async def get_poa(
    poa_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PowerOfAttorney).where(
            PowerOfAttorney.id == poa_id,
            PowerOfAttorney.tenant_id == current_user.tenant_id,
        )
    )
    poa = result.scalar_one_or_none()
    if not poa:
        raise HTTPException(status_code=404, detail="Power of attorney not found.")
    return poa


@router.patch("/{poa_id}", response_model=PoaOut)
async def patch_poa(
    poa_id: uuid.UUID,
    body: PoaPatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PowerOfAttorney).where(
            PowerOfAttorney.id == poa_id,
            PowerOfAttorney.tenant_id == current_user.tenant_id,
        )
    )
    poa = result.scalar_one_or_none()
    if not poa:
        raise HTTPException(status_code=404, detail="Power of attorney not found.")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(poa, field, val)
    await db.commit()
    await db.refresh(poa)
    return poa


@router.post("/{poa_id}/check", response_model=PoaOut)
async def check_poa(
    poa_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-check procuration status against provider (mock implementation)."""
    result = await db.execute(
        select(PowerOfAttorney).where(
            PowerOfAttorney.id == poa_id,
            PowerOfAttorney.tenant_id == current_user.tenant_id,
        )
    )
    poa = result.scalar_one_or_none()
    if not poa:
        raise HTTPException(status_code=404, detail="Power of attorney not found.")

    # Update last check timestamp and derive status from expiry
    poa.last_checked_at = datetime.now(timezone.utc)
    if poa.valid_until and poa.valid_until < date.today():
        poa.status = PoaStatus.EXPIRED.value
    elif poa.status == PoaStatus.PENDING.value:
        poa.status = PoaStatus.ACTIVE.value

    await db.commit()
    await db.refresh(poa)
    return poa
