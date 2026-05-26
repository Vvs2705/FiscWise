import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from fastapi import status
from app.models.operations import AccountReceivable, AccountingClient
from app.models.tenant import Tenant
from app.services.scheduler import send_payment_reminders_scheduled

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_delinquency_report(client_with_auth_a, test_db):
    http_client, user, client, db = client_with_auth_a
    tenant_id = user.tenant_id

    # 1. Create an overdue receivable
    past_due_date = date.today() - timedelta(days=5)
    rec1 = AccountReceivable(
        tenant_id=tenant_id,
        client_id=client.id,
        description="Honorários - 2026-05",
        amount=Decimal("350.00"),
        due_date=past_due_date,
        status="pending"
    )
    db.add(rec1)
    await db.commit()

    # 2. Query /api/v1/financeiro/inadimplencia
    response = http_client.get("/api/v1/financeiro/inadimplencia")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_clients"] >= 1
    assert data["total_overdue_count"] >= 1
    
    # Find client in report
    matched = [c for c in data["clients"] if c["client_id"] == str(client.id)]
    assert len(matched) == 1
    assert matched[0]["client_name"] == client.name
    assert Decimal(matched[0]["overdue_total"]) == Decimal("350.00")

@pytest.mark.asyncio
async def test_payment_reminder_scheduled_job(test_db):
    tenant_id = uuid.uuid4()
    
    tenant = Tenant(id=tenant_id, name="Test Tenant")
    test_db.add(tenant)
    await test_db.commit()

    client = AccountingClient(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Test Remindee Client",
        document="10000000000145",
        status="active"
    )
    test_db.add(client)
    await test_db.commit()

    # Create due date exactly today (D0)
    rec = AccountReceivable(
        tenant_id=tenant_id,
        client_id=client.id,
        description="Honorários - Remind",
        amount=Decimal("150.00"),
        due_date=date.today(),
        status="pending"
    )
    test_db.add(rec)
    await test_db.commit()

    # Trigger scheduler task manually
    await send_payment_reminders_scheduled()
