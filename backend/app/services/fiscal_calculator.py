"""Pure domain logic for Brazilian fiscal calculations.

This module is intentionally framework-free so it can be unit-tested
without a database or HTTP context.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


# ---------------------------------------------------------------------------
# Simples Nacional – Anexo I (Comércio) – Revenue ranges and rates
# Simplified 2024 table — 6 faixas
# ---------------------------------------------------------------------------

_SIMPLES_COMMERCE_RANGES = [
    # (max_revenue, nominal_rate, deducao)
    (Decimal("180000.00"),  Decimal("0.04"),  Decimal("0")),
    (Decimal("360000.00"),  Decimal("0.073"), Decimal("5940")),
    (Decimal("720000.00"),  Decimal("0.095"), Decimal("13860")),
    (Decimal("1800000.00"), Decimal("0.107"), Decimal("22500")),
    (Decimal("3600000.00"), Decimal("0.143"), Decimal("87300")),
    (Decimal("4800000.00"), Decimal("0.19"),  Decimal("378000")),
]

_SIMPLES_SERVICES_RANGES = [
    # Anexo III (Serviços profissionais — simplificado)
    (Decimal("180000.00"),  Decimal("0.06"),  Decimal("0")),
    (Decimal("360000.00"),  Decimal("0.112"), Decimal("9360")),
    (Decimal("720000.00"),  Decimal("0.135"), Decimal("17640")),
    (Decimal("1800000.00"), Decimal("0.16"),  Decimal("35640")),
    (Decimal("3600000.00"), Decimal("0.21"),  Decimal("125640")),
    (Decimal("4800000.00"), Decimal("0.33"),  Decimal("648000")),
]

_MEI_LIMIT = Decimal("81000.00")
_SIMPLES_LIMIT = Decimal("4800000.00")

# ICMS inter-state rates matrix (simplified)
_ICMS_INTERSTATE: dict[tuple[str, str], Decimal] = {}

# Intra-state default rates by UF
_ICMS_INTERNAL: dict[str, Decimal] = {
    "SP": Decimal("0.18"),
    "RJ": Decimal("0.20"),
    "MG": Decimal("0.18"),
    "RS": Decimal("0.17"),
    "PR": Decimal("0.15"),
    "SC": Decimal("0.17"),
    "BA": Decimal("0.19"),
    "GO": Decimal("0.17"),
    "DF": Decimal("0.18"),
}
_ICMS_INTERNAL_DEFAULT = Decimal("0.17")

# PIS/COFINS rates
_PIS_PRESUMIDO = Decimal("0.0065")
_COFINS_PRESUMIDO = Decimal("0.03")
_PIS_REAL = Decimal("0.0165")
_COFINS_REAL = Decimal("0.076")


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Simples Nacional
# ---------------------------------------------------------------------------

def _effective_simples_rate(annual_revenue: Decimal, ranges: list) -> Decimal:
    """Compute effective Simples Nacional rate for a given revenue."""
    for max_rev, nominal_rate, deducao in ranges:
        if annual_revenue <= max_rev:
            raw_tax = annual_revenue * nominal_rate - deducao
            effective = raw_tax / annual_revenue
            return _round2(effective)
    # Não elegível
    return Decimal("0")


def simulate_simples_nacional(annual_revenue: Decimal, activity_type: str) -> dict:
    """Calculate Simples Nacional tax burden."""
    eligible = annual_revenue <= _SIMPLES_LIMIT

    if "servi" in activity_type.lower():
        ranges = _SIMPLES_SERVICES_RANGES
        regime_label = "Simples Nacional – Serviços (Anexo III)"
    else:
        ranges = _SIMPLES_COMMERCE_RANGES
        regime_label = "Simples Nacional – Comércio (Anexo I)"

    if not eligible:
        return {
            "regime": "simples_nacional",
            "regime_label": regime_label,
            "eligible": False,
            "ineligibility_reason": "Faturamento acima do limite de R$ 4.800.000/ano.",
            "annual_tax_burden": Decimal("0"),
            "effective_rate": Decimal("0"),
            "monthly_installment": Decimal("0"),
            "breakdown": {},
        }

    effective_rate = _effective_simples_rate(annual_revenue, ranges)
    annual_tax = _round2(annual_revenue * effective_rate)
    monthly_installment = _round2(annual_tax / 12)

    return {
        "regime": "simples_nacional",
        "regime_label": regime_label,
        "eligible": True,
        "annual_tax_burden": annual_tax,
        "effective_rate": effective_rate,
        "monthly_installment": monthly_installment,
        "breakdown": {
            "base_rate_applied": str(effective_rate),
            "faturamento_anual": str(annual_revenue),
        },
    }


# ---------------------------------------------------------------------------
# Lucro Presumido
# ---------------------------------------------------------------------------

def simulate_lucro_presumido(annual_revenue: Decimal, activity_type: str) -> dict:
    """Calculate Lucro Presumido tax burden (IRPJ + CSLL + PIS + COFINS)."""
    # Presumption percentages
    is_service = "servi" in activity_type.lower()
    irpj_presumption = Decimal("0.32") if is_service else Decimal("0.08")
    csll_presumption = Decimal("0.32") if is_service else Decimal("0.12")

    irpj_base = annual_revenue * irpj_presumption
    csll_base = annual_revenue * csll_presumption

    irpj = _round2(irpj_base * Decimal("0.15"))
    csll = _round2(csll_base * Decimal("0.09"))
    pis = _round2(annual_revenue * _PIS_PRESUMIDO)
    cofins = _round2(annual_revenue * _COFINS_PRESUMIDO)

    annual_tax = irpj + csll + pis + cofins
    effective_rate = _round2(annual_tax / annual_revenue)
    monthly_installment = _round2(annual_tax / 12)

    return {
        "regime": "lucro_presumido",
        "regime_label": "Lucro Presumido",
        "eligible": True,
        "annual_tax_burden": annual_tax,
        "effective_rate": effective_rate,
        "monthly_installment": monthly_installment,
        "breakdown": {
            "irpj": str(irpj),
            "csll": str(csll),
            "pis": str(pis),
            "cofins": str(cofins),
            "irpj_presumption": str(irpj_presumption),
        },
    }


# ---------------------------------------------------------------------------
# Lucro Real — simplified estimation
# ---------------------------------------------------------------------------

def simulate_lucro_real(
    annual_revenue: Decimal,
    activity_type: str,
    payroll_total: Optional[Decimal] = None,
) -> dict:
    """Estimate Lucro Real tax burden.

    Uses a simplified assumption that margin is ~10% of revenue.
    Full accuracy requires the client's DRE.
    """
    estimated_profit = _round2(annual_revenue * Decimal("0.10"))
    irpj = _round2(estimated_profit * Decimal("0.15"))
    csll = _round2(estimated_profit * Decimal("0.09"))
    pis = _round2(annual_revenue * _PIS_REAL)
    cofins = _round2(annual_revenue * _COFINS_REAL)

    annual_tax = irpj + csll + pis + cofins
    effective_rate = _round2(annual_tax / annual_revenue)
    monthly_installment = _round2(annual_tax / 12)

    return {
        "regime": "lucro_real",
        "regime_label": "Lucro Real",
        "eligible": True,
        "annual_tax_burden": annual_tax,
        "effective_rate": effective_rate,
        "monthly_installment": monthly_installment,
        "breakdown": {
            "irpj": str(irpj),
            "csll": str(csll),
            "pis": str(pis),
            "cofins": str(cofins),
            "note": "Estimativa com margem de lucro presumida de 10%.",
        },
    }


# ---------------------------------------------------------------------------
# MEI
# ---------------------------------------------------------------------------

def simulate_mei(annual_revenue: Decimal) -> dict:
    """Calculate MEI DAS tax burden (fixed monthly value)."""
    eligible = annual_revenue <= _MEI_LIMIT

    # Fixed 2024 DAS value (commerce/services approximation)
    monthly_das = Decimal("71.60")
    annual_tax = _round2(monthly_das * 12)
    effective_rate = _round2(annual_tax / annual_revenue) if annual_revenue else Decimal("0")

    return {
        "regime": "mei",
        "regime_label": "MEI",
        "eligible": eligible,
        "ineligibility_reason": "Faturamento acima do limite MEI de R$ 81.000/ano." if not eligible else None,
        "annual_tax_burden": annual_tax if eligible else Decimal("0"),
        "effective_rate": effective_rate if eligible else Decimal("0"),
        "monthly_installment": monthly_das if eligible else Decimal("0"),
        "breakdown": {
            "monthly_das": str(monthly_das),
            "note": "Valor fixo de DAS 2024. Confirme tabela vigente.",
        },
    }


# ---------------------------------------------------------------------------
# ICMS inter-state
# ---------------------------------------------------------------------------

def simulate_icms(
    origin_state: str,
    destination_state: str,
    transaction_value: Decimal,
) -> dict:
    """Compute inter-state ICMS and DIFAL (simplified)."""
    origin_internal = _ICMS_INTERNAL.get(origin_state.upper(), _ICMS_INTERNAL_DEFAULT)
    dest_internal = _ICMS_INTERNAL.get(destination_state.upper(), _ICMS_INTERNAL_DEFAULT)

    # Inter-state rate: 7% for less-developed states, 12% otherwise
    interstate_rate = Decimal("0.07") if destination_state.upper() in {"N", "NE", "CO"} else Decimal("0.12")

    icms_origin = _round2(transaction_value * interstate_rate)
    difal = _round2(transaction_value * (dest_internal - interstate_rate))
    difal = max(Decimal("0"), difal)

    total_icms = _round2(icms_origin + difal)
    effective_rate = _round2(total_icms / transaction_value)

    return {
        "origin_state": origin_state.upper(),
        "destination_state": destination_state.upper(),
        "transaction_value": transaction_value,
        "icms_origin_rate": interstate_rate,
        "icms_destination_rate": dest_internal,
        "difal_applicable": difal > 0,
        "icms_due_origin": icms_origin,
        "icms_due_destination": difal,
        "total_icms": total_icms,
        "effective_rate": effective_rate,
    }


# ---------------------------------------------------------------------------
# PIS / COFINS
# ---------------------------------------------------------------------------

def simulate_pis_cofins(
    regime: str,
    monthly_revenue: Decimal,
    deductible_costs: Optional[Decimal] = None,
) -> dict:
    """Calculate monthly PIS/COFINS."""
    if regime == "lucro_real":
        pis_rate = _PIS_REAL
        cofins_rate = _COFINS_REAL
        credits = _round2(deductible_costs * (pis_rate + cofins_rate)) if deductible_costs else Decimal("0")
        pis_due = _round2(monthly_revenue * pis_rate - credits * (pis_rate / (pis_rate + cofins_rate)))
        cofins_due = _round2(monthly_revenue * cofins_rate - credits * (cofins_rate / (pis_rate + cofins_rate)))
    else:
        pis_rate = _PIS_PRESUMIDO
        cofins_rate = _COFINS_PRESUMIDO
        credits = Decimal("0")
        pis_due = _round2(monthly_revenue * pis_rate)
        cofins_due = _round2(monthly_revenue * cofins_rate)

    total_due = _round2(pis_due + cofins_due)
    effective_rate = _round2(total_due / monthly_revenue)

    return {
        "regime": regime,
        "monthly_revenue": monthly_revenue,
        "pis_rate": pis_rate,
        "cofins_rate": cofins_rate,
        "pis_due": pis_due,
        "cofins_due": cofins_due,
        "total_due": total_due,
        "effective_rate": effective_rate,
        "credits_applied": credits if credits > 0 else None,
    }


# ---------------------------------------------------------------------------
# Best-regime comparison
# ---------------------------------------------------------------------------

def compare_regimes(
    annual_revenue: Decimal,
    activity_type: str,
    payroll_total: Optional[Decimal] = None,
) -> tuple[list[dict], str]:
    """Run all regimes and return results + recommended regime slug."""
    results = [
        simulate_mei(annual_revenue),
        simulate_simples_nacional(annual_revenue, activity_type),
        simulate_lucro_presumido(annual_revenue, activity_type),
        simulate_lucro_real(annual_revenue, activity_type, payroll_total),
    ]

    eligible = [r for r in results if r["eligible"]]
    if not eligible:
        return results, "lucro_real"

    best = min(eligible, key=lambda r: r["annual_tax_burden"])
    return results, best["regime"]
