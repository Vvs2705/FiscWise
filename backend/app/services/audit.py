"""Service for logging and querying audit events."""

import uuid
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.core.deps import _set_current_tenant_context

logger = logging.getLogger(__name__)


async def log_audit_event(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    action: str,
    entity_type: str,
    actor_user_id: Optional[uuid.UUID] = None,
    actor_role: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    before_data: Optional[dict] = None,
    after_data: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[AuditEvent]:
    """
    Create and persist a new audit event.
    
    This function commits the event to the database. It handles potential
    database errors gracefully, logging the failure without breaking the parent transaction.
    """
    try:
        await _set_current_tenant_context(db, tenant_id)

        event = AuditEvent(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_data=before_data,
            after_data=after_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        logger.info(
            "Audit event logged: action=%s, tenant_id=%s, actor=%s",
            action,
            tenant_id,
            actor_user_id,
        )
        return event
    except Exception as e:
        logger.error("Failed to persist audit event: %s", str(e), exc_info=True)
        # Rollback to keep session valid
        try:
            await db.rollback()
        except Exception:
            pass
        return None
