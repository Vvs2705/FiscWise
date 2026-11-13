"""Notification Engine for FiscWise

Scans pending document checklist items and queues/sends notifications to clients.

E-mail goes through app.services.email_service (Resend via httpx). Without
RESEND_ENABLED + RESEND_API_KEY nothing is sent and the message is recorded as
'skipped' (reason: email_disabled); a provider error is recorded as 'failed'.

Portal links use settings.portal_url (PORTAL_URL, default APP_URL + "/portal").
"""

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationMessage, NotificationTemplate
from app.models.obligation import DocumentChecklistItem
from app.models.operations import AccountingClient
from app.models.tenant import Tenant, SubscriptionStatus
from app.core.config import settings
from app.core.deps import _set_current_tenant_context
from app.services import email_service

logger = logging.getLogger(__name__)

EMAIL_PROVIDER = "resend"

# Reasons recorded in NotificationMessage.error_message and returned by APIs.
REASON_EMAIL_DISABLED = "email_disabled"
REASON_NO_RECIPIENT = "no_recipient"
REASON_PROVIDER_ERROR = "provider_error"


async def _get_pending_document_template(db: AsyncSession) -> Optional[NotificationTemplate]:
    """Fetch the global pending-documents email template."""
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.tenant_id == None,  # noqa: E711
            NotificationTemplate.channel == "email",
            NotificationTemplate.is_active == True,  # noqa: E712
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def _send_email(recipient: str, subject: str, body: str) -> tuple[str, Optional[str]]:
    """
    Dispatch an email through email_service.

    Returns (status, reason): ('sent', None) on success, ('skipped',
    'email_disabled') when sending is off in this installation, ('failed',
    'provider_error') when the provider refused / the network failed.
    """
    if not recipient:
        return "skipped", REASON_NO_RECIPIENT
    sent = await email_service.send_email(
        to=recipient,
        subject=subject,
        html=email_service.render_client_message_email(subject, body),
    )
    if sent:
        return "sent", None
    if not email_service.is_configured():
        return "skipped", REASON_EMAIL_DISABLED
    return "failed", REASON_PROVIDER_ERROR


async def deliver_client_email(
    db: AsyncSession,
    *,
    tenant_id,
    client_id,
    recipient: Optional[str],
    subject: str,
    body: str,
    template_id=None,
) -> NotificationMessage:
    """Send one e-mail to a client and record it with its REAL outcome.

    The NotificationMessage is added to the session (not committed): the caller
    commits. status is 'sent' | 'skipped' | 'failed'; error_message holds the
    reason (email_disabled | no_recipient | provider_error).
    """
    status, reason = await _send_email(recipient or "", subject, body)
    msg = NotificationMessage(
        tenant_id=tenant_id,
        client_id=client_id,
        template_id=template_id,
        channel="email",
        recipient=recipient or "",
        subject=subject,
        body=body,
        status=status,
        provider=EMAIL_PROVIDER if status != "skipped" else None,
        error_message=reason,
        sent_at=datetime.now(timezone.utc) if status == "sent" else None,
    )
    db.add(msg)
    return msg


async def notify_pending_documents_for_tenant(
    db: AsyncSession,
    tenant_id,
    competence_month: Optional[date] = None,
) -> dict:
    """
    For one tenant: find clients with pending checklist items, send one email per client.

    Idempotent within the same day — skips clients that already received a notification
    today (checks notification_messages created today).

    Returns counts: {sent, skipped, failed, clients_notified}.
    """
    today = date.today()
    comp_month = competence_month or date(today.year, today.month, 1)
    await _set_current_tenant_context(db, tenant_id)

    # Load tenant name for email signature
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        return {"sent": 0, "skipped": 0, "failed": 0, "clients_notified": 0}

    office_name = getattr(tenant, "name", "Escritório Contábil")

    # Fetch default email template
    template = await _get_pending_document_template(db)

    # Find clients with pending checklist items for this month
    pending_result = await db.execute(
        select(
            DocumentChecklistItem.client_id,
            AccountingClient.name.label("client_name"),
            AccountingClient.email.label("client_email"),
        )
        .join(AccountingClient, DocumentChecklistItem.client_id == AccountingClient.id)
        .where(
            DocumentChecklistItem.tenant_id == tenant_id,
            DocumentChecklistItem.competence_month == comp_month,
            DocumentChecklistItem.status == "pending",
            AccountingClient.email != None,  # noqa: E711
        )
        .distinct()
    )
    pending_clients = pending_result.all()

    if not pending_clients:
        return {"sent": 0, "skipped": 0, "failed": 0, "clients_notified": 0}

    # Deduplication: get clients already notified today
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    already_notified_result = await db.execute(
        select(NotificationMessage.client_id).where(
            NotificationMessage.tenant_id == tenant_id,
            NotificationMessage.created_at >= today_start,
            NotificationMessage.status.in_(["sent", "skipped"]),
        )
    )
    already_notified_ids = {row[0] for row in already_notified_result.all()}

    counts = {"sent": 0, "skipped": 0, "failed": 0, "clients_notified": 0}

    for row in pending_clients:
        client_id = row.client_id
        client_name = row.client_name
        client_email = row.client_email

        if client_id in already_notified_ids:
            counts["skipped"] += 1
            continue

        # Gather pending item names for this client
        items_result = await db.execute(
            select(DocumentChecklistItem.document_name).where(
                DocumentChecklistItem.tenant_id == tenant_id,
                DocumentChecklistItem.client_id == client_id,
                DocumentChecklistItem.competence_month == comp_month,
                DocumentChecklistItem.status == "pending",
            )
        )
        item_names = [r[0] for r in items_result.all()]
        pending_list = "\n".join(f"  • {name}" for name in item_names)

        # Render template or use hardcoded fallback
        comp_label = comp_month.strftime("%B/%Y").capitalize()
        context = {
            "client_name": client_name,
            "competence_month": comp_label,
            "pending_items": pending_list,
            "portal_link": f"{settings.portal_url}/login",
            "office_name": office_name,
        }

        if template:
            subject, body = template.render(context)
        else:
            subject = f"Documentos pendentes para {comp_label} — {office_name}"
            body = (
                f"Olá {client_name},\n\n"
                f"Precisamos que você nos envie os seguintes documentos referentes a {comp_label}:\n\n"
                f"{pending_list}\n\n"
                f"Acesse o portal para enviar: {settings.portal_url}/login\n\n"
                f"Atenciosamente,\n{office_name}"
            )

        msg = await deliver_client_email(
            db,
            tenant_id=tenant_id,
            client_id=client_id,
            recipient=client_email,
            subject=subject,
            body=body,
            template_id=template.id if template else None,
        )
        status = msg.status

        if status == "sent":
            counts["sent"] += 1
        elif status == "skipped":
            counts["skipped"] += 1
        else:
            counts["failed"] += 1
        counts["clients_notified"] += 1

    await db.commit()
    logger.info(
        "notify_pending_documents tenant=%s month=%s: %s",
        tenant_id, comp_month, counts,
    )
    return counts


async def notify_pending_documents_all_tenants(db: AsyncSession) -> dict:
    """
    Scheduled job: notify all active tenants.

    Called by the APScheduler weekly job (Mondays at 09:00).
    """
    from app.core.plan_access import acesso_expirado

    tenants_result = await db.execute(
        select(Tenant).where(
            Tenant.subscription_status.in_([SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE])
        )
    )
    # Conta vencida (só leitura) não dispara e-mail para os clientes dela.
    tenant_ids = [t.id for t in tenants_result.scalars().all() if not acesso_expirado(t)]

    totals = {"sent": 0, "skipped": 0, "failed": 0, "tenants_processed": 0, "errors": 0}

    for tid in tenant_ids:
        try:
            result = await notify_pending_documents_for_tenant(db, tid)
            totals["sent"] += result.get("sent", 0)
            totals["skipped"] += result.get("skipped", 0)
            totals["failed"] += result.get("failed", 0)
            totals["tenants_processed"] += 1
        except Exception as exc:
            logger.error("Notification job failed for tenant %s: %s", tid, exc, exc_info=True)
            totals["errors"] += 1

    logger.info("notify_pending_documents_all_tenants completed: %s", totals)
    return totals
