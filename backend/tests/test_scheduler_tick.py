"""Tick externo do agendador (Cloud Scheduler → POST /api/v1/internal/tick)."""

from datetime import datetime

import pytest
import pytz

from app.core.config import settings
from app.services import scheduler


def _utc(*args):
    return datetime(*args, tzinfo=pytz.UTC)


@pytest.mark.parametrize(
    "now, expected",
    [
        # Horários de negócio em Brasília (UTC-3): 02h BRT = 05h UTC.
        # 1º do mês, 02h: cobrança mensal + limpeza
        (_utc(2026, 11, 1, 5, 0), {"generate_monthly_billing", "cleanup_auth_rate_limiter"}),
        # 1º do mês, 03h17 (tick atrasado ainda pega a hora): obrigações
        (_utc(2026, 11, 1, 6, 17), {"generate_obligations", "cleanup_auth_rate_limiter"}),
        # segunda-feira 09h: documentos pendentes
        (_utc(2026, 11, 2, 12, 0), {"notify_pending_documents", "cleanup_auth_rate_limiter"}),
        # todo dia 08h: lembretes de pagamento
        (_utc(2026, 11, 4, 11, 0), {"send_payment_reminders", "cleanup_auth_rate_limiter"}),
        # hora comum: só a limpeza
        (_utc(2026, 11, 4, 15, 0), {"cleanup_auth_rate_limiter"}),
    ],
)
def test_due_job_ids_matches_cron_definitions(now, expected):
    assert set(scheduler.due_job_ids(now)) == expected


def test_due_job_ids_treats_naive_datetime_as_utc():
    assert "send_payment_reminders" in scheduler.due_job_ids(datetime(2026, 11, 4, 11, 30))


@pytest.mark.asyncio
async def test_run_due_jobs_runs_only_due_jobs_and_survives_errors(monkeypatch):
    calls = []

    async def ok():
        calls.append("ok")

    async def boom():
        raise RuntimeError("falhou")

    original = scheduler._job_definitions

    def fake_definitions():
        funcs = {"send_payment_reminders": boom, "cleanup_auth_rate_limiter": ok}
        return [
            (job_id, name, funcs.get(job_id, ok), trigger)
            for job_id, name, _func, trigger in original()
        ]

    monkeypatch.setattr(scheduler, "_job_definitions", fake_definitions)

    result = await scheduler.run_due_jobs(_utc(2026, 11, 4, 11, 0))

    assert result["jobs"] == {"send_payment_reminders": "error", "cleanup_auth_rate_limiter": "ok"}
    assert calls == ["ok"]


def test_tick_is_hidden_when_cron_secret_not_set(client, monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "")
    response = client.post("/api/v1/internal/tick", headers={"X-Cron-Secret": "x"})
    assert response.status_code == 404


def test_tick_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "s3cr3t-de-teste")
    assert client.post("/api/v1/internal/tick").status_code == 401
    response = client.post("/api/v1/internal/tick", headers={"X-Cron-Secret": "errado"})
    assert response.status_code == 401


def test_tick_runs_due_jobs_with_valid_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "s3cr3t-de-teste")

    async def fake_run_due_jobs():
        return {"at": "2026-11-04T08:00:00+00:00", "jobs": {"cleanup_auth_rate_limiter": "ok"}}

    from app.api.v1.endpoints import internal

    monkeypatch.setattr(internal, "run_due_jobs", fake_run_due_jobs)

    response = client.post("/api/v1/internal/tick", headers={"X-Cron-Secret": "s3cr3t-de-teste"})

    assert response.status_code == 200
    assert response.json()["jobs"] == {"cleanup_auth_rate_limiter": "ok"}


@pytest.mark.asyncio
async def test_external_mode_does_not_start_apscheduler(monkeypatch):
    monkeypatch.setattr(settings, "SCHEDULER_MODE", "external")
    monkeypatch.setattr(scheduler, "scheduler", None)

    await scheduler.start_scheduler()

    assert scheduler.scheduler is None
