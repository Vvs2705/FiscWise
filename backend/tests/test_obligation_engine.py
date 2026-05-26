import pytest
from datetime import date
from sqlalchemy import select
from app.services.obligation_engine import generate_obligations_for_month
from app.models.obligation import ObligationInstance, ObligationRule
from app.models.operations import AccountingClient
from app.models.tenant import Tenant

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_obligation_engine_dynamic_generation(client_with_auth_a, test_db):
    http_client, user, client, db = client_with_auth_a
    tenant_id = user.tenant_id

    # Configure client's profile fields
    client.regime_tributario = "simples_nacional"
    client.tem_funcionarios = True
    client.municipio_ibge = "3550308"  # São Paulo
    client.uf = "SP"
    client.cnae = "6201500"

    await db.commit()

    # Debug print: Check what tenants are in the database
    tenants = (await db.execute(select(Tenant))).scalars().all()
    print("\nALL TENANTS IN DATABASE:", tenants)

    # Generate obligations for May 2026
    summary = await generate_obligations_for_month(db, 2026, 5)
    assert summary["created"] > 0

    # Query created instances
    result = await db.execute(
        select(ObligationInstance).where(ObligationInstance.client_id == client.id)
    )
    instances = result.scalars().all()

    # Fetch rules to verify codes
    rule_ids = [inst.rule_id for inst in instances]
    rules_result = await db.execute(
        select(ObligationRule).where(ObligationRule.id.in_(rule_ids))
    )
    rules = rules_result.scalars().all()
    rule_codes = {r.code for r in rules}

    # Should contain DAS, PGDAS-D, DCTFWEB, ESOCIAL, and municipal ISS (ISS_3550308)
    assert "DAS" in rule_codes
    assert "PGDAS-D" in rule_codes
    assert "DCTFWEB" in rule_codes
    assert "ESOCIAL" in rule_codes
    assert "ISS_3550308" in rule_codes
