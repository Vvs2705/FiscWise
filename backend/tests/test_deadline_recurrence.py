import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.operations import DeadlineItem
from app.schemas.operations import DeadlineCreate, DeadlineUpdate


class TestDeadlineRecurrence:
    """Tests for Custom Deadline Recurrence (auto-spawning next instance on completion)."""

    @pytest.mark.asyncio
    async def test_create_recurring_deadline(self, client_with_auth_a):
        """POST /api/v1/deadlines with recurrence fields."""
        client, _, existing_client, _ = client_with_auth_a

        due = (date.today() + timedelta(days=5)).isoformat()
        payload = DeadlineCreate(
            client_id=existing_client.id,
            title="Relatório Mensal de Impostos",
            category="fiscal",
            due_date=due,
            status="pending",
            priority="medium",
            is_recurring=True,
            recurrence_interval="monthly"
        )

        response = client.post("/api/v1/deadlines", json=payload.model_dump(mode="json"))

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Relatório Mensal de Impostos"
        assert data["is_recurring"] is True
        assert data["recurrence_interval"] == "monthly"
        assert data["recurrence_parent_id"] is None

    @pytest.mark.asyncio
    async def test_complete_recurring_deadline_monthly(self, client_with_auth_a):
        """PATCH /api/v1/deadlines/{id} with status=completed spawns next monthly instance."""
        client, _, existing_client, test_db = client_with_auth_a

        # 1. Create a recurring deadline with due_date = 2026-03-31
        start_due = date(2026, 3, 31)
        deadline = DeadlineItem(
            id=uuid.uuid4(),
            tenant_id=existing_client.tenant_id,
            client_id=existing_client.id,
            title="Rotina de Fechamento",
            category="contabil",
            due_date=start_due,
            status="pending",
            priority="medium",
            is_recurring=True,
            recurrence_interval="monthly"
        )
        test_db.add(deadline)
        await test_db.commit()
        await test_db.refresh(deadline)

        # 2. Mark it completed
        payload = DeadlineUpdate(status="completed")
        response = client.patch(
            f"/api/v1/deadlines/{deadline.id}",
            json=payload.model_dump(exclude_unset=True),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

        # 3. Retrieve all deadlines for this client from DB
        stmt = select(DeadlineItem).where(DeadlineItem.client_id == existing_client.id).order_by(DeadlineItem.due_date.asc())
        result = await test_db.execute(stmt)
        deadlines = result.scalars().all()

        assert len(deadlines) == 2
        
        # Original deadline
        d1 = deadlines[0]
        assert d1.id == deadline.id
        assert d1.status == "completed"

        # Spawned deadline
        d2 = deadlines[1]
        assert d2.id != deadline.id
        assert d2.title == "Rotina de Fechamento"
        assert d2.category == "contabil"
        # 31 of March + 1 month = 30 of April (handling end-of-month overflow correctly)
        assert d2.due_date == date(2026, 4, 30)
        assert d2.status == "pending"
        assert d2.is_recurring is True
        assert d2.recurrence_interval == "monthly"
        assert d2.recurrence_parent_id == deadline.id
        assert d2.tenant_id == existing_client.tenant_id

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "interval,start_date,expected_date",
        [
            ("weekly", date(2026, 5, 10), date(2026, 5, 17)),
            ("monthly", date(2026, 1, 31), date(2026, 2, 28)),  # Leap year check (2026 is non-leap, so 28)
            ("monthly", date(2024, 1, 31), date(2024, 2, 29)),  # 2024 is leap year, so 29
            ("quarterly", date(2026, 10, 31), date(2027, 1, 31)),
            ("yearly", date(2024, 2, 29), date(2025, 2, 28)),   # Feb 29 to next year Feb 28
        ]
    )
    async def test_recurrence_intervals(self, client_with_auth_a, interval, start_date, expected_date):
        """Test calculation of next due dates for all intervals."""
        client, _, existing_client, test_db = client_with_auth_a

        deadline = DeadlineItem(
            id=uuid.uuid4(),
            tenant_id=existing_client.tenant_id,
            client_id=existing_client.id,
            title=f"Test {interval}",
            category="fiscal",
            due_date=start_date,
            status="pending",
            priority="medium",
            is_recurring=True,
            recurrence_interval=interval
        )
        test_db.add(deadline)
        await test_db.commit()
        await test_db.refresh(deadline)

        payload = DeadlineUpdate(status="completed")
        response = client.patch(
            f"/api/v1/deadlines/{deadline.id}",
            json=payload.model_dump(exclude_unset=True),
        )
        assert response.status_code == 200

        # Fetch the spawned child from DB
        stmt = select(DeadlineItem).where(DeadlineItem.recurrence_parent_id == deadline.id)
        result = await test_db.execute(stmt)
        child = result.scalar_one_or_none()

        assert child is not None
        assert child.due_date == expected_date
        assert child.status == "pending"
        assert child.tenant_id == existing_client.tenant_id

    @pytest.mark.asyncio
    async def test_non_recurring_deadline_no_spawn(self, client_with_auth_a):
        """Completing a non-recurring deadline does NOT spawn a new instance."""
        client, _, existing_client, test_db = client_with_auth_a

        deadline = DeadlineItem(
            id=uuid.uuid4(),
            tenant_id=existing_client.tenant_id,
            client_id=existing_client.id,
            title="Non-recurring",
            category="fiscal",
            due_date=date.today(),
            status="pending",
            priority="medium",
            is_recurring=False
        )
        test_db.add(deadline)
        await test_db.commit()

        payload = DeadlineUpdate(status="completed")
        response = client.patch(
            f"/api/v1/deadlines/{deadline.id}",
            json=payload.model_dump(exclude_unset=True),
        )
        assert response.status_code == 200

        # Verify no child was spawned
        stmt = select(DeadlineItem).where(DeadlineItem.recurrence_parent_id == deadline.id)
        result = await test_db.execute(stmt)
        assert result.scalar_one_or_none() is None
