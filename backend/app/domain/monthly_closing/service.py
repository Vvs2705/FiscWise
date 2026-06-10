import uuid
import calendar
import logging
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import select, func, and_, or_

from app.domain.monthly_closing.models import MonthlyClosing
from app.domain.monthly_closing.repository import MonthlyClosingRepository
from app.domain.invoices.models import Invoice
from app.domain.guias.models import TaxGuide
from app.models.operations import AccountingClient, DeadlineItem
from app.core.audit import audit_log

logger = logging.getLogger(__name__)

# Mirrors the checklist template the frontend renders. Stored per closing so
# each closing can evolve independently of future template changes.
DEFAULT_CHECKLIST = [
    {"id": "ck-01", "label": "Documentos do cliente recebidos"},
    {"id": "ck-02", "label": "Notas fiscais emitidas"},
    {"id": "ck-03", "label": "Guias geradas e enviadas"},
    {"id": "ck-04", "label": "Comprovantes de pagamento anexados"},
    {"id": "ck-05", "label": "Obrigações acessórias cumpridas"},
    {"id": "ck-06", "label": "Consulta e-CAC realizada"},
    {"id": "ck-07", "label": "Pendências fiscais verificadas"},
    {"id": "ck-08", "label": "Dossiê gerado e enviado"},
]


def _competence_bounds(competence: str) -> tuple[date, date]:
    """Return (first_day, last_day) for a YYYY-MM competence string."""
    year, month = int(competence[:4]), int(competence[5:7])
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _fresh_checklist() -> List[dict]:
    return [{**item, "status": "pending", "notes": None, "completed_at": None} for item in DEFAULT_CHECKLIST]


def _recompute(closing: MonthlyClosing) -> None:
    """Recompute score, status and blockers from the checklist state."""
    items = closing.checklist or []
    countable = [i for i in items if i.get("status") != "na"]
    done = [i for i in countable if i.get("status") == "done"]
    blocked = [i for i in countable if i.get("status") == "blocked"]

    closing.score = round((len(done) / len(countable)) * 100) if countable else 0
    closing.blockers = [i["label"] for i in blocked]

    if closing.dossier_generated_at and not blocked and len(done) == len(countable):
        closing.status = "completed"
    elif blocked:
        closing.status = "blocked"
    elif countable and len(done) == len(countable):
        closing.status = "ready_for_review"
    elif done:
        closing.status = "in_progress"
    else:
        closing.status = "not_started"


# Invoices in these statuses no longer count toward the competence totals.
_INVOICE_DEAD_STATUSES = ("cancelled", "replaced", "failed")


class MonthlyClosingService:
    def __init__(self, repo: MonthlyClosingRepository):
        self.repo = repo

    async def _collect_counters(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        first_day: date,
        last_day: date,
    ) -> dict:
        """Count real invoices, tax guides and deadline items for the competence."""
        invoice_counts = await self.repo.db.execute(
            select(
                func.count(Invoice.id).filter(Invoice.status.notin_(_INVOICE_DEAD_STATUSES)),
                func.count(Invoice.id).filter(
                    and_(
                        Invoice.status.notin_(_INVOICE_DEAD_STATUSES),
                        Invoice.status != "issued",
                    )
                ),
            ).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.client_id == client_id,
                    Invoice.competencia >= first_day,
                    Invoice.competencia <= last_day,
                )
            )
        )
        invoices_count, invoices_pending = invoice_counts.one()

        guide_counts = await self.repo.db.execute(
            select(
                func.count(TaxGuide.id),
                func.count(TaxGuide.id).filter(
                    or_(TaxGuide.status == "paga", TaxGuide.paga_em.is_not(None))
                ),
            ).where(
                and_(
                    TaxGuide.tenant_id == tenant_id,
                    TaxGuide.client_id == client_id,
                    TaxGuide.competencia >= first_day,
                    TaxGuide.competencia <= last_day,
                )
            )
        )
        guides_count, guides_paid = guide_counts.one()

        deadline_counts = await self.repo.db.execute(
            select(
                func.count(DeadlineItem.id),
                func.count(DeadlineItem.id).filter(DeadlineItem.status == "completed"),
            ).where(
                and_(
                    DeadlineItem.tenant_id == tenant_id,
                    DeadlineItem.client_id == client_id,
                    DeadlineItem.due_date >= first_day,
                    DeadlineItem.due_date <= last_day,
                )
            )
        )
        obligations_total, obligations_done = deadline_counts.one()

        return {
            "invoices_count": invoices_count or 0,
            "invoices_pending": invoices_pending or 0,
            "guides_count": guides_count or 0,
            "guides_paid": guides_paid or 0,
            "obligations_total": obligations_total or 0,
            "obligations_done": obligations_done or 0,
        }

    async def list_closings(self, tenant_id: uuid.UUID, competence: Optional[str] = None) -> List[MonthlyClosing]:
        return await self.repo.list_closings(tenant_id, competence)

    async def get_closing(self, closing_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[MonthlyClosing]:
        return await self.repo.get_by_id(closing_id, tenant_id)

    async def generate_for_competence(self, tenant_id: uuid.UUID, competence: str) -> dict:
        """Create one closing per active client for the competence (idempotent)."""
        first_day, last_day = _competence_bounds(competence)

        result = await self.repo.db.execute(
            select(AccountingClient).where(
                and_(
                    AccountingClient.tenant_id == tenant_id,
                    AccountingClient.status == "active",
                )
            )
        )
        clients = list(result.scalars().all())

        created = 0
        skipped = 0
        new_closings: List[MonthlyClosing] = []

        for client in clients:
            existing = await self.repo.get_by_client_competence(client.id, competence, tenant_id)
            if existing:
                skipped += 1
                continue

            # Seed counters from real invoices, guides and deadline items.
            counters = await self._collect_counters(tenant_id, client.id, first_day, last_day)

            new_closings.append(
                MonthlyClosing(
                    tenant_id=tenant_id,
                    client_id=client.id,
                    competence=competence,
                    status="not_started",
                    score=0,
                    blockers=[],
                    checklist=_fresh_checklist(),
                    **counters,
                )
            )
            created += 1

        if new_closings:
            await self.repo.add_all(new_closings)

        await audit_log(
            action="monthly_closing.generated",
            tenant_id=str(tenant_id),
            details={"competence": competence, "created": created, "skipped": skipped},
        )
        return {"competence": competence, "created": created, "skipped": skipped}

    async def update_checklist_item(
        self,
        closing_id: uuid.UUID,
        item_id: str,
        tenant_id: uuid.UUID,
        *,
        status: str,
        notes: Optional[str] = None,
    ) -> Optional[MonthlyClosing]:
        closing = await self.repo.get_by_id(closing_id, tenant_id)
        if not closing:
            return None

        # Deep-copy the items: mutating the loaded dicts in place would make the
        # old and new JSONB values compare equal and SQLAlchemy would skip the
        # UPDATE for this column.
        items = [dict(i) for i in (closing.checklist or [])]
        target = next((i for i in items if i.get("id") == item_id), None)
        if target is None:
            raise ValueError(f"Checklist item not found: {item_id}")

        target["status"] = status
        if notes is not None:
            target["notes"] = notes
        target["completed_at"] = (
            datetime.now(timezone.utc).isoformat() if status == "done" else None
        )

        # Reassign so SQLAlchemy detects the JSONB mutation.
        closing.checklist = items
        _recompute(closing)
        saved = await self.repo.save(closing)

        await audit_log(
            action="monthly_closing.checklist_updated",
            tenant_id=str(tenant_id),
            details={"closing_id": str(closing_id), "item_id": item_id, "status": status},
        )
        return saved

    async def refresh_counters(self, closing: MonthlyClosing) -> MonthlyClosing:
        """Re-count invoices/guides/obligations so the closing reflects reality."""
        first_day, last_day = _competence_bounds(closing.competence)
        counters = await self._collect_counters(
            closing.tenant_id, closing.client_id, first_day, last_day
        )
        for field, value in counters.items():
            setattr(closing, field, value)
        return await self.repo.save(closing)

    async def generate_dossier(self, closing_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[MonthlyClosing]:
        closing = await self.repo.get_by_id(closing_id, tenant_id)
        if not closing:
            return None

        # Counters must be fresh: the dossier snapshot is built from them.
        first_day, last_day = _competence_bounds(closing.competence)
        counters = await self._collect_counters(tenant_id, closing.client_id, first_day, last_day)
        for field, value in counters.items():
            setattr(closing, field, value)

        closing.dossier_generated_at = datetime.now(timezone.utc)

        # Generating the dossier completes the corresponding checklist item.
        # Deep copy for the same JSONB change-detection reason as above.
        items = [dict(i) for i in (closing.checklist or [])]
        for item in items:
            if item.get("id") == "ck-08" and item.get("status") != "done":
                item["status"] = "done"
                item["completed_at"] = closing.dossier_generated_at.isoformat()
        closing.checklist = items

        _recompute(closing)
        saved = await self.repo.save(closing)

        await audit_log(
            action="monthly_closing.dossier_generated",
            tenant_id=str(tenant_id),
            details={"closing_id": str(closing_id)},
        )
        return saved
