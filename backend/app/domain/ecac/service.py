import uuid
import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select

from app.domain.ecac.models import EcacProxy, EcacFiscalSituation
from app.domain.ecac.repository import EcacRepository
from app.domain.ecac.schemas import EcacProxyCreate
from app.domain.ecac.integrations.base import EcacIntegrationProvider
from app.core.audit import audit_log

logger = logging.getLogger(__name__)

class EcacService:
    def __init__(self, repo: EcacRepository):
        self.repo = repo

    async def create_proxy(self, payload: EcacProxyCreate, tenant_id: uuid.UUID) -> EcacProxy:
        proxy = EcacProxy(
            tenant_id=tenant_id,
            client_id=payload.client_id,
            outorgante_cpf_cnpj=payload.outorgante_cpf_cnpj,
            outorgante_nome=payload.outorgante_nome,
            procurador_cpf=payload.procurador_cpf,
            tipo=payload.tipo,
            servicos_autorizados=payload.servicos_autorizados,
            data_inicio=payload.data_inicio,
            data_validade=payload.data_validade,
            status="ativa",
        )
        
        # Check if expires in 30 days to trigger alert
        if payload.data_validade:
            today = date.today()
            if today <= payload.data_validade <= today + timedelta(days=30):
                await audit_log(
                    action="proxy.expiring",
                    tenant_id=str(tenant_id),
                    details={"proxy_id": str(proxy.id), "days_remaining": (payload.data_validade - today).days}
                )

        return await self.repo.create_proxy(proxy)

    async def list_proxies(self, tenant_id: uuid.UUID) -> List[EcacProxy]:
        return await self.repo.list_proxies(tenant_id)

    async def list_expiring_proxies(self, tenant_id: uuid.UUID) -> List[EcacProxy]:
        proxies = await self.repo.list_expiring_proxies(tenant_id, days=30)
        today = date.today()
        for p in proxies:
            days_left = (p.data_validade - today).days if p.data_validade else 0
            await audit_log(
                action="proxy.expiring",
                tenant_id=str(tenant_id),
                details={"proxy_id": str(p.id), "days_remaining": days_left}
            )
        return proxies

    async def list_clients_without_proxy(self, tenant_id: uuid.UUID):
        return await self.repo.list_clients_without_proxy(tenant_id)

    async def get_fiscal_situation(self, client_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[EcacFiscalSituation]:
        return await self.repo.get_fiscal_situation_by_client_id(client_id, tenant_id)

    async def refresh_fiscal_situation_sync(self, client_id: uuid.UUID, tenant_id: uuid.UUID, provider: EcacIntegrationProvider) -> EcacFiscalSituation:
        from app.models.operations import AccountingClient
        
        result = await self.repo.db.execute(
            select(AccountingClient).where(
                AccountingClient.id == client_id,
                AccountingClient.tenant_id == tenant_id
            )
        )
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

        cpf_cnpj = client.document
        if not cpf_cnpj:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client has no CPF/CNPJ document registered")

        data = await provider.fetch_fiscal_situation(cpf_cnpj)
        
        cert_valid = None
        if data.get("certidao_validade"):
            try:
                cert_valid = date.fromisoformat(data["certidao_validade"])
            except ValueError:
                pass

        situation = EcacFiscalSituation(
            tenant_id=tenant_id,
            client_id=client_id,
            cpf_cnpj=cpf_cnpj,
            status_geral=data.get("status_geral"),
            pendencias=data.get("pendencias", []),
            debitos=data.get("debitos", []),
            certidao_status=data.get("certidao_status"),
            certidao_validade=cert_valid,
            raw_response=data.get("raw"),
        )
        
        saved = await self.repo.create_fiscal_situation(situation)
        
        await audit_log(
            action="ecac.situation_consulted",
            tenant_id=str(tenant_id),
            details={"client_id": str(client_id), "status_geral": situation.status_geral}
        )
        
        return saved
