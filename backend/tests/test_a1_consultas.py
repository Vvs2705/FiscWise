"""A1: autenticação em uma consulta, dashboards agregados e paginação com teto.

As contagens usam o evento before_cursor_execute do engine de teste (SQLite).
Em PostgreSQL a autenticação soma só o set_config do RLS (2 idas ao banco).
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.requests import Request

from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.models.billing import TenantSubscription
from app.models.operations import AccountReceivable, DeadlineItem, DigitalCertificate, AccountingClient
from app.models.plan import Plan


class _QueryCounter:
    def __init__(self, engine):
        self.engine = engine.sync_engine
        self.statements: list[str] = []

    def _on_execute(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self._on_execute)
        return self

    def __exit__(self, *exc):
        event.remove(self.engine, "before_cursor_execute", self._on_execute)

    @property
    def count(self) -> int:
        return len(self.statements)


def _request(path: str = "/api/v1/dashboard/overview") -> Request:
    return Request({"type": "http", "method": "GET", "path": path, "headers": [], "query_string": b""})


async def _with_subscription(db, tenant_id):
    plan = Plan(id=uuid.uuid4(), slug=f"p-{uuid.uuid4().hex[:8]}", name="Plano", active=True)
    db.add(plan)
    await db.flush()
    db.add(TenantSubscription(tenant_id=tenant_id, plan_id=plan.id, status="active"))
    await db.commit()
    return plan


def _sqlite_date_trunc(unit, value):
    # Só para o teste: o dashboard usa date_trunc do PostgreSQL.
    if value is None:
        return None
    return f"{str(value)[:7]}-01 00:00:00" if unit == "month" else value


async def _register_date_trunc(test_db):
    conn = await test_db.connection()
    await conn.run_sync(
        lambda sync_conn: sync_conn.connection.dbapi_connection.create_function("date_trunc", 2, _sqlite_date_trunc)
    )


def _fresh_session(test_db):
    # Sessão nova = identity map vazio, como numa requisição real.
    return async_sessionmaker(test_db.bind, expire_on_commit=False, autoflush=False)()


@pytest.mark.asyncio
async def test_get_current_user_carrega_usuario_tenant_e_assinatura_em_uma_consulta(test_db, user_a):
    await _with_subscription(test_db, user_a.tenant_id)
    token = create_access_token(user_id=str(user_a.id), tenant_id=str(user_a.tenant_id), role="owner")

    async with _fresh_session(test_db) as session:
        with _QueryCounter(test_db.bind) as counter:
            user = await get_current_user(_request(), token, session)
            # O que plan_access lê em toda rota precisa vir junto, sem lazy load.
            assert user.tenant.id == user_a.tenant_id
            assert user.tenant.subscription is not None
            assert user.tenant.subscription.status == "active"
        assert counter.count == 1, counter.statements


@pytest.mark.asyncio
async def test_get_current_user_sem_assinatura_continua_em_uma_consulta(test_db, user_a):
    token = create_access_token(user_id=str(user_a.id), tenant_id=str(user_a.tenant_id), role="owner")

    async with _fresh_session(test_db) as session:
        with _QueryCounter(test_db.bind) as counter:
            user = await get_current_user(_request(), token, session)
            assert user.tenant.subscription is None
        assert counter.count == 1, counter.statements


async def _seed_dashboard(db, tenant_id, client_id):
    today = date.today()
    db.add_all(
        [
            AccountingClient(id=uuid.uuid4(), tenant_id=tenant_id, name="Inativo", status="inactive",
                             document="11222333000181", client_code="X1"),
            DeadlineItem(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, title="Pendente futuro",
                         due_date=today + timedelta(days=3), status="pending"),
            DeadlineItem(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, title="Pendente vencido",
                         due_date=today - timedelta(days=3), status="pending"),
            DeadlineItem(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, title="Concluído vencido",
                         due_date=today - timedelta(days=5), status="completed"),
            DeadlineItem(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, title="Atrasado",
                         due_date=today - timedelta(days=1), status="overdue"),
            DigitalCertificate(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, label="Vence logo",
                               valid_until=today + timedelta(days=10), status="valid"),
            DigitalCertificate(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, label="Longe",
                               valid_until=today + timedelta(days=90), status="valid"),
            DigitalCertificate(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, label="Revogado",
                               valid_until=today + timedelta(days=5), status="revoked"),
            AccountReceivable(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, description="Aberto",
                              amount=Decimal("100.00"), due_date=today + timedelta(days=5), status="pending"),
            AccountReceivable(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, description="Vencido",
                              amount=Decimal("40.50"), due_date=today - timedelta(days=5), status="pending"),
            AccountReceivable(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, description="Pago antigo",
                              amount=Decimal("999.00"), due_date=today - timedelta(days=400), status="paid",
                              paid_at=datetime(today.year - 1, 1, 15, tzinfo=timezone.utc)),
        ]
    )
    await db.commit()


@pytest.mark.asyncio
async def test_dashboard_overview_agrega_em_cinco_consultas(test_db, user_a, client_a, tenant_b):
    from app.api.v1.endpoints.operations import dashboard_overview

    await _register_date_trunc(test_db)
    await _seed_dashboard(test_db, user_a.tenant_id, client_a.id)
    # Dados de outro escritório não podem entrar nas contagens.
    other_client = AccountingClient(id=uuid.uuid4(), tenant_id=tenant_b.id, name="B", status="active",
                                    document="99888777000166", client_code="B1")
    test_db.add(other_client)
    await test_db.flush()
    test_db.add(AccountReceivable(id=uuid.uuid4(), tenant_id=tenant_b.id, client_id=other_client.id,
                                  description="B", amount=Decimal("7.00"),
                                  due_date=date.today() - timedelta(days=1), status="pending"))
    await test_db.commit()

    async with _fresh_session(test_db) as session:
        with _QueryCounter(test_db.bind) as counter:
            overview = await dashboard_overview(current_user=user_a, db=session)
        # 1 agregada + próximos prazos + mensal + semanal + recentes (antes: 13).
        assert counter.count == 5, counter.statements

    assert overview.active_clients == 1
    assert overview.pending_deadlines == 2
    assert overview.overdue_deadlines == 2  # pendente vencido + atrasado (concluído não conta)
    assert overview.certificates_expiring_30d == 1
    assert overview.open_receivables == 2
    assert overview.overdue_receivables == 1
    assert overview.receivables_amount_open == Decimal("140.50")
    assert overview.receivables_amount_overdue == Decimal("40.50")
    assert overview.total_received_month == Decimal("0")
    assert [d.title for d in overview.upcoming_deadlines] == ["Pendente futuro"]
    assert overview.monthly_received == []
    assert len(overview.weekly_received) == 7
    assert {r.description for r in overview.recent_receivables} == {"Aberto", "Vencido", "Pago antigo"}


@pytest.mark.asyncio
async def test_dashboard_overview_tenant_vazio_devolve_zeros(test_db, user_b):
    from app.api.v1.endpoints.operations import dashboard_overview

    await _register_date_trunc(test_db)
    async with _fresh_session(test_db) as session:
        overview = await dashboard_overview(current_user=user_b, db=session)

    assert overview.active_clients == 0
    assert overview.open_receivables == 0
    assert overview.receivables_amount_open == Decimal("0")
    assert overview.receivables_amount_overdue == Decimal("0")
    assert overview.total_received_month == Decimal("0")
    assert overview.upcoming_deadlines == []


# ── Paginação ─────────────────────────────────────────────────────────────────


async def _seed_deadlines(db, tenant_id, client_id, n=5):
    due = date.today() + timedelta(days=10)
    ids = sorted(uuid.uuid4() for _ in range(n))
    db.add_all(
        DeadlineItem(id=i, tenant_id=tenant_id, client_id=client_id, title=f"P{k}", due_date=due, status="pending")
        for k, i in enumerate(ids)
    )
    await db.commit()
    return [str(i) for i in ids]


@pytest.mark.asyncio
async def test_listagem_sem_parametros_devolve_tudo_e_total(client_with_auth_a):
    client, user_a, client_a, db = client_with_auth_a
    ids = await _seed_deadlines(db, user_a.tenant_id, client_a.id)

    response = client.get("/api/v1/deadlines")

    assert response.status_code == 200
    assert [d["id"] for d in response.json()] == ids  # mesma data: desempate por id
    assert response.headers["X-Total-Count"] == "5"


@pytest.mark.asyncio
async def test_listagem_limit_offset(client_with_auth_a):
    client, user_a, client_a, db = client_with_auth_a
    ids = await _seed_deadlines(db, user_a.tenant_id, client_a.id)

    first = client.get("/api/v1/deadlines", params={"limit": 2, "offset": 0})
    second = client.get("/api/v1/deadlines", params={"limit": 2, "offset": 2})
    last = client.get("/api/v1/deadlines", params={"limit": 2, "offset": 4})
    beyond = client.get("/api/v1/deadlines", params={"limit": 2, "offset": 50})

    assert [d["id"] for d in first.json()] == ids[0:2]
    assert [d["id"] for d in second.json()] == ids[2:4]
    assert [d["id"] for d in last.json()] == ids[4:5]
    assert beyond.json() == []
    for r in (first, second, last, beyond):
        assert r.headers["X-Total-Count"] == "5"


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 501}, {"offset": -1}])
async def test_listagem_recusa_limites_fora_do_teto(client_with_auth_a, params):
    client, *_ = client_with_auth_a
    assert client.get("/api/v1/clients", params=params).status_code == 422


@pytest.mark.asyncio
async def test_listagem_aceita_teto_maximo(client_with_auth_a):
    client, *_ = client_with_auth_a
    response = client.get("/api/v1/clients", params={"limit": 500})
    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/clients",
        "/api/v1/deadlines",
        "/api/v1/documents",
        "/api/v1/certificates",
        "/api/v1/receivables",
        "/api/v1/obligations/rules",
        "/api/v1/obligations/instances",
        "/api/v1/obligations/checklist",
        "/api/v1/rag/documents",
    ],
)
async def test_listagens_paginadas_mantem_formato_lista(client_with_auth_a, path):
    client, *_ = client_with_auth_a
    response = client.get(path, params={"limit": 1})
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 1
    assert "X-Total-Count" in response.headers


@pytest.mark.asyncio
async def test_listagens_por_cliente_paginadas(client_with_auth_a):
    client, _, client_a, _ = client_with_auth_a
    for path in (
        f"/api/v1/clients/{client_a.id}/documents",
        f"/api/v1/clients/{client_a.id}/partners",
        f"/api/v1/clients/{client_a.id}/company-documents",
    ):
        response = client.get(path, params={"limit": 1, "offset": 0})
        assert response.status_code == 200, (path, response.text)
        assert response.json() == []
        assert response.headers["X-Total-Count"] == "0"
