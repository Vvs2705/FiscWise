"""Endpoints for managing company official documents."""

from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.operations import CompanyDocument, AccountingClient
from app.schemas.company_documents import (
    CompanyDocumentCreate,
    CompanyDocumentUpdate,
    CompanyDocumentResponse,
    CompanyDocumentListResponse,
)

router = APIRouter(prefix="/clients/{client_id}/company-documents", tags=["Company Documents"])


@router.post("", response_model=CompanyDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_company_document(
    client_id: UUID,
    doc_data: CompanyDocumentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyDocumentResponse:
    """Upload a company document (CNPJ, contracts, licenses, etc.)."""
    # Verify client belongs to tenant
    client = await db.execute(
        select(AccountingClient).where(
            AccountingClient.id == client_id,
            AccountingClient.tenant_id == current_user.tenant_id,
        )
    )
    if not client.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    doc = CompanyDocument(
        tenant_id=current_user.tenant_id,
        client_id=client_id,
        **doc_data.model_dump(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return CompanyDocumentResponse.model_validate(doc)


@router.get("", response_model=list[CompanyDocumentListResponse])
async def list_company_documents(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CompanyDocumentListResponse]:
    """List all company documents for a client."""
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
        select(CompanyDocument).where(
            CompanyDocument.client_id == client_id,
            CompanyDocument.tenant_id == current_user.tenant_id,
        )
    )
    docs = result.scalars().all()
    return [CompanyDocumentListResponse.model_validate(d) for d in docs]


@router.get("/expiring-soon", response_model=list[CompanyDocumentListResponse])
async def get_expiring_documents(
    client_id: UUID,
    days_threshold: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CompanyDocumentListResponse]:
    """Get company documents expiring within the specified days."""
    # Verify client belongs to tenant
    client = await db.execute(
        select(AccountingClient).where(
            AccountingClient.id == client_id,
            AccountingClient.tenant_id == current_user.tenant_id,
        )
    )
    if not client.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    from datetime import timedelta
    expiration_threshold = datetime.utcnow().date() + timedelta(days=days_threshold)

    result = await db.execute(
        select(CompanyDocument).where(
            and_(
                CompanyDocument.client_id == client_id,
                CompanyDocument.tenant_id == current_user.tenant_id,
                CompanyDocument.expiration_date.isnot(None),
                CompanyDocument.expiration_date <= expiration_threshold,
                CompanyDocument.status == "valid",
            )
        )
    )
    docs = result.scalars().all()
    return [CompanyDocumentListResponse.model_validate(d) for d in docs]


@router.get("/{doc_id}", response_model=CompanyDocumentResponse)
async def get_company_document(
    client_id: UUID,
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyDocumentResponse:
    """Get a specific company document details."""
    doc = await db.execute(
        select(CompanyDocument).where(
            CompanyDocument.id == doc_id,
            CompanyDocument.client_id == client_id,
            CompanyDocument.tenant_id == current_user.tenant_id,
        )
    )
    if not (doc_obj := doc.scalar_one_or_none()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return CompanyDocumentResponse.model_validate(doc_obj)


@router.put("/{doc_id}", response_model=CompanyDocumentResponse)
async def update_company_document(
    client_id: UUID,
    doc_id: UUID,
    doc_data: CompanyDocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyDocumentResponse:
    """Update company document information."""
    doc = await db.execute(
        select(CompanyDocument).where(
            CompanyDocument.id == doc_id,
            CompanyDocument.client_id == client_id,
            CompanyDocument.tenant_id == current_user.tenant_id,
        )
    )
    if not (doc_obj := doc.scalar_one_or_none()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    update_data = doc_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc_obj, field, value)

    await db.commit()
    await db.refresh(doc_obj)
    return CompanyDocumentResponse.model_validate(doc_obj)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company_document(
    client_id: UUID,
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a company document."""
    doc = await db.execute(
        select(CompanyDocument).where(
            CompanyDocument.id == doc_id,
            CompanyDocument.client_id == client_id,
            CompanyDocument.tenant_id == current_user.tenant_id,
        )
    )
    if not (doc_obj := doc.scalar_one_or_none()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await db.delete(doc_obj)
    await db.commit()
