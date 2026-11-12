"""
Fiscal Monitor API Router for FiscWise.
Provides access to CNPJ fiscal status sync, CND history, NF-e retrieval, and invoice imports.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.operations import AccountingClient
from app.models.fiscal_monitor import FiscalMonitorSummary, FiscalNFe
from app.services import fiscal_monitor_service
from app.schemas.fiscal_monitor import (
    FiscalMonitorSummaryResponse,
    FiscalNFeResponse,
    FiscalMonitorSyncResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fiscal-monitor", tags=["Fiscal Monitor"])


class ExternalNFeImportRequest(BaseModel):
    client_id: uuid.UUID
    access_key: str = Field(..., min_length=44, max_length=44)
    nfe_number: str
    nfe_type: str = Field(..., description="ENTRADA | SAIDA")
    issuer_name: str
    issuer_document: str
    recipient_name: str
    recipient_document: str
    value: Decimal
    issued_at: datetime


@router.post("/sync/{client_id}", response_model=FiscalMonitorSyncResponse)
async def sync_client_status(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FiscalMonitorSyncResponse:
    """
    Atualiza a situação cadastral real do CNPJ (BrasilAPI).
    Débitos, CND e NF-e não são consultados: exigem integração SERPRO.
    """
    try:
        summary, error = await fiscal_monitor_service.sync_client_fiscal_status(
            db=db,
            client_id=client_id,
            tenant_id=current_user.tenant_id,
        )
    except fiscal_monitor_service.FiscalMonitorNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integração não configurada: o Monitor Fiscal está em modo simulado neste ambiente.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.exception("Erro ao sincronizar monitor fiscal para o cliente %s", client_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao sincronizar a situação cadastral.",
        )

    if error:
        return FiscalMonitorSyncResponse(
            status="error",
            message=f"Não foi possível consultar a situação cadastral: {error}",
            summary=FiscalMonitorSummaryResponse.model_validate(summary),
        )
    return FiscalMonitorSyncResponse(
        status="success",
        message="Situação cadastral atualizada.",
        summary=FiscalMonitorSummaryResponse.model_validate(summary),
    )


@router.get("/status/{client_id}", response_model=FiscalMonitorSummaryResponse)
async def get_client_status(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FiscalMonitorSummaryResponse:
    """
    Retorna o resumo da situação fiscal do cliente.
    Se o cliente ainda não foi sincronizado, retorna uma resposta padrão de status pendente.
    """
    # 1. Verifica se o cliente existe
    stmt_client = select(AccountingClient).where(
        (AccountingClient.id == client_id) &
        (AccountingClient.tenant_id == current_user.tenant_id)
    )
    res_client = await db.execute(stmt_client)
    client = res_client.scalar_one_or_none()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado."
        )

    # 2. Busca o resumo fiscal
    stmt_summary = select(FiscalMonitorSummary).where(
        (FiscalMonitorSummary.client_id == client_id) &
        (FiscalMonitorSummary.tenant_id == current_user.tenant_id)
    )
    res_summary = await db.execute(stmt_summary)
    summary = res_summary.scalar_one_or_none()

    if not summary:
        # Retorna um objeto padrão para sinalizar que nunca foi sincronizado
        return FiscalMonitorSummaryResponse(
            id=uuid.uuid4(),
            tenant_id=current_user.tenant_id,
            client_id=client_id,
            cnpj_status="PENDENTE",
            cnd_status=fiscal_monitor_service.NOT_CONSULTED,
        )

    return FiscalMonitorSummaryResponse.model_validate(summary)


@router.get("/nfes/{client_id}", response_model=List[FiscalNFeResponse])
async def list_client_nfes(
    client_id: uuid.UUID,
    nfe_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[FiscalNFeResponse]:
    """
    Lista as notas fiscais (NF-e) capturadas da Receita Federal para o cliente.
    """
    # 1. Verifica se o cliente existe
    stmt_client = select(AccountingClient).where(
        (AccountingClient.id == client_id) &
        (AccountingClient.tenant_id == current_user.tenant_id)
    )
    res_client = await db.execute(stmt_client)
    client = res_client.scalar_one_or_none()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado."
        )

    # 2. Query NF-es
    stmt = select(FiscalNFe).where(
        (FiscalNFe.client_id == client_id) &
        (FiscalNFe.tenant_id == current_user.tenant_id) &
        # Linhas com URL inventada vieram do simulador antigo: não são NF-e reais.
        or_(
            FiscalNFe.xml_url.is_(None),
            ~FiscalNFe.xml_url.like(f"{fiscal_monitor_service.LEGACY_FAKE_URL_PREFIX}%"),
        )
    ).order_by(desc(FiscalNFe.issued_at))

    if nfe_type:
        stmt = stmt.where(FiscalNFe.nfe_type == nfe_type)

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    nfes = result.scalars().all()

    return [FiscalNFeResponse.model_validate(n) for n in nfes]


@router.post("/nfes/import", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def import_nfe(
    payload: ExternalNFeImportRequest,
    current_user: User = Depends(get_current_user),
) -> None:
    """Importação de NF-e por parceiro ainda não existe: responde 501 sem gravar."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Importação de NF-e não implementada: exige integração com a Receita (SERPRO) ou parceiro.",
    )
