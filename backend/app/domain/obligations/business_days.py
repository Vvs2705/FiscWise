"""Calendário fiscal: dias úteis, feriados e fuso de Brasília.

Prazos fiscais caem em data de Brasília e, quando o dia não é útil, são
antecipados ou prorrogados conforme a norma de cada obrigação. Federal usa
só o calendário nacional; estadual soma os feriados da UF; municipal soma
também os do município (código IBGE).

As tabelas estaduais e municipais são parciais e precisam de revisão de
contador. Cidade sem entrada aqui usa só nacional + UF.
"""

from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Dict, Optional

import pytz

TZ_BR = pytz.timezone("America/Sao_Paulo")

POSTPONE = "postpone"  # prorroga para o próximo dia útil
ANTICIPATE = "anticipate"  # antecipa para o dia útil anterior

# Regra por código de obrigação. Sem entrada = antecipar, que nunca gera um
# prazo depois do legal. Revisar com contador antes de confiar em produção.
NON_BUSINESS_DAY_POLICY: Dict[str, str] = {
    "DAS": POSTPONE,  # Res. CGSN 140/2018, art. 40, §3º
    "PGDAS-D": POSTPONE,  # acompanha o vencimento do DAS
    "DCTFWEB": ANTICIPATE,
    "ESOCIAL": ANTICIPATE,
    "EFD-REINF": ANTICIPATE,
}

# Feriados estaduais fixos (mês, dia, nome).
STATE_HOLIDAYS: Dict[str, tuple] = {
    "AC": ((1, 23, "Dia do Evangélico"), (6, 15, "Aniversário do Acre"), (9, 5, "Dia da Amazônia")),
    "AL": ((6, 24, "São João"), (6, 29, "São Pedro"), (9, 16, "Emancipação de Alagoas")),
    "AM": ((9, 5, "Elevação do Amazonas a Província"),),
    "AP": ((3, 19, "São José"), (9, 13, "Criação do Território do Amapá")),
    "BA": ((7, 2, "Independência da Bahia"),),
    "CE": ((3, 19, "São José"), (3, 25, "Data Magna do Ceará")),
    "DF": ((11, 30, "Dia do Evangélico"),),
    "MA": ((7, 28, "Adesão do Maranhão à Independência"),),
    "MS": ((10, 11, "Criação do Estado"),),
    "PA": ((8, 15, "Adesão do Pará à Independência"),),
    "PB": ((8, 5, "Fundação do Estado"),),
    "PE": ((3, 6, "Revolução Pernambucana"),),
    "PI": ((10, 19, "Dia do Piauí"),),
    "PR": ((12, 19, "Emancipação do Paraná"),),
    "RJ": ((4, 23, "São Jorge"),),
    "RN": ((10, 3, "Mártires de Cunhaú e Uruaçu"),),
    "RO": ((1, 4, "Criação do Estado"), (6, 18, "Dia do Evangélico")),
    "RR": ((10, 5, "Criação de Roraima"),),
    "RS": ((9, 20, "Revolução Farroupilha"),),
    "SE": ((7, 8, "Emancipação de Sergipe"),),
    "SP": ((7, 9, "Revolução Constitucionalista"),),
    "TO": ((9, 8, "Nossa Senhora da Natividade"), (10, 5, "Criação do Estado")),
}

# Feriados municipais fixos por código IBGE (capitais principais).
MUNICIPAL_HOLIDAYS: Dict[str, tuple] = {
    "3550308": ((1, 25, "Aniversário de São Paulo"),),
    "3304557": ((1, 20, "São Sebastião"),),
    "3106200": ((8, 15, "Assunção de Nossa Senhora"), (12, 8, "Imaculada Conceição")),
    "2927408": ((6, 24, "São João"), (12, 8, "Nossa Senhora da Conceição da Praia")),
    "4106902": ((9, 8, "Nossa Senhora da Luz dos Pinhais"),),
    "4314902": ((2, 2, "Nossa Senhora dos Navegantes"),),
    "2611606": ((7, 16, "Nossa Senhora do Carmo"), (12, 8, "Nossa Senhora da Conceição")),
}


def today_br() -> date:
    """Data de hoje no fuso de Brasília (o servidor roda em UTC)."""
    return datetime.now(TZ_BR).date()


def easter_sunday(year: int) -> date:
    """Domingo de Páscoa (algoritmo gregoriano de Meeus/Jones/Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


@lru_cache(maxsize=64)
def national_holidays(year: int) -> Dict[date, str]:
    """Feriados nacionais e dias sem expediente bancário em todo o país."""
    holidays = {
        date(year, 1, 1): "Confraternização Universal",
        date(year, 4, 21): "Tiradentes",
        date(year, 5, 1): "Dia do Trabalho",
        date(year, 9, 7): "Independência",
        date(year, 10, 12): "Nossa Senhora Aparecida",
        date(year, 11, 2): "Finados",
        date(year, 11, 15): "Proclamação da República",
        date(year, 12, 25): "Natal",
    }
    if year >= 2024:  # Lei 14.759/2023
        holidays[date(year, 11, 20)] = "Consciência Negra"

    easter = easter_sunday(year)
    # Carnaval e Corpus Christi são ponto facultativo, mas sem expediente bancário.
    holidays[easter - timedelta(days=48)] = "Carnaval"
    holidays[easter - timedelta(days=47)] = "Carnaval"
    holidays[easter - timedelta(days=2)] = "Sexta-feira Santa"
    holidays[easter + timedelta(days=60)] = "Corpus Christi"
    return holidays


def holidays_for(
    year: int, uf: Optional[str] = None, municipio_ibge: Optional[str] = None
) -> Dict[date, str]:
    """Feriados que valem para o local: nacional + UF + município."""
    result = dict(national_holidays(year))
    extra = []
    if uf:
        extra.extend(STATE_HOLIDAYS.get(uf.upper(), ()))
    if municipio_ibge:
        extra.extend(MUNICIPAL_HOLIDAYS.get(str(municipio_ibge), ()))
    for month, day, name in extra:
        result.setdefault(date(year, month, day), name)
    return result


def is_business_day(
    d: date, uf: Optional[str] = None, municipio_ibge: Optional[str] = None
) -> bool:
    return d.weekday() < 5 and d not in holidays_for(d.year, uf, municipio_ibge)


def adjust_to_business_day(
    d: date,
    policy: str = ANTICIPATE,
    uf: Optional[str] = None,
    municipio_ibge: Optional[str] = None,
) -> date:
    """Move a data para o dia útil anterior ou seguinte, se ela não for útil."""
    step = timedelta(days=1 if policy == POSTPONE else -1)
    while not is_business_day(d, uf, municipio_ibge):
        d += step
    return d


def policy_for(code: str) -> str:
    return NON_BUSINESS_DAY_POLICY.get((code or "").upper(), ANTICIPATE)
