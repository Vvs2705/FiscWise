"""
Fiscal Monitor Service for FiscWise.

Situação cadastral do CNPJ consultada de verdade na BrasilAPI (pública e
gratuita). Débitos, CND e NF-e dependem da integração com a Receita (SERPRO),
que não está contratada: esses blocos ficam explicitamente "indisponíveis" —
nada é inventado nem gravado como real.
"""

import asyncio
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.integration_mode import mock_blocked, normalize_provider
from app.models.fiscal_monitor import FiscalMonitorSummary
from app.models.operations import AccountingClient, ClientDocument, DeadlineItem
from app.models.audit import AuditEvent

logger = logging.getLogger(__name__)

UNAVAILABLE_MESSAGE = (
    "Consulta de débitos/CND/NF-e exige integração com a Receita (SERPRO) — não configurada"
)
NOT_CONSULTED = "NAO_CONSULTADO"

# Marcas deixadas pelo Monitor Fiscal simulado antigo (para limpeza segura).
LEGACY_FAKE_URL_PREFIX = "https://fiscwise.storage/"
_LEGACY_TASK_TITLE_PREFIX = "Regularizar DAS Simples Nacional - Competência "
_LEGACY_TASK_DESCRIPTION_PREFIX = "Alerta automático de irregularidade identificado na Receita Federal."
_LEGACY_CND_NOTES = "Download automático realizado pelo Monitor Fiscal da Receita Federal."

# Campos úteis da BrasilAPI guardados em situation_details.
_BRASILAPI_FIELDS = (
    "razao_social",
    "nome_fantasia",
    "descricao_situacao_cadastral",
    "data_situacao_cadastral",
    "motivo_situacao_cadastral",
    "cnae_fiscal",
    "cnae_fiscal_descricao",
    "natureza_juridica",
    "codigo_natureza_juridica",
    "opcao_pelo_simples",
    "data_opcao_pelo_simples",
    "opcao_pelo_mei",
    "data_opcao_pelo_mei",
    "data_inicio_atividade",
    "uf",
    "municipio",
)

# Permite aos testes injetar um httpx.AsyncClient com MockTransport.
_http_client_override: Optional[httpx.AsyncClient] = None


class FiscalMonitorNotConfiguredError(RuntimeError):
    """Provider mock em produção/staging, ou provider desconhecido."""


class CnpjLookupError(RuntimeError):
    """Falha ao consultar a situação cadastral (rede, 4xx/5xx, CNPJ inválido)."""


def _digits(value: Optional[str]) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


async def _get_with_retry(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """GET com 1 retry (backoff curto) para erro de rede ou 5xx/429."""
    last_exc: Optional[Exception] = None
    for attempt in range(2):
        try:
            response = await client.get(url)
            if response.status_code >= 500 or response.status_code == 429:
                last_exc = CnpjLookupError(f"BrasilAPI respondeu HTTP {response.status_code}")
            else:
                return response
        except httpx.HTTPError as exc:
            last_exc = exc
        if attempt == 0:
            await asyncio.sleep(0.5)
    raise CnpjLookupError(f"Falha ao consultar a BrasilAPI: {last_exc}")


async def fetch_cnpj_brasilapi(
    cnpj: str, http_client: Optional[httpx.AsyncClient] = None
) -> Dict[str, Any]:
    digits = _digits(cnpj)
    if len(digits) != 14:
        raise CnpjLookupError("Cliente sem CNPJ válido (14 dígitos) para consulta cadastral.")
    url = f"{settings.BRASILAPI_BASE_URL.rstrip('/')}/cnpj/v1/{digits}"
    client = http_client or _http_client_override
    if client is not None:
        response = await _get_with_retry(client, url)
    else:
        async with httpx.AsyncClient(timeout=settings.BRASILAPI_TIMEOUT_SECONDS) as owned:
            response = await _get_with_retry(owned, url)
    if response.status_code == 404:
        raise CnpjLookupError("CNPJ não encontrado na base da Receita (BrasilAPI).")
    if response.status_code >= 400:
        raise CnpjLookupError(f"BrasilAPI respondeu HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise CnpjLookupError("Resposta inválida da BrasilAPI.") from exc


def _mock_registry(client: AccountingClient) -> Dict[str, Any]:
    """Somente testes/dev: dados cadastrais determinísticos, marcados como mock."""
    return {
        "razao_social": client.name,
        "descricao_situacao_cadastral": "ATIVA",
        "data_situacao_cadastral": "2020-01-01",
        "cnae_fiscal": 6920601,
        "cnae_fiscal_descricao": "Atividades de contabilidade",
        "natureza_juridica": "Sociedade Empresária Limitada",
        "opcao_pelo_simples": True,
        "opcao_pelo_mei": False,
        "data_inicio_atividade": "2020-01-01",
    }


async def _lookup_registry(client: AccountingClient, provider: str) -> Dict[str, Any]:
    if provider == "mock":
        return _mock_registry(client)
    if provider == "brasilapi":
        return await fetch_cnpj_brasilapi(client.document or "")
    raise FiscalMonitorNotConfiguredError(f"FISCAL_MONITOR_PROVIDER desconhecido: {provider}")


async def _retire_legacy_fake_records(
    db: AsyncSession, client_id: uuid.UUID, tenant_id: uuid.UUID
) -> Dict[str, int]:
    """Neutraliza registros criados pelo Monitor Fiscal simulado antigo.

    Nada é apagado fisicamente (regra offline): prazos falsos viram
    ``cancelled`` e CNDs com URL inventada viram ``missing`` sem link.
    Só toca o que tem as marcas exatas do mock antigo.
    """
    tasks = (
        await db.execute(
            select(DeadlineItem).where(
                (DeadlineItem.tenant_id == tenant_id)
                & (DeadlineItem.client_id == client_id)
                & (DeadlineItem.category == "fiscal")
                & (DeadlineItem.title.like(f"{_LEGACY_TASK_TITLE_PREFIX}%"))
                & (DeadlineItem.status != "cancelled")
            )
        )
    ).scalars().all()
    now = datetime.now(timezone.utc)
    cancelled = 0
    for task in tasks:
        if not (task.description or "").startswith(_LEGACY_TASK_DESCRIPTION_PREFIX):
            continue
        if task.status == "completed":
            continue
        task.status = "cancelled"
        task.updated_at = now
        cancelled += 1

    docs = (
        await db.execute(
            select(ClientDocument).where(
                (ClientDocument.tenant_id == tenant_id)
                & (ClientDocument.client_id == client_id)
                & (ClientDocument.document_type == "certidao_negativa")
                & (ClientDocument.file_url.like(f"{LEGACY_FAKE_URL_PREFIX}%"))
            )
        )
    ).scalars().all()
    for doc in docs:
        doc.status = "missing"
        doc.file_url = None
        doc.notes = (
            "Registro simulado pelo Monitor Fiscal antigo — não há certidão real. "
            "Emita a CND no portal da Receita."
        )
        doc.updated_at = now

    return {"cancelled_tasks": cancelled, "retired_cnds": len(docs)}


async def sync_client_fiscal_status(
    db: AsyncSession,
    client_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> tuple[FiscalMonitorSummary, Optional[str]]:
    """Atualiza a situação cadastral real do cliente.

    Retorna ``(summary, erro)``; ``erro`` é None quando a consulta funcionou.
    Em caso de falha nada é inventado: os dados cadastrais anteriores (se
    houver) são mantidos e o erro fica registrado em ``situation_details``.
    """
    provider = normalize_provider(settings.FISCAL_MONITOR_PROVIDER, "brasilapi")
    if mock_blocked(provider):
        raise FiscalMonitorNotConfiguredError(
            "Integração do Monitor Fiscal não configurada (provider mock em produção)."
        )

    client = (
        await db.execute(
            select(AccountingClient).where(
                (AccountingClient.id == client_id) & (AccountingClient.tenant_id == tenant_id)
            )
        )
    ).scalar_one_or_none()
    if not client:
        raise ValueError("Cliente não encontrado ou não pertence a este inquilino.")

    summary = (
        await db.execute(
            select(FiscalMonitorSummary).where(
                (FiscalMonitorSummary.client_id == client_id)
                & (FiscalMonitorSummary.tenant_id == tenant_id)
            )
        )
    ).scalar_one_or_none()
    if not summary:
        summary = FiscalMonitorSummary(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=client_id,
            cnpj_status="PENDENTE",
        )
        db.add(summary)

    now = datetime.now(timezone.utc)
    error: Optional[str] = None
    previous = summary.situation_details or {}
    try:
        data = await _lookup_registry(client, provider)
        details = {key: data.get(key) for key in _BRASILAPI_FIELDS if key in data}
        details["source"] = provider
        details["consulted_at"] = now.isoformat()
        summary.situation_details = details
        situacao = (data.get("descricao_situacao_cadastral") or "").strip().upper()
        summary.cnpj_status = situacao or "DESCONHECIDA"
    except CnpjLookupError as exc:
        error = str(exc)
        logger.warning("Monitor Fiscal: falha na consulta cadastral (client=%s): %s", client_id, exc)
        kept = dict(previous) if previous.get("source") in ("brasilapi", "mock") else {}
        kept["status"] = "error"
        kept["last_error"] = error
        kept["last_error_at"] = now.isoformat()
        summary.situation_details = kept
        if not kept.get("source"):
            summary.cnpj_status = "ERRO_CONSULTA"

    # Débitos, CND e NF-e: não consultados (exigem SERPRO). Zera o que o mock
    # antigo tenha deixado gravado.
    summary.has_debts = False
    summary.debt_count = 0
    summary.total_debt_value = Decimal("0.00")
    summary.debts_list = None
    summary.cnd_status = NOT_CONSULTED
    summary.last_cnd_document_id = None
    summary.last_cnd_download_at = None
    summary.last_sync_at = now
    summary.updated_at = now
    await db.flush()

    cleanup = await _retire_legacy_fake_records(db, client_id, tenant_id)

    db.add(
        AuditEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            action="fiscal_monitor.sync",
            entity_type="fiscal_monitor_summary",
            entity_id=summary.id,
            after_data={
                "provider": provider,
                "cnpj_status": summary.cnpj_status,
                "error": error,
                **cleanup,
            },
        )
    )
    await db.commit()
    await db.refresh(summary)
    return summary, error
