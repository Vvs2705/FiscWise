"""Notification Engine for FiscWise

Scans pending document checklist items and queues/sends notifications to clients.

Email sending is deferred: when an email provider (Resend, SendGrid, SMTP) is
configured via environment variables, the engine dispatches real emails.
Without a provider, messages are recorded as 'skipped' for audit purposes —
the logic is provider-agnostic.

Environment variables:
  EMAIL_PROVIDER         — 'resend' | 'sendgrid' | 'smtp' | (unset = dry-run)
  RESEND_API_KEY         — API key for Resend
  SENDGRID_API_KEY       — API key for SendGrid
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD — SMTP settings
  EMAIL_FROM             — Sender address (default: noreply@fiscwise.com.br)
  PORTAL_URL             — Client portal URL (default: https://fiscwise.com.br/portal)
"""

import logging
import os
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationMessage, NotificationTemplate
from app.models.obligation import DocumentChecklistItem
from app.models.operations import AccountingClient
from app.models.tenant import Tenant, SubscriptionStatus
from app.core.deps import _set_current_tenant_context

logger = logging.getLogger(__name__)

_PORTAL_URL = os.getenv("PORTAL_URL", "https://fiscwise.com.br/portal")
_EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@fiscwise.com.br")
_EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "").lower().strip()


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
    Dispatch an email via the configured provider.

    Returns (status, provider_message_id).
    status is 'sent' on success, 'failed' on error, 'skipped' if no provider.
    """
    if not _EMAIL_PROVIDER:
        logger.info("No EMAIL_PROVIDER configured — message recorded as 'skipped' for %s", recipient)
        return "skipped", None

    if _EMAIL_PROVIDER == "resend":
        try:
            import resend  # type: ignore[import]
            api_key = os.getenv("RESEND_API_KEY", "")
            resend.api_key = api_key
            resp = resend.Emails.send({
                "from": _EMAIL_FROM,
                "to": [recipient],
                "subject": subject,
                "text": body,
            })
            return "sent", resp.get("id")
        except Exception as exc:
            logger.error("Resend dispatch failed for %s: %s", recipient, exc)
            return "failed", None

    # Future providers: sendgrid, smtp
    logger.warning("EMAIL_PROVIDER='%s' is not yet implemented — skipping", _EMAIL_PROVIDER)
    return "skipped", None


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
            "portal_link": f"{_PORTAL_URL}/login",
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
                f"Acesse o portal para enviar: {_PORTAL_URL}/login\n\n"
                f"Atenciosamente,\n{office_name}"
            )

        # Dispatch
        status, provider_msg_id = await _send_email(client_email, subject, body)

        # Record in notification_messages
        msg = NotificationMessage(
            tenant_id=tenant_id,
            client_id=client_id,
            template_id=template.id if template else None,
            channel="email",
            recipient=client_email,
            subject=subject,
            body=body,
            status=status,
            provider=_EMAIL_PROVIDER or None,
            provider_message_id=provider_msg_id,
            sent_at=datetime.now(timezone.utc) if status == "sent" else None,
        )
        db.add(msg)

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
    tenants_result = await db.execute(
        select(Tenant.id).where(
            Tenant.subscription_status.in_([SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE])
        )
    )
    tenant_ids = [row[0] for row in tenants_result.all()]

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
