"""Ajustes fiscais: feriados e prazos por escritório ou regra geral.

Regras de aplicação (decisão do dono, 14/11/2026):
- Ajuste do escritório vale só para os clientes dele.
- Regra geral (tenant_id NULL) vale para todos, mas sempre limitada à UF e,
  se informado, ao município da regra: quem não tem cliente ali não muda nada.
- Ajuste com município vale só para clientes daquele município; sem município,
  para a UF inteira.
- Feriado municipal mexe só em prazo municipal; feriado estadual, em prazo
  estadual e municipal; prazo federal segue o calendário nacional.
- Prazo: o ajuste mais específico vence (município antes de UF; do escritório
  antes do geral).
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Iterable, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.obligations.business_days import today_br
from app.models.ajustes_fiscais import FiscalCalendarAdjustment
from app.models.obligation import ClientObligationProfile, ObligationInstance, ObligationRule
from app.models.operations import AccountingClient

logger = logging.getLogger(__name__)

UFS = frozenset(
    "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
)
STATUS_ABERTOS = ("pending", "in_progress", "overdue")


async def carregar_ajustes(db: AsyncSession, tenant_id: Optional[uuid.UUID]) -> list[FiscalCalendarAdjustment]:
    """Ajustes ativos que valem para o escritório: os dele e os gerais."""
    cond = FiscalCalendarAdjustment.tenant_id.is_(None)
    if tenant_id is not None:
        cond = or_(cond, FiscalCalendarAdjustment.tenant_id == tenant_id)
    res = await db.execute(
        select(FiscalCalendarAdjustment).where(and_(FiscalCalendarAdjustment.ativo.is_(True), cond))
    )
    return list(res.scalars().all())


def ajustes_do_cliente(
    ajustes: Iterable[FiscalCalendarAdjustment], uf: Optional[str], municipio_ibge: Optional[str]
) -> list[FiscalCalendarAdjustment]:
    """Só os ajustes da UF do cliente; os municipais, só do município dele."""
    if not uf:
        return []
    uf = uf.upper()
    mun = str(municipio_ibge) if municipio_ibge else None
    return [
        a for a in ajustes
        if (a.uf or "").upper() == uf and (a.municipio_ibge is None or a.municipio_ibge == mun)
    ]


def feriados_extras(
    ajustes: Iterable[FiscalCalendarAdjustment], anos: Iterable[int]
) -> dict[date, tuple[str, str]]:
    """{data: (nome, nivel)} — nivel "municipio" ou "uf"."""
    result: dict[date, tuple[str, str]] = {}
    anos = list(anos)
    for a in ajustes:
        if a.tipo != "feriado" or not a.mes or not a.dia:
            continue
        nivel = "municipio" if a.municipio_ibge else "uf"
        for ano in ([a.ano] if a.ano else anos):
            try:
                d = date(ano, a.mes, a.dia)
            except ValueError:  # 29/02 em ano não bissexto
                continue
            result.setdefault(d, (a.nome or "Feriado (ajuste fiscal)", nivel))
    return result


def prazo_ajustado(ajustes: Iterable[FiscalCalendarAdjustment], code: Optional[str]) -> Optional[int]:
    """Dia de vencimento ajustado para a obrigação, se houver (o mais específico vence)."""
    if not code:
        return None
    code = code.upper()
    candidatos = [
        a for a in ajustes
        if a.tipo == "prazo" and a.due_day and (a.obrigacao_code or "").upper() == code
    ]
    if not candidatos:
        return None
    candidatos.sort(key=lambda a: (a.municipio_ibge is None, a.tenant_id is None))
    return candidatos[0].due_day


def parametros_de_vencimento(
    ajustes: Iterable[FiscalCalendarAdjustment],
    rule_code: Optional[str],
    uf: Optional[str],
    municipio_ibge: Optional[str],
    competencia: date,
) -> tuple[Optional[int], dict]:
    """(due_day_override, extra_holidays) para compute_due_date."""
    do_cliente = ajustes_do_cliente(ajustes, uf, municipio_ibge)
    if not do_cliente:
        return None, {}
    anos = (competencia.year, competencia.year + 1)
    return prazo_ajustado(do_cliente, rule_code), feriados_extras(do_cliente, anos)


def _local_do_cliente(client: AccountingClient, profile: Optional[ClientObligationProfile]):
    uf = client.uf or (profile.state if profile else None)
    return (uf.upper() if uf else None), client.municipio_ibge


async def recalcular_vencimentos(
    db: AsyncSession,
    *,
    uf: str,
    municipio_ibge: Optional[str] = None,
    tenant_id: Optional[uuid.UUID] = None,
) -> int:
    """Recalcula o vencimento das obrigações abertas (vencimento >= hoje) dos
    clientes da UF/município. Com ``tenant_id``, só daquele escritório; sem,
    de todos (rodar sem contexto de escritório). Devolve quantas mudaram.
    """
    from app.services.obligation_engine import compute_due_date

    uf = uf.upper()
    stmt = (
        select(ObligationInstance, AccountingClient, ClientObligationProfile, ObligationRule)
        .join(AccountingClient, AccountingClient.id == ObligationInstance.client_id)
        .join(ObligationRule, ObligationRule.id == ObligationInstance.rule_id)
        .outerjoin(
            ClientObligationProfile,
            and_(
                ClientObligationProfile.client_id == AccountingClient.id,
                ClientObligationProfile.tenant_id == AccountingClient.tenant_id,
            ),
        )
        .where(
            ObligationInstance.status.in_(STATUS_ABERTOS),
            ObligationInstance.due_date >= today_br(),
            or_(AccountingClient.uf == uf, ClientObligationProfile.state == uf),
        )
    )
    if municipio_ibge:
        stmt = stmt.where(AccountingClient.municipio_ibge == str(municipio_ibge))
    if tenant_id is not None:
        stmt = stmt.where(ObligationInstance.tenant_id == tenant_id)

    linhas = (await db.execute(stmt)).all()
    cache: dict[uuid.UUID, list[FiscalCalendarAdjustment]] = {}
    mudaram = 0
    for inst, client, profile, rule in linhas:
        if inst.tenant_id not in cache:
            cache[inst.tenant_id] = await carregar_ajustes(db, inst.tenant_id)
        c_uf, c_mun = _local_do_cliente(client, profile)
        override, extras = parametros_de_vencimento(
            cache[inst.tenant_id], rule.code, c_uf, c_mun, inst.competence_month
        )
        novo = compute_due_date(
            rule, inst.competence_month.year, inst.competence_month.month,
            uf=c_uf, municipio_ibge=c_mun, due_day_override=override, extra_holidays=extras,
        )
        if novo != inst.due_date:
            inst.due_date = novo
            mudaram += 1
    if mudaram:
        logger.info("ajustes_fiscais: %s vencimentos recalculados (uf=%s mun=%s tenant=%s)",
                    mudaram, uf, municipio_ibge, tenant_id)
    return mudaram
