"""Handlers da fila `background_jobs` (ver contrato em app/services/job_queue.py).

Kinds registrados aqui:

- `document.parse`  payload {"document_id", "storage_path", "file_name", "tmp_path"?}
                    chave  "document.parse:<document_id>"
- `invoice.emit`    payload {"invoice_id", "tenant_id"}
                    chave  "invoice.emit:<invoice_id>"
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.job_queue import (
    JobContext,
    JobRetry,
    PermanentJobError,
    _enter_worker_mode,
    enqueue,
    job_handler,
)

logger = logging.getLogger(__name__)


# ── document.parse ──────────────────────────────────────────────────────────

DOCUMENT_PARSE = "document.parse"


def document_parse_key(document_id: uuid.UUID) -> str:
    return f"{DOCUMENT_PARSE}:{document_id}"


@job_handler(DOCUMENT_PARSE)
async def handle_document_parse(ctx: JobContext) -> Dict[str, Any]:
    from app.api.v1.endpoints.operations import apply_document_parse, mark_document_parse_failed
    from app.core.storage import download_bytes

    p = ctx.payload
    if ctx.tenant_id is None:
        raise PermanentJobError("document.parse exige tenant_id")
    document_id = uuid.UUID(str(p["document_id"]))
    file_name = p.get("file_name") or "file"
    file_path: Optional[str] = p.get("tmp_path")
    downloaded = False

    try:
        if not (file_path and os.path.exists(file_path)):
            # Outra instância (ou a mesma depois de reiniciar): busca no Storage.
            data = await download_bytes("documents", p["storage_path"])
            if data is None:
                raise PermanentJobError("Arquivo indisponível (storage não configurado)")
            suffix = Path(file_name).suffix.lower()
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(data)
                file_path = tmp.name
            downloaded = True

        status = await apply_document_parse(ctx.db, document_id, ctx.tenant_id, file_path, file_name)
    except Exception as exc:
        if isinstance(exc, PermanentJobError) or ctx.is_last_attempt:
            await ctx.db.rollback()
            await mark_document_parse_failed(ctx.db, document_id, ctx.tenant_id, str(exc)[:500])
        raise
    finally:
        if downloaded and file_path:
            _safe_unlink(file_path)

    # Sucesso: o temporário original também pode ir embora.
    if p.get("tmp_path"):
        _safe_unlink(p["tmp_path"])
    return {"document_id": str(document_id), "parse_status": status}


def _safe_unlink(path: str) -> None:
    try:
        if os.path.exists(path):
            os.unlink(path)
    except OSError as exc:  # pragma: no cover
        logger.warning("não removi o temporário %s: %s", path, exc)


# ── invoice.emit ────────────────────────────────────────────────────────────

INVOICE_EMIT = "invoice.emit"
# Nota em `queued` mais nova que isto fica para o fluxo que a enfileirou
# (ex.: o BackgroundTasks do POST /invoices/{id}/emit), evitando corrida.
INVOICE_SWEEP_GRACE = timedelta(minutes=10)

# Falhas em que o pedido não chegou ao provedor: seguro tentar de novo.
# Timeout de LEITURA não entra: a prefeitura pode ter emitido; o fluxo existente
# marca `failed` com rejeição EXCEPTION para revisão humana (evita nota dupla).
_TRANSIENT_PROVIDER_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.PoolTimeout,
    ConnectionRefusedError,
)


def invoice_emit_key(invoice_id: uuid.UUID) -> str:
    return f"{INVOICE_EMIT}:{invoice_id}"


def get_emission_provider():
    """Mesmo provedor do POST /invoices/{id}/emit (hoje o de simulação)."""
    from app.domain.invoices.providers.mock import MockNfseProvider

    return MockNfseProvider()


class _TransientGuardProvider:
    """Converte falha de conexão do provedor em TransientEmissionError."""

    def __init__(self, inner) -> None:
        self._inner = inner

    async def emit(self, invoice_data: dict) -> dict:
        from app.domain.invoices.providers.base import TransientEmissionError

        try:
            return await self._inner.emit(invoice_data)
        except TransientEmissionError:
            raise
        except _TRANSIENT_PROVIDER_ERRORS as exc:
            raise TransientEmissionError(f"{type(exc).__name__}: {exc}") from exc

    def __getattr__(self, name):
        return getattr(self._inner, name)


async def enqueue_invoice_emit(
    db: AsyncSession, invoice_id: uuid.UUID, tenant_id: uuid.UUID, *, requeue_if_finished: bool = False
):
    return await enqueue(
        db,
        INVOICE_EMIT,
        {"invoice_id": str(invoice_id), "tenant_id": str(tenant_id)},
        tenant_id=tenant_id,
        idempotency_key=invoice_emit_key(invoice_id),
        requeue_if_finished=requeue_if_finished,
    )


@job_handler(INVOICE_EMIT)
async def handle_invoice_emit(ctx: JobContext) -> Dict[str, Any]:
    from app.domain.invoices.providers.base import TransientEmissionError
    from app.domain.invoices.repository import InvoiceRepository
    from app.domain.invoices.service import InvoiceService

    invoice_id = uuid.UUID(str(ctx.payload["invoice_id"]))
    tenant_id = uuid.UUID(str(ctx.payload["tenant_id"]))
    if ctx.tenant_id is None or tenant_id != ctx.tenant_id:
        raise PermanentJobError("tenant_id do payload difere do job")

    repo = InvoiceRepository(ctx.db)
    invoice = await repo.get_by_id(invoice_id, tenant_id)
    if invoice is None:
        return {"invoice_id": str(invoice_id), "skipped": "not_found"}
    # Só age se a nota ainda está na fila: offline nunca autoriza nada sozinho.
    if invoice.status != "queued":
        return {"invoice_id": str(invoice_id), "skipped": invoice.status}

    service = InvoiceService(repo)
    provider = _TransientGuardProvider(get_emission_provider())
    try:
        invoice = await service.process_emission_sync(invoice_id, tenant_id, provider)
    except TransientEmissionError as exc:
        # O serviço já devolveu a nota para `queued`; tenta de novo mais tarde.
        raise JobRetry(f"Provedor indisponível: {exc}", delay_s=300.0) from exc
    return {"invoice_id": str(invoice_id), "status": invoice.status, "numero": invoice.numero}


async def drain_queued_invoices(db: AsyncSession) -> int:
    """Enfileira `invoice.emit` para toda nota em `queued` sem job pendente.

    Idempotente (chave por nota): rodar duas vezes não duplica. Um job já
    encerrado (done/failed) é reaberto, porque a nota voltou para a fila depois
    dele (ex.: rejeitada → corrigida → reenviada, ou provedor fora por horas).
    Retorna quantas notas foram consideradas.
    """
    from app.core.deps import _set_current_tenant_context
    from app.domain.invoices.models import Invoice
    from app.models.tenant import Tenant

    await _enter_worker_mode(db)
    cutoff = datetime.now(timezone.utc) - INVOICE_SWEEP_GRACE
    tenant_ids = [row[0] for row in (await db.execute(select(Tenant.id))).all()]
    total = 0
    try:
        for tid in tenant_ids:
            await _set_current_tenant_context(db, tid)
            invoice_ids = [
                row[0]
                for row in (
                    await db.execute(
                        select(Invoice.id).where(
                            Invoice.tenant_id == tid,
                            Invoice.status == "queued",
                            Invoice.updated_at <= cutoff,
                        )
                    )
                ).all()
            ]
            for inv_id in invoice_ids:
                await enqueue_invoice_emit(db, inv_id, tid, requeue_if_finished=True)
                total += 1
            await db.commit()
    finally:
        db.info.pop("tenant_id", None)
    if total:
        logger.info("varredor de notas: %s nota(s) em queued na fila", total)
    return total
