"""Background Task Scheduler for FiscWise

Manages scheduled tasks like automatic monthly billing generation.
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)

# Competência, "dia 1" e D-n são datas de Brasília: em UTC o job do dia 1
# às 02:00 caía às 23:00 do último dia do mês anterior.
TZ_BR = pytz.timezone("America/Sao_Paulo")

# Rotina que vale em toda máquina (memória do próprio processo).
_PER_PROCESS_JOBS = {"cleanup_auth_rate_limiter"}

scheduler: AsyncIOScheduler = None


def init_scheduler():
    """Initialize the APScheduler instance."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone=pytz.UTC)


def _job_definitions():
    """Rotinas agendadas (fonte única para os dois modos de execução).

    Horários de negócio no fuso de Brasília. Usado pelo APScheduler (SCHEDULER_MODE=internal) e pelo
    tick externo do Cloud Scheduler (SCHEDULER_MODE=external).
    """
    return [
        # Monthly billing generation on the 1st of each month at 2:00 (Brasília)
        ("generate_monthly_billing", "Generate Monthly Billing",
         generate_monthly_billing_scheduled,
         CronTrigger(day=1, hour=2, minute=0, timezone=TZ_BR)),
        # Obligation engine on the 1st of each month at 3:00 (Brasília)
        # Runs after billing (2:00 AM) to avoid DB contention
        ("generate_obligations", "Generate Monthly Fiscal Obligations",
         generate_obligations_scheduled,
         CronTrigger(day=1, hour=3, minute=0, timezone=TZ_BR)),
        # Weekly document pending notifications — every Monday at 09:00 (Brasília)
        ("notify_pending_documents", "Weekly Pending Document Notifications",
         notify_pending_documents_scheduled,
         CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=TZ_BR)),
        # Limpa entradas expiradas do rate limiter a cada hora (evita memory leak)
        ("cleanup_auth_rate_limiter", "Auth Rate Limiter Cleanup",
         cleanup_auth_rate_limiter,
         CronTrigger(minute=0, timezone=pytz.UTC)),
        # Payment reminders daily at 8:00 (Brasília)
        ("send_payment_reminders", "Send Payment Reminders",
         send_payment_reminders_scheduled,
         CronTrigger(hour=8, minute=0, timezone=TZ_BR)),
    ]


async def start_scheduler():
    """Start the in-process scheduler (SCHEDULER_MODE=internal only).

    Em SCHEDULER_MODE=external (Cloud Run com scale-to-zero) o processo pode
    ser desligado a qualquer momento, então as rotinas são disparadas pelo
    Cloud Scheduler via POST /api/v1/internal/tick (ver run_due_jobs).
    """
    from app.core.config import settings

    if settings.SCHEDULER_MODE == "external":
        logger.info("SCHEDULER_MODE=external — APScheduler desligado; rotinas via /api/v1/internal/tick")
        return

    init_scheduler()

    # RUN_SCHEDULER=false (modo internal com 2+ máquinas): só a limpeza local roda
    # aqui, senão cobrança e lembretes saem em dobro.
    if not settings.RUN_SCHEDULER:
        logger.info("RUN_SCHEDULER=false: jobs de negócio desligados nesta máquina")
    for job_id, name, func, trigger in _job_definitions():
        if not settings.RUN_SCHEDULER and job_id not in _PER_PROCESS_JOBS:
            continue
        scheduler.add_job(func, trigger, id=job_id, name=name, replace_existing=True)

    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started successfully")


def due_job_ids(now: datetime) -> list[str]:
    """IDs das rotinas cujo horário cai na hora cheia de `now` (UTC)."""
    if now.tzinfo is None:
        now = pytz.UTC.localize(now)
    window_start = now.astimezone(pytz.UTC).replace(minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(hours=1)
    due = []
    for job_id, _name, _func, trigger in _job_definitions():
        next_fire = trigger.get_next_fire_time(None, window_start)
        if next_fire is not None and next_fire < window_end:
            due.append(job_id)
    return due


async def run_due_jobs(now: datetime | None = None) -> dict:
    """Executa, em sequência, as rotinas devidas nesta hora.

    Chamado de hora em hora pelo Cloud Scheduler. Roda dentro da requisição
    (e não em background) porque no Cloud Run a CPU só fica alocada enquanto
    a requisição está aberta.
    """
    now = now or datetime.now(pytz.UTC)
    due = set(due_job_ids(now))
    results: dict[str, str] = {}
    for job_id, _name, func, _trigger in _job_definitions():
        if job_id not in due:
            continue
        try:
            await func()
            results[job_id] = "ok"
        except Exception as exc:  # each job already logs; never abort the tick
            logger.error("Scheduled job %s failed: %s", job_id, exc, exc_info=True)
            results[job_id] = "error"
    logger.info("Scheduler tick at %s ran: %s", now.isoformat(), results or "nothing due")
    return {"at": now.isoformat(), "jobs": results}


async def generate_obligations_scheduled():
    """
    Scheduled task to generate monthly fiscal obligations.
    Runs on the 1st of each month at 3:00 (Brasília).
    """
    from app.core.deps import get_sessionmaker
    from app.services.obligation_engine import generate_obligations_for_month

    try:
        now = datetime.now(TZ_BR)
        # Generate for PREVIOUS month (we're on day 1 of the new month)
        if now.month == 1:
            year, month = now.year - 1, 12
        else:
            year, month = now.year, now.month - 1

        async_session = get_sessionmaker()
        async with async_session() as db:
            summary = await generate_obligations_for_month(db, year, month)
            logger.info(
                f"Obligation generation scheduled task completed: {summary}"
            )
    except Exception as e:
        logger.error(f"Error in scheduled obligation generation: {str(e)}")


async def notify_pending_documents_scheduled():
    """
    Weekly scheduled task: send pending document notifications to clients.
    Runs every Monday at 09:00 AM UTC.
    """
    from app.core.deps import get_sessionmaker
    from app.services.notification_engine import notify_pending_documents_all_tenants

    try:
        async_session = get_sessionmaker()
        async with async_session() as db:
            summary = await notify_pending_documents_all_tenants(db)
            logger.info("Weekly document notification job completed: %s", summary)
    except Exception as exc:
        logger.error("Error in weekly document notification job: %s", exc, exc_info=True)


async def stop_scheduler():
    """Stop the scheduler."""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


async def cleanup_auth_rate_limiter():
    """
    Remove entradas expiradas do rate limiter de autenticação.
    Roda a cada hora para evitar memory leak em deploys long-running.
    """
    from app.core.auth_rate_limiter import auth_rate_limiter
    removed = auth_rate_limiter.cleanup_expired()
    if removed:
        logger.info("Auth rate limiter cleanup: %d entradas removidas", removed)


async def generate_monthly_billing_scheduled():
    """
    Scheduled task to generate monthly billing.
    Runs on the 1st of each month.
    """
    from sqlalchemy import select, and_
    import calendar

    from app.core.deps import _set_current_tenant_context, get_sessionmaker
    from app.models.operations import AccountingClient, AccountReceivable
    from app.models.tenant import Tenant

    try:
        # Get shared database sessionmaker
        async_session = get_sessionmaker()

        async with async_session() as db:
            # Get current month
            now = datetime.now(TZ_BR)
            year, month = now.year, now.month

            # Get all tenants
            result = await db.execute(select(Tenant).where(Tenant.is_active == True))
            tenants = result.scalars().all()

            total_created = 0
            total_skipped = 0

            for tenant in tenants:
                await _set_current_tenant_context(db, tenant.id)

                # Find clients with monthly_fee > 0
                stmt = select(AccountingClient).where(
                    and_(
                        AccountingClient.tenant_id == tenant.id,
                        AccountingClient.monthly_fee > 0,
                        AccountingClient.status == "active"
                    )
                )
                result = await db.execute(stmt)
                clients = result.scalars().all()

                for client in clients:
                    # Check if invoice already exists for this month
                    existing = await db.execute(
                        select(AccountReceivable).where(
                            and_(
                                AccountReceivable.tenant_id == tenant.id,
                                AccountReceivable.client_id == client.id,
                                AccountReceivable.description.like(
                                    f"Honorários - {year:04d}-{month:02d}%"
                                )
                            )
                        )
                    )

                    if existing.scalar_one_or_none():
                        total_skipped += 1
                        continue

                    # Calculate due date
                    from datetime import date
                    max_day = calendar.monthrange(year, month)[1]
                    due_day = min(client.billing_day, max_day)
                    due_date = date(year, month, due_day)

                    # Create receivable
                    receivable = AccountReceivable(
                        tenant_id=tenant.id,
                        client_id=client.id,
                        description=f"Honorários - {year:04d}-{month:02d}",
                        amount=client.monthly_fee,
                        due_date=due_date,
                        status="pending",
                    )
                    db.add(receivable)
                    total_created += 1

                await db.commit()

            logger.info(
                f"Monthly billing scheduled task completed: "
                f"created={total_created}, skipped={total_skipped}"
            )

    except Exception as e:
        logger.error(f"Error in scheduled monthly billing generation: {str(e)}")


async def send_payment_reminders_scheduled():
    """
    Check receivables matching offsets (D-7, D-3, D0, D+1, D+3, D+7)
    and emit a 'payment.reminder' event for each.
    """
    from datetime import date, timedelta
    from sqlalchemy import select, and_
    from app.core.deps import get_sessionmaker
    from app.models.operations import AccountReceivable
    from app.core.audit import audit_log

    try:
        async_session = get_sessionmaker()
        async with async_session() as db:
            today = datetime.now(TZ_BR).date()
            target_dates = [
                today + timedelta(days=7),   # D-7
                today + timedelta(days=3),   # D-3
                today,                       # D0
                today - timedelta(days=1),   # D+1
                today - timedelta(days=3),   # D+3
                today - timedelta(days=7),   # D+7
            ]

            stmt = select(AccountReceivable).where(
                and_(
                    AccountReceivable.status != "paid",
                    AccountReceivable.status != "cancelled",
                    AccountReceivable.due_date.in_(target_dates)
                )
            )
            result = await db.execute(stmt)
            receivables = result.scalars().all()

            # ponytail: ainda não envia nada ao cliente; só registra o evento
            # payment.reminder em audit_events. Envio real fica para o
            # notification_engine quando houver e-mail/WhatsApp de produção.
            reminders_logged = 0
            for receivable in receivables:
                await audit_log(
                    action="payment.reminder",
                    tenant_id=str(receivable.tenant_id),
                    details={
                        "receivable_id": str(receivable.id),
                        "client_id": str(receivable.client_id),
                        "amount": str(receivable.amount),
                        "due_date": receivable.due_date.isoformat(),
                        "status": receivable.status,
                    }
                )
                reminders_logged += 1

            logger.info(
                f"Payment reminders scheduled task completed: "
                f"{reminders_logged} lembretes registrados (envio ao cliente não implementado)."
            )
    except Exception as e:
        logger.error(f"Error in scheduled payment reminders: {str(e)}")
