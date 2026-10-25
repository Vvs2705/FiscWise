"""Dias úteis, feriados e fuso de Brasília no cálculo de prazos fiscais."""

from datetime import date, datetime

import pytest
import pytz

from app.domain.obligations import business_days as bd
from app.models.obligation import ObligationRule
from app.services.obligation_engine import compute_due_date


def _rule(code, due_day, jurisdiction="federal", recurrence="monthly", state=None):
    return ObligationRule(
        code=code, name=code, jurisdiction=jurisdiction,
        recurrence=recurrence, due_day=due_day, state=state, active=True,
    )


@pytest.mark.parametrize("year, expected", [
    (2024, date(2024, 3, 31)),
    (2025, date(2025, 4, 20)),
    (2026, date(2026, 4, 5)),
    (2027, date(2027, 3, 28)),
])
def test_easter_sunday(year, expected):
    assert bd.easter_sunday(year) == expected


def test_national_holidays_2026_include_mobile_dates():
    h = bd.national_holidays(2026)
    assert h[date(2026, 2, 16)] == "Carnaval"
    assert h[date(2026, 2, 17)] == "Carnaval"
    assert h[date(2026, 4, 3)] == "Sexta-feira Santa"
    assert h[date(2026, 6, 4)] == "Corpus Christi"
    assert h[date(2026, 11, 20)] == "Consciência Negra"


def test_consciencia_negra_only_from_2024():
    assert date(2023, 11, 20) not in bd.national_holidays(2023)


def test_state_and_municipal_holidays_are_local():
    assert not bd.is_business_day(date(2026, 7, 9), uf="SP")
    assert bd.is_business_day(date(2026, 7, 9), uf="RJ")
    assert not bd.is_business_day(date(2027, 1, 25), uf="SP", municipio_ibge="3550308")
    assert bd.is_business_day(date(2027, 1, 25), uf="SP")


def test_das_on_sunday_is_postponed_to_monday():
    # Competência 08/2026: dia 20/09/2026 é domingo.
    assert compute_due_date(_rule("DAS", 20), 2026, 8) == date(2026, 9, 21)


def test_das_on_national_holiday_is_postponed():
    # Competência 10/2026: 20/11/2026 (sexta) é Consciência Negra.
    assert compute_due_date(_rule("DAS", 20), 2026, 10) == date(2026, 11, 23)


def test_dctfweb_on_holiday_is_anticipated():
    # Competência 10/2028: 15/11/2028 (quarta) é Proclamação da República.
    assert compute_due_date(_rule("DCTFWEB", 15), 2028, 10) == date(2028, 11, 14)


def test_esocial_on_sunday_is_anticipated_to_friday():
    # Competência 10/2026: 15/11/2026 é domingo e feriado.
    assert compute_due_date(_rule("ESOCIAL", 15), 2026, 10) == date(2026, 11, 13)


def test_business_day_keeps_nominal_date():
    # Competência 05/2026: 20/06/2026 é sábado; 15/06/2026 é segunda.
    assert compute_due_date(_rule("EFD-REINF", 15), 2026, 5) == date(2026, 6, 15)


def test_unknown_rule_defaults_to_anticipate():
    assert bd.policy_for("QUALQUER") == bd.ANTICIPATE
    # Competência 08/2026: 20/09/2026 é domingo -> sexta 18/09.
    assert compute_due_date(_rule("QUALQUER", 20), 2026, 8) == date(2026, 9, 18)


def test_municipal_rule_uses_city_holiday():
    rule = _rule("ISS_3550308", 25, jurisdiction="municipal")
    # Competência 12/2026: 25/01/2027 (segunda) é aniversário de São Paulo.
    assert compute_due_date(rule, 2026, 12, uf="SP", municipio_ibge="3550308") == date(2027, 1, 22)
    assert compute_due_date(rule, 2026, 12, uf="RJ", municipio_ibge="3304557") == date(2027, 1, 25)


def test_federal_rule_ignores_local_holidays():
    rule = _rule("DCTFWEB", 25)
    assert compute_due_date(rule, 2026, 12, uf="SP", municipio_ibge="3550308") == date(2027, 1, 25)


def test_state_rule_uses_uf_but_not_city():
    rule = _rule("ICMS", 9, jurisdiction="estadual", state="SP")
    # Competência 06/2026: 09/07/2026 (quinta) é feriado estadual em SP.
    assert compute_due_date(rule, 2026, 6) == date(2026, 7, 8)
    assert compute_due_date(_rule("ICMS", 9, jurisdiction="estadual"), 2026, 6, uf="RJ") == date(2026, 7, 9)


def test_yearly_rule_due_in_competence_month():
    # 01/01/2027 é feriado e sexta; antecipa para 31/12/2026.
    assert compute_due_date(_rule("ANUAL", 1, recurrence="yearly"), 2027, 1) == date(2026, 12, 31)


def test_today_br_uses_brasilia(monkeypatch):
    # 02:00 UTC de 25/10/2026 ainda é 24/10 em Brasília.
    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 25, 2, 0, tzinfo=pytz.UTC).astimezone(tz)

    monkeypatch.setattr(bd, "datetime", FakeDatetime)
    assert bd.today_br() == date(2026, 10, 24)
