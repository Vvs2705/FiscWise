"""Endpoints for managing company partners/shareholders."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.operations import CompanyPartner, AccountingClient
from app.schemas.partners import PartnerCreate, PartnerUpdate, PartnerResponse

router = APIRouter(prefix="/clients/{client_id}/partners", tags=["Partners"])


@router.post("", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
async def create_partner(
    client_id: UUID,
    partner_data: PartnerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerResponse:
    """Create a new company partner/shareholder."""
    # Verify client belongs to tenant
    client = await db.execute(
        select(AccountingClient).where(
            AccountingClient.id == client_id,
            AccountingClient.tenant_id == current_user.tenant_id,
        )
    )
    if not client.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    partner = CompanyPartner(
        tenant_id=current_user.tenant_id,
        client_id=client_id,
        **partner_data.model_dump(),
    )
    db.add(partner)
    await db.commit()
    await db.refresh(partner)
    return PartnerResponse.model_validate(partner)


@router.get("", response_model=list[PartnerResponse])
async def list_partners(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerResponse]:
    """List all partners for a client."""
    # Verify client belongs to tenant
    client = await db.execute(
        select(AccountingClient).where(
            AccountingClient.id == client_id,
            AccountingClient.tenant_id == current_user.tenant_id,
        )
    )
    if not client.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    result = await db.execute(
        select(CompanyPartner).where(
            CompanyPartner.client_id == client_id,
            CompanyPartner.tenant_id == current_user.tenant_id,
        )
    )
    partners = result.scalars().all()
    return [PartnerResponse.model_validate(p) for p in partners]


@router.get("/{partner_id}", response_model=PartnerResponse)
async def get_partner(
    client_id: UUID,
    partner_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerResponse:
    """Get a specific partner details."""
    partner = await db.execute(
        select(CompanyPartner).where(
            CompanyPartner.id == partner_id,
            CompanyPartner.client_id == client_id,
            CompanyPartner.tenant_id == current_user.tenant_id,
        )
    )
    if not (partner_obj := partner.scalar_one_or_none()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    return PartnerResponse.model_validate(partner_obj)


@router.put("/{partner_id}", response_model=PartnerResponse)
async def update_partner(
    client_id: UUID,
    partner_id: UUID,
    partner_data: PartnerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerResponse:
    """Update a partner information."""
    partner = await db.execute(
        select(CompanyPartner).where(
            CompanyPartner.id == partner_id,
            CompanyPartner.client_id == client_id,
            CompanyPartner.tenant_id == current_user.tenant_id,
        )
    )
    if not (partner_obj := partner.scalar_one_or_none()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    update_data = partner_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(partner_obj, field, value)

    await db.commit()
    await db.refresh(partner_obj)
    return PartnerResponse.model_validate(partner_obj)


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner(
    client_id: UUID,
    partner_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a partner."""
    partner = await db.execute(
        select(CompanyPartner).where(
            CompanyPartner.id == partner_id,
            CompanyPartner.client_id == client_id,
            CompanyPartner.tenant_id == current_user.tenant_id,
        )
    )
    if not (partner_obj := partner.scalar_one_or_none()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    await db.delete(partner_obj)
    await db.commit()
