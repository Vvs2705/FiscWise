"""Background Task Scheduler for FiscWise

Manages scheduled tasks like automatic monthly billing generation.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler = None


def init_scheduler():
    """Initialize the APScheduler instance."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone=pytz.UTC)


async def start_scheduler():
    """Start the scheduler."""
    init_scheduler()

    # Schedule monthly billing generation on the 1st of each month at 2:00 AM UTC
    scheduler.add_job(
        generate_monthly_billing_scheduled,
        CronTrigger(day=1, hour=2, minute=0),
        id="generate_monthly_billing",
        name="Generate Monthly Billing",
        replace_existing=True,
    )

    # Schedule obligation engine on the 1st of each month at 3:00 AM UTC
    # Runs after billing (2:00 AM) to avoid DB contention
    scheduler.add_job(
        generate_obligations_scheduled,
        CronTrigger(day=1, hour=3, minute=0),
        id="generate_obligations",
        name="Generate Monthly Fiscal Obligations",
        replace_existing=True,
    )

    # Schedule weekly document pending notifications — every Monday at 09:00 AM UTC
    scheduler.add_job(
        notify_pending_documents_scheduled,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="notify_pending_documents",
        name="Weekly Pending Document Notifications",
        replace_existing=True,
    )

    # Limpa entradas expiradas do rate limiter a cada hora (evita memory leak)
    scheduler.add_job(
        cleanup_auth_rate_limiter,
        CronTrigger(minute=0),  # todo hora cheia
        id="cleanup_auth_rate_limiter",
        name="Auth Rate Limiter Cleanup",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started successfully")


async def generate_obligations_scheduled():
    """
    Scheduled task to generate monthly fiscal obligations.
    Runs on the 1st of each month at 3:00 AM UTC.
    """
    from app.core.deps import get_sessionmaker
    from app.services.obligation_engine import generate_obligations_for_month

    try:
        now = datetime.utcnow()
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
            now = datetime.utcnow()
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
