import uuid
import calendar
import logging
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import select, func, and_

from app.domain.monthly_closing.models import MonthlyClosing
from app.domain.monthly_closing.repository import MonthlyClosingRepository
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


class MonthlyClosingService:
    def __init__(self, repo: MonthlyClosingRepository):
        self.repo = repo

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

            # Seed obligation counters from real deadline items in the competence month.
            counts = await self.repo.db.execute(
                select(
                    func.count(DeadlineItem.id),
                    func.count(DeadlineItem.id).filter(DeadlineItem.status == "completed"),
                ).where(
                    and_(
                        DeadlineItem.tenant_id == tenant_id,
                        DeadlineItem.client_id == client.id,
                        DeadlineItem.due_date >= first_day,
                        DeadlineItem.due_date <= last_day,
                    )
                )
            )
            obligations_total, obligations_done = counts.one()

            new_closings.append(
                MonthlyClosing(
                    tenant_id=tenant_id,
                    client_id=client.id,
                    competence=competence,
                    status="not_started",
                    score=0,
                    blockers=[],
                    checklist=_fresh_checklist(),
                    obligations_total=obligations_total or 0,
                    obligations_done=obligations_done or 0,
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

    async def generate_dossier(self, closing_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[MonthlyClosing]:
        closing = await self.repo.get_by_id(closing_id, tenant_id)
        if not closing:
            return None

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
