import uuid
from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy import select, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ecac.models import EcacProxy, EcacFiscalSituation
from app.models.operations import AccountingClient

class EcacRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_proxy_by_id(self, proxy_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[EcacProxy]:
        result = await self.db.execute(
            select(EcacProxy).where(
                EcacProxy.id == proxy_id,
                EcacProxy.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_proxies(self, tenant_id: uuid.UUID) -> List[EcacProxy]:
        result = await self.db.execute(
            select(EcacProxy).where(EcacProxy.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def list_expiring_proxies(self, tenant_id: uuid.UUID, days: int = 30) -> List[EcacProxy]:
        today = date.today()
        limit_date = today + timedelta(days=days)
        result = await self.db.execute(
            select(EcacProxy).where(
                and_(
                    EcacProxy.tenant_id == tenant_id,
                    EcacProxy.data_validade >= today,
                    EcacProxy.data_validade <= limit_date,
                    EcacProxy.status == "ativa"
                )
            )
        )
        return list(result.scalars().all())

    async def create_proxy(self, proxy: EcacProxy) -> EcacProxy:
        self.db.add(proxy)
        await self.db.commit()
        await self.db.refresh(proxy)
        return proxy

    async def update_proxy(self, proxy: EcacProxy) -> EcacProxy:
        self.db.add(proxy)
        await self.db.commit()
        await self.db.refresh(proxy)
        return proxy

    async def get_fiscal_situation_by_client_id(self, client_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[EcacFiscalSituation]:
        result = await self.db.execute(
            select(EcacFiscalSituation)
            .where(
                and_(
                    EcacFiscalSituation.client_id == client_id,
                    EcacFiscalSituation.tenant_id == tenant_id
                )
            )
            .order_by(EcacFiscalSituation.consultado_em.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_fiscal_situation(self, situation: EcacFiscalSituation) -> EcacFiscalSituation:
        self.db.add(situation)
        await self.db.commit()
        await self.db.refresh(situation)
        return situation

    async def list_clients_without_proxy(self, tenant_id: uuid.UUID) -> List[AccountingClient]:
        # Subquery for clients that have active proxies
        active_proxies_subq = select(EcacProxy.client_id).where(
            and_(
                EcacProxy.tenant_id == tenant_id,
                EcacProxy.client_id != None,
                EcacProxy.status == "ativa"
            )
        ).scalar_subquery()

        result = await self.db.execute(
            select(AccountingClient).where(
                and_(
                    AccountingClient.tenant_id == tenant_id,
                    AccountingClient.status == "active",
                    not_(AccountingClient.id.in_(active_proxies_subq))
                )
            )
        )
        return list(result.scalars().all())
