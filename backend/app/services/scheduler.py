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

    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started successfully")


async def stop_scheduler():
    """Stop the scheduler."""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


async def generate_monthly_billing_scheduled():
    """
    Scheduled task to generate monthly billing.
    Runs on the 1st of each month.
    """
    from sqlalchemy import select, and_
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    import calendar

    from app.core.config import settings
    from app.models.operations import AccountingClient, AccountReceivable
    from app.models.tenant import Tenant

    try:
        # Create database connection
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

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

        await engine.dispose()

    except Exception as e:
        logger.error(f"Error in scheduled monthly billing generation: {str(e)}")
