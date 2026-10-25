"""Scheduler: fuso de Brasília e jobs de negócio só onde RUN_SCHEDULER=true (DB-2, DB-6)."""

import pytest

from app.core.config import settings
from app.services import scheduler as sched

BUSINESS = {
    "generate_monthly_billing",
    "generate_obligations",
    "notify_pending_documents",
    "send_payment_reminders",
}


@pytest.fixture
async def fresh_scheduler():
    sched.scheduler = None
    yield
    await sched.stop_scheduler()
    sched.scheduler = None


async def _job_ids():
    await sched.start_scheduler()
    return {j.id: j for j in sched.scheduler.get_jobs()}


async def test_run_scheduler_false_so_limpa_rate_limiter(fresh_scheduler, monkeypatch):
    monkeypatch.setattr(settings, "RUN_SCHEDULER", False)
    assert set(await _job_ids()) == {"cleanup_auth_rate_limiter"}


async def test_jobs_de_negocio_no_fuso_de_brasilia(fresh_scheduler, monkeypatch):
    monkeypatch.setattr(settings, "RUN_SCHEDULER", True)
    jobs = await _job_ids()
    assert BUSINESS <= set(jobs)
    for job_id in BUSINESS:
        assert str(jobs[job_id].trigger.timezone) == "America/Sao_Paulo"
