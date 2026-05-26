"""Invoice domain repository — all DB queries isolated here."""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.invoices.models import Invoice, InvoiceIssuer, InvoiceServiceProfile, InvoiceEvent


async def get_invoice(db: AsyncSession, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Invoice]:
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def list_invoices(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    competence: Optional[str] = None,
    issuer_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Invoice]:
    q = select(Invoice).where(Invoice.tenant_id == tenant_id)
    if competence:
        q = q.where(Invoice.competence == competence)
    if issuer_id:
        q = q.where(Invoice.issuer_id == issuer_id)
    if status:
        q = q.where(Invoice.status == status)
    q = q.order_by(Invoice.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_issuer(db: AsyncSession, issuer_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[InvoiceIssuer]:
    result = await db.execute(
        select(InvoiceIssuer).where(
            InvoiceIssuer.id == issuer_id, InvoiceIssuer.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def list_issuers(db: AsyncSession, tenant_id: uuid.UUID) -> list[InvoiceIssuer]:
    result = await db.execute(
        select(InvoiceIssuer).where(InvoiceIssuer.tenant_id == tenant_id, InvoiceIssuer.active.is_(True))
    )
    return list(result.scalars().all())


async def get_invoice_events(db: AsyncSession, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> list[InvoiceEvent]:
    result = await db.execute(
        select(InvoiceEvent)
        .where(InvoiceEvent.invoice_id == invoice_id, InvoiceEvent.tenant_id == tenant_id)
        .order_by(InvoiceEvent.occurred_at.asc())
    )
    return list(result.scalars().all())
