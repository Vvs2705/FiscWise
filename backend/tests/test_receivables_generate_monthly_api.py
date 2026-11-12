"""POST /receivables/generate-monthly — usado pelo botão "Gerar mensalidades do mês"."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.operations import AccountingClient, AccountReceivable

pytestmark = pytest.mark.integration

YM = "2026-09"


async def _client_with_fee(db, tenant_id, name="Cliente Honorário", fee="450.00", day=10):
    c = AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant_id, name=name, entity_type="pj",
        status="active", monthly_fee=Decimal(fee), billing_day=day,
    )
    db.add(c)
    await db.commit()
    return c


async def test_generate_monthly_is_idempotent(client_with_auth_a):
    http, user, _, db = client_with_auth_a
    c = await _client_with_fee(db, user.tenant_id)

    first = http.post("/api/v1/receivables/generate-monthly", params={"year_month": YM})
    assert first.status_code == 200, first.text
    assert first.json()["created"] >= 1

    second = http.post("/api/v1/receivables/generate-monthly", params={"year_month": YM})
    assert second.status_code == 200
    assert second.json()["created"] == 0
    assert second.json()["skipped_duplicates"] == first.json()["created"]

    rows = (await db.execute(
        select(AccountReceivable).where(AccountReceivable.client_id == c.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].due_date == date(2026, 9, 10)
    assert rows[0].amount == Decimal("450.00")


async def test_generate_monthly_with_two_existing_invoices_does_not_500(client_with_auth_a):
    http, user, _, db = client_with_auth_a
    c = await _client_with_fee(db, user.tenant_id, name="Com ajuste")
    for desc in (f"Honorários - {YM}", f"Honorários - {YM} (ajuste)"):
        db.add(AccountReceivable(
            id=uuid.uuid4(), tenant_id=user.tenant_id, client_id=c.id,
            description=desc, amount=Decimal("10.00"), due_date=date(2026, 9, 5), status="pending",
        ))
    await db.commit()

    resp = http.post("/api/v1/receivables/generate-monthly", params={"year_month": YM})
    assert resp.status_code == 200, resp.text
    assert resp.json()["skipped_duplicates"] >= 1


async def test_generate_monthly_rejects_bad_format(client_with_auth_a):
    http, *_ = client_with_auth_a
    assert http.post("/api/v1/receivables/generate-monthly", params={"year_month": "09/2026"}).status_code == 422
