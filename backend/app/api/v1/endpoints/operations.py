"""Operational MVP endpoints for FiscWise pilots."""

import logging
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import Date as SADate, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.plan_access import PLAN_INTERMEDIARIO, check_chat_quota, require_plan, resolve_plan
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
from app.models.user import User
from app.services.ai_fiscal import classify_fiscal_document, generate_client_operational_summary
from app.services.document_parser import parse_document
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
    DocumentUpdate,
    InadimplenciaReport,
    MonthlyData,
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
    raw = current_user.tenant.plan_slug if current_user.tenant else None
    return resolve_plan(raw, getattr(current_user, "email", None))


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
    await db.commit()
    await db.refresh(instance)
    return instance


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

    async def count_for(statement):
        result = await db.execute(statement)
        return int(result.scalar_one() or 0)

    active_clients = await count_for(
        select(func.count()).select_from(AccountingClient).where(
            AccountingClient.tenant_id == tenant_id,
            AccountingClient.status == "active",
        )
    )
    pending_deadlines = await count_for(
        select(func.count()).select_from(DeadlineItem).where(
            DeadlineItem.tenant_id == tenant_id,
            DeadlineItem.status == "pending",
        )
    )
    overdue_deadlines = await count_for(
        select(func.count()).select_from(DeadlineItem).where(
            DeadlineItem.tenant_id == tenant_id,
            DeadlineItem.status != "completed",
            DeadlineItem.due_date < today,
        )
    )
    certificates_expiring_30d = await count_for(
        select(func.count()).select_from(DigitalCertificate).where(
            DigitalCertificate.tenant_id == tenant_id,
            DigitalCertificate.status == "valid",
            DigitalCertificate.valid_until >= today,
            DigitalCertificate.valid_until <= limit_date,
        )
    )
    open_receivables = await count_for(
        select(func.count()).select_from(AccountReceivable).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status == "pending",
        )
    )
    overdue_receivables = await count_for(
        select(func.count()).select_from(AccountReceivable).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status != "paid",
            AccountReceivable.due_date < today,
        )
    )

    amount_open_result = await db.execute(
        select(func.coalesce(func.sum(AccountReceivable.amount), 0)).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status == "pending",
        )
    )
    amount_overdue_result = await db.execute(
        select(func.coalesce(func.sum(AccountReceivable.amount), 0)).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status != "paid",
            AccountReceivable.due_date < today,
        )
    )
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

    # ── Financeiro: total recebido no mes corrente ─────────────────────────────
    first_of_month = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
    received_month_result = await db.execute(
        select(func.coalesce(func.sum(AccountReceivable.amount), 0)).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status == "paid",
            AccountReceivable.paid_at >= first_of_month,
        )
    )
    total_received_month = Decimal(received_month_result.scalar_one() or 0)

    # ── Financeiro: tendencia mensal (ano corrente) ────────────────────────────
    first_of_year = datetime(today.year, 1, 1, tzinfo=timezone.utc)
    monthly_raw = await db.execute(
        select(
            func.date_trunc("month", AccountReceivable.paid_at).label("month"),
            func.coalesce(func.sum(AccountReceivable.amount), 0).label("total"),
        )
        .where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status == "paid",
            AccountReceivable.paid_at >= first_of_year,
        )
        .group_by(func.date_trunc("month", AccountReceivable.paid_at))
        .order_by(func.date_trunc("month", AccountReceivable.paid_at).asc())
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
        receivables_amount_open=Decimal(amount_open_result.scalar_one() or 0),
        receivables_amount_overdue=Decimal(amount_overdue_result.scalar_one() or 0),
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

    async def count_for(statement) -> int:
        result = await db.execute(statement)
        return int(result.scalar_one() or 0)

    # ── Obligation status totals for this competence month ─────────────────────
    status_raw = await db.execute(
        select(
            ObligationInstance.status,
            func.count().label("cnt"),
        )
        .where(
            ObligationInstance.tenant_id == tenant_id,
            ObligationInstance.competence_month == first_of_month,
        )
        .group_by(ObligationInstance.status)
    )
    status_map: dict[str, int] = {}
    for row in status_raw.all():
        status_map[row.status] = int(row.cnt)

    total_pending = status_map.get("pending", 0)
    total_in_progress = status_map.get("in_progress", 0)
    total_delivered = status_map.get("delivered", 0)
    total_overdue = status_map.get("overdue", 0)

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

    # ── Documents awaiting approval (received but not yet approved) ────────────
    docs_awaiting_approval = await count_for(
        select(func.count()).select_from(DocumentChecklistItem).where(
            DocumentChecklistItem.tenant_id == tenant_id,
            DocumentChecklistItem.competence_month == first_of_month,
            DocumentChecklistItem.status == "received",
        )
    )

    # ── Certificates expiring in the next 30 days ──────────────────────────────
    limit_date = today + timedelta(days=30)
    certificates_expiring_30d = await count_for(
        select(func.count()).select_from(DigitalCertificate).where(
            DigitalCertificate.tenant_id == tenant_id,
            DigitalCertificate.status == "valid",
            DigitalCertificate.valid_until >= today,
            DigitalCertificate.valid_until <= limit_date,
        )
    )

    # ── Overdue receivables ────────────────────────────────────────────────────
    overdue_receivables_count = await count_for(
        select(func.count()).select_from(AccountReceivable).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status != "paid",
            AccountReceivable.due_date < today,
        )
    )
    overdue_amount_result = await db.execute(
        select(func.coalesce(func.sum(AccountReceivable.amount), 0)).where(
            AccountReceivable.tenant_id == tenant_id,
            AccountReceivable.status != "paid",
            AccountReceivable.due_date < today,
        )
    )

    return ProductivityOverview(
        competence_month=competence_str,
        compliance_rate=compliance_rate,
        total_pending=total_pending,
        total_in_progress=total_in_progress,
        total_delivered=total_delivered,
        total_overdue=total_overdue,
        obligations_by_collaborator=obligations_by_collaborator,
        clients_with_most_pending=clients_with_most_pending,
        docs_awaiting_approval=docs_awaiting_approval,
        certificates_expiring_30d=certificates_expiring_30d,
        overdue_receivables_count=overdue_receivables_count,
        overdue_receivables_amount=Decimal(overdue_amount_result.scalar_one() or 0),
    )


@router.get("/clients", response_model=list[AccountingClientResponse])
async def list_clients(
    search: str | None = Query(default=None, max_length=120),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    tax_regime: str | None = Query(default=None, max_length=80),
    entity_type: str | None = Query(default=None, max_length=16),
    cnae_code: str | None = Query(default=None, max_length=20),
    current_user: User = Depends(get_current_user),
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
    result = await db.execute(statement.order_by(AccountingClient.name.asc()))
    return list(result.scalars().all())


@router.get("/clients/{client_id}", response_model=AccountingClientResponse)
async def get_client(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
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
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)

    # ── Plan limit enforcement ────────────────────────────────────────────────
    try:
        from app.core.plan_access import resolve_plan
        from app.models.plan import Plan
        from app.models.tenant import Tenant

        tenant_row = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant_obj = tenant_row.scalar_one_or_none()
        effective_slug = resolve_plan(
            tenant_obj.plan_slug if tenant_obj else None, current_user.email
        ) or "free"

        plan_row = await db.execute(select(Plan).where(Plan.slug == effective_slug))
        plan_obj = plan_row.scalar_one_or_none()

        if plan_obj and plan_obj.max_clients is not None:
            count_result = await db.execute(
                select(func.count()).select_from(AccountingClient).where(
                    AccountingClient.tenant_id == tenant_id,
                    AccountingClient.status == "active",
                )
            )
            current_count = int(count_result.scalar_one() or 0)
            if current_count >= plan_obj.max_clients:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Limite de clientes atingido para o plano {plan_obj.name} "
                        f"({plan_obj.max_clients} clientes ativos). "
                        f"Faça upgrade em fiscwise.com.br/planos."
                    ),
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Plan limit check failed (non-fatal): %s", exc)
    # ─────────────────────────────────────────────────────────────────────────

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
    return client


@router.patch("/clients/{client_id}", response_model=AccountingClientResponse)
@router.put("/clients/{client_id}", response_model=AccountingClientResponse)
async def update_client(
    client_id: uuid.UUID,
    payload: AccountingClientUpdate,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    client = await _get_client_or_404(db, tenant_id, client_id)
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
    return client


@router.delete("/clients/{client_id}", response_model=AccountingClientResponse)
async def deactivate_client(
    client_id: uuid.UUID,
    request: Request = None,
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(DeadlineItem).where(DeadlineItem.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(DeadlineItem.client_id == client_id)
    if status_filter:
        statement = statement.where(DeadlineItem.status == status_filter)
    result = await db.execute(statement.order_by(DeadlineItem.due_date.asc()))
    return list(result.scalars().all())


@router.get("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def get_deadline(
    deadline_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """Buscar prazo especifico por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_item_or_404(db, DeadlineItem, tenant_id, deadline_id, "Deadline not found")


@router.post("/deadlines", response_model=DeadlineResponse, status_code=status.HTTP_201_CREATED)
async def create_deadline(
    payload: DeadlineCreate,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    item = await _get_item_or_404(db, DeadlineItem, tenant_id, deadline_id, "Deadline not found")
    _apply_updates(item, payload)
    if payload.status == "completed" and item.completed_at is None:
        item.completed_at = datetime.now(timezone.utc)
    return await _commit_refresh(db, item)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    client_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(ClientDocument).where(ClientDocument.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(ClientDocument.client_id == client_id)
    result = await db.execute(statement.order_by(ClientDocument.created_at.desc()))
    return list(result.scalars().all())


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Buscar documento especifico por ID."""
    tenant_id = _tenant_id(current_user)
    return await _get_item_or_404(db, ClientDocument, tenant_id, document_id, "Document not found")


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, payload.client_id)
    document = ClientDocument(tenant_id=tenant_id, **payload.model_dump())
    db.add(document)
    return await _commit_refresh(db, document)


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    document = await _get_item_or_404(db, ClientDocument, tenant_id, document_id, "Document not found")
    _apply_updates(document, payload)
    return await _commit_refresh(db, document)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    request: Request = None,
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


@router.post("/documents/upload")
async def upload_document_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Faz upload de arquivo para Supabase Storage e retorna a URL publica."""
    import uuid as _uuid
    import httpx
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

    unique_name = f"{tenant_id}/{_uuid.uuid4().hex}{file_ext}"
    bucket = "documents"

    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # Upload para Supabase Storage via REST
    storage_url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{unique_name}"

    # Supabase Storage aceita tanto o JWT service role quanto as novas chaves
    # sb_secret_* — ambos os headers sao necessarios para compatibilidade
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            storage_url,
            content=file_bytes,
            headers={
                "apikey": settings.SUPABASE_SECRET_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
                "Content-Type": content_type,
                "x-upsert": "false",
            },
        )

    if resp.status_code not in (200, 201):
        logger.error("Supabase Storage upload failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload file to storage",
        )

    # URL publica
    public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{unique_name}"
    return {"url": public_url, "path": unique_name}


@router.get("/certificates", response_model=list[CertificateResponse])
async def list_certificates(
    client_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(DigitalCertificate).where(DigitalCertificate.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(DigitalCertificate.client_id == client_id)
    result = await db.execute(statement.order_by(DigitalCertificate.valid_until.asc()))
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


@router.get("/receivables", response_model=list[ReceivableResponse])
async def list_receivables(
    client_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(current_user)
    statement = select(AccountReceivable).where(AccountReceivable.tenant_id == tenant_id)
    if client_id:
        statement = statement.where(AccountReceivable.client_id == client_id)
    if status_filter:
        statement = statement.where(AccountReceivable.status == status_filter)
    result = await db.execute(statement.order_by(AccountReceivable.due_date.asc()))
    return list(result.scalars().all())


@router.get("/receivables/{receivable_id}", response_model=ReceivableResponse)
async def get_receivable(
    receivable_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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


@router.post("/receivables/generate-monthly")
async def generate_monthly_billing(
    year_month: str = Query(..., regex=r"^\d{4}-\d{2}$", description="Format: YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Gera automaticamente faturas de honorários para clientes com monthly_fee."""
    import calendar
    from dateutil.parser import parse

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
        existing = await db.execute(
            select(AccountReceivable).where(
                (AccountReceivable.client_id == client.id)
                & (AccountReceivable.description.like(f"Honorários - {year_month}%"))
            )
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
        .order_by(AccountReceivable.due_date.desc())
        .limit(limit)
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
    file: UploadFile = File(...),
    document_type: str = Query(..., max_length=80, description="Tipo: contract, secret_sheet, certificate, etc"),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> DocumentResponse:
    """Upload de arquivo para cliente (PDF, Excel, Word)."""
    import tempfile
    import os

    tenant_id = _tenant_id(current_user)

    # Validar cliente
    client = await _get_client_or_404(db, tenant_id, client_id)

    # Simular armazenamento em arquivo temporário
    file_ext = Path(file.filename).suffix if file.filename else ".bin"
    storage_path = f"{tenant_id}/{uuid.uuid4()}{file_ext}"
    file_url = f"https://storage.example.com/documents/{storage_path}"

    # Salvar arquivo temporário para parsing
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
        content = await file.read()
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

    # Agendar parsing em background
    background_tasks.add_task(
        _parse_document_background,
        document.id,
        tmp_path,
        file.filename or "file",
        tenant_id,
        db
    )

    return DocumentResponse.from_orm(document)


@router.get("/clients/{client_id}/documents", response_model=list[DocumentResponse])
async def list_client_documents(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista documentos de um cliente."""
    tenant_id = _tenant_id(current_user)
    await _get_client_or_404(db, tenant_id, client_id)

    stmt = select(ClientDocument).where(ClientDocument.client_id == client_id)
    result = await db.execute(stmt.order_by(ClientDocument.id.desc()))
    return list(result.scalars().all())


async def _parse_document_background(
    document_id: uuid.UUID,
    file_path: str,
    file_name: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Background task to parse document asynchronously."""
    import os

    try:
        parsed_data, error = await parse_document(file_path, file_name)

        # Get document from DB
        result = await db.execute(
            select(ClientDocument).where(
                (ClientDocument.id == document_id)
                & (ClientDocument.tenant_id == tenant_id)
            )
        )
        document = result.scalar_one_or_none()

        if document:
            if error:
                document.parse_status = "failed"
                document.parse_error = error
            else:
                ai_classification = await classify_fiscal_document(
                    parsed_data,
                    file_name=file_name,
                    declared_document_type=document.document_type,
                )
                if ai_classification:
                    parsed_data = {
                        **(parsed_data or {}),
                        "ai_classification": ai_classification,
                    }

                document.parse_status = "completed"
                document.parsed_data = parsed_data
                document.parsed_at = datetime.now(timezone.utc)

            db.add(document)
            await db.commit()

    except Exception as e:
        logger.error(f"Background parsing error for document {document_id}: {str(e)}")

    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.error(f"Error cleaning temp file {file_path}: {str(e)}")
