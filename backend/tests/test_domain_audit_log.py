"""audit_log dos domínios grava em audit_events (antes era stub que só logava — DB-1)."""

from decimal import Decimal

from sqlalchemy import select

from app.core.audit import audit_log
from app.models.audit import AuditEvent


async def test_audit_log_persiste_evento(test_db, tenant_a):
    await audit_log(
        action="guide.paid",
        tenant_id=str(tenant_a.id),
        details={"valor": Decimal("123.45")},
    )
    eventos = (await test_db.execute(select(AuditEvent))).scalars().all()
    assert len(eventos) == 1
    assert eventos[0].action == "guide.paid"
    assert eventos[0].entity_type == "guide"
    assert eventos[0].tenant_id == tenant_a.id
    assert eventos[0].after_data == {"valor": "123.45"}


async def test_audit_log_nao_derruba_quem_chama(tenant_a):
    await audit_log(action="x.y", tenant_id="nao-e-uuid")
