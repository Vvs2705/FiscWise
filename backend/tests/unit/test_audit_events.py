import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.audit import AuditEvent
from app.services.audit import log_audit_event


@pytest.mark.asyncio
async def test_log_audit_event_success(test_db: AsyncSession):
    """Verify that log_audit_event correctly persists audit logs to the database."""
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    
    event = await log_audit_event(
        db=test_db,
        tenant_id=tenant_id,
        action="client.create",
        entity_type="client",
        actor_user_id=actor_id,
        actor_role="owner",
        entity_id=entity_id,
        before_data=None,
        after_data={"name": "New Test Client", "status": "active"},
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    )
    
    assert event is not None
    assert event.id is not None
    assert event.action == "client.create"
    assert event.tenant_id == tenant_id
    assert event.actor_user_id == actor_id
    assert event.actor_role == "owner"
    assert event.entity_id == entity_id
    assert event.after_data == {"name": "New Test Client", "status": "active"}
    assert event.ip_address == "127.0.0.1"
    assert event.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    
    # Query database to verify persistence
    result = await test_db.execute(select(AuditEvent).where(AuditEvent.id == event.id))
    db_event = result.scalar_one_or_none()
    assert db_event is not None
    assert db_event.id == event.id
    assert db_event.action == "client.create"
    assert db_event.tenant_id == tenant_id
    assert db_event.actor_user_id == actor_id
