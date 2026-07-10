"""Integração dos relatórios agregados (/api/v1/reports).

Valida que as agregações refletem apenas dados reais do tenant e que o
resumo financeiro é restrito a owner/admin. Sem números fabricados.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.operations import AccountingClient, AccountReceivable
from app.models.obligation import ObligationInstance
from app.domain.guias.models import TaxGuide
from app.domain.monthly_closing.models import MonthlyClosing
from app.domain.invoices.models import Invoice, InvoiceIssuer
from app.domain.ecac.models import EcacProxy

pytestmark = pytest.mark.integration

TODAY = date.today()
FIRST = date(TODAY.year, TODAY.month, 1)
COMPETENCE = f"{TODAY.year:04d}-{TODAY.month:02d}"


async def _seed_tenant_a(db, tenant_id, client_id):
    """Semeia dados reais de um mês de competência para o tenant A."""
    # Clientes extras (situação)
    inactive = AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant_id, name="Inativo", entity_type="pj",
        status="inactive",
    )
    onboarding = AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant_id, name="Onboarding", entity_type="pj",
        status="onboarding",
    )
    db.add_all([inactive, onboarding])

    # Contas a receber: faturado (pendente + pago no mês) e vencido (mês anterior)
    db.add_all([
        AccountReceivable(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id,
            description="Honorários pendentes", amount=Decimal("1000.00"),
            due_date=date(TODAY.year, TODAY.month, 15), status="pending",
        ),
        AccountReceivable(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id,
            description="Honorários pagos", amount=Decimal("700.00"),
            due_date=date(TODAY.year, TODAY.month, 10), status="paid",
            paid_at=datetime(TODAY.year, TODAY.month, 10, 12, 0, tzinfo=timezone.utc),
        ),
        AccountReceivable(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id,
            description="Vencido", amount=Decimal("500.00"),
            due_date=FIRST - timedelta(days=10), status="pending",
        ),
    ])

    # Obrigações (competência): delivered / pending / overdue
    for st in ("delivered", "pending", "overdue"):
        db.add(ObligationInstance(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id,
            competence_month=FIRST, due_date=TODAY, status=st,
        ))

    # Guias (competência): paga / aguardando (venc. futuro) / vencida (venc. passado)
    db.add_all([
        TaxGuide(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, tipo="DAS",
            competencia=FIRST, valor=Decimal("300.00"),
            vencimento=TODAY + timedelta(days=5), status="paga",
        ),
        TaxGuide(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, tipo="DAS",
            competencia=FIRST, valor=Decimal("300.00"),
            vencimento=TODAY + timedelta(days=5), status="pendente",
        ),
        TaxGuide(
            id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, tipo="DARF",
            competencia=FIRST, valor=Decimal("400.00"),
            vencimento=TODAY - timedelta(days=5), status="pendente",
        ),
    ])

    # Fechamentos (um por cliente): completed / blocked / not_started
    db.add_all([
        MonthlyClosing(id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id,
                       competence=COMPETENCE, status="completed"),
        MonthlyClosing(id=uuid.uuid4(), tenant_id=tenant_id, client_id=inactive.id,
                       competence=COMPETENCE, status="blocked"),
        MonthlyClosing(id=uuid.uuid4(), tenant_id=tenant_id, client_id=onboarding.id,
                       competence=COMPETENCE, status="not_started"),
    ])

    # Notas fiscais (competência): issued / rejected
    issuer = InvoiceIssuer(
        id=uuid.uuid4(), tenant_id=tenant_id, cnpj="12345678000199",
        regime_tributario="simples", municipio_ibge="3550308",
    )
    db.add(issuer)
    await db.flush()
    for st in ("issued", "rejected"):
        db.add(Invoice(
            id=uuid.uuid4(), tenant_id=tenant_id, issuer_id=issuer.id,
            client_id=client_id, status=st, competencia=FIRST,
            valor_servico=Decimal("1000.00"), descricao_servico="Serviço",
        ))

    # Procurações a vencer: 20 dias (d30), 50 dias (d60), 200 dias (fora do horizonte)
    db.add_all([
        EcacProxy(id=uuid.uuid4(), tenant_id=tenant_id, outorgante_cpf_cnpj="1",
                  procurador_cpf="1", status="ativa",
                  data_validade=TODAY + timedelta(days=20)),
        EcacProxy(id=uuid.uuid4(), tenant_id=tenant_id, outorgante_cpf_cnpj="2",
                  procurador_cpf="2", status="ativa",
                  data_validade=TODAY + timedelta(days=50)),
        EcacProxy(id=uuid.uuid4(), tenant_id=tenant_id, outorgante_cpf_cnpj="3",
                  procurador_cpf="3", status="ativa",
                  data_validade=TODAY + timedelta(days=200)),
    ])

    await db.commit()


@pytest.mark.asyncio
async def test_reports_summary_real_aggregation(client_with_auth_a):
    http, user, client, db = client_with_auth_a
    await _seed_tenant_a(db, user.tenant_id, client.id)

    resp = http.get("/api/v1/reports/summary", params={"competence": COMPETENCE})
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(data["revenue_billed"]) == Decimal("1700.00")   # 1000 + 700
    assert Decimal(data["revenue_received"]) == Decimal("700.00")
    assert Decimal(data["overdue_amount"]) == Decimal("500.00")
    assert data["overdue_clients"] == 1
    assert data["active_clients"] >= 1
    assert data["competence"] == COMPETENCE


@pytest.mark.asyncio
async def test_reports_operational_real_aggregation(client_with_auth_a):
    http, user, client, db = client_with_auth_a
    await _seed_tenant_a(db, user.tenant_id, client.id)

    resp = http.get("/api/v1/reports/operational", params={"competence": COMPETENCE})
    assert resp.status_code == 200
    data = resp.json()

    assert data["clients_by_status"]["inactive"] == 1
    assert data["clients_by_status"]["onboarding"] == 1
    assert data["clients_by_status"]["active"] >= 1

    obl = data["obligations_by_status"]
    assert (obl["delivered"], obl["pending"], obl["overdue"], obl["total"]) == (1, 1, 1, 3)

    guias = data["guias_by_status"]
    assert (guias["paid"], guias["awaiting"], guias["overdue"], guias["total"]) == (1, 1, 1, 3)

    closings = data["closings_by_status"]
    assert closings["completed"] == 1
    assert closings["blocked"] == 1
    assert closings["not_started"] == 1

    inv = data["invoices_by_status"]
    assert (inv["issued"], inv["rejected"], inv["total"]) == (1, 1, 2)

    proxies = data["proxies_expiring"]
    assert proxies["d30"] == 1
    assert proxies["d60"] == 1
    assert proxies["total"] == 2  # o de 200 dias fica de fora


@pytest.mark.asyncio
async def test_reports_summary_tenant_isolation(client_with_auth_a):
    http, user, client, db = client_with_auth_a
    await _seed_tenant_a(db, user.tenant_id, client.id)

    # Recebível vencido de OUTRO tenant não pode vazar para o resumo do tenant A
    other_tenant = uuid.uuid4()
    db.add(AccountReceivable(
        id=uuid.uuid4(), tenant_id=other_tenant, client_id=uuid.uuid4(),
        description="Vencido de outro tenant", amount=Decimal("99999.00"),
        due_date=FIRST - timedelta(days=30), status="pending",
    ))
    await db.commit()

    resp = http.get("/api/v1/reports/summary", params={"competence": COMPETENCE})
    assert resp.status_code == 200
    assert Decimal(resp.json()["overdue_amount"]) == Decimal("500.00")


@pytest.mark.asyncio
async def test_reports_summary_forbidden_for_member(client_with_auth_b):
    http, user, client, db = client_with_auth_b
    resp = http.get("/api/v1/reports/summary", params={"competence": COMPETENCE})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reports_requires_auth(client):
    headers = {"X-Tenant-ID": "9df4b224-c8dc-4cdf-9bb6-40af6d206e62"}
    assert client.get("/api/v1/reports/operational", headers=headers).status_code in (401, 403)
    assert client.get("/api/v1/reports/summary", headers=headers).status_code in (401, 403)


@pytest.mark.asyncio
async def test_reports_invalid_competence(client_with_auth_a):
    http, user, client, db = client_with_auth_a
    resp = http.get("/api/v1/reports/operational", params={"competence": "2026-13"})
    assert resp.status_code == 400
