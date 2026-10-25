"""Auditoria dos domínios (guias, notas, fechamento, e-CAC, caixa postal, scheduler).

Grava em `audit_events` numa sessão própria: o evento persiste mesmo que a
transação de quem chamou ainda esteja aberta, e uma falha ao auditar nunca
derruba a operação de negócio (só vai para o log).
"""

import json
import logging
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def audit_log(
    action: str,
    tenant_id: Any,
    details: Optional[dict] = None,
    entity_type: Optional[str] = None,
) -> None:
    from app.core.deps import get_sessionmaker
    from app.services.audit import log_audit_event

    try:
        async with get_sessionmaker()() as db:
            await log_audit_event(
                db,
                tenant_id=uuid.UUID(str(tenant_id)),
                action=action,
                entity_type=entity_type or action.split(".")[0],
                # default=str: Decimal/date/UUID dos domínios viram texto no JSON.
                after_data=json.loads(json.dumps(details, default=str)) if details else None,
            )
    except Exception:
        logger.exception("audit_log falhou: action=%s tenant=%s", action, tenant_id)
