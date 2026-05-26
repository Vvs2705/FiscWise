"""Request-aware audit helper for FiscWise endpoints.

Thin wrapper around app.services.audit that extracts IP and User-Agent
from a FastAPI Request object so endpoint code doesn't need to do it manually.

Usage in endpoints:
    from app.core.audit import audit_request

    await audit_request(
        db=db,
        request=request,
        user=current_user,
        action="document.uploaded",
        entity_type="document",
        entity_id=doc.id,
    )
"""

import uuid
from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit import log_audit_event
from app.models.audit import AuditEvent


def _extract_ip(request: Request) -> Optional[str]:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def audit_request(
    db: AsyncSession,
    request: Request,
    tenant_id: uuid.UUID,
    action: str,
    entity_type: str,
    actor_user_id: Optional[uuid.UUID] = None,
    actor_role: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    before_data: Optional[dict] = None,
    after_data: Optional[dict] = None,
) -> Optional[AuditEvent]:
    """Record an audit event extracting IP/UA from the FastAPI Request."""
    return await log_audit_event(
        db=db,
        tenant_id=tenant_id,
        action=action,
        entity_type=entity_type,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        entity_id=entity_id,
        before_data=before_data,
        after_data=after_data,
        ip_address=_extract_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
