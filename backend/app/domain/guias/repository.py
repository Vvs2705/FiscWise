import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.guias.models import TaxGuide

class TaxGuideRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, guide_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[TaxGuide]:
        result = await self.db.execute(
            select(TaxGuide).where(
                TaxGuide.id == guide_id,
                TaxGuide.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        tenant_id: uuid.UUID,
        tipo: Optional[str] = None,
        status_filter: Optional[str] = None,
        competencia: Optional[date] = None,
        client_id: Optional[uuid.UUID] = None,
    ) -> List[TaxGuide]:
        stmt = select(TaxGuide).where(TaxGuide.tenant_id == tenant_id)
        
        if tipo:
            stmt = stmt.where(TaxGuide.tipo == tipo)
        if status_filter:
            stmt = stmt.where(TaxGuide.status == status_filter)
        if competencia:
            stmt = stmt.where(TaxGuide.competencia == competencia)
        if client_id:
            stmt = stmt.where(TaxGuide.client_id == client_id)

        stmt = stmt.order_by(TaxGuide.vencimento.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, guide: TaxGuide) -> TaxGuide:
        self.db.add(guide)
        await self.db.commit()
        await self.db.refresh(guide)
        return guide

    async def update(self, guide: TaxGuide) -> TaxGuide:
        self.db.add(guide)
        await self.db.commit()
        await self.db.refresh(guide)
        return guide

    async def list_pending_receipts(self, tenant_id: uuid.UUID) -> List[TaxGuide]:
        result = await self.db.execute(
            select(TaxGuide).where(
                and_(
                    TaxGuide.tenant_id == tenant_id,
                    TaxGuide.status == "paga",
                    or_(
                        TaxGuide.comprovante_storage_path == None,
                        TaxGuide.comprovante_storage_path == ""
                    )
                )
            ).order_by(TaxGuide.vencimento.asc())
        )
        return list(result.scalars().all())
