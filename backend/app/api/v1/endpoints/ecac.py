import uuid
from typing import List, Optional, Any
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, get_sessionmaker
from app.models.user import User
from app.domain.ecac.service import EcacService
from app.domain.ecac.repository import EcacRepository
from app.domain.ecac.schemas import EcacProxyCreate, EcacProxyUpdate, EcacProxyResponse, EcacFiscalSituationResponse
from app.domain.ecac.integrations.mock import MockEcacIntegrationProvider
from app.models.operations import AccountingClient
from app.schemas.operations import AccountingClientResponse

router = APIRouter(prefix="/ecac", tags=["e-CAC"])

def _tenant_id(current_user: User) -> uuid.UUID:
    return current_user.tenant_id

async def refresh_fiscal_situation_background(client_id: uuid.UUID, tenant_id: uuid.UUID):
    async_session = get_sessionmaker()
    async with async_session() as db:
        repo = EcacRepository(db)
        service = EcacService(repo)
        provider = MockEcacIntegrationProvider()
        try:
            await service.refresh_fiscal_situation_sync(client_id, tenant_id, provider)
        except Exception as e:
            print("ERROR IN BACKGROUND TASK:", str(e))

@router.get("/proxies", response_model=List[EcacProxyResponse])
async def list_proxies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = EcacRepository(db)
    service = EcacService(repo)
    return await service.list_proxies(_tenant_id(current_user))

@router.post("/proxies", response_model=EcacProxyResponse, status_code=status.HTTP_201_CREATED)
async def create_proxy(
    payload: EcacProxyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = EcacRepository(db)
    service = EcacService(repo)
    return await service.create_proxy(payload, _tenant_id(current_user))

@router.get("/proxies/expiring", response_model=List[EcacProxyResponse])
async def list_expiring_proxies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = EcacRepository(db)
    service = EcacService(repo)
    return await service.list_expiring_proxies(_tenant_id(current_user))

@router.get("/clients-without-proxy", response_model=List[AccountingClientResponse])
async def list_clients_without_proxy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = EcacRepository(db)
    service = EcacService(repo)
    return await service.list_clients_without_proxy(_tenant_id(current_user))

@router.get("/proxies/{id}", response_model=EcacProxyResponse)
async def get_proxy(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = EcacRepository(db)
    proxy = await repo.get_proxy_by_id(id, _tenant_id(current_user))
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return proxy

@router.put("/proxies/{id}", response_model=EcacProxyResponse)
async def update_proxy(
    id: uuid.UUID,
    payload: EcacProxyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = EcacRepository(db)
    proxy = await repo.get_proxy_by_id(id, _tenant_id(current_user))
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(proxy, field, val)
        
    return await repo.update_proxy(proxy)

@router.get("/fiscal-situation/{client_id}", response_model=EcacFiscalSituationResponse)
async def get_fiscal_situation(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = EcacRepository(db)
    service = EcacService(repo)
    situation = await service.get_fiscal_situation(client_id, _tenant_id(current_user))
    if not situation:
        raise HTTPException(status_code=404, detail="Fiscal situation not consulted yet. Call POST /refresh first.")
    return situation

@router.post("/fiscal-situation/{client_id}/refresh", response_model=dict)
async def refresh_fiscal_situation(
    client_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = EcacRepository(db)
    
    # Check client exists first
    result = await db.execute(
        select(AccountingClient).where(
            AccountingClient.id == client_id,
            AccountingClient.tenant_id == _tenant_id(current_user)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")

    background_tasks.add_task(refresh_fiscal_situation_background, client_id, _tenant_id(current_user))
    return {"status": "queued", "message": "e-CAC fiscal situation query queued successfully"}
