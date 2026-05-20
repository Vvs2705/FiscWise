"""Operational MVP endpoints for CTFlow pilots."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.operations import (
    AccountReceivable,
    AccountingClient,
    ClientDocument,
    DeadlineItem,
    DigitalCertificate,
)
from app.models.user import User
from app.schemas.operations import (
    AccountingClientCreate,
    AccountingClientResponse,
    AccountingClientUpdate,
    CertificateCreate,
    CertificateResponse,
    CertificateUpdate,
    DashboardOverview,
    DeadlineCreate,
    DeadlineResponse,
    DeadlineUpdate,
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    ReceivableCreate,
    ReceivableResponse,
    ReceivableUpdate,
)


router = APIRouter()
ModelT = TypeVar("ModelT")


def _tenant_id(current_user: User) -> uuid.UUID:
    return current_user.tenant_id


def _apply_updates(instance: Any, payload: Any) -> None:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(instance, key, value)


async def _get_client_or_404(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
) -> AccountingClient:
    result = await db.execute(
        select(AccountingClient).where(
            AccountingClient.tenant_id == tenant_id,
            AccountingClient.id == client_id,
        )
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return client


async def _get_item_or_404(
    db: AsyncSession,
    model: type[ModelT],
    tenant_id: uuid.UUID,
    item_id: uuid.UUID,
    not_found_message: str,
) -> ModelT:
    result = await db.execute(
        select(model).where(
            model.tenant_id == tenant_id,  # type: ignore[attr-defined]
            model.id == item_id,  # type: ignore[attr-defined]
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_message,
        )
    return item


async def _commit_refresh(db: AsyncSession, instance: Any) -> Any:
    await db.commit()
    await db.refresh(instance)
    return instance


@router.get("/dashboard/overview", response_model=DashboardOverview)
async def dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardOverview:
    tenant_id = _tenant_id(current_user)
    today = date.today()
    limit_date = today + timedelta(days=30)

    async def count_for(statement):
        result = await db.execute(statement)
        return int(result.scalar_one() or 0)

    active_clients = await count_for(
        select(func.count()).select_from(AccountingClient).where(
            AccountingClient.tenant_id == tenant_id,
            AccountingClient.status == "active",
        )
    )
    pending_deadlines = await count_for(
        select(func.count()).select_from(DeadlineItem).where(
            DeadlineItem.tenant_id == tenant_id,
            DeadlineItem.status == "pending",
        )
    )
    overdue_deadlines = await count_for(
        select(func.count()).select_from(DeadlineItem).where(
            DeadlineItem.tenant_id == tenant_id,
            DeadlineItem.status != "completed",
            DeadlineItem.due_date < today,
        )
    )
    certificates_expiring_30d = await count_for(
        select(func.count()).select_from(DigitalCertificate).where(
            DigitalCertificate.tenant_id == tenant_id,
            DigitalCertificate.status == "valid",
            DigitalCertificate.valid_until >= today,
            DigitalCertificate.valid_until <= limit_date,
        )
    )
    open_receivables = await count_for(
        select(func.count()).select_from(AccountReceivable).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status == "pending",
        )
    )
    overdue_receivables = await count_for(
        select(func.count()).select_from(AccountReceivable).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status != "paid",
            AccountReceivable.due_date < today,
        )
    )

    amount_open_result = await db.execute(
        select(func.coalesce(func.sum(AccountReceivable.amount), 0)).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status == "pending",
        )
    )
    amount_overdue_result = await db.execute(
        select(func.coalesce(func.sum(AccountReceivable.amount), 0)).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status != "paid",
            AccountReceivable.due_date < today,
        )
    )
    upcoming_result = await db.execute(
        select(DeadlineItem)
        .where(
            DeadlineItem.tenant_id == tenant_id,
            DeadlineItem.status != "completed",
            DeadlineItem.due_date >= today,
        )
        .order_by(DeadlineItem.due_date.asc())
        .limit(8)
    )

    return DashboardOverview(
        active_clients=active_clients,
        pending_deadlines=pending_deadlines,
        overdue_deadlines=overdue_deadlines,
        certificates_expiring_30d=certificates_expiring_30d,
        open_receivables=open_receivables,
        overdue_receivables=overdue_receivables,
        receivables_amount_open=Decimal(amount_open_result.scalar_one() or 0),
        receivables_amount_overdue=Decimal(amount_overdue_result.scalar_one() or 0),
        upcoming_deadlines=list(upcoming_result.scalars().all()),
    )


@router.get("/clients", response_model=list[AccountingClientResponse])
async def list_clients(
    search: str | None = Query(default=None, max_length=120),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(AccountingClient).where(AccountingClient.tenant_id == tenant_id)
    if status_filter:
        statement = statement.where(AccountingClient.status == status_filter)
    if search:
        term = f"%{search}%"
        statement = statement.where(
            or_(
                AccountingClient.name.ilike(term),
                AccountingClient.document.ilike(term),
            )
        )
    result = await db.execute(statement.order_by(AccountingClient.name.asc()))
    return list(result.scalars().all())


@router.get("/clients/{client_id}", response_model=AccountingClientResponse)
async def get_client(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountingClientResponse:
    """Buscar cliente especifico por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_client_or_404(db, tenant_id, client_id)


@router.post("/clients", response_model=AccountingClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: AccountingClientCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    if payload.document:
        existing = await db.execute(
            select(AccountingClient).where(
                AccountingClient.tenant_id == tenant_id,
                AccountingClient.document == payload.document,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A client with this document already exists",
            )

    client = AccountingClient(tenant_id=tenant_id, **payload.model_dump())
    db.add(client)
    return await _commit_refresh(db, client)


@router.patch("/clients/{client_id}", response_model=AccountingClientResponse)
async def update_client(
    client_id: uuid.UUID,
    payload: AccountingClientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    client = await _get_client_or_404(db, tenant_id, client_id)
    _apply_updates(client, payload)
    return await _commit_refresh(db, client)


@router.delete("/clients/{client_id}", response_model=AccountingClientResponse)
async def deactivate_client(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    client = await _get_client_or_404(db, tenant_id, client_id)
    client.status = "inactive"
    return await _commit_refresh(db, client)


@router.get("/deadlines", response_model=list[DeadlineResponse])
async def list_deadlines(
    client_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(DeadlineItem).where(DeadlineItem.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(DeadlineItem.client_id == client_id)
    if status_filter:
        statement = statement.where(DeadlineItem.status == status_filter)
    result = await db.execute(statement.order_by(DeadlineItem.due_date.asc()))
    return list(result.scalars().all())


@router.get("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def get_deadline(
    deadline_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """Buscar prazo especifico por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_item_or_404(db, DeadlineItem, tenant_id, deadline_id, "Deadline not found")


@router.post("/deadlines", response_model=DeadlineResponse, status_code=status.HTTP_201_CREATED)
async def create_deadline(
    payload: DeadlineCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, payload.client_id)
    item = DeadlineItem(tenant_id=tenant_id, **payload.model_dump())
    db.add(item)
    return await _commit_refresh(db, item)


@router.patch("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def update_deadline(
    deadline_id: uuid.UUID,
    payload: DeadlineUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    item = await _get_item_or_404(db, DeadlineItem, tenant_id, deadline_id, "Deadline not found")
    _apply_updates(item, payload)
    if payload.status == "completed" and item.completed_at is None:
        item.completed_at = datetime.now(timezone.utc)
    return await _commit_refresh(db, item)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    client_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(ClientDocument).where(ClientDocument.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(ClientDocument.client_id == client_id)
    result = await db.execute(statement.order_by(ClientDocument.created_at.desc()))
    return list(result.scalars().all())


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Buscar documento especifico por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_item_or_404(db, ClientDocument, tenant_id, document_id, "Document not found")


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, payload.client_id)
    document = ClientDocument(tenant_id=tenant_id, **payload.model_dump())
    db.add(document)
    return await _commit_refresh(db, document)


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    document = await _get_item_or_404(db, ClientDocument, tenant_id, document_id, "Document not found")
    _apply_updates(document, payload)
    return await _commit_refresh(db, document)


@router.get("/certificates", response_model=list[CertificateResponse])
async def list_certificates(
    client_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(DigitalCertificate).where(DigitalCertificate.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(DigitalCertificate.client_id == client_id)
    result = await db.execute(statement.order_by(DigitalCertificate.valid_until.asc()))
    return list(result.scalars().all())


@router.get("/certificates/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(
    certificate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CertificateResponse:
    """Buscar certificado digital especifico por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_item_or_404(
        db,
        DigitalCertificate,
        tenant_id,
        certificate_id,
        "Certificate not found",
    )


@router.post("/certificates", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def create_certificate(
    payload: CertificateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, payload.client_id)
    certificate = DigitalCertificate(tenant_id=tenant_id, **payload.model_dump())
    db.add(certificate)
    return await _commit_refresh(db, certificate)


@router.patch("/certificates/{certificate_id}", response_model=CertificateResponse)
async def update_certificate(
    certificate_id: uuid.UUID,
    payload: CertificateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    certificate = await _get_item_or_404(
        db,
        DigitalCertificate,
        tenant_id,
        certificate_id,
        "Certificate not found",
    )
    _apply_updates(certificate, payload)
    return await _commit_refresh(db, certificate)


@router.get("/receivables", response_model=list[ReceivableResponse])
async def list_receivables(
    client_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(AccountReceivable).where(AccountReceivable.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(AccountReceivable.client_id == client_id)
    if status_filter:
        statement = statement.where(AccountReceivable.status == status_filter)
    result = await db.execute(statement.order_by(AccountReceivable.due_date.asc()))
    return list(result.scalars().all())


@router.get("/receivables/{receivable_id}", response_model=ReceivableResponse)
async def get_receivable(
    receivable_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReceivableResponse:
    """Buscar conta a receber especifica por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_item_or_404(
        db,
        AccountReceivable,
        tenant_id,
        receivable_id,
        "Receivable not found",
    )


@router.post("/receivables", response_model=ReceivableResponse, status_code=status.HTTP_201_CREATED)
async def create_receivable(
    payload: ReceivableCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, payload.client_id)
    receivable = AccountReceivable(tenant_id=tenant_id, **payload.model_dump())
    db.add(receivable)
    return await _commit_refresh(db, receivable)


@router.patch("/receivables/{receivable_id}", response_model=ReceivableResponse)
async def update_receivable(
    receivable_id: uuid.UUID,
    payload: ReceivableUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    receivable = await _get_item_or_404(
        db,
        AccountReceivable,
        tenant_id,
        receivable_id,
        "Receivable not found",
    )
    _apply_updates(receivable, payload)
    if payload.status == "paid" and receivable.paid_at is None:
        receivable.paid_at = datetime.now(timezone.utc)
    return await _commit_refresh(db, receivable)

