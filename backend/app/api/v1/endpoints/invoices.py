import logging
import uuid
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User

def _tenant_id(current_user: User) -> uuid.UUID:
    return current_user.tenant_id
from app.domain.invoices.service import InvoiceService
from app.domain.invoices.repository import InvoiceRepository
from app.domain.invoices.providers.factory import (
    NfseProviderNotConfiguredError,
    build_nfse_provider,
)
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invoices", tags=["Invoices"])


def _provider_or_503():
    """Em produção com provider mock: 503 antes de qualquer mudança de status."""
    try:
        return build_nfse_provider()
    except NfseProviderNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


async def process_emission_background(invoice_id: uuid.UUID, tenant_id: uuid.UUID):
    async_session = get_sessionmaker()
    async with async_session() as db:
        repo = InvoiceRepository(db)
        service = InvoiceService(repo)
        try:
            provider = build_nfse_provider()
            await service.process_emission_sync(invoice_id, tenant_id, provider)
        except Exception as exc:
            logger.exception("Falha ao processar emissão da NFS-e %s", invoice_id)
            try:
                await db.rollback()
                await service.record_background_failure(invoice_id, tenant_id, str(exc))
            except Exception:
                logger.exception("Falha ao registrar a rejeição da NFS-e %s", invoice_id)

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
    _provider_or_503()
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    try:
        invoice = await service.queue_emission(id, _tenant_id(current_user))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    background_tasks.add_task(process_emission_background, id, _tenant_id(current_user))
    return invoice

@router.post("/{id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    id: uuid.UUID,
    payload: InvoiceCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = _provider_or_503()
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    try:
        return await service.cancel_invoice(id, _tenant_id(current_user), payload.reason, provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

@router.get("/{id}/pdf")
async def get_pdf(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    content, filename = await service.get_pdf_bytes(id, _tenant_id(current_user))
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.get("/{id}/xml")
async def get_xml(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InvoiceRepository(db)
    service = InvoiceService(repo)
    xml, filename = await service.get_xml_content(id, _tenant_id(current_user))
    return Response(
        content=xml.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

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
