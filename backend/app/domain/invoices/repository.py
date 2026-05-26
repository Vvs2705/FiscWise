import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.invoices.models import Invoice, InvoiceIssuer, InvoiceEvent, InvoiceRejection

class InvoiceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_issuer_by_id(self, issuer_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[InvoiceIssuer]:
        stmt = select(InvoiceIssuer).where(
            and_(
                InvoiceIssuer.id == issuer_id,
                InvoiceIssuer.tenant_id == tenant_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_issuer_by_cnpj(self, cnpj: str, tenant_id: uuid.UUID) -> Optional[InvoiceIssuer]:
        stmt = select(InvoiceIssuer).where(
            and_(
                InvoiceIssuer.cnpj == cnpj,
                InvoiceIssuer.tenant_id == tenant_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_issuers(self, tenant_id: uuid.UUID) -> List[InvoiceIssuer]:
        stmt = select(InvoiceIssuer).where(InvoiceIssuer.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_issuer(self, issuer: InvoiceIssuer) -> InvoiceIssuer:
        self.db.add(issuer)
        await self.db.commit()
        await self.db.refresh(issuer)
        return issuer

    async def get_by_id(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Invoice]:
        stmt = select(Invoice).where(
            and_(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
        client_id: Optional[uuid.UUID] = None,
        competencia: Optional[date] = None,
    ) -> List[Invoice]:
        stmt = select(Invoice).where(Invoice.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Invoice.status == status)
        if client_id:
            stmt = stmt.where(Invoice.client_id == client_id)
        if competencia:
            stmt = stmt.where(Invoice.competencia == competencia)
        
        result = await self.db.execute(stmt.order_by(Invoice.created_at.desc()))
        return list(result.scalars().all())

    async def create_invoice(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def update_invoice(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def create_event(self, event: InvoiceEvent) -> InvoiceEvent:
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def list_events(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> List[InvoiceEvent]:
        # Validate that the invoice belongs to the tenant first
        invoice_check = await self.get_by_id(invoice_id, tenant_id)
        if not invoice_check:
            return []
        
        stmt = select(InvoiceEvent).where(
            and_(
                InvoiceEvent.invoice_id == invoice_id,
                InvoiceEvent.tenant_id == tenant_id
            )
        ).order_by(InvoiceEvent.created_at.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_rejection(self, rejection: InvoiceRejection) -> InvoiceRejection:
        self.db.add(rejection)
        await self.db.commit()
        await self.db.refresh(rejection)
        return rejection

    async def list_rejections(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> List[InvoiceRejection]:
        # Validate that the invoice belongs to the tenant first
        invoice_check = await self.get_by_id(invoice_id, tenant_id)
        if not invoice_check:
            return []
            
        stmt = select(InvoiceRejection).where(
            and_(
                InvoiceRejection.invoice_id == invoice_id,
                InvoiceRejection.tenant_id == tenant_id
            )
        ).order_by(InvoiceRejection.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
