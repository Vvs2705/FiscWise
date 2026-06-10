import uuid
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.monthly_closing.models import MonthlyClosing


class MonthlyClosingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_closings(
        self, tenant_id: uuid.UUID, competence: Optional[str] = None
    ) -> List[MonthlyClosing]:
        conditions = [MonthlyClosing.tenant_id == tenant_id]
        if competence:
            conditions.append(MonthlyClosing.competence == competence)
        result = await self.db.execute(
            select(MonthlyClosing).where(and_(*conditions)).order_by(MonthlyClosing.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, closing_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[MonthlyClosing]:
        result = await self.db.execute(
            select(MonthlyClosing).where(
                and_(MonthlyClosing.id == closing_id, MonthlyClosing.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_client_competence(
        self, client_id: uuid.UUID, competence: str, tenant_id: uuid.UUID
    ) -> Optional[MonthlyClosing]:
        result = await self.db.execute(
            select(MonthlyClosing).where(
                and_(
                    MonthlyClosing.client_id == client_id,
                    MonthlyClosing.competence == competence,
                    MonthlyClosing.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def save(self, closing: MonthlyClosing) -> MonthlyClosing:
        self.db.add(closing)
        await self.db.commit()
        await self.db.refresh(closing)
        return closing

    async def add_all(self, closings: List[MonthlyClosing]) -> None:
        self.db.add_all(closings)
        await self.db.commit()
