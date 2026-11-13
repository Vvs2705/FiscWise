"""RLS de verdade, em PostgreSQL, com um role SEM bypass (TEN-3).

A suíte normal usa SQLite e nunca exercita as policies. Este teste roda no CI
(RUN_PG_RLS=1, banco do service postgres já migrado até o head) e prova que,
para um role comum:
- com escritório no contexto (toda requisição autenticada), ele só vê e só
  grava linhas do próprio escritório;
- sem contexto (rotina do sistema: agendador, webhooks, backup) vê tudo —
  exceção `current_app_tenant_id() IS NULL` da migração u7w8forcerls;
- toda tabela com RLS tem FORCE, para valer também ao dono das tabelas
  (em produção a API conecta como o dono, `fiscwise_app`).
"""

import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.operations import AccountingClient
from app.models.tenant import Tenant

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_PG_RLS") != "1", reason="só no CI com PostgreSQL migrado"
)

PROBE = "rls_probe"


async def test_rls_isola_escritorios_para_role_sem_bypass():
    admin_url = make_url(os.environ["DATABASE_URL"])
    admin = create_async_engine(admin_url)
    async with admin.begin() as c:
        await c.execute(
            text(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{PROBE}') "
                f"THEN CREATE ROLE {PROBE} LOGIN PASSWORD '{PROBE}' NOBYPASSRLS; END IF; END $$"
            )
        )
        await c.execute(text(f"GRANT USAGE ON SCHEMA public TO {PROBE}"))
        await c.execute(text(f"GRANT SELECT, INSERT ON accounting_clients TO {PROBE}"))

    ta, tb = uuid.uuid4(), uuid.uuid4()
    async with AsyncSession(admin) as s:
        s.add_all(
            [Tenant(id=ta, name="Escritório A"), Tenant(id=tb, name="Escritório B")]
        )
        await s.flush()
        s.add_all(
            [
                AccountingClient(
                    id=uuid.uuid4(),
                    tenant_id=ta,
                    name="Cliente A",
                    entity_type="pj",
                    status="active",
                    client_code="0001",
                ),
                AccountingClient(
                    id=uuid.uuid4(),
                    tenant_id=tb,
                    name="Cliente B",
                    entity_type="pj",
                    status="active",
                    client_code="0001",
                ),
            ]
        )
        await s.commit()

    probe = create_async_engine(admin_url.set(username=PROBE, password=PROBE))
    try:
        async with probe.connect() as c:
            sem_contexto = await c.scalar(
                text("SELECT count(*) FROM accounting_clients")
            )
            await c.execute(
                text("SELECT set_config('app.current_tenant_id', :t, false)"),
                {"t": str(ta)},
            )
            vistos = {
                r[0]
                for r in await c.execute(
                    text("SELECT tenant_id FROM accounting_clients")
                )
            }
            # Com o escritório A no contexto, gravar no escritório B é recusado.
            gravou_em_b = True
            try:
                async with c.begin_nested():
                    await c.execute(
                        text(
                            "INSERT INTO accounting_clients (id, tenant_id, name, entity_type, status, client_code, created_at, updated_at) "
                            "VALUES (:id, :t, 'Invasao', 'pj', 'active', '0002', now(), now())"
                        ),
                        {"id": uuid.uuid4(), "t": tb},
                    )
            except Exception:
                gravou_em_b = False
        assert sem_contexto >= 2  # rotina do sistema vê todos os escritórios
        assert vistos == {ta}
        assert gravou_em_b is False

        async with admin.connect() as c:
            sem_force = (
                await c.execute(
                    text(
                        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity "
                        "AND NOT c.relforcerowsecurity"
                    )
                )
            ).scalars().all()
        assert sem_force == []
    finally:
        await probe.dispose()
        async with admin.begin() as c:
            await c.execute(
                text("DELETE FROM accounting_clients WHERE tenant_id IN (:a, :b)"),
                {"a": ta, "b": tb},
            )
            await c.execute(
                text("DELETE FROM tenants WHERE id IN (:a, :b)"), {"a": ta, "b": tb}
            )
        await admin.dispose()
