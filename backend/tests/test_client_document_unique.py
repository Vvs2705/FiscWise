"""Editar cliente para um CNPJ que já existe no escritório devolve 409, não 500 (DB-4)."""

import uuid

from app.models.operations import AccountingClient


async def test_editar_para_cnpj_duplicado(client_with_auth_a):
    http, user, client_a, test_db = client_with_auth_a
    outro = AccountingClient(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        name="Outro",
        document="11222333000181",
        entity_type="pj",
        status="active",
        client_code="9999",
    )
    test_db.add(outro)
    await test_db.commit()

    resp = http.patch(
        f"/api/v1/clients/{outro.id}", json={"document": client_a.document}
    )
    assert resp.status_code == 409, resp.text
    # o mesmo documento em outro escritório continua permitido (índice é por tenant)
