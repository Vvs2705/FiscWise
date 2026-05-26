"""Invoice domain API endpoints."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.storage import get_signed_url
from app.models.user import User
from app.domain.invoices import schemas, service
from app.domain.invoices.repository import (
    list_invoices, get_invoice, list_issuers, get_issuer, get_invoice_events,
)
from app.domain.invoices.models import InvoiceIssuer, InvoiceServiceProfile

router = APIRouter(prefix="/invoices", tags=["Invoices / NFS-e"])
issuers_router = APIRouter(prefix="/invoice-issuers", tags=["Invoice Issuers"])
profiles_router = APIRouter(prefix="/invoice-service-profiles", tags=["Invoice Service Profiles"])


# ── Invoices ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[schemas.InvoiceOut])
async def list_invoices_endpoint(
    competence: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    issuer_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_invoices(db, current_user.tenant_id, competence, issuer_id, status_filter, limit, offset)


@router.post("", response_model=schemas.InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice_endpoint(
    body: schemas.InvoiceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_draft(db, current_user.tenant_id, body, current_user.id)


@router.get("/{invoice_id}", response_model=schemas.InvoiceOut)
async def get_invoice_endpoint(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await get_invoice(db, invoice_id, current_user.tenant_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return inv


@router.patch("/{invoice_id}", response_model=schemas.InvoiceOut)
async def patch_invoice_endpoint(
    invoice_id: uuid.UUID,
    body: schemas.InvoicePatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await get_invoice(db, invoice_id, current_user.tenant_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if inv.status != "draft":
        raise HTTPException(status_code=422, detail="Only draft invoices can be patched.")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(inv, field, val)
    await db.commit()
    await db.refresh(inv)
    return inv


@router.post("/{invoice_id}/issue", response_model=schemas.InvoiceOut)
async def issue_invoice_endpoint(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.issue_invoice(db, invoice_id, current_user.tenant_id, current_user.id)


@router.post("/{invoice_id}/cancel", response_model=schemas.InvoiceOut)
async def cancel_invoice_endpoint(
    invoice_id: uuid.UUID,
    body: schemas.InvoiceCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.cancel_invoice(db, invoice_id, current_user.tenant_id, current_user.id, body.reason)


@router.get("/{invoice_id}/events", response_model=list[schemas.InvoiceEventOut])
async def get_invoice_events_endpoint(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await get_invoice(db, invoice_id, current_user.tenant_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return await get_invoice_events(db, invoice_id, current_user.tenant_id)


@router.get("/{invoice_id}/pdf-url")
async def get_invoice_pdf_url(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await get_invoice(db, invoice_id, current_user.tenant_id)
    if not inv or not inv.pdf_storage_key:
        raise HTTPException(status_code=404, detail="PDF not available.")
    url = get_signed_url("invoices", inv.pdf_storage_key, ttl_seconds=300, tenant_id=current_user.tenant_id)
    return {"url": url, "expires_in": 300}


@router.get("/{invoice_id}/xml-url")
async def get_invoice_xml_url(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await get_invoice(db, invoice_id, current_user.tenant_id)
    if not inv or not inv.xml_storage_key:
        raise HTTPException(status_code=404, detail="XML not available.")
    url = get_signed_url("invoices", inv.xml_storage_key, ttl_seconds=300, tenant_id=current_user.tenant_id)
    return {"url": url, "expires_in": 300}


# ── Issuers ───────────────────────────────────────────────────────────────────

@issuers_router.get("", response_model=list[schemas.InvoiceIssuerOut])
async def list_issuers_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_issuers(db, current_user.tenant_id)


@issuers_router.post("", response_model=schemas.InvoiceIssuerOut, status_code=201)
async def create_issuer_endpoint(
    body: schemas.InvoiceIssuerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    issuer = InvoiceIssuer(id=uuid.uuid4(), tenant_id=current_user.tenant_id, **body.model_dump())
    db.add(issuer)
    await db.commit()
    await db.refresh(issuer)
    return issuer


@issuers_router.patch("/{issuer_id}", response_model=schemas.InvoiceIssuerOut)
async def patch_issuer_endpoint(
    issuer_id: uuid.UUID,
    body: schemas.InvoiceIssuerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    issuer = await get_issuer(db, issuer_id, current_user.tenant_id)
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found.")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(issuer, field, val)
    await db.commit()
    await db.refresh(issuer)
    return issuer
