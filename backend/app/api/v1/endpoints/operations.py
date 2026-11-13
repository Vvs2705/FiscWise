"""Operational MVP endpoints for FiscWise pilots."""

import logging
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, TypeVar

logger = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import Date as SADate, and_, cast, func, or_, select, text, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_principal, get_current_user, get_db
from app.core.document_links import DOCUMENTS_BUCKET, SIGNED_URL_TTL, sign_file_urls, storage_ref
from app.core.plan_access import (
    PLAN_INTERMEDIARIO,
    ai_classification_allowed,
    check_chat_quota,
    ensure_can_add_client,
    ensure_can_add_document,
    require_ai_configured,
    require_plan,
    resolve_user_plan,
)
from app.core.pagination import Page, page_params, paginate
from app.services.audit import log_audit_event
from app.models.calculator import AssistantRole, FiscalAssistantMessage
from app.models.operations import (
    AccountReceivable,
    AccountingClient,
    ClientDocument,
    DeadlineItem,
    DigitalCertificate,
)
from app.models.obligation import DocumentChecklistItem, ObligationInstance
from app.domain.monthly_closing.models import MonthlyClosing
from app.models.user import User
from app.services.ai_fiscal import classify_fiscal_document, generate_client_operational_summary
from app.services.document_parser import is_skipped, parse_document
from app.services import webhook_service as _webhook_svc
from app.schemas.operations import (
    AccountingClientCreate,
    AccountingClientResponse,
    AccountingClientUpdate,
    CertificateCreate,
    CertificateResponse,
    CertificateUpdate,
    ClientBillingConfig,
    ClientBillingConfigUpdate,
    ClientBillingHistoryItem,
    ClientAiSummaryResponse,
    ClientPendingStats,
    CollaboratorStats,
    DailyData,
    DashboardOverview,
    DeadlineCreate,
    DeadlineResponse,
    DeadlineUpdate,
    DocumentCreate,
    DocumentResponse,
    DocumentUploadResponse,
    DocumentUpdate,
    InadimplenciaReport,
    MonthlyData,
    PendingDocumentItem,
    ProductivityOverview,
    ReceivableCreate,
    ReceivableResponse,
    ReceivableUpdate,
    ReceivableWithClient,
)


router = APIRouter()
ModelT = TypeVar("ModelT")

_MONTH_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
_DAY_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]  # weekday() == 0 -> Seg


def _tenant_id(current_user: User) -> uuid.UUID:
    return current_user.tenant_id


def _plan(current_user: User) -> str | None:
    return resolve_user_plan(current_user)


def _apply_updates(instance: Any, payload: Any) -> None:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(instance, key, value)


async def _get_client_or_404(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
) -> AccountingClient:
    result = await db.execute(
        select(AccountingClient).where(
            AccountingClient.tenant_id == tenant_id,
            AccountingClient.id == client_id,
        )
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return client


async def _get_item_or_404(
    db: AsyncSession,
    model: type[ModelT],
    tenant_id: uuid.UUID,
    item_id: uuid.UUID,
    not_found_message: str,
) -> ModelT:
    result = await db.execute(
        select(model).where(
            model.tenant_id == tenant_id,  # type: ignore[attr-defined]
            model.id == item_id,  # type: ignore[attr-defined]
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_message,
        )
    return item


async def _commit_refresh(db: AsyncSession, instance: Any) -> Any:
    try:
        await db.commit()
    except IntegrityError:
        # Violação de unicidade (ex.: mesmo CNPJ no escritório) vira 409, não 500.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um registro com esses dados (ex.: mesmo CNPJ/CPF).",
        )
    await db.refresh(instance)
    return instance


async def _soft_delete(
    db: AsyncSession,
    request: Request,
    current_user: User,
    item: Any,
    *,
    terminal_status: str,
    blocked_statuses: dict[str, str],
    entity_type: str,
) -> Any:
    """Exclusão lógica: leva `item` ao status terminal e registra auditoria.

    Idempotente: se já está no status terminal, devolve o item como está.
    Status em `blocked_statuses` (ex.: concluído/pago) são terminais e não
    podem ser excluídos — responde 409 com a mensagem associada.
    """
    if item.status == terminal_status:
        return item
    if item.status in blocked_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=blocked_statuses[item.status],
        )
    before_status = item.status
    item.status = terminal_status
    item = await _commit_refresh(db, item)
    await log_audit_event(
        db=db,
        tenant_id=item.tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action=f"{entity_type}.{terminal_status}",
        entity_type=entity_type,
        entity_id=item.id,
        before_data={"status": before_status},
        after_data={"status": terminal_status},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    return item


async def _generate_client_code(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    """Gera codigo de 4 digitos unico para o tenant. Retry em caso de colisao."""
    for attempt in range(20):
        code = f"{random.randint(0, 9999):04d}"
        existing = await db.execute(
            select(AccountingClient).where(
                AccountingClient.tenant_id == tenant_id,
                AccountingClient.client_code == code,
            )
        )
        if existing.scalar_one_or_none() is None:
            return code
        logger.debug("client_code %s collision on attempt %d, retrying", code, attempt + 1)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate unique client code after 20 attempts",
    )


@router.get("/dashboard/overview", response_model=DashboardOverview)
async def dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardOverview:
    tenant_id = _tenant_id(current_user)
    today = date.today()
    limit_date = today + timedelta(days=30)

    # Contagens e somas dos quatro cadastros numa consulta só (antes eram 9
    # idas ao banco). Cada subconsulta agrega uma tabela e devolve uma linha;
    # FILTER é SQL padrão (PostgreSQL e SQLite).
    first_of_month = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
    clients_agg = (
        select(
            func.count().filter(AccountingClient.status == "active").label("active_clients"),
        )
        .where(AccountingClient.tenant_id == tenant_id)
        .subquery()
    )
    deadlines_agg = (
        select(
            func.count().filter(DeadlineItem.status == "pending").label("pending_deadlines"),
            func.count()
            .filter(DeadlineItem.status != "completed", DeadlineItem.due_date < today)
            .label("overdue_deadlines"),
        )
        .where(DeadlineItem.tenant_id == tenant_id)
        .subquery()
    )
    certificates_agg = (
        select(
            func.count()
            .filter(
                DigitalCertificate.status == "valid",
                DigitalCertificate.valid_until >= today,
                DigitalCertificate.valid_until <= limit_date,
            )
            .label("certificates_expiring_30d"),
        )
        .where(DigitalCertificate.tenant_id == tenant_id)
        .subquery()
    )
    is_open = AccountReceivable.status == "pending"
    is_overdue = and_(AccountReceivable.status != "paid", AccountReceivable.due_date < today)
    is_received_month = and_(
        AccountReceivable.status == "paid", AccountReceivable.paid_at >= first_of_month
    )
    receivables_agg = (
        select(
            func.count().filter(is_open).label("open_receivables"),
            func.count().filter(is_overdue).label("overdue_receivables"),
            func.coalesce(func.sum(AccountReceivable.amount).filter(is_open), 0).label("amount_open"),
            func.coalesce(func.sum(AccountReceivable.amount).filter(is_overdue), 0).label("amount_overdue"),
            func.coalesce(func.sum(AccountReceivable.amount).filter(is_received_month), 0).label(
                "received_month"
            ),
        )
        .where(AccountReceivable.tenant_id == tenant_id)
        .subquery()
    )
    totals = (
        await db.execute(
            select(clients_agg, deadlines_agg, certificates_agg, receivables_agg).select_from(
                clients_agg.join(deadlines_agg, true())
                .join(certificates_agg, true())
                .join(receivables_agg, true())
            )
        )
    ).one()
    active_clients = int(totals.active_clients or 0)
    pending_deadlines = int(totals.pending_deadlines or 0)
    overdue_deadlines = int(totals.overdue_deadlines or 0)
    certificates_expiring_30d = int(totals.certificates_expiring_30d or 0)
    open_receivables = int(totals.open_receivables or 0)
    overdue_receivables = int(totals.overdue_receivables or 0)

    upcoming_result = await db.execute(
        select(DeadlineItem)
        .where(
            DeadlineItem.tenant_id == tenant_id,
            DeadlineItem.status != "completed",
            DeadlineItem.due_date >= today,
        )
        .order_by(DeadlineItem.due_date.asc())
        .limit(8)
    )

    # ── Financeiro: total recebido no mes corrente (vem da consulta agregada) ──
    total_received_month = Decimal(totals.received_month or 0)

    # ── Financeiro: tendencia mensal (ano corrente) ────────────────────────────
    first_of_year = datetime(today.year, 1, 1, tzinfo=timezone.utc)
    monthly_raw = await db.execute(
        select(
            func.date_trunc(text("'month'"), AccountReceivable.paid_at).label("month"),
            func.coalesce(func.sum(AccountReceivable.amount), 0).label("total"),
        )
        .where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status == "paid",
            AccountReceivable.paid_at >= first_of_year,
        )
        .group_by(func.date_trunc(text("'month'"), AccountReceivable.paid_at))
        .order_by(func.date_trunc(text("'month'"), AccountReceivable.paid_at).asc())
    )
    monthly_received = [
        MonthlyData(mes=_MONTH_PT[row.month.month - 1], valor=Decimal(row.total or 0))
        for row in monthly_raw.all()
    ]

    # ── Financeiro: receita diaria ultimos 7 dias ──────────────────────────────
    seven_days_ago = today - timedelta(days=6)
    seven_days_ago_dt = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) - timedelta(days=6)
    weekly_raw = await db.execute(
        select(
            cast(AccountReceivable.paid_at, SADate).label("day"),
            func.coalesce(func.sum(AccountReceivable.amount), 0).label("total"),
        )
        .where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status == "paid",
            AccountReceivable.paid_at >= seven_days_ago_dt,
        )
        .group_by(cast(AccountReceivable.paid_at, SADate))
        .order_by(cast(AccountReceivable.paid_at, SADate).asc())
    )
    weekly_map = {row.day: Decimal(row.total or 0) for row in weekly_raw.all()}
    weekly_received = [
        DailyData(
            dia=_DAY_PT[(seven_days_ago + timedelta(days=i)).weekday()],
            receita=weekly_map.get(seven_days_ago + timedelta(days=i), Decimal(0)),
        )
        for i in range(7)
    ]

    # ── Financeiro: recebiveis recentes com nome do cliente ────────────────────
    recent_raw = await db.execute(
        select(
            AccountReceivable.id,
            AccountReceivable.client_id,
            AccountingClient.name.label("client_name"),
            AccountReceivable.description,
            AccountReceivable.amount,
            AccountReceivable.due_date,
            AccountReceivable.status,
            AccountReceivable.paid_at,
            AccountReceivable.created_at,
            AccountReceivable.updated_at,
        )
        .join(AccountingClient, AccountReceivable.client_id == AccountingClient.id)
        .where(AccountReceivable.tenant_id == tenant_id)
        .order_by(AccountReceivable.created_at.desc())
        .limit(8)
    )
    recent_receivables = [
        ReceivableWithClient(**dict(row))
        for row in recent_raw.mappings().all()
    ]

    return DashboardOverview(
        active_clients=active_clients,
        pending_deadlines=pending_deadlines,
        overdue_deadlines=overdue_deadlines,
        certificates_expiring_30d=certificates_expiring_30d,
        open_receivables=open_receivables,
        overdue_receivables=overdue_receivables,
        receivables_amount_open=Decimal(totals.amount_open or 0),
        receivables_amount_overdue=Decimal(totals.amount_overdue or 0),
        upcoming_deadlines=list(upcoming_result.scalars().all()),
        # novos campos financeiros
        total_received_month=total_received_month,
        monthly_received=monthly_received,
        weekly_received=weekly_received,
        recent_receivables=recent_receivables,
    )


@router.get("/dashboard/productivity", response_model=ProductivityOverview)
async def dashboard_productivity(
    year: int | None = Query(default=None, ge=2020, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductivityOverview:
    """
    Painel de produtividade do escritório — owner/admin apenas.

    Retorna métricas de obrigações, colaboradores, clientes e alertas
    para o mês de competência especificado (padrão: mês atual).
    """
    if current_user.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can access the productivity dashboard",
        )

    tenant_id = _tenant_id(current_user)
    today = date.today()
    comp_year = year or today.year
    comp_month = month or today.month
    first_of_month = date(comp_year, comp_month, 1)
    competence_str = f"{comp_year:04d}-{comp_month:02d}"

    limit_date = today + timedelta(days=30)

    # ── Totais numa consulta só (antes eram 6 idas ao banco) ───────────────────
    # Cada subconsulta agrega uma tabela e devolve uma linha; FILTER é SQL padrão.
    obligations_agg = (
        select(
            func.count().filter(ObligationInstance.status == "pending").label("total_pending"),
            func.count().filter(ObligationInstance.status == "in_progress").label("total_in_progress"),
            func.count().filter(ObligationInstance.status == "delivered").label("total_delivered"),
            func.count().filter(ObligationInstance.status == "overdue").label("total_overdue"),
        )
        .where(
            ObligationInstance.tenant_id == tenant_id,
            ObligationInstance.competence_month == first_of_month,
        )
        .subquery()
    )
    checklist_agg = (
        select(func.count().label("docs_awaiting_approval"))
        .select_from(DocumentChecklistItem)
        .where(
            DocumentChecklistItem.tenant_id == tenant_id,
            DocumentChecklistItem.competence_month == first_of_month,
            DocumentChecklistItem.status == "received",
        )
        .subquery()
    )
    closings_agg = (
        select(func.count().label("total_blocked"))
        .select_from(MonthlyClosing)
        .where(
            MonthlyClosing.tenant_id == tenant_id,
            MonthlyClosing.competence == competence_str,
            MonthlyClosing.status == "blocked",
        )
        .subquery()
    )
    certificates_agg = (
        select(func.count().label("certificates_expiring_30d"))
        .select_from(DigitalCertificate)
        .where(
            DigitalCertificate.tenant_id == tenant_id,
            DigitalCertificate.status == "valid",
            DigitalCertificate.valid_until >= today,
            DigitalCertificate.valid_until <= limit_date,
        )
        .subquery()
    )
    receivables_agg = (
        select(
            func.count().label("overdue_receivables_count"),
            func.coalesce(func.sum(AccountReceivable.amount), 0).label("overdue_receivables_amount"),
        )
        .where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status != "paid",
            AccountReceivable.due_date < today,
        )
        .subquery()
    )
    totals = (
        await db.execute(
            select(obligations_agg, checklist_agg, closings_agg, certificates_agg, receivables_agg).select_from(
                obligations_agg.join(checklist_agg, true())
                .join(closings_agg, true())
                .join(certificates_agg, true())
                .join(receivables_agg, true())
            )
        )
    ).one()

    total_pending = int(totals.total_pending or 0)
    total_in_progress = int(totals.total_in_progress or 0)
    total_delivered = int(totals.total_delivered or 0)
    total_overdue = int(totals.total_overdue or 0)

    closed = total_delivered + total_overdue
    compliance_rate = round((total_delivered / closed * 100) if closed > 0 else 0.0, 1)

    # ── Obligations by collaborator ────────────────────────────────────────────
    collab_raw = await db.execute(
        select(
            ObligationInstance.assigned_to,
            User.full_name,
            ObligationInstance.status,
            func.count().label("cnt"),
        )
        .outerjoin(User, ObligationInstance.assigned_to == User.id)
        .where(
            ObligationInstance.tenant_id == tenant_id,
            ObligationInstance.competence_month == first_of_month,
        )
        .group_by(
            ObligationInstance.assigned_to,
            User.full_name,
            ObligationInstance.status,
        )
        .order_by(ObligationInstance.assigned_to)
    )

    collab_pivot: dict[str | None, CollaboratorStats] = {}
    for row in collab_raw.all():
        key = str(row.assigned_to) if row.assigned_to else "__unassigned__"
        if key not in collab_pivot:
            collab_pivot[key] = CollaboratorStats(
                user_id=row.assigned_to,
                user_name=row.full_name or "Não atribuído",
            )
        s = row.status
        if s == "pending":
            collab_pivot[key].pending += int(row.cnt)
        elif s == "in_progress":
            collab_pivot[key].in_progress += int(row.cnt)
        elif s == "delivered":
            collab_pivot[key].delivered += int(row.cnt)
        elif s == "overdue":
            collab_pivot[key].overdue += int(row.cnt)
        collab_pivot[key].total += int(row.cnt)

    obligations_by_collaborator = sorted(
        collab_pivot.values(), key=lambda x: x.total, reverse=True
    )

    # ── Clients with most pending obligations ──────────────────────────────────
    top_pending_raw = await db.execute(
        select(
            ObligationInstance.client_id,
            AccountingClient.name.label("client_name"),
            func.count().label("pending_count"),
        )
        .join(AccountingClient, ObligationInstance.client_id == AccountingClient.id)
        .where(
            ObligationInstance.tenant_id == tenant_id,
            ObligationInstance.competence_month == first_of_month,
            ObligationInstance.status == "pending",
        )
        .group_by(ObligationInstance.client_id, AccountingClient.name)
        .order_by(func.count().desc())
        .limit(5)
    )
    clients_with_most_pending = [
        ClientPendingStats(
            client_id=row.client_id,
            client_name=row.client_name,
            pending_count=int(row.pending_count),
        )
        for row in top_pending_raw.all()
    ]

    docs_awaiting_approval = int(totals.docs_awaiting_approval or 0)

    # ── Sample list of pending documents (same source as the count above) ──────
    pending_docs_raw = await db.execute(
        select(
            DocumentChecklistItem.id,
            AccountingClient.name.label("client_name"),
            DocumentChecklistItem.document_name,
            DocumentChecklistItem.received_at,
            DocumentChecklistItem.created_at,
        )
        .join(AccountingClient, DocumentChecklistItem.client_id == AccountingClient.id)
        .where(
            DocumentChecklistItem.tenant_id == tenant_id,
            DocumentChecklistItem.competence_month == first_of_month,
            DocumentChecklistItem.status == "received",
        )
        .order_by(DocumentChecklistItem.received_at.desc().nullslast())
        .limit(5)
    )
    pending_documents = []
    for row in pending_docs_raw.all():
        ref = row.received_at or row.created_at
        days_waiting = (today - ref.date()).days if ref else 0
        pending_documents.append(
            PendingDocumentItem(
                id=row.id,
                client_name=row.client_name,
                document_name=row.document_name,
                days_waiting=max(0, days_waiting),
                status="received",
            )
        )

    total_blocked = int(totals.total_blocked or 0)
    certificates_expiring_30d = int(totals.certificates_expiring_30d or 0)
    overdue_receivables_count = int(totals.overdue_receivables_count or 0)

    return ProductivityOverview(
        competence_month=competence_str,
        compliance_rate=compliance_rate,
        total_pending=total_pending,
        total_in_progress=total_in_progress,
        total_delivered=total_delivered,
        total_overdue=total_overdue,
        total_blocked=total_blocked,
        obligations_by_collaborator=obligations_by_collaborator,
        clients_with_most_pending=clients_with_most_pending,
        pending_documents=pending_documents,
        docs_awaiting_approval=docs_awaiting_approval,
        certificates_expiring_30d=certificates_expiring_30d,
        overdue_receivables_count=overdue_receivables_count,
        overdue_receivables_amount=Decimal(totals.overdue_receivables_amount or 0),
    )


@router.get("/clients", response_model=list[AccountingClientResponse])
async def list_clients(
    search: str | None = Query(default=None, max_length=120),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    tax_regime: str | None = Query(default=None, max_length=80),
    entity_type: str | None = Query(default=None, max_length=16),
    cnae_code: str | None = Query(default=None, max_length=20),
    page: Page = Depends(page_params),
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(AccountingClient).where(AccountingClient.tenant_id == tenant_id)
    if status_filter:
        statement = statement.where(AccountingClient.status == status_filter)
    if tax_regime:
        statement = statement.where(AccountingClient.tax_regime == tax_regime)
    if entity_type:
        statement = statement.where(AccountingClient.entity_type == entity_type)
    if cnae_code:
        statement = statement.where(AccountingClient.cnae_code.ilike(f"{cnae_code}%"))
    if search:
        term = f"%{search}%"
        statement = statement.where(
            or_(
                AccountingClient.name.ilike(term),
                AccountingClient.document.ilike(term),
                AccountingClient.client_code.ilike(term),
            )
        )
    return await paginate(
        db, statement.order_by(AccountingClient.name.asc(), AccountingClient.id.asc()), page
    )


@router.get("/clients/{client_id}", response_model=AccountingClientResponse)
async def get_client(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> AccountingClientResponse:
    """Buscar cliente especifico por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_client_or_404(db, tenant_id, client_id)


@router.post(
    "/clients/{client_id}/ai-summary",
    response_model=ClientAiSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def get_client_ai_summary(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClientAiSummaryResponse:
    """Generate an AI operational summary for a single client."""
    tenant_id = _tenant_id(current_user)
    plan = _plan(current_user)
    require_plan(plan, PLAN_INTERMEDIARIO, "Resumo por IA de cliente")
    # Sem chave de IA: 503 antes de gravar a mensagem que consome a cota.
    require_ai_configured()

    has_quota, _ = await check_chat_quota(tenant_id, plan, db)
    if not has_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Você atingiu o limite de 20 mensagens mensais do plano Intermediário. "
                "Faça upgrade para o plano Premium para ter acesso ilimitado."
            ),
        )

    client = await _get_client_or_404(db, tenant_id, client_id)

    documents_result = await db.execute(
        select(ClientDocument)
        .where(ClientDocument.tenant_id == tenant_id, ClientDocument.client_id == client_id)
        .order_by(ClientDocument.created_at.desc())
        .limit(8)
    )
    obligations_result = await db.execute(
        select(ObligationInstance)
        .where(ObligationInstance.tenant_id == tenant_id, ObligationInstance.client_id == client_id)
        .order_by(ObligationInstance.due_date.asc())
        .limit(8)
    )
    receivables_result = await db.execute(
        select(AccountReceivable)
        .where(AccountReceivable.tenant_id == tenant_id, AccountReceivable.client_id == client_id)
        .order_by(AccountReceivable.due_date.asc())
        .limit(8)
    )
    certificates_result = await db.execute(
        select(DigitalCertificate)
        .where(DigitalCertificate.tenant_id == tenant_id, DigitalCertificate.client_id == client_id)
        .order_by(DigitalCertificate.valid_until.asc())
        .limit(5)
    )

    context = {
        "client": {
            "name": client.name,
            "document": client.document,
            "status": client.status,
            "tax_regime": client.tax_regime,
            "entity_type": client.entity_type,
            "notes": client.notes,
        },
        "documents": [
            {
                "name": doc.name,
                "type": doc.document_type,
                "status": doc.status,
                "parse_status": doc.parse_status,
                "ai_classification": (doc.parsed_data or {}).get("ai_classification")
                if doc.parsed_data
                else None,
            }
            for doc in documents_result.scalars().all()
        ],
        "obligations": [
            {
                "due_date": item.due_date,
                "status": item.status,
                "priority": item.priority,
                "competence_month": item.competence_month,
            }
            for item in obligations_result.scalars().all()
        ],
        "receivables": [
            {
                "description": item.description,
                "amount": item.amount,
                "due_date": item.due_date,
                "status": item.status,
            }
            for item in receivables_result.scalars().all()
        ],
        "certificates": [
            {
                "label": item.label,
                "valid_until": item.valid_until,
                "status": item.status,
            }
            for item in certificates_result.scalars().all()
        ],
    }

    user_msg = FiscalAssistantMessage(
        tenant_id=tenant_id,
        role=AssistantRole.USER,
        content=f"Gerar resumo operacional do cliente {client.id}",
    )
    db.add(user_msg)
    await db.flush()

    summary, tokens_used = await generate_client_operational_summary(context)
    if not summary:
        summary = "Resumo por IA temporariamente indisponivel. Valide os dados manualmente."

    assistant_msg = FiscalAssistantMessage(
        tenant_id=tenant_id,
        role=AssistantRole.ASSISTANT,
        content=summary,
        tokens_used=tokens_used,
    )
    db.add(assistant_msg)
    await db.commit()

    _, remaining_after = await check_chat_quota(tenant_id, plan, db)
    return ClientAiSummaryResponse(
        client_id=client.id,
        summary=summary,
        remaining_quota=remaining_after,
        tokens_used=tokens_used,
    )


@router.post("/clients", response_model=AccountingClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: AccountingClientCreate,
    request: Request,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)

    # Limite de clientes do plano efetivo. Falha fechada: erro na checagem
    # recusa o cadastro (503) em vez de deixar passar sem limite.
    if (payload.status or "active") == "active":
        await ensure_can_add_client(db, tenant_id, current_user.email)

    if payload.document:
        existing = await db.execute(
            select(AccountingClient).where(
                AccountingClient.tenant_id == tenant_id,
                AccountingClient.document == payload.document,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A client with this document already exists",
            )

    client_code = await _generate_client_code(db, tenant_id)
    client = AccountingClient(
        tenant_id=tenant_id,
        client_code=client_code,
        **payload.model_dump(),
    )
    db.add(client)
    client = await _commit_refresh(db, client)
    await log_audit_event(
        db=db,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="client.create",
        entity_type="client",
        entity_id=client.id,
        after_data={"name": client.name, "document": client.document},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    # Fire-and-forget webhook dispatch for client.created
    await _webhook_svc.dispatch_event(
        db=db,
        tenant_id=tenant_id,
        event="client.created",
        data={"id": str(client.id), "name": client.name, "document": client.document},
    )
    return client


@router.patch("/clients/{client_id}", response_model=AccountingClientResponse)
@router.put("/clients/{client_id}", response_model=AccountingClientResponse)
async def update_client(
    client_id: uuid.UUID,
    payload: AccountingClientUpdate,
    request: Request,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    client = await _get_client_or_404(db, tenant_id, client_id)
    # Reativar cliente conta no limite de clientes ativos do plano.
    if payload.status == "active" and client.status != "active":
        await ensure_can_add_client(db, tenant_id, current_user.email)
    before_data = {"name": client.name, "document": client.document}
    _apply_updates(client, payload)
    client = await _commit_refresh(db, client)
    await log_audit_event(
        db=db,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="client.update",
        entity_type="client",
        entity_id=client.id,
        before_data=before_data,
        after_data={"name": client.name, "document": client.document},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    await _webhook_svc.dispatch_event(
        db=db,
        tenant_id=tenant_id,
        event="client.updated",
        data={
            "id": str(client.id),
            "name": client.name,
            "document": client.document,
            "status": client.status,
            "changed_fields": sorted(payload.model_dump(exclude_unset=True).keys()),
        },
    )
    return client


@router.delete("/clients/{client_id}", response_model=AccountingClientResponse)
async def deactivate_client(
    client_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    client = await _get_client_or_404(db, tenant_id, client_id)
    before_status = client.status
    client.status = "inactive"
    client = await _commit_refresh(db, client)
    await log_audit_event(
        db=db,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="client.deactivate",
        entity_type="client",
        entity_id=client.id,
        before_data={"status": before_status},
        after_data={"status": "inactive"},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    return client


@router.get("/deadlines", response_model=list[DeadlineResponse])
async def list_deadlines(
    client_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    page: Page = Depends(page_params),
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(DeadlineItem).where(DeadlineItem.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(DeadlineItem.client_id == client_id)
    if status_filter:
        statement = statement.where(DeadlineItem.status == status_filter)
    return await paginate(
        db, statement.order_by(DeadlineItem.due_date.asc(), DeadlineItem.id.asc()), page
    )


@router.get("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def get_deadline(
    deadline_id: uuid.UUID,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """Buscar prazo especifico por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_item_or_404(db, DeadlineItem, tenant_id, deadline_id, "Deadline not found")


def get_next_due_date(current_date: date, interval: str) -> date:
    if interval == "weekly":
        return current_date + timedelta(days=7)
    elif interval == "monthly":
        year = current_date.year
        month = current_date.month + 1
        if month > 12:
            month = 1
            year += 1
        day = current_date.day
        import calendar
        _, last_day = calendar.monthrange(year, month)
        day = min(day, last_day)
        return date(year, month, day)
    elif interval == "quarterly":
        year = current_date.year
        month = current_date.month + 3
        while month > 12:
            month -= 12
            year += 1
        day = current_date.day
        import calendar
        _, last_day = calendar.monthrange(year, month)
        day = min(day, last_day)
        return date(year, month, day)
    elif interval == "yearly":
        year = current_date.year + 1
        month = current_date.month
        day = current_date.day
        if month == 2 and day == 29:
            import calendar
            if not calendar.isleap(year):
                day = 28
        return date(year, month, day)
    return current_date


@router.post("/deadlines", response_model=DeadlineResponse, status_code=status.HTTP_201_CREATED)
async def create_deadline(
    payload: DeadlineCreate,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, payload.client_id)
    item = DeadlineItem(tenant_id=tenant_id, **payload.model_dump())
    db.add(item)
    return await _commit_refresh(db, item)


@router.patch("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def update_deadline(
    deadline_id: uuid.UUID,
    payload: DeadlineUpdate,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    item = await _get_item_or_404(db, DeadlineItem, tenant_id, deadline_id, "Deadline not found")
    
    # Check if we are marking it completed now
    marking_completed = payload.status == "completed" and item.status != "completed"
    
    _apply_updates(item, payload)
    
    if payload.status == "completed" and item.completed_at is None:
        item.completed_at = datetime.now(timezone.utc)
        
    if marking_completed and item.is_recurring and item.recurrence_interval:
        next_due = get_next_due_date(item.due_date, item.recurrence_interval)
        new_item = DeadlineItem(
            tenant_id=item.tenant_id,
            client_id=item.client_id,
            title=item.title,
            category=item.category,
            due_date=next_due,
            status="pending",
            priority=item.priority,
            description=item.description,
            is_recurring=True,
            recurrence_interval=item.recurrence_interval,
            recurrence_parent_id=item.id,
        )
        db.add(new_item)
        
    return await _commit_refresh(db, item)


@router.delete("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def cancel_deadline(
    deadline_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exclusão lógica do prazo (status `cancelled`)."""
    tenant_id = _tenant_id(current_user)
    item = await _get_item_or_404(db, DeadlineItem, tenant_id, deadline_id, "Deadline not found")
    return await _soft_delete(
        db, request, current_user, item,
        terminal_status="cancelled",
        blocked_statuses={"completed": "Prazo já concluído não pode ser excluído."},
        entity_type="deadline",
    )



async def _documents_out(docs, tenant_id: uuid.UUID) -> list[DocumentResponse]:
    """Serializa documentos trocando a referência do storage por URL assinada."""
    out = [DocumentResponse.model_validate(d) for d in docs]
    await sign_file_urls(out, tenant_id)
    return out


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    client_id: uuid.UUID | None = None,
    page: Page = Depends(page_params),
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(ClientDocument).where(ClientDocument.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(ClientDocument.client_id == client_id)
    docs = await paginate(
        db, statement.order_by(ClientDocument.created_at.desc(), ClientDocument.id.desc()), page
    )
    return await _documents_out(docs, tenant_id)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Buscar documento especifico por ID."""
    tenant_id = _tenant_id(current_user)
    doc = await _get_item_or_404(db, ClientDocument, tenant_id, document_id, "Document not found")
    return (await _documents_out([doc], tenant_id))[0]


def _tenant_storage_path(file_url: str | None, tenant_id: uuid.UUID) -> str | None:
    """Path no bucket ``documents`` quando ``file_url`` é um objeto do próprio
    tenant no nosso storage (referência ``documents/<tenant>/...`` gerada por
    /documents/upload, ou a URL pública antiga). Qualquer outra URL devolve
    None: o backend nunca busca URL arbitrária (evita SSRF)."""
    from app.core.document_links import object_path_for

    path = object_path_for(file_url, tenant_id)
    if not path:
        return None
    if Path(path).suffix.lower() not in _DOC_UPLOAD_EXTS:
        return None
    return path


async def _download_and_parse_background(
    document_id: uuid.UUID,
    storage_path: str,
    file_name: str,
    tenant_id: uuid.UUID,
) -> None:
    """Baixa o arquivo do storage e reaproveita o mesmo parser do upload por cliente."""
    import tempfile
    from app.core.deps import _set_current_tenant_context, get_sessionmaker
    from app.core.storage import download_bytes

    try:
        content = await download_bytes("documents", storage_path)
        error = None if content else "Arquivo indisponível no storage para classificação automática."
    except Exception as exc:  # noqa: BLE001 — registra no documento em vez de sumir
        content, error = None, f"Falha ao baixar o arquivo para classificação: {exc}"

    if not content:
        async_session = get_sessionmaker()
        async with async_session() as db:
            await _set_current_tenant_context(db, tenant_id)
            document = (
                await db.execute(
                    select(ClientDocument).where(
                        (ClientDocument.id == document_id)
                        & (ClientDocument.tenant_id == tenant_id)
                    )
                )
            ).scalar_one_or_none()
            if document:
                document.parse_status = "failed"
                document.parse_error = error
                await db.commit()
        return

    with tempfile.NamedTemporaryFile(suffix=Path(storage_path).suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    await _parse_document_background(document_id, tmp_path, file_name, tenant_id)


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, payload.client_id)
    await ensure_can_add_document(db, tenant_id, payload.client_id, current_user.email)
    document = ClientDocument(tenant_id=tenant_id, **payload.model_dump())
    # Classificação automática só quando o arquivo está no nosso storage;
    # sem arquivo acessível o documento fica "unavailable" (UI explica) em vez
    # de "Aguardando processamento" para sempre.
    storage_path = _tenant_storage_path(payload.file_url, tenant_id)
    document.parse_status = "processing" if storage_path else "unavailable"
    db.add(document)
    doc = await _commit_refresh(db, document)
    if storage_path:
        background_tasks.add_task(
            _download_and_parse_background,
            doc.id,
            storage_path,
            doc.name,
            tenant_id,
        )
    # Fire-and-forget webhook dispatch for document.uploaded
    await _webhook_svc.dispatch_event(
        db=db,
        tenant_id=tenant_id,
        event="document.uploaded",
        data={"id": str(doc.id), "name": doc.name, "client_id": str(doc.client_id)},
    )
    return (await _documents_out([doc], tenant_id))[0]


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    document = await _get_item_or_404(db, ClientDocument, tenant_id, document_id, "Document not found")
    _apply_updates(document, payload)
    doc = await _commit_refresh(db, document)
    return (await _documents_out([doc], tenant_id))[0]


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    document = await _get_item_or_404(db, ClientDocument, tenant_id, document_id, "Document not found")
    doc_name = document.name
    await db.delete(document)
    await db.commit()
    await log_audit_event(
        db=db,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="document.delete",
        entity_type="document",
        entity_id=document_id,
        before_data={"name": doc_name},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )


_DOC_UPLOAD_MAX_BYTES = 20 * 1024 * 1024  # mesmo teto anunciado na tela de Documentos
_DOC_UPLOAD_EXTS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".xml", ".csv", ".txt", ".ofx",
    ".xls", ".xlsx", ".doc", ".docx", ".zip",
}


@router.post("/documents/upload")
async def upload_document_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Sobe o arquivo para o bucket privado `documents`.

    Devolve `url` = referência do storage (`documents/<tenant>/<arquivo>`), que o
    frontend grava em `file_url` no POST /documents; a leitura troca por URL
    assinada. `signed_url` serve para pré-visualizar logo após o upload.
    """
    import uuid as _uuid
    from app.core import storage as _storage
    from app.core.config import settings

    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage not configured",
        )

    # Gera path unico: {tenant_id}/{uuid}_{filename_ext}
    tenant_id = _tenant_id(current_user)
    file_ext = ""
    if file.filename and "." in file.filename:
        file_ext = "." + file.filename.rsplit(".", 1)[-1].lower()

    # Allowlist por extensão + teto de tamanho. Certificado .pfx/.p12 fica de
    # fora (chave privada não vai para este bucket).
    if file_ext not in _DOC_UPLOAD_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo de arquivo não aceito. Use: {', '.join(sorted(_DOC_UPLOAD_EXTS))}",
        )

    unique_name = f"{tenant_id}/{_uuid.uuid4().hex}{file_ext}"

    file_bytes = await file.read(_DOC_UPLOAD_MAX_BYTES + 1)
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")
    if len(file_bytes) > _DOC_UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo maior que {_DOC_UPLOAD_MAX_BYTES // (1024 * 1024)} MB",
        )
    content_type = file.content_type or "application/octet-stream"

    try:
        await _storage.upload_bytes(DOCUMENTS_BUCKET, unique_name, file_bytes, content_type)
    except RuntimeError:
        logger.exception("Supabase Storage upload failed (%s)", unique_name)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload file to storage",
        )

    ref = storage_ref(unique_name)
    try:
        signed_url: str | None = await _storage.get_signed_url(
            DOCUMENTS_BUCKET, unique_name, ttl=SIGNED_URL_TTL
        )
    except RuntimeError:
        signed_url = None
    return {"url": ref, "path": unique_name, "signed_url": signed_url}


@router.get("/certificates", response_model=list[CertificateResponse])
async def list_certificates(
    client_id: uuid.UUID | None = None,
    page: Page = Depends(page_params),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(DigitalCertificate).where(DigitalCertificate.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(DigitalCertificate.client_id == client_id)
    return await paginate(
        db, statement.order_by(DigitalCertificate.valid_until.asc(), DigitalCertificate.id.asc()), page
    )


@router.get("/certificates/expiring", response_model=list[CertificateResponse])
async def list_expiring_certificates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List certificates expiring in the next 60 days."""
    tenant_id = _tenant_id(current_user)
    today = date.today()
    limit_date = today + timedelta(days=60)
    stmt = select(DigitalCertificate).where(
        DigitalCertificate.tenant_id == tenant_id,
        DigitalCertificate.valid_until >= today,
        DigitalCertificate.valid_until <= limit_date,
        DigitalCertificate.bloqueado == False
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/certificates/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(
    certificate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CertificateResponse:
    """Buscar certificado digital especifico por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_item_or_404(
        db,
        DigitalCertificate,
        tenant_id,
        certificate_id,
        "Certificate not found",
    )


@router.post("/certificates", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def create_certificate(
    payload: CertificateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, payload.client_id)
    certificate = DigitalCertificate(tenant_id=tenant_id, **payload.model_dump())
    db.add(certificate)
    return await _commit_refresh(db, certificate)


@router.patch("/certificates/{certificate_id}", response_model=CertificateResponse)
async def update_certificate(
    certificate_id: uuid.UUID,
    payload: CertificateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    certificate = await _get_item_or_404(
        db,
        DigitalCertificate,
        tenant_id,
        certificate_id,
        "Certificate not found",
    )
    _apply_updates(certificate, payload)
    return await _commit_refresh(db, certificate)


@router.post("/certificates/{certificate_id}/block", response_model=CertificateResponse)
async def block_certificate(
    certificate_id: uuid.UUID,
    reason: str = Query(..., description="Reason for blocking"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Block a digital certificate from further use."""
    tenant_id = _tenant_id(current_user)
    certificate = await _get_item_or_404(
        db,
        DigitalCertificate,
        tenant_id,
        certificate_id,
        "Certificate not found",
    )
    return await _revoke_certificate(db, current_user, certificate, reason)


async def _revoke_certificate(
    db: AsyncSession,
    current_user: User,
    certificate: DigitalCertificate,
    reason: str,
) -> DigitalCertificate:
    """Bloqueia/revoga o certificado (status `revoked`) e registra auditoria."""
    certificate.bloqueado = True
    certificate.motivo_bloqueio = reason
    certificate.status = "revoked"

    # Audit log
    await log_audit_event(
        db=db,
        tenant_id=certificate.tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="certificate.blocked",
        entity_type="certificate",
        entity_id=certificate.id,
        after_data={"bloqueado": True, "motivo_bloqueio": reason},
    )

    return await _commit_refresh(db, certificate)


@router.delete("/certificates/{certificate_id}", response_model=CertificateResponse)
async def revoke_certificate(
    certificate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exclusão lógica do certificado: mesma semântica de `/block` (status `revoked`).

    Idempotente: certificado já revogado é devolvido como está.
    """
    tenant_id = _tenant_id(current_user)
    certificate = await _get_item_or_404(
        db,
        DigitalCertificate,
        tenant_id,
        certificate_id,
        "Certificate not found",
    )
    if certificate.status == "revoked":
        return certificate
    return await _revoke_certificate(db, current_user, certificate, "Excluído pelo usuário")


@router.get("/certificates/{certificate_id}/usage-trail")
async def get_certificate_usage_trail(
    certificate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit trail log for digital certificate usage."""
    tenant_id = _tenant_id(current_user)
    await _get_item_or_404(
        db,
        DigitalCertificate,
        tenant_id,
        certificate_id,
        "Certificate not found",
    )
    
    from app.models.audit import AuditEvent
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == tenant_id,
        AuditEvent.entity_type == "certificate",
        AuditEvent.entity_id == certificate_id
    ).order_by(AuditEvent.created_at.desc())
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "action": e.action,
            "actor_user_id": e.actor_user_id,
            "created_at": e.created_at.isoformat(),
            "details": e.after_data
        }
        for e in events
    ]


@router.get("/receivables", response_model=list[ReceivableResponse])
async def list_receivables(
    client_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    page: Page = Depends(page_params),
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(AccountReceivable).where(AccountReceivable.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(AccountReceivable.client_id == client_id)
    if status_filter:
        statement = statement.where(AccountReceivable.status == status_filter)
    return await paginate(
        db, statement.order_by(AccountReceivable.due_date.asc(), AccountReceivable.id.asc()), page
    )


@router.get("/receivables/{receivable_id}", response_model=ReceivableResponse)
async def get_receivable(
    receivable_id: uuid.UUID,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ReceivableResponse:
    """Buscar conta a receber especifica por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_item_or_404(
        db,
        AccountReceivable,
        tenant_id,
        receivable_id,
        "Receivable not found",
    )


@router.post("/receivables", response_model=ReceivableResponse, status_code=status.HTTP_201_CREATED)
async def create_receivable(
    payload: ReceivableCreate,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, payload.client_id)
    receivable = AccountReceivable(tenant_id=tenant_id, **payload.model_dump())
    db.add(receivable)
    return await _commit_refresh(db, receivable)


@router.patch("/receivables/{receivable_id}", response_model=ReceivableResponse)
async def update_receivable(
    receivable_id: uuid.UUID,
    payload: ReceivableUpdate,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    receivable = await _get_item_or_404(
        db,
        AccountReceivable,
        tenant_id,
        receivable_id,
        "Receivable not found",
    )
    _apply_updates(receivable, payload)
    if payload.status == "paid" and receivable.paid_at is None:
        receivable.paid_at = datetime.now(timezone.utc)
    return await _commit_refresh(db, receivable)


@router.delete("/receivables/{receivable_id}", response_model=ReceivableResponse)
async def cancel_receivable(
    receivable_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exclusão lógica da cobrança (status `cancelled`)."""
    tenant_id = _tenant_id(current_user)
    receivable = await _get_item_or_404(
        db,
        AccountReceivable,
        tenant_id,
        receivable_id,
        "Receivable not found",
    )
    return await _soft_delete(
        db, request, current_user, receivable,
        terminal_status="cancelled",
        blocked_statuses={"paid": "Cobrança já paga não pode ser excluída."},
        entity_type="receivable",
    )


@router.post("/receivables/generate-monthly")
async def generate_monthly_billing(
    year_month: str = Query(..., regex=r"^\d{4}-\d{2}$", description="Format: YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Gera automaticamente faturas de honorários para clientes com monthly_fee."""
    import calendar

    tenant_id = _tenant_id(current_user)

    try:
        year, month = map(int, year_month.split("-"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format deve ser YYYY-MM",
        )

    # Buscar clientes com monthly_fee > 0
    stmt = select(AccountingClient).where(
        (AccountingClient.tenant_id == tenant_id)
        & (AccountingClient.monthly_fee > 0)
        & (AccountingClient.status == "active")
    )
    result = await db.execute(stmt)
    clients = list(result.scalars().all())

    created_count = 0
    skipped_count = 0

    for client in clients:
        # Checar se já existe fatura para este mês
        # limit(1): com duas faturas do mês (ex.: ajuste manual) o
        # scalar_one_or_none() estourava MultipleResultsFound (500).
        existing = await db.execute(
            select(AccountReceivable.id).where(
                (AccountReceivable.tenant_id == tenant_id)
                & (AccountReceivable.client_id == client.id)
                & (AccountReceivable.description.like(f"Honorários - {year_month}%"))
            ).limit(1)
        )

        if existing.scalar_one_or_none():
            skipped_count += 1
            continue

        # Calcular vencimento (billing_day do cliente)
        max_day = calendar.monthrange(year, month)[1]
        due_day = min(client.billing_day, max_day)
        due_date = date(year, month, due_day)

        # Criar novo AccountReceivable
        receivable = AccountReceivable(
            tenant_id=tenant_id,
            client_id=client.id,
            description=f"Honorários - {year_month}",
            amount=client.monthly_fee,
            due_date=due_date,
            status="pending",
        )
        db.add(receivable)
        created_count += 1

    await db.commit()

    return {
        "status": "success",
        "year_month": year_month,
        "created": created_count,
        "skipped_duplicates": skipped_count,
        "message": f"Geradas {created_count} faturas de honorários",
    }


@router.get("/clients/{client_id}/billing-config", response_model=ClientBillingConfig)
async def get_client_billing_config(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClientBillingConfig:
    """Get billing / honorários configuration for a specific client."""
    client = await _get_client_or_404(db, _tenant_id(current_user), client_id)
    return ClientBillingConfig(
        client_id=client.id,
        client_name=client.name,
        monthly_fee=client.monthly_fee,
        billing_day=client.billing_day or 1,
        annual_adjustment_percent=client.annual_adjustment_percent,
    )


@router.patch("/clients/{client_id}/billing-config", response_model=ClientBillingConfig)
async def update_client_billing_config(
    client_id: uuid.UUID,
    payload: ClientBillingConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClientBillingConfig:
    """Update billing / honorários configuration for a specific client."""
    if current_user.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can update billing configuration",
        )
    client = await _get_client_or_404(db, _tenant_id(current_user), client_id)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)

    db.add(client)
    await db.commit()
    await db.refresh(client)

    return ClientBillingConfig(
        client_id=client.id,
        client_name=client.name,
        monthly_fee=client.monthly_fee,
        billing_day=client.billing_day or 1,
        annual_adjustment_percent=client.annual_adjustment_percent,
    )


@router.get("/clients/{client_id}/billing-history", response_model=list[ClientBillingHistoryItem])
async def get_client_billing_history(
    client_id: uuid.UUID,
    limit: int = Query(default=24, ge=1, le=120),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ClientBillingHistoryItem]:
    """Get billing history (honorários receivables) for a specific client."""
    await _get_client_or_404(db, _tenant_id(current_user), client_id)

    result = await db.execute(
        select(AccountReceivable)
        .where(
            AccountReceivable.tenant_id == _tenant_id(current_user),
            AccountReceivable.client_id == client_id,
            AccountReceivable.description.like("Honorários%"),
        )
        .order_by(AccountReceivable.due_date.desc(), AccountReceivable.id.desc())
        .limit(limit)
        .offset(offset)
    )
    receivables = result.scalars().all()

    return [
        ClientBillingHistoryItem(
            id=r.id,
            description=r.description,
            amount=r.amount,
            due_date=r.due_date,
            status=r.status,
            paid_at=r.paid_at.isoformat() if r.paid_at else None,
            created_at=r.created_at.isoformat(),
        )
        for r in receivables
    ]


@router.get("/financeiro/inadimplencia", response_model=InadimplenciaReport)
async def get_inadimplencia_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InadimplenciaReport:
    """
    Inadimplência report: clients with overdue receivables.

    Groups overdue receivables by client and returns ranked by total overdue amount.
    Owner/admin only.
    """
    if current_user.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can access the inadimplência report",
        )

    tenant_id = _tenant_id(current_user)
    today = date.today()

    # Group overdue receivables by client
    grouped_raw = await db.execute(
        select(
            AccountReceivable.client_id,
            AccountingClient.name.label("client_name"),
            AccountingClient.document.label("document"),
            AccountingClient.email.label("email"),
            func.count().label("overdue_count"),
            func.coalesce(func.sum(AccountReceivable.amount), 0).label("overdue_total"),
            func.min(AccountReceivable.due_date).label("oldest_due"),
        )
        .join(AccountingClient, AccountReceivable.client_id == AccountingClient.id)
        .where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status != "paid",
            AccountReceivable.due_date < today,
        )
        .group_by(
            AccountReceivable.client_id,
            AccountingClient.name,
            AccountingClient.document,
            AccountingClient.email,
        )
        .order_by(func.coalesce(func.sum(AccountReceivable.amount), 0).desc())
    )

    from app.schemas.operations import InadimplenciaClientItem
    clients_list = []
    total_overdue_count = 0
    total_overdue_amount = Decimal(0)

    for row in grouped_raw.all():
        oldest = row.oldest_due
        days_overdue = (today - oldest).days if oldest else 0
        overdue_total = Decimal(row.overdue_total or 0)
        overdue_count = int(row.overdue_count)

        clients_list.append(
            InadimplenciaClientItem(
                client_id=row.client_id,
                client_name=row.client_name,
                document=row.document,
                email=row.email,
                overdue_count=overdue_count,
                overdue_total=overdue_total,
                oldest_due_date=oldest,
                days_overdue=days_overdue,
            )
        )
        total_overdue_count += overdue_count
        total_overdue_amount += overdue_total

    from datetime import datetime, timezone
    return InadimplenciaReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_clients=len(clients_list),
        total_overdue_count=total_overdue_count,
        total_overdue_amount=total_overdue_amount,
        clients=clients_list,
    )


@router.post("/clients/{client_id}/documents")
async def upload_client_document(
    client_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    document_type: str = Query(..., max_length=80, description="Tipo: contract, secret_sheet, certificate, etc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload de arquivo para cliente (PDF, Excel, Word).

    Resposta igual à de antes, mais `job_id` (status em GET /api/v1/jobs/{id}).
    """
    import tempfile

    tenant_id = _tenant_id(current_user)

    # Validar cliente e o limite de documentos do plano (antes de subir o arquivo)
    await _get_client_or_404(db, tenant_id, client_id)
    await ensure_can_add_document(db, tenant_id, client_id, current_user.email)

    # Antes gravava uma URL de exemplo (storage.example.com) e nunca guardava o
    # arquivo, mas marcava o documento como disponível (TEN-6). Agora sobe de
    # verdade, com as mesmas regras do /documents/upload.
    from app.core import storage as _storage

    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in _DOC_UPLOAD_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo de arquivo não aceito. Use: {', '.join(sorted(_DOC_UPLOAD_EXTS))}",
        )
    content = await file.read(_DOC_UPLOAD_MAX_BYTES + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")
    if len(content) > _DOC_UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo maior que {_DOC_UPLOAD_MAX_BYTES // (1024 * 1024)} MB",
        )
    storage_path = f"{tenant_id}/{uuid.uuid4().hex}{file_ext}"
    await _storage.upload_bytes(
        DOCUMENTS_BUCKET, storage_path, content, file.content_type or "application/octet-stream"
    )
    # Bucket privado: grava a referência; a resposta devolve URL assinada.
    file_url = storage_ref(storage_path)

    # Salvar arquivo temporário para parsing
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    # Criar registro no banco
    document = ClientDocument(
        tenant_id=tenant_id,
        client_id=client_id,
        name=file.filename or "Documento sem nome",
        document_type=document_type,
        file_url=file_url,
        status="available",
        parse_status="processing",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    await log_audit_event(
        db=db,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="document.upload",
        entity_type="document",
        entity_id=document.id,
        after_data={"name": document.name, "document_type": document.document_type},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    await _webhook_svc.dispatch_event(
        db=db,
        tenant_id=tenant_id,
        event="document.uploaded",
        data={
            "id": str(document.id),
            "name": document.name,
            "client_id": str(client_id),
            "document_type": document.document_type,
        },
    )

    # Parsing na fila em Postgres (antes: BackgroundTasks, que morria quando o
    # Cloud Run desligava a instância). Tenta já, numa task; se a instância cair,
    # o tick horário retoma baixando o arquivo do Storage.
    from app.services import job_queue
    from app.services.job_handlers import DOCUMENT_PARSE, document_parse_key

    job = await job_queue.enqueue(
        db,
        DOCUMENT_PARSE,
        {
            "document_id": str(document.id),
            "storage_path": storage_path,
            "file_name": file.filename or "file",
            "tmp_path": tmp_path,
        },
        tenant_id=tenant_id,
        idempotency_key=document_parse_key(document.id),
    )
    job_id = job.id
    await db.commit()
    job_queue.kick()

    out = (await _documents_out([document], tenant_id))[0]
    return DocumentUploadResponse(**out.model_dump(), job_id=job_id)


@router.get("/clients/{client_id}/documents", response_model=list[DocumentResponse])
async def list_client_documents(
    client_id: uuid.UUID,
    page: Page = Depends(page_params),
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    """Lista documentos de um cliente."""
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, client_id)

    stmt = select(ClientDocument).where(
        ClientDocument.tenant_id == tenant_id,
        ClientDocument.client_id == client_id,
    )
    docs = await paginate(
        db, stmt.order_by(ClientDocument.created_at.desc(), ClientDocument.id.desc()), page
    )
    return await _documents_out(docs, tenant_id)


async def apply_document_parse(
    db: AsyncSession,
    document_id: uuid.UUID,
    tenant_id: uuid.UUID,
    file_path: str,
    file_name: str,
) -> Optional[str]:
    """Faz o parse e grava o resultado no documento. Levanta em erro inesperado
    (a fila decide o retry). Retorna o parse_status final, ou None se o
    documento não existe mais."""
    parsed_data, error = await parse_document(file_path, file_name)

    result = await db.execute(
        select(ClientDocument).where(
            (ClientDocument.id == document_id)
            & (ClientDocument.tenant_id == tenant_id)
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        return None

    skipped_reason = None if error else is_skipped(parsed_data)
    if error:
        document.parse_status = "failed"
        document.parse_error = error
    elif skipped_reason:
        # Formato aceito que o parser não lê (imagem sem OCR, .doc):
        # não é falha — registra o motivo e não chama a IA.
        document.parse_status = "skipped"
        document.parse_error = skipped_reason
        document.parsed_data = parsed_data
        document.parsed_at = datetime.now(timezone.utc)
    else:
        # Classificação por IA conta no saldo mensal de IA do plano
        # (plans.max_ai_calls_month). Sem saldo, o documento é lido igual,
        # só sem a classificação, e o motivo fica registrado.
        allowed, reason = await ai_classification_allowed(db, tenant_id)
        ai_classification = None
        if allowed:
            ai_classification = await classify_fiscal_document(
                parsed_data,
                file_name=file_name,
                declared_document_type=document.document_type,
            )
        elif reason:
            parsed_data = {**(parsed_data or {}), "ai_classification_skipped": reason}
        if ai_classification:
            parsed_data = {
                **(parsed_data or {}),
                "ai_classification": ai_classification,
            }
            document.ai_classified_at = datetime.now(timezone.utc)

        document.parse_status = "completed"
        document.parsed_data = parsed_data
        document.parsed_at = datetime.now(timezone.utc)

    db.add(document)
    await db.commit()
    return document.parse_status


async def mark_document_parse_failed(
    db: AsyncSession, document_id: uuid.UUID, tenant_id: uuid.UUID, error: str
) -> None:
    """Falha definitiva do job: o documento não fica preso em 'processing'."""
    result = await db.execute(
        select(ClientDocument).where(
            (ClientDocument.id == document_id) & (ClientDocument.tenant_id == tenant_id)
        )
    )
    document = result.scalar_one_or_none()
    if document and document.parse_status in ("processing", "pending"):
        document.parse_status = "failed"
        document.parse_error = error
        await db.commit()


async def _parse_document_background(
    document_id: uuid.UUID,
    file_path: str,
    file_name: str,
    tenant_id: uuid.UUID,
) -> None:
    """Parse em BackgroundTasks (ainda usado pela coleta via WhatsApp)."""
    import os
    from app.core.deps import _set_current_tenant_context, get_sessionmaker

    try:
        async_session = get_sessionmaker()
        async with async_session() as db:
            await _set_current_tenant_context(db, tenant_id)
            await apply_document_parse(db, document_id, tenant_id, file_path, file_name)

    except Exception as e:
        logger.error(f"Background parsing error for document {document_id}: {str(e)}")

    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.error(f"Error cleaning temp file {file_path}: {str(e)}")
