"""Relatórios operacionais e financeiros — agregações reais por tenant.

Não fabrica números: cada rota agrega apenas dados já persistidos no banco,
sempre filtrando por ``current_user.tenant_id`` (isolamento multi-tenant).
Segue o mesmo padrão dos agregadores em ``operations.py``
(``dashboard_overview`` / ``get_inadimplencia_report``): ``func.count`` /
``func.sum`` + ``GROUP BY``, sem tabelas novas nem camada de serviço.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.operations import AccountingClient, AccountReceivable
from app.models.obligation import ObligationInstance
from app.domain.guias.models import TaxGuide
from app.domain.monthly_closing.models import MonthlyClosing
from app.domain.invoices.models import Invoice
from app.domain.ecac.models import EcacProxy

router = APIRouter(prefix="/reports", tags=["Reports"])


# ── Schemas ────────────────────────────────────────────────────────────────
class ClientsByStatus(BaseModel):
    active: int
    onboarding: int
    inactive: int
    total: int


class ObligationsByStatus(BaseModel):
    delivered: int
    pending: int
    in_progress: int
    overdue: int
    total: int


class GuiasByStatus(BaseModel):
    paid: int
    awaiting: int
    overdue: int
    total: int


class ClosingsByStatus(BaseModel):
    completed: int
    in_progress: int
    blocked: int
    not_started: int
    total: int


class InvoicesByStatus(BaseModel):
    issued: int
    rejected: int
    cancelled: int
    total: int


class ProxiesExpiring(BaseModel):
    d30: int
    d60: int
    d90: int
    total: int


class OperationalReport(BaseModel):
    competence: str
    clients_by_status: ClientsByStatus
    obligations_by_status: ObligationsByStatus
    guias_by_status: GuiasByStatus
    closings_by_status: ClosingsByStatus
    invoices_by_status: InvoicesByStatus
    proxies_expiring: ProxiesExpiring


class ReportsSummary(BaseModel):
    competence: str
    revenue_billed: Decimal
    revenue_received: Decimal
    overdue_amount: Decimal
    overdue_clients: int
    active_clients: int
    new_clients_month: int


# ── Helpers ────────────────────────────────────────────────────────────────
def _parse_competence(competence: str | None) -> tuple[int, int]:
    """``"YYYY-MM"`` -> ``(year, month)``. Default: mês atual."""
    if not competence:
        today = date.today()
        return today.year, today.month
    try:
        year_str, month_str = competence.split("-")
        year, month = int(year_str), int(month_str)
        if not (1 <= month <= 12) or not (2000 <= year <= 2100):
            raise ValueError
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Competência inválida, use o formato YYYY-MM",
        )
    return year, month


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    """Primeiro dia do mês e primeiro dia do mês seguinte (intervalo semiaberto)."""
    first = date(year, month, 1)
    next_first = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return first, next_first


async def _count(db: AsyncSession, statement) -> int:
    result = await db.execute(statement)
    return int(result.scalar_one() or 0)


def _require_admin(current_user: User) -> None:
    if current_user.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas owner/admin podem acessar o resumo financeiro",
        )


# ── Rotas ──────────────────────────────────────────────────────────────────
@router.get("/summary", response_model=ReportsSummary)
async def reports_summary(
    competence: str | None = Query(default=None, description="YYYY-MM (padrão: mês atual)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportsSummary:
    """Resumo financeiro do escritório — owner/admin apenas.

    Receita faturada (contas a receber vencendo na competência), receita
    recebida (pagas na competência) e inadimplência (em aberto e vencidas).
    """
    _require_admin(current_user)
    tenant_id: uuid.UUID = current_user.tenant_id
    year, month = _parse_competence(competence)
    first, next_first = _month_bounds(year, month)
    today = date.today()

    billed_result = await db.execute(
        select(func.coalesce(func.sum(AccountReceivable.amount), 0)).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.due_date >= first,
            AccountReceivable.due_date < next_first,
        )
    )
    first_dt = datetime(year, month, 1, tzinfo=timezone.utc)
    next_first_dt = datetime(next_first.year, next_first.month, 1, tzinfo=timezone.utc)
    received_result = await db.execute(
        select(func.coalesce(func.sum(AccountReceivable.amount), 0)).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status == "paid",
            AccountReceivable.paid_at >= first_dt,
            AccountReceivable.paid_at < next_first_dt,
        )
    )
    overdue_result = await db.execute(
        select(
            func.coalesce(func.sum(AccountReceivable.amount), 0),
            func.count(func.distinct(AccountReceivable.client_id)),
        ).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status != "paid",
            AccountReceivable.due_date < today,
        )
    )
    overdue_amount, overdue_clients = overdue_result.one()

    active_clients = await _count(
        db,
        select(func.count()).select_from(AccountingClient).where(
            AccountingClient.tenant_id == tenant_id,
            AccountingClient.status == "active",
        ),
    )
    new_clients_month = await _count(
        db,
        select(func.count()).select_from(AccountingClient).where(
            AccountingClient.tenant_id == tenant_id,
            AccountingClient.created_at >= first_dt,
            AccountingClient.created_at < next_first_dt,
        ),
    )

    return ReportsSummary(
        competence=f"{year:04d}-{month:02d}",
        revenue_billed=Decimal(billed_result.scalar_one() or 0),
        revenue_received=Decimal(received_result.scalar_one() or 0),
        overdue_amount=Decimal(overdue_amount or 0),
        overdue_clients=int(overdue_clients or 0),
        active_clients=active_clients,
        new_clients_month=new_clients_month,
    )


@router.get("/operational", response_model=OperationalReport)
async def reports_operational(
    competence: str | None = Query(default=None, description="YYYY-MM (padrão: mês atual)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OperationalReport:
    """Relatórios operacionais agregados por status, filtrados por tenant.

    Clientes, obrigações, guias, fechamentos, notas fiscais e procurações a
    vencer. Grupos sem dados retornam zeros (estado vazio honesto no front).
    """
    tenant_id: uuid.UUID = current_user.tenant_id
    year, month = _parse_competence(competence)
    first, next_first = _month_bounds(year, month)
    competence_str = f"{year:04d}-{month:02d}"
    today = date.today()

    async def status_map(model, *filters) -> dict[str, int]:
        rows = await db.execute(
            select(model.status, func.count())
            .where(model.tenant_id == tenant_id, *filters)
            .group_by(model.status)
        )
        return {str(s): int(c) for s, c in rows.all()}

    # 1. Clientes por situação
    clients = await status_map(AccountingClient)
    clients_by_status = ClientsByStatus(
        active=clients.get("active", 0),
        onboarding=clients.get("onboarding", 0),
        inactive=clients.get("inactive", 0),
        total=sum(clients.values()),
    )

    # 2. Obrigações por status (competência)
    obl = await status_map(
        ObligationInstance, ObligationInstance.competence_month == first
    )
    obligations_by_status = ObligationsByStatus(
        delivered=obl.get("delivered", 0),
        pending=obl.get("pending", 0),
        in_progress=obl.get("in_progress", 0),
        overdue=obl.get("overdue", 0),
        total=obl.get("delivered", 0)
        + obl.get("pending", 0)
        + obl.get("in_progress", 0)
        + obl.get("overdue", 0),
    )

    # 3. Guias por status (competência)
    guia_paid = await _count(
        db,
        select(func.count()).select_from(TaxGuide).where(
            TaxGuide.tenant_id == tenant_id,
            TaxGuide.competencia >= first,
            TaxGuide.competencia < next_first,
            TaxGuide.status.in_(["paga", "paid"]),
        ),
    )
    guia_awaiting = await _count(
        db,
        select(func.count()).select_from(TaxGuide).where(
            TaxGuide.tenant_id == tenant_id,
            TaxGuide.competencia >= first,
            TaxGuide.competencia < next_first,
            TaxGuide.status.notin_(["paga", "paid", "cancelada"]),
            TaxGuide.vencimento >= today,
        ),
    )
    guia_overdue = await _count(
        db,
        select(func.count()).select_from(TaxGuide).where(
            TaxGuide.tenant_id == tenant_id,
            TaxGuide.competencia >= first,
            TaxGuide.competencia < next_first,
            TaxGuide.status.notin_(["paga", "paid", "cancelada"]),
            TaxGuide.vencimento < today,
        ),
    )
    guias_by_status = GuiasByStatus(
        paid=guia_paid,
        awaiting=guia_awaiting,
        overdue=guia_overdue,
        total=guia_paid + guia_awaiting + guia_overdue,
    )

    # 4. Fechamentos por status (competência)
    closings = await status_map(
        MonthlyClosing, MonthlyClosing.competence == competence_str
    )
    closings_by_status = ClosingsByStatus(
        completed=closings.get("completed", 0),
        in_progress=closings.get("in_progress", 0) + closings.get("ready_for_review", 0),
        blocked=closings.get("blocked", 0),
        not_started=closings.get("not_started", 0),
        total=sum(closings.values()),
    )

    # 5. Notas fiscais por status (competência)
    inv = await status_map(
        Invoice,
        Invoice.competencia >= first,
        Invoice.competencia < next_first,
    )
    inv_issued = inv.get("issued", 0)
    inv_rejected = inv.get("rejected", 0)
    inv_cancelled = (
        inv.get("cancelled", 0)
        + inv.get("replaced", 0)
        + inv.get("failed", 0)
        + inv.get("cancel_requested", 0)
    )
    invoices_by_status = InvoicesByStatus(
        issued=inv_issued,
        rejected=inv_rejected,
        cancelled=inv_cancelled,
        total=inv_issued + inv_rejected + inv_cancelled,
    )

    # 6. Procurações a vencer (30/60/90 dias)
    async def proxies_until(days: int) -> int:
        return await _count(
            db,
            select(func.count()).select_from(EcacProxy).where(
                EcacProxy.tenant_id == tenant_id,
                EcacProxy.status == "ativa",
                EcacProxy.data_validade >= today,
                EcacProxy.data_validade <= today + timedelta(days=days),
            ),
        )

    cumulative_30 = await proxies_until(30)
    cumulative_60 = await proxies_until(60)
    cumulative_90 = await proxies_until(90)
    proxies_expiring = ProxiesExpiring(
        d30=cumulative_30,
        d60=cumulative_60 - cumulative_30,
        d90=cumulative_90 - cumulative_60,
        total=cumulative_90,
    )

    return OperationalReport(
        competence=competence_str,
        clients_by_status=clients_by_status,
        obligations_by_status=obligations_by_status,
        guias_by_status=guias_by_status,
        closings_by_status=closings_by_status,
        invoices_by_status=invoices_by_status,
        proxies_expiring=proxies_expiring,
    )
