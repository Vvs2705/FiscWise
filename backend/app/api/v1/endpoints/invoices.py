import uuid
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User

def _tenant_id(current_user: User) -> uuid.UUID:
    return current_user.tenant_id
from app.domain.invoices.service import InvoiceService
from app.domain.invoices.repository import InvoiceRepository
from app.domain.invoices.providers.mock import MockNfseProvider
from app.domain.invoices.schemas import (
    InvoiceIssuerCreate,
    InvoiceIssuerResponse,
    InvoiceCreate,
    InvoiceResponse,
    InvoiceEventResponse,
    InvoiceRejectionResponse,
    InvoiceCancelRequest
)
from app.core.deps import get_sessionmaker

router = APIRouter(prefix="/invoices", tags=["Invoices"])

async def process_emission_background(invoice_id: uuid.UUID, tenant_id: uuid.UUID):
    async_session = get_sessionmaker()
    async with async_session() as db:
        repo = InvoiceRepository(db)
        service = InvoiceService(repo)
        provider = MockNfseProvider()
        try:
            await service.process_emission_sync(invoice_id, tenant_id, provider)
        except Exception:
            pass

@router.post("/issuers", response_model=InvoiceIssuerResponse, status_code=status.HTTP_201_CREATED)
async def create_issuer(
    payload: InvoiceIssuerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    return await service.create_issuer(payload, _tenant_id(current_user))

@router.get("/issuers", response_model=List[InvoiceIssuerResponse])
async def list_issuers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    return await service.list_issuers(_tenant_id(current_user))

@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    return await service.create_invoice(payload, _tenant_id(current_user))

@router.get("", response_model=List[InvoiceResponse])
async def list_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    client_id: Optional[uuid.UUID] = Query(None),
    competencia: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    return await service.list_invoices(
        _tenant_id(current_user),
        status_filter=status_filter,
        client_id=client_id,
        competencia=competencia
    )

@router.get("/{id}", response_model=InvoiceResponse)
async def get_invoice(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    return await service.get_invoice(id, _tenant_id(current_user))

@router.post("/{id}/emit", response_model=InvoiceResponse)
async def emit_invoice(
    id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    invoice = await service.queue_emission(id, _tenant_id(current_user))
    background_tasks.add_task(process_emission_background, id, _tenant_id(current_user))
    return invoice

@router.post("/{id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    id: uuid.UUID,
    payload: InvoiceCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    provider = MockNfseProvider()
    return await service.cancel_invoice(id, _tenant_id(current_user), payload.reason, provider)

@router.get("/{id}/pdf")
async def get_pdf(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    url = await service.get_pdf_signed_url(id, _tenant_id(current_user))
    return {"url": url}

@router.get("/{id}/xml")
async def get_xml(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    url = await service.get_xml_signed_url(id, _tenant_id(current_user))
    return {"url": url}

@router.get("/{id}/events", response_model=List[InvoiceEventResponse])
async def list_events(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    await service.get_invoice(id, _tenant_id(current_user))
    return await repo.list_events(id, _tenant_id(current_user))

@router.get("/{id}/rejections", response_model=List[InvoiceRejectionResponse])
async def list_rejections(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    await service.get_invoice(id, _tenant_id(current_user))
    return await repo.list_rejections(id, _tenant_id(current_user))
