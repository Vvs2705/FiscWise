"""Leitura em cache (TTL 5 min) dos catálogos globais: planos e regras de obrigação.

As duas tabelas não têm tenant_id e só mudam por migration/seed ou pelo motor de
obrigações (que chama `invalidate_obligation_rules()`). O cache guarda cópias
congeladas, nunca objetos ORM, para não vazar estado entre sessões.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ttl_cache import obligation_rules_cache, plans_cache
from app.models.obligation import ObligationRule
from app.models.plan import Plan


@dataclass(frozen=True)
class PlanSnapshot:
    id: uuid.UUID
    slug: str
    name: str
    description: Optional[str]
    price_monthly: Optional[Decimal]
    max_clients: Optional[int]
    max_users: Optional[int]
    max_ai_calls_month: Optional[int]
    max_documents_per_client: Optional[int]
    features: Optional[Dict[str, Any]]
    active: bool

    @classmethod
    def from_model(cls, p: Plan) -> "PlanSnapshot":
        return cls(
            id=p.id, slug=p.slug, name=p.name, description=p.description,
            price_monthly=p.price_monthly, max_clients=p.max_clients, max_users=p.max_users,
            max_ai_calls_month=p.max_ai_calls_month,
            max_documents_per_client=p.max_documents_per_client,
            features=dict(p.features) if p.features else p.features,
            active=bool(p.active),
        )


@dataclass(frozen=True)
class ObligationRuleSnapshot:
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str]
    jurisdiction: str
    state: Optional[str]
    applies_to_regimes: Optional[Tuple[str, ...]]
    recurrence: str
    due_day: Optional[int]
    requires_employees: bool
    active: bool


async def _load_plans(db: AsyncSession) -> Dict[str, PlanSnapshot]:
    rows = (await db.execute(select(Plan))).scalars().all()
    return {p.slug: PlanSnapshot.from_model(p) for p in rows}


async def _all_plans(db: AsyncSession) -> Dict[str, PlanSnapshot]:
    return await plans_cache.get_or_load("all", lambda: _load_plans(db))


async def get_active_plans(db: AsyncSession) -> list[PlanSnapshot]:
    """Planos ativos, mesma ordem de antes (preço crescente, NULL primeiro)."""
    plans = [p for p in (await _all_plans(db)).values() if p.active]
    plans.sort(key=lambda p: (p.price_monthly is not None, p.price_monthly or 0))
    return plans


async def get_plan_by_slug(db: AsyncSession, slug: Optional[str]) -> Optional[PlanSnapshot]:
    if not slug:
        return None
    return (await _all_plans(db)).get(slug)


async def get_obligation_rules(db: AsyncSession, active_only: bool) -> list[ObligationRuleSnapshot]:
    async def _load() -> tuple:
        stmt = select(ObligationRule)
        if active_only:
            stmt = stmt.where(ObligationRule.active == True)  # noqa: E712
        rows = (
            await db.execute(stmt.order_by(ObligationRule.jurisdiction, ObligationRule.code))
        ).scalars().all()
        return tuple(
            ObligationRuleSnapshot(
                id=r.id, code=r.code, name=r.name, description=r.description,
                jurisdiction=r.jurisdiction, state=r.state,
                applies_to_regimes=(
                    tuple(r.applies_to_regimes) if r.applies_to_regimes else r.applies_to_regimes
                ),
                recurrence=r.recurrence, due_day=r.due_day,
                requires_employees=bool(r.requires_employees), active=bool(r.active),
            )
            for r in rows
        )

    return list(await obligation_rules_cache.get_or_load(("rules", active_only), _load))


def invalidate_plans() -> None:
    plans_cache.invalidate()


def invalidate_obligation_rules() -> None:
    obligation_rules_cache.invalidate()
