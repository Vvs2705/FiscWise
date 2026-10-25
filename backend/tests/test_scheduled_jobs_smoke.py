"""As rotinas agendadas engolem exceções e só logam: este teste falha se alguma
delas logar erro numa base com um escritório e um cliente (pegou o DB-15)."""

import logging
from decimal import Decimal

import pytest

from app.services import scheduler


@pytest.mark.parametrize(
    "job",
    [
        "generate_monthly_billing_scheduled",
        "generate_obligations_scheduled",
        "notify_pending_documents_scheduled",
        "send_payment_reminders_scheduled",
    ],
)
async def test_rotina_roda_sem_erro(job, test_db, client_a, caplog):
    client_a.monthly_fee = Decimal("100.00")
    await test_db.commit()
    with caplog.at_level(logging.ERROR, logger="app.services.scheduler"):
        await getattr(scheduler, job)()
    erros = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert not erros, erros
