"""Fila de trabalho em segundo plano baseada no Postgres (tabela `background_jobs`).

Feita para o Cloud Run com scale-to-zero, sem worker sempre ligado e sem custo:

- `enqueue(...)` grava o job na mesma transação do pedido (idempotente pela chave);
- logo depois do commit, `kick()` dispara `run_pending` numa task "best-effort"
  com sessão própria. A instância pode ser desligada no meio: tudo bem;
- o `POST /internal/tick` (Cloud Scheduler, de hora em hora) chama `run_tick()`,
  que varre o que ficou pendente com orçamento de ~5 min (o deadline do Scheduler
  é 900 s);
- job "running" com `locked_at` há mais de 15 min é considerado abandonado
  (instância morreu) e volta a ser executado.

Contrato para registrar um tipo de job (ex.: Frente G)
------------------------------------------------------
    from app.services.job_queue import JobContext, job_handler

    @job_handler("meu.kind")
    async def meu_handler(ctx: JobContext) -> dict | None:
        ...  # ctx.db já está com o contexto RLS do ctx.tenant_id

- `kind`: "<domínio>.<ação>", minúsculo. O módulo do handler precisa ser
  importado no boot do worker: acrescente-o em `HANDLER_MODULES`.
- `payload`: dict JSON pequeno com IDs (nunca o arquivo ou dados sensíveis).
- `idempotency_key`: "<kind>:<id do recurso>". Enfileirar de novo com a mesma
  chave devolve o job existente, sem duplicar.
- Retry: exceção comum → nova tentativa com backoff (1 min, 5 min, 25 min...;
  máx. `max_attempts`, padrão 3). `JobRetry(delay_s)` pede retry com atraso
  próprio. `PermanentJobError` falha na hora, sem retry. O handler deve ser
  idempotente: pode rodar mais de uma vez se a instância morrer no meio.
- Retorno do handler (dict ou None) fica em `result`.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import socket
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from sqlalchemy import and_, event, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.background_job import BackgroundJob

logger = logging.getLogger(__name__)

STALE_LOCK_AFTER = timedelta(minutes=15)
TICK_TIME_BUDGET_S = 300.0  # ~5 min, dentro do deadline de 900 s do Cloud Scheduler
TICK_MAX_JOBS = 200
KICK_TIME_BUDGET_S = 60.0
KICK_MAX_JOBS = 10
KICK_ENABLED = True  # testes desligam (a task concorreria com a sessão do teste)

# Módulos com @job_handler, importados antes de rodar a fila.
HANDLER_MODULES = ["app.services.job_handlers"]

HandlerFn = Callable[["JobContext"], Awaitable[Optional[Dict[str, Any]]]]
_REGISTRY: Dict[str, HandlerFn] = {}
_background_tasks: set[asyncio.Task] = set()


class PermanentJobError(Exception):
    """Falha definitiva: o job vai para `failed` sem nova tentativa."""


class JobRetry(Exception):
    """Pede nova tentativa depois de `delay_s` segundos (conta como tentativa)."""

    def __init__(self, message: str, delay_s: float = 60.0) -> None:
        super().__init__(message)
        self.delay_s = delay_s


@dataclass
class JobContext:
    db: AsyncSession
    job_id: uuid.UUID
    kind: str
    tenant_id: Optional[uuid.UUID]
    payload: Dict[str, Any]
    attempt: int
    max_attempts: int

    @property
    def is_last_attempt(self) -> bool:
        return self.attempt >= self.max_attempts


def job_handler(kind: str) -> Callable[[HandlerFn], HandlerFn]:
    """Registra o handler de um `kind`. Um kind tem um único handler."""

    def deco(fn: HandlerFn) -> HandlerFn:
        existing = _REGISTRY.get(kind)
        if existing is not None and existing is not fn:
            raise ValueError(f"job kind já registrado: {kind}")
        _REGISTRY[kind] = fn
        return fn

    return deco


def registered_kinds() -> list[str]:
    _load_handler_modules()
    return sorted(_REGISTRY)


def _load_handler_modules() -> None:
    for mod in HANDLER_MODULES:
        importlib.import_module(mod)


# ── RLS: o worker enxerga todos os jobs ─────────────────────────────────────
# A policy de background_jobs libera todas as linhas quando app.job_worker=on.
# set_config(..., true) vale só na transação: reaplicamos a cada BEGIN, como
# deps._reapply_tenant_context faz com o tenant. Nunca é session-level, para
# não vazar o privilégio para uma requisição que pegue a mesma conexão.

@event.listens_for(Session, "after_begin")
def _reapply_worker_flag(session, transaction, connection) -> None:
    if session.info.get("job_worker") and connection.dialect.name == "postgresql":
        connection.execute(text("SELECT set_config('app.job_worker', 'on', true)"))


def _dialect(db: AsyncSession) -> str:
    try:
        return db.get_bind().dialect.name
    except Exception:  # pragma: no cover
        return ""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"


async def _enter_worker_mode(db: AsyncSession) -> None:
    db.info["job_worker"] = True
    if _dialect(db) == "postgresql":
        # A transação corrente pode já ter começado antes da flag.
        await db.execute(text("SELECT set_config('app.job_worker', 'on', true)"))


# ── Enfileirar ──────────────────────────────────────────────────────────────

async def enqueue(
    db: AsyncSession,
    kind: str,
    payload: Dict[str, Any],
    tenant_id: Optional[uuid.UUID],
    idempotency_key: Optional[str] = None,
    run_after: Optional[datetime] = None,
    *,
    max_attempts: int = 3,
    requeue_if_finished: bool = False,
) -> BackgroundJob:
    """Grava o job (flush, sem commit: entra na transação de quem chamou).

    Com `idempotency_key`, um segundo enqueue devolve o job já existente.
    `requeue_if_finished=True` reabre um job com a mesma chave que já terminou
    (done/failed/cancelled), zerando as tentativas — usado pelo varredor de
    notas quando a nota voltou a `queued` depois de um job encerrado.
    """
    now = _utcnow()
    values = dict(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        kind=kind,
        payload=payload or {},
        status="queued",
        attempts=0,
        max_attempts=max_attempts,
        run_after=run_after or now,
        idempotency_key=idempotency_key,
        created_at=now,
        updated_at=now,
    )
    if idempotency_key is None:
        job = BackgroundJob(**values)
        db.add(job)
        await db.flush()
        return job

    dialect = _dialect(db)
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    stmt = dialect_insert(BackgroundJob).values(**values).on_conflict_do_nothing(
        index_elements=["idempotency_key"]
    )
    await db.execute(stmt)
    job = (
        await db.execute(
            select(BackgroundJob)
            .where(BackgroundJob.idempotency_key == idempotency_key)
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if job is None:  # chave usada por linha invisível (outro tenant via RLS)
        raise ValueError(f"idempotency_key em uso: {idempotency_key}")
    if requeue_if_finished and job.status in ("done", "failed", "cancelled"):
        job.status = "queued"
        job.attempts = 0
        job.run_after = run_after or now
        job.locked_at = None
        job.locked_by = None
        job.last_error = None
        job.payload = payload or {}
        job.updated_at = now
        await db.flush()
    return job


# ── Reservar e executar ─────────────────────────────────────────────────────

async def claim_next(db: AsyncSession, worker_id: str) -> Optional[BackgroundJob]:
    """Reserva o próximo job devido (ou abandonado) e o marca `running`.

    Postgres: `FOR UPDATE SKIP LOCKED` — duas execuções simultâneas (tick +
    kick) nunca pegam o mesmo job. SQLite (testes): sem FOR UPDATE.
    """
    await _enter_worker_mode(db)
    while True:
        now = _utcnow()
        stmt = (
            select(BackgroundJob)
            .where(
                or_(
                    and_(BackgroundJob.status == "queued", BackgroundJob.run_after <= now),
                    and_(
                        BackgroundJob.status == "running",
                        BackgroundJob.locked_at < now - STALE_LOCK_AFTER,
                    ),
                )
            )
            .order_by(BackgroundJob.run_after, BackgroundJob.created_at)
            .limit(1)
            .execution_options(populate_existing=True)
        )
        if _dialect(db) == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        job = (await db.execute(stmt)).scalar_one_or_none()
        if job is None:
            await db.commit()
            return None

        if job.status == "running":
            logger.warning(
                "job_abandonado id=%s kind=%s locked_by=%s", job.id, job.kind, job.locked_by
            )
            if job.attempts >= job.max_attempts:
                job.status = "failed"
                job.last_error = (
                    f"Abandonado: a instância parou durante a execução "
                    f"(tentativa {job.attempts}/{job.max_attempts})."
                )
                job.locked_at = None
                job.locked_by = None
                job.updated_at = now
                await db.commit()
                continue

        job.status = "running"
        job.locked_at = now
        job.locked_by = worker_id
        job.attempts = (job.attempts or 0) + 1
        job.updated_at = now
        await db.commit()
        return job


def retry_delay_seconds(attempt: int) -> float:
    """1 min, 5 min, 25 min... (teto de 6 h)."""
    return min(60.0 * (5 ** max(attempt - 1, 0)), 6 * 3600.0)


async def _reload(db: AsyncSession, job_id: uuid.UUID) -> Optional[BackgroundJob]:
    return await db.get(BackgroundJob, job_id, populate_existing=True)


async def _execute(db: AsyncSession, job: BackgroundJob) -> str:
    from app.core.deps import _set_current_tenant_context

    job_id, kind, tenant_id = job.id, job.kind, job.tenant_id
    ctx = JobContext(
        db=db, job_id=job_id, kind=kind, tenant_id=tenant_id,
        payload=dict(job.payload or {}), attempt=job.attempts, max_attempts=job.max_attempts,
    )
    handler = _REGISTRY.get(kind)
    try:
        if handler is None:
            raise PermanentJobError(f"Nenhum handler registrado para '{kind}'")
        if tenant_id is not None:
            await _set_current_tenant_context(db, tenant_id)
        result = await handler(ctx)
        job = await _reload(db, job_id)
        job.status = "done"
        job.result = result
        job.last_error = None
        job.locked_at = None
        job.locked_by = None
        job.updated_at = _utcnow()
        await db.commit()
        return "done"
    except Exception as exc:
        try:
            await db.rollback()
        except Exception:  # pragma: no cover
            pass
        err = f"{type(exc).__name__}: {exc}"[:2000]
        job = await _reload(db, job_id)
        if job is None:  # pragma: no cover - linha apagada no meio
            return "failed"
        now = _utcnow()
        job.last_error = err
        job.locked_at = None
        job.locked_by = None
        job.updated_at = now
        if isinstance(exc, PermanentJobError) or job.attempts >= job.max_attempts:
            job.status = "failed"
            outcome = "failed"
            logger.error("job_falhou id=%s kind=%s erro=%s", job_id, kind, err)
            if not isinstance(exc, (PermanentJobError, JobRetry)):
                logger.debug("traceback job %s:\n%s", job_id, traceback.format_exc())
        else:
            delay = exc.delay_s if isinstance(exc, JobRetry) else retry_delay_seconds(job.attempts)
            job.status = "queued"
            job.run_after = now + timedelta(seconds=delay)
            outcome = "retry"
            logger.warning(
                "job_retry id=%s kind=%s tentativa=%s/%s em=%ss erro=%s",
                job_id, kind, job.attempts, job.max_attempts, int(delay), err,
            )
        await db.commit()
        return outcome
    finally:
        # O próximo job pode ser de outro escritório: nada de contexto herdado.
        db.info.pop("tenant_id", None)


async def run_pending(
    db: AsyncSession,
    max_jobs: int = TICK_MAX_JOBS,
    time_budget_s: float = TICK_TIME_BUDGET_S,
    worker_id: Optional[str] = None,
) -> Dict[str, int]:
    """Executa jobs devidos até `max_jobs` ou até estourar `time_budget_s`."""
    _load_handler_modules()
    worker_id = worker_id or default_worker_id()
    start = time.monotonic()
    counts = {"done": 0, "retry": 0, "failed": 0}
    try:
        while sum(counts.values()) < max_jobs and (time.monotonic() - start) < time_budget_s:
            job = await claim_next(db, worker_id)
            if job is None:
                break
            outcome = await _execute(db, job)
            counts[outcome] = counts.get(outcome, 0) + 1
    finally:
        db.info.pop("job_worker", None)
        db.info.pop("tenant_id", None)
    if any(counts.values()):
        logger.info("job_queue worker=%s %s", worker_id, counts)
    return counts


# ── Disparo sem worker ──────────────────────────────────────────────────────

async def _kick_run(max_jobs: int, time_budget_s: float) -> None:
    from app.core.deps import get_sessionmaker

    try:
        async with get_sessionmaker()() as db:
            await run_pending(db, max_jobs=max_jobs, time_budget_s=time_budget_s)
    except Exception as exc:  # best-effort: o tick retoma
        logger.warning("job_queue kick falhou (o tick retoma): %s", exc)


def kick(max_jobs: int = KICK_MAX_JOBS, time_budget_s: float = KICK_TIME_BUDGET_S) -> None:
    """Depois do commit de um enqueue: tenta processar já, numa task própria.

    Best-effort: no Cloud Run a CPU pode ser reduzida depois da resposta e a
    instância pode morrer. O job continua na tabela e o tick horário o executa.
    """
    if not KICK_ENABLED:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(_kick_run(max_jobs, time_budget_s))
    _background_tasks.add(task)  # referência forte: evita a task ser coletada
    task.add_done_callback(_background_tasks.discard)


async def run_tick(time_budget_s: float = TICK_TIME_BUDGET_S) -> Dict[str, Any]:
    """Rotina horária: varre notas em `queued` e processa a fila."""
    from app.core.deps import get_sessionmaker

    _load_handler_modules()
    out: Dict[str, Any] = {}
    async with get_sessionmaker()() as db:
        from app.services.job_handlers import drain_queued_invoices

        try:
            out["invoices_enqueued"] = await drain_queued_invoices(db)
        except Exception as exc:
            logger.error("varredor de notas falhou: %s", exc, exc_info=True)
            await db.rollback()
            out["invoices_enqueued"] = "error"
        out["jobs"] = await run_pending(db, time_budget_s=time_budget_s)
    return out
