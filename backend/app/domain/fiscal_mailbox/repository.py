import uuid
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fiscal_mailbox.models import FiscalMailboxMessage


class FiscalMailboxRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_messages(
        self,
        tenant_id: uuid.UUID,
        *,
        client_id: Optional[uuid.UUID] = None,
        risk: Optional[str] = None,
        status: Optional[str] = None,
        organ: Optional[str] = None,
    ) -> List[FiscalMailboxMessage]:
        conditions = [FiscalMailboxMessage.tenant_id == tenant_id]
        if client_id is not None:
            conditions.append(FiscalMailboxMessage.client_id == client_id)
        if risk:
            conditions.append(FiscalMailboxMessage.risk == risk)
        if status:
            conditions.append(FiscalMailboxMessage.status == status)
        if organ:
            conditions.append(FiscalMailboxMessage.organ == organ)

        result = await self.db.execute(
            select(FiscalMailboxMessage)
            .where(and_(*conditions))
            .order_by(FiscalMailboxMessage.received_at.desc().nullslast())
        )
        return list(result.scalars().all())

    async def get_by_id(self, message_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[FiscalMailboxMessage]:
        result = await self.db.execute(
            select(FiscalMailboxMessage).where(
                and_(
                    FiscalMailboxMessage.id == message_id,
                    FiscalMailboxMessage.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str, tenant_id: uuid.UUID) -> Optional[FiscalMailboxMessage]:
        result = await self.db.execute(
            select(FiscalMailboxMessage).where(
                and_(
                    FiscalMailboxMessage.external_id == external_id,
                    FiscalMailboxMessage.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def add(self, message: FiscalMailboxMessage) -> FiscalMailboxMessage:
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def save(self, message: FiscalMailboxMessage) -> FiscalMailboxMessage:
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message
