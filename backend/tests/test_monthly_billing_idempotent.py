"""Cobrança mensal rodando duas vezes não duplica honorário (DB-5)."""

from decimal import Decimal

from sqlalchemy import select

from app.models.operations import AccountReceivable
from app.services.scheduler import generate_monthly_billing_scheduled


async def test_cobranca_mensal_idempotente(test_db, client_a):
    client_a.monthly_fee = Decimal("300.00")
    client_a.billing_day = 10
    await test_db.commit()

    await generate_monthly_billing_scheduled()
    await generate_monthly_billing_scheduled()

    rows = (await test_db.execute(select(AccountReceivable).where(AccountReceivable.client_id == client_a.id))).scalars().all()
    assert len(rows) == 1
    assert rows[0].competence and rows[0].description.endswith(rows[0].competence)
