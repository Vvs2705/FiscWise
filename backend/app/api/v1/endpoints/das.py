from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.operations import DasPayment, AccountingClient
from app.schemas.das import DasPaymentCreate, DasPaymentUpdate, DasPaymentResponse
from app.services import webhook_service as _webhook_svc

router = APIRouter(prefix="/das", tags=["DAS Monthly Payments"])


@router.post("", response_model=DasPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_das_payment(
    payload: DasPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DasPaymentResponse:
    """
    Create a new DAS payment record or update if it already exists for the client and period.
    """
    # Verify client exists and belongs to tenant
    client = await db.scalar(
        select(AccountingClient).where(
            AccountingClient.id == payload.client_id,
            AccountingClient.tenant_id == current_user.tenant_id,
        )
    )
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or does not belong to your tenant",
        )

    # Check if a DAS payment record already exists for this client and period
    existing_das = await db.scalar(
        select(DasPayment).where(
            DasPayment.tenant_id == current_user.tenant_id,
            DasPayment.client_id == payload.client_id,
            DasPayment.period == payload.period,
        )
    )

    if existing_das:
        # Update existing
        existing_das.revenue = payload.revenue
        existing_das.tax_amount = payload.tax_amount
        existing_das.due_date = payload.due_date
        existing_das.status = payload.status
        if payload.status == "paid" and not existing_das.paid_at:
            existing_das.paid_at = datetime.now(timezone.utc)
        elif payload.status != "paid":
            existing_das.paid_at = None
        if payload.notes is not None:
            existing_das.notes = payload.notes
        
        await db.commit()
        await db.refresh(existing_das)
        res = DasPaymentResponse.model_validate(existing_das)
        res.client_name = client.name
        return res

    # Create new
    das = DasPayment(
        tenant_id=current_user.tenant_id,
        client_id=payload.client_id,
        period=payload.period,
        revenue=payload.revenue,
        tax_amount=payload.tax_amount,
        due_date=payload.due_date,
        status=payload.status,
        paid_at=datetime.now(timezone.utc) if payload.status == "paid" else None,
        notes=payload.notes,
    )
    db.add(das)
    await db.commit()
    await db.refresh(das)
    
    res = DasPaymentResponse.model_validate(das)
    res.client_name = client.name
    return res


@router.get("", response_model=list[DasPaymentResponse])
async def list_das_payments(
    client_id: Optional[UUID] = None,
    year: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DasPaymentResponse]:
    """
    List monthly DAS payments for the tenant, optionally filtered by client_id and reference year.
    """
    query = select(DasPayment, AccountingClient.name.label("client_name")).join(
        AccountingClient,
        and_(
            AccountingClient.id == DasPayment.client_id,
            AccountingClient.tenant_id == current_user.tenant_id,
        )
    ).where(DasPayment.tenant_id == current_user.tenant_id)

    if client_id:
        query = query.where(DasPayment.client_id == client_id)

    if year:
        query = query.where(DasPayment.period.like(f"{year}-%"))

    query = query.order_by(DasPayment.period.asc())
    
    result = await db.execute(query)
    
    das_list = []
    for row in result.all():
        das = row[0]
        c_name = row[1]
        res = DasPaymentResponse.model_validate(das)
        res.client_name = c_name
        das_list.append(res)
        
    return das_list


@router.put("/{das_id}", response_model=DasPaymentResponse)
async def update_das_payment(
    das_id: UUID,
    payload: DasPaymentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DasPaymentResponse:
    """
    Update a specific DAS payment entry.
    """
    das = await db.scalar(
        select(DasPayment).where(
            DasPayment.id == das_id,
            DasPayment.tenant_id == current_user.tenant_id,
        )
    )
    if not das:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DAS payment record not found",
        )

    # Get client to fetch client name
    client = await db.scalar(
        select(AccountingClient).where(AccountingClient.id == das.client_id)
    )

    # Update fields
    if payload.revenue is not None:
        das.revenue = payload.revenue
    if payload.tax_amount is not None:
        das.tax_amount = payload.tax_amount
    if payload.due_date is not None:
        das.due_date = payload.due_date
    if payload.status is not None:
        das.status = payload.status
        if payload.status == "paid" and not das.paid_at:
            das.paid_at = datetime.now(timezone.utc)
        elif payload.status != "paid":
            das.paid_at = None
    if payload.file_url is not None:
        das.file_url = payload.file_url
    if payload.notes is not None:
        das.notes = payload.notes

    await db.commit()
    await db.refresh(das)
    
    res = DasPaymentResponse.model_validate(das)
    if client:
        res.client_name = client.name
    return res


@router.patch("/{das_id}/pay", response_model=DasPaymentResponse)
async def mark_das_as_paid(
    das_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DasPaymentResponse:
    """
    Quickly mark a DAS payment as paid.
    """
    das = await db.scalar(
        select(DasPayment).where(
            DasPayment.id == das_id,
            DasPayment.tenant_id == current_user.tenant_id,
        )
    )
    if not das:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DAS payment record not found",
        )

    client = await db.scalar(
        select(AccountingClient).where(AccountingClient.id == das.client_id)
    )

    das.status = "paid"
    das.paid_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(das)
    
    res = DasPaymentResponse.model_validate(das)
    if client:
        res.client_name = client.name

    # Fire-and-forget webhook dispatch for das.paid
    await _webhook_svc.dispatch_event(
        db=db,
        tenant_id=current_user.tenant_id,
        event="das.paid",
        data={
            "id": str(das.id),
            "client_id": str(das.client_id),
            "client_name": client.name if client else None,
            "period": das.period,
            "tax_amount": str(das.tax_amount),
            "paid_at": das.paid_at.isoformat() if das.paid_at else None,
        },
    )
    return res


@router.delete("/{das_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_das_payment(
    das_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a DAS payment entry.
    """
    das = await db.scalar(
        select(DasPayment).where(
            DasPayment.id == das_id,
            DasPayment.tenant_id == current_user.tenant_id,
        )
    )
    if not das:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DAS payment record not found",
        )

    await db.delete(das)
    await db.commit()
