"""Fiscal Obligation Engine for FiscWise.

Generates ObligationInstance records for all active clients each month
based on their ClientObligationProfile and the global ObligationRule catalog.

Entry points:
  - generate_obligations_for_month(db, year, month) — called by scheduler on 1st
  - get_applicable_rules(profile, all_rules) — pure function, easily testable
"""

import calendar
import logging
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.obligation import (
    ClientObligationProfile,
    DocumentChecklistItem,
    ObligationInstance,
    ObligationRule,
)
from app.models.operations import AccountingClient
from app.models.tenant import Tenant, SubscriptionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure logic — rule matching
# ---------------------------------------------------------------------------

def get_applicable_rules(
    profile: ClientObligationProfile,
    all_rules: List[ObligationRule],
    year: int,
    month: int,
) -> List[ObligationRule]:
    """Return the subset of rules that apply to a client profile in a given month.

    Filters:
      - rule.active must be True
      - rule.valid_from / valid_until must include the competence month (if set)
      - rule.applies_to_regimes: must include profile.tax_regime (if set)
      - rule.applies_to_entity_types: handled by presence of profile data
      - rule.requires_employees: profile.has_employees must be True
      - rule.recurrence == 'monthly' — always included if other checks pass
      - rule.recurrence == 'yearly'  — included only in the yearly due month
        (approximated as December for annual rules; due_day controls the day)
      - rule.recurrence == 'quarterly' — included for months 3, 6, 9, 12
    """
    competence_start = date(year, month, 1)
    result = []

    for rule in all_rules:
        if not rule.active:
            continue

        # Date validity
        if rule.valid_from and competence_start < rule.valid_from:
            continue
        if rule.valid_until and competence_start > rule.valid_until:
            continue

        # Employee requirement
        if rule.requires_employees and not profile.has_employees:
            continue

        # Tax regime match
        if rule.applies_to_regimes and profile.tax_regime:
            if profile.tax_regime not in rule.applies_to_regimes:
                continue
        elif rule.applies_to_regimes and not profile.tax_regime:
            # Rule requires a regime but client has none set — skip
            continue

        # Recurrence filter
        if rule.recurrence == "monthly":
            pass  # Always include
        elif rule.recurrence == "quarterly":
            if month not in (3, 6, 9, 12):
                continue
        elif rule.recurrence == "yearly":
            # Annual obligations are due in specific months. By convention we
            # generate them in January so the office has time to prepare.
            if month != 1:
                continue
        elif rule.recurrence == "event":
            # Event-driven rules are never auto-generated
            continue

        result.append(rule)

    return result


def compute_due_date(rule: ObligationRule, year: int, month: int) -> date:
    """Calculate the due date for a rule in a given competence month."""
    due_day = rule.due_day or 20

    # For yearly rules due in January, due date is in the same month
    if rule.recurrence == "yearly":
        max_day = calendar.monthrange(year, month)[1]
        return date(year, month, min(due_day, max_day))

    # Monthly / quarterly: due date is in the FOLLOWING month to give time
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    max_day = calendar.monthrange(next_year, next_month)[1]
    return date(next_year, next_month, min(due_day, max_day))


# ---------------------------------------------------------------------------
# Main engine — scheduled job
# ---------------------------------------------------------------------------

async def generate_obligations_for_month(
    db: AsyncSession,
    year: int,
    month: int,
) -> dict:
    """Generate ObligationInstance records for all active clients.

    Idempotent: skips instances that already exist for (client_id, rule_id, competence_month).

    Returns a summary dict: {created, skipped, tenants_processed, errors}.
    """
    competence_month = date(year, month, 1)
    logger.info("Obligation engine starting for competence_month=%s", competence_month)

    # Load all active rules upfront
    rules_result = await db.execute(
        select(ObligationRule).where(ObligationRule.active == True)
    )
    all_rules: List[ObligationRule] = rules_result.scalars().all()

    if not all_rules:
        logger.warning("No active obligation rules found — skipping generation")
        return {"created": 0, "skipped": 0, "tenants_processed": 0, "errors": 0}

    # Load all active tenants (trial or active subscriptions)
    tenants_result = await db.execute(
        select(Tenant).where(
            Tenant.subscription_status.in_([SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE])
        )
    )
    tenants = tenants_result.scalars().all()

    total_created = 0
    total_skipped = 0
    total_errors = 0

    for tenant in tenants:
        try:
            # Get all active clients for this tenant
            clients_result = await db.execute(
                select(AccountingClient).where(
                    and_(
                        AccountingClient.tenant_id == tenant.id,
                        AccountingClient.status == "active",
                    )
                )
            )
            clients = clients_result.scalars().all()

            for client in clients:
                # Fetch fiscal profile (may not exist yet)
                profile_result = await db.execute(
                    select(ClientObligationProfile).where(
                        ClientObligationProfile.client_id == client.id
                    )
                )
                profile = profile_result.scalar_one_or_none()

                if not profile:
                    # No profile configured — skip this client
                    continue

                applicable_rules = get_applicable_rules(profile, all_rules, year, month)

                for rule in applicable_rules:
                    # Idempotency check
                    existing_result = await db.execute(
                        select(ObligationInstance).where(
                            and_(
                                ObligationInstance.client_id == client.id,
                                ObligationInstance.rule_id == rule.id,
                                ObligationInstance.competence_month == competence_month,
                            )
                        )
                    )
                    if existing_result.scalar_one_or_none():
                        total_skipped += 1
                        continue

                    due_date = compute_due_date(rule, year, month)

                    instance = ObligationInstance(
                        tenant_id=tenant.id,
                        client_id=client.id,
                        rule_id=rule.id,
                        competence_month=competence_month,
                        due_date=due_date,
                        status="pending",
                        priority=_compute_priority(rule, due_date),
                    )
                    db.add(instance)
                    total_created += 1

            await db.commit()

        except Exception as exc:
            logger.error(
                "Error generating obligations for tenant_id=%s: %s",
                tenant.id, exc, exc_info=True,
            )
            try:
                await db.rollback()
            except Exception:
                pass
            total_errors += 1

    summary = {
        "created": total_created,
        "skipped": total_skipped,
        "tenants_processed": len(tenants),
        "errors": total_errors,
    }
    logger.info("Obligation engine completed: %s", summary)
    return summary


def _compute_priority(rule: ObligationRule, due_date: date) -> str:
    """Compute initial priority based on rule jurisdiction and due date proximity."""
    today = date.today()
    days_until_due = (due_date - today).days

    if days_until_due <= 3:
        return "critical"
    if days_until_due <= 7:
        return "high"
    if rule.jurisdiction == "federal":
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Checklist helpers
# ---------------------------------------------------------------------------

async def get_client_checklist(
    db: AsyncSession,
    tenant_id: UUID,
    client_id: UUID,
    competence_month: date,
) -> List[DocumentChecklistItem]:
    """Fetch all checklist items for a client in a given month."""
    result = await db.execute(
        select(DocumentChecklistItem).where(
            and_(
                DocumentChecklistItem.tenant_id == tenant_id,
                DocumentChecklistItem.client_id == client_id,
                DocumentChecklistItem.competence_month == competence_month,
            )
        ).order_by(DocumentChecklistItem.created_at)
    )
    return result.scalars().all()
