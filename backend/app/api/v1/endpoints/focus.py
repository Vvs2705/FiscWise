"""Daily focus aggregator.

Builds the "what needs your attention today" list from real sources:
pending deadline items, unread fiscal mailbox messages, unpaid tax guides,
expiring digital certificates and pending client documents. Read-only —
no new tables.
"""

import uuid
from datetime import date, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.operations import (
    AccountingClient,
    ClientDocument,
    DeadlineItem,
    DigitalCertificate,
)
from app.domain.fiscal_mailbox.models import FiscalMailboxMessage
from app.domain.guias.models import TaxGuide

router = APIRouter(prefix="/focus", tags=["Daily Focus"])

_SOURCE_LIMIT = 20


def _item(
    *,
    id: str,
    group: str,
    type: str,
    title: str,
    client: str,
    competence: str | None,
    deadline: str | None,
    risk: str,
    status: str,
    primary_label: str,
    primary_href: str,
    secondary_label: str | None = None,
    secondary_href: str | None = None,
    responsible: str = "Você",
) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "id": id,
        "group": group,
        "type": type,
        "title": title,
        "client": client,
        "competence": competence,
        "deadline": deadline,
        "risk": risk,
        "status": status,
        "responsible": responsible,
        "primary_action": {"label": primary_label, "href": primary_href},
    }
    if secondary_label and secondary_href:
        item["secondary_action"] = {"label": secondary_label, "href": secondary_href}
    return item


@router.get("")
async def get_focus_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id: uuid.UUID = current_user.tenant_id
    today = date.today()
    week_limit = today + timedelta(days=7)
    cert_limit = today + timedelta(days=30)
    items: List[Dict[str, Any]] = []

    # 1. Pending deadline items (overdue -> critical, today -> today, next 7d -> week)
    deadlines = await db.execute(
        select(DeadlineItem, AccountingClient.name)
        .join(AccountingClient, AccountingClient.id == DeadlineItem.client_id)
        .where(
            and_(
                DeadlineItem.tenant_id == tenant_id,
                DeadlineItem.status == "pending",
                DeadlineItem.due_date <= week_limit,
            )
        )
        .order_by(DeadlineItem.due_date.asc())
        .limit(_SOURCE_LIMIT)
    )
    for deadline, client_name in deadlines.all():
        if deadline.due_date < today:
            group, risk, suffix = "critical", "critical", " — em atraso"
        elif deadline.due_date == today:
            group, risk, suffix = "today", "high", " — vence hoje"
        else:
            group, risk, suffix = "week", "medium", ""
        items.append(
            _item(
                id=f"deadline-{deadline.id}",
                group=group,
                type="obligation",
                title=f"{deadline.title}{suffix}",
                client=client_name,
                competence=deadline.due_date.strftime("%Y-%m"),
                deadline=deadline.due_date.isoformat(),
                risk=risk,
                status=deadline.status,
                primary_label="Ver obrigação",
                primary_href="/obrigacoes",
            )
        )

    # 2. Unresolved fiscal mailbox messages
    messages = await db.execute(
        select(FiscalMailboxMessage)
        .where(
            and_(
                FiscalMailboxMessage.tenant_id == tenant_id,
                FiscalMailboxMessage.status.in_(["unread", "read", "in_progress"]),
                FiscalMailboxMessage.risk.in_(["critical", "high", "medium"]),
            )
        )
        .order_by(FiscalMailboxMessage.received_at.desc().nullslast())
        .limit(_SOURCE_LIMIT)
    )
    for msg in messages.scalars().all():
        group = "critical" if msg.risk in ("critical", "high") else "week"
        items.append(
            _item(
                id=f"mailbox-{msg.id}",
                group=group,
                type="ecac",
                title=msg.subject,
                client=msg.client_name or "—",
                competence=None,
                deadline=msg.deadline.date().isoformat() if msg.deadline else None,
                risk=msg.risk,
                status=msg.status,
                primary_label="Ver mensagem",
                primary_href="/caixa-postal-fiscal",
            )
        )

    # 3. Unpaid tax guides due within the window
    guides = await db.execute(
        select(TaxGuide, AccountingClient.name)
        .join(AccountingClient, AccountingClient.id == TaxGuide.client_id)
        .where(
            and_(
                TaxGuide.tenant_id == tenant_id,
                TaxGuide.status.notin_(["paga", "paid", "cancelada"]),
                TaxGuide.vencimento <= week_limit,
            )
        )
        .order_by(TaxGuide.vencimento.asc())
        .limit(_SOURCE_LIMIT)
    )
    for guide, client_name in guides.all():
        if guide.vencimento < today:
            group, risk = "critical", "critical"
        elif guide.vencimento == today:
            group, risk = "today", "high"
        else:
            group, risk = "week", "medium"
        items.append(
            _item(
                id=f"guide-{guide.id}",
                group=group,
                type="guide",
                title=f"{guide.tipo} — pagamento pendente",
                client=client_name,
                competence=guide.competencia.strftime("%Y-%m") if guide.competencia else None,
                deadline=guide.vencimento.isoformat(),
                risk=risk,
                status=guide.status,
                primary_label="Ver guia",
                primary_href=f"/guias/{guide.id}",
            )
        )

    # 4. Certificates expiring within 30 days
    certificates = await db.execute(
        select(DigitalCertificate, AccountingClient.name)
        .join(AccountingClient, AccountingClient.id == DigitalCertificate.client_id)
        .where(
            and_(
                DigitalCertificate.tenant_id == tenant_id,
                DigitalCertificate.status == "valid",
                DigitalCertificate.valid_until >= today,
                DigitalCertificate.valid_until <= cert_limit,
            )
        )
        .order_by(DigitalCertificate.valid_until.asc())
        .limit(_SOURCE_LIMIT)
    )
    for cert, client_name in certificates.all():
        days_left = (cert.valid_until - today).days
        items.append(
            _item(
                id=f"certificate-{cert.id}",
                group="week",
                type="certificate",
                title=f"Certificado vencendo em {days_left} dia{'s' if days_left != 1 else ''}",
                client=client_name,
                competence=None,
                deadline=cert.valid_until.isoformat(),
                risk="medium" if days_left > 7 else "high",
                status="expiring",
                primary_label="Renovar certificado",
                primary_href="/certificados",
            )
        )

    # 5. Documents waiting on the client
    documents = await db.execute(
        select(ClientDocument, AccountingClient.name)
        .join(AccountingClient, AccountingClient.id == ClientDocument.client_id)
        .where(
            and_(
                ClientDocument.tenant_id == tenant_id,
                ClientDocument.status == "pending",
            )
        )
        .order_by(ClientDocument.created_at.desc())
        .limit(_SOURCE_LIMIT)
    )
    for doc, client_name in documents.all():
        items.append(
            _item(
                id=f"document-{doc.id}",
                group="waiting_client",
                type="document",
                title=f"Documento pendente: {doc.name}",
                client=client_name,
                competence=None,
                deadline=None,
                risk="medium",
                status="pending",
                responsible="Cliente",
                primary_label="Ver documentos",
                primary_href="/documentos",
                secondary_label="Enviar WhatsApp",
                secondary_href="/whatsapp",
            )
        )

    return {"items": items}
