"""
Fiscal Calculator Service for FiscWise - Feature #7

Pure domain logic for Brazilian tax calculations:
- Simples Nacional (Anexos I-VI)
- Lucro Presumido
- Lucro Real (simplified)
- ICMS interstate operations
- PIS/COFINS cumulative and non-cumulative

No I/O here — only deterministic math.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


# ---------------------------------------------------------------------------
# Simples Nacional tables (2024 legislation)
# Each entry: (upper_bound, aliquota_nominal, deducao)
# Revenue in annual BRL
# ---------------------------------------------------------------------------

_SIMPLES_ANEXO_I = [
    (Decimal("180000"), Decimal("0.04"), Decimal("0")),
    (Decimal("360000"), Decimal("0.073"), Decimal("5940")),
    (Decimal("720000"), Decimal("0.095"), Decimal("13860")),
    (Decimal("1800000"), Decimal("0.107"), Decimal("22500")),
    (Decimal("3600000"), Decimal("0.143"), Decimal("87300")),
    (Decimal("4800000"), Decimal("0.19"), Decimal("378000")),
]

_SIMPLES_ANEXO_III = [
    (Decimal("180000"), Decimal("0.06"), Decimal("0")),
    (Decimal("360000"), Decimal("0.112"), Decimal("9360")),
    (Decimal("720000"), Decimal("0.135"), Decimal("17640")),
    (Decimal("1800000"), Decimal("0.16"), Decimal("35640")),
    (Decimal("3600000"), Decimal("0.21"), Decimal("125640")),
    (Decimal("4800000"), Decimal("0.33"), Decimal("648000")),
]

_SIMPLES_ANEXO_IV = [
    (Decimal("180000"), Decimal("0.045"), Decimal("0")),
    (Decimal("360000"), Decimal("0.09"), Decimal("8100")),
    (Decimal("720000"), Decimal("0.102"), Decimal("12420")),
    (Decimal("1800000"), Decimal("0.14"), Decimal("39780")),
    (Decimal("3600000"), Decimal("0.22"), Decimal("183780")),
    (Decimal("4800000"), Decimal("0.33"), Decimal("828000")),
]

_SIMPLES_ANEXO_V = [
    (Decimal("180000"), Decimal("0.155"), Decimal("0")),
    (Decimal("360000"), Decimal("0.18"), Decimal("4500")),
    (Decimal("720000"), Decimal("0.195"), Decimal("9900")),
    (Decimal("1800000"), Decimal("0.205"), Decimal("17100")),
    (Decimal("3600000"), Decimal("0.23"), Decimal("62100")),
    (Decimal("4800000"), Decimal("0.305"), Decimal("540000")),
]

_SIMPLES_LIMITE = Decimal("4800000")


def _simples_efetivo(receita_bruta_anual: Decimal, table: list) -> Decimal:
    """Calculate effective Simples Nacional rate for a given revenue and annex."""
    if receita_bruta_anual > _SIMPLES_LIMITE:
        # Exceeds Simples limit — signal caller to exclude
        return Decimal("-1")

    for upper, aliquota, deducao in table:
        if receita_bruta_anual <= upper:
            efetivo = ((receita_bruta_anual * aliquota) - deducao) / receita_bruta_anual
            return efetivo.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    # Above last bracket (should not happen given the limit check above)
    return Decimal("-1")


def _pick_simples_table(activity_code: str | None) -> list:
    """
    Pick the most appropriate Simples Nacional annex.

    Very simplified heuristic — in production this would cross-reference
    the full CNAE table. For the MVP we use:
    - Services (CNAE starting with 6x/7x/8x/9x) → Anexo III or IV
    - Commerce / Industry → Anexo I
    """
    if activity_code is None:
        return _SIMPLES_ANEXO_III  # default to services

    first_digit = str(activity_code).strip()[0]
    if first_digit in ("6", "7", "8", "9"):
        return _SIMPLES_ANEXO_III
    if first_digit in ("4", "5"):  # commerce
        return _SIMPLES_ANEXO_I
    return _SIMPLES_ANEXO_IV  # construction / mixed


# ---------------------------------------------------------------------------
# Lucro Presumido rates (federal taxes only — state taxes excluded)
# ---------------------------------------------------------------------------

_LP_PRESUNCAO_SERVICO = Decimal("0.32")   # 32% presumption base for services
_LP_PRESUNCAO_COMERCIO = Decimal("0.08")  # 8% for commerce

_LP_IRPJ_RATE = Decimal("0.15")
_LP_IRPJ_ADD_RATE = Decimal("0.10")      # adicional de 10% above threshold
_LP_IRPJ_ADD_THRESHOLD = Decimal("20000") # monthly R$ 20 k / annual R$ 240 k
_LP_CSLL_RATE = Decimal("0.09")
_LP_PIS_RATE = Decimal("0.0065")         # cumulative
_LP_COFINS_RATE = Decimal("0.03")        # cumulative
_LP_ISS_RATE = Decimal("0.05")           # assumed maximum; varies by municipality


def _calculate_lucro_presumido(
    annual_revenue: Decimal,
    annual_payroll: Decimal,
    is_service: bool = True,
) -> dict[str, Any]:
    """Calculate Lucro Presumido taxes for a given revenue."""

    presuncao = _LP_PRESUNCAO_SERVICO if is_service else _LP_PRESUNCAO_COMERCIO
    base_irpj = annual_revenue * presuncao

    irpj = base_irpj * _LP_IRPJ_RATE
    # Adicional de 10% on the portion above R$ 240 k/year
    adicional_base = max(base_irpj - (_LP_IRPJ_ADD_THRESHOLD * 12), Decimal("0"))
    irpj_adicional = adicional_base * _LP_IRPJ_ADD_RATE

    csll = base_irpj * _LP_CSLL_RATE
    pis = annual_revenue * _LP_PIS_RATE
    cofins = annual_revenue * _LP_COFINS_RATE
    iss = annual_revenue * _LP_ISS_RATE if is_service else Decimal("0")

    total = (irpj + irpj_adicional + csll + pis + cofins + iss).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    effective_rate = (total / annual_revenue).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )

    return {
        "irpj": float(irpj.quantize(Decimal("0.01"))),
        "irpj_adicional": float(irpj_adicional.quantize(Decimal("0.01"))),
        "csll": float(csll.quantize(Decimal("0.01"))),
        "pis": float(pis.quantize(Decimal("0.01"))),
        "cofins": float(cofins.quantize(Decimal("0.01"))),
        "iss": float(iss.quantize(Decimal("0.01"))),
        "total_tax": float(total),
        "effective_rate": float(effective_rate),
        "regime": "lucro_presumido",
    }


# ---------------------------------------------------------------------------
# Lucro Real (simplified — uses actual cost/profit as base)
# ---------------------------------------------------------------------------

_LR_IRPJ_RATE = Decimal("0.15")
_LR_IRPJ_ADD_RATE = Decimal("0.10")
_LR_IRPJ_ADD_THRESHOLD_ANNUAL = Decimal("240000")
_LR_CSLL_RATE = Decimal("0.09")
_LR_PIS_RATE = Decimal("0.0165")          # non-cumulative
_LR_COFINS_RATE = Decimal("0.076")         # non-cumulative
_LR_ISS_RATE = Decimal("0.05")


def _calculate_lucro_real(
    annual_revenue: Decimal,
    annual_costs: Decimal,
    annual_payroll: Decimal,
    is_service: bool = True,
) -> dict[str, Any]:
    """Calculate Lucro Real taxes using taxable profit as base."""

    taxable_profit = max(annual_revenue - annual_costs - annual_payroll, Decimal("0"))

    irpj = taxable_profit * _LR_IRPJ_RATE
    adicional_base = max(taxable_profit - _LR_IRPJ_ADD_THRESHOLD_ANNUAL, Decimal("0"))
    irpj_adicional = adicional_base * _LR_IRPJ_ADD_RATE

    csll = taxable_profit * _LR_CSLL_RATE

    # Non-cumulative PIS/COFINS — credited inputs reduce the base
    # Simplified: assume 30% of costs generate credits
    creditable_costs = annual_costs * Decimal("0.30")
    pis = max((annual_revenue - creditable_costs) * _LR_PIS_RATE, Decimal("0"))
    cofins = max((annual_revenue - creditable_costs) * _LR_COFINS_RATE, Decimal("0"))

    iss = annual_revenue * _LR_ISS_RATE if is_service else Decimal("0")

    total = (irpj + irpj_adicional + csll + pis + cofins + iss).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    effective_rate = (total / annual_revenue).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    ) if annual_revenue > 0 else Decimal("0")

    return {
        "irpj": float(irpj.quantize(Decimal("0.01"))),
        "irpj_adicional": float(irpj_adicional.quantize(Decimal("0.01"))),
        "csll": float(csll.quantize(Decimal("0.01"))),
        "pis": float(pis.quantize(Decimal("0.01"))),
        "cofins": float(cofins.quantize(Decimal("0.01"))),
        "iss": float(iss.quantize(Decimal("0.01"))),
        "taxable_profit": float(taxable_profit.quantize(Decimal("0.01"))),
        "total_tax": float(total),
        "effective_rate": float(effective_rate),
        "regime": "lucro_real",
    }


# ---------------------------------------------------------------------------
# ICMS interstate table (2024)
# Keys: (origin_state, destination_state) → aliquota interestadual
# Simplified: most interstate rates are 12% (SE/S) or 7% (others to N/NE/CO)
# ---------------------------------------------------------------------------

_ICMS_INTERSTATE_RATES: dict[str, Decimal] = {
    # SP origin
    ("SP", "RJ"): Decimal("0.12"),
    ("SP", "MG"): Decimal("0.12"),
    ("SP", "PR"): Decimal("0.12"),
    ("SP", "SC"): Decimal("0.12"),
    ("SP", "RS"): Decimal("0.12"),
    # Default for operations to N/NE/CO
}

_ICMS_INTERSTATE_DEFAULT_SE_S = Decimal("0.12")
_ICMS_INTERSTATE_DEFAULT_OTHERS = Decimal("0.07")

_SOUTH_SOUTHEAST = {"SP", "RJ", "MG", "ES", "PR", "SC", "RS"}

_ICMS_INTERNAL_RATES: dict[str, Decimal] = {
    "SP": Decimal("0.18"),
    "RJ": Decimal("0.20"),
    "MG": Decimal("0.18"),
    "ES": Decimal("0.17"),
    "PR": Decimal("0.195"),
    "SC": Decimal("0.17"),
    "RS": Decimal("0.17"),
    "BA": Decimal("0.19"),
    "PE": Decimal("0.185"),
    "CE": Decimal("0.20"),
    "GO": Decimal("0.17"),
    "DF": Decimal("0.18"),
    "MT": Decimal("0.17"),
    "MS": Decimal("0.17"),
    "PA": Decimal("0.17"),
    "AM": Decimal("0.20"),
}

_DIFAL_RATE_SUPPLIER = Decimal("0.80")  # 80% of DIFAL stays with origin state post-EC87
_DIFAL_RATE_DESTINATION = Decimal("0.20")  # 20% to destination (transitional, now 100%)


def _get_icms_interstate_rate(origin: str, destination: str) -> Decimal:
    """Return the interstate ICMS rate between two states."""
    key = (origin.upper(), destination.upper())
    if key in _ICMS_INTERSTATE_RATES:
        return _ICMS_INTERSTATE_RATES[key]
    if destination.upper() in _SOUTH_SOUTHEAST:
        return _ICMS_INTERSTATE_DEFAULT_SE_S
    return _ICMS_INTERSTATE_DEFAULT_OTHERS


def _get_icms_internal_rate(state: str) -> Decimal:
    """Return the internal ICMS rate for a state (default 17% if unknown)."""
    return _ICMS_INTERNAL_RATES.get(state.upper(), Decimal("0.17"))


def calculate_icms(
    ncm_code: str,
    origin_state: str,
    destination_state: str,
    operation_value: Decimal,
    is_buyer_taxpayer: bool = True,
) -> dict[str, Any]:
    """
    Calculate ICMS for an interstate operation.

    Returns a breakdown including:
    - Interstate rate (aliquota interestadual)
    - ICMS value charged by origin state
    - DIFAL (if buyer is final consumer / non-taxpayer)
    - Effective tax on the operation
    """
    origin = origin_state.upper()
    destination = destination_state.upper()

    interstate_rate = _get_icms_interstate_rate(origin, destination)
    internal_destination_rate = _get_icms_internal_rate(destination)

    icms_interstate = (operation_value * interstate_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # DIFAL applies when buyer is final consumer (non-taxpayer) or
    # for goods destined to final consumption in another state
    difal_total = Decimal("0")
    difal_origin = Decimal("0")
    difal_destination = Decimal("0")

    if not is_buyer_taxpayer:
        difal_total = ((internal_destination_rate - interstate_rate) * operation_value).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        # Since 2019 EC 87 transition: 100% DIFAL goes to destination state
        difal_destination = difal_total
        difal_origin = Decimal("0")

    effective_rate = (icms_interstate + difal_total) / operation_value
    effective_rate = effective_rate.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    return {
        "ncm_code": ncm_code,
        "origin_state": origin,
        "destination_state": destination,
        "operation_value": float(operation_value),
        "interstate_rate": float(interstate_rate),
        "internal_destination_rate": float(internal_destination_rate),
        "icms_interstate": float(icms_interstate),
        "difal_total": float(difal_total),
        "difal_origin": float(difal_origin),
        "difal_destination": float(difal_destination),
        "effective_rate": float(effective_rate),
        "is_buyer_taxpayer": is_buyer_taxpayer,
    }


# ---------------------------------------------------------------------------
# PIS/COFINS
# ---------------------------------------------------------------------------

_PIS_CUMULATIVO = Decimal("0.0065")
_COFINS_CUMULATIVO = Decimal("0.03")
_PIS_NAO_CUMULATIVO = Decimal("0.0165")
_COFINS_NAO_CUMULATIVO = Decimal("0.076")


def calculate_pis_cofins(
    monthly_revenue: Decimal,
    is_non_cumulative: bool,
    deductible_credits: Decimal | None = None,
) -> dict[str, Any]:
    """
    Calculate PIS and COFINS for a given monthly revenue.

    Cumulative (Lucro Presumido / Simples outside Simples rules):
        PIS  = 0.65%   COFINS = 3.00%
    Non-cumulative (Lucro Real):
        PIS  = 1.65%   COFINS = 7.60%
        Credits from inputs can be deducted.
    """
    if is_non_cumulative:
        pis_rate = _PIS_NAO_CUMULATIVO
        cofins_rate = _COFINS_NAO_CUMULATIVO
        credits = deductible_credits or Decimal("0")
    else:
        pis_rate = _PIS_CUMULATIVO
        cofins_rate = _COFINS_CUMULATIVO
        credits = Decimal("0")  # no credits in cumulative regime

    pis_gross = (monthly_revenue * pis_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    cofins_gross = (monthly_revenue * cofins_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Split credits proportionally between PIS and COFINS
    total_gross = pis_gross + cofins_gross
    if total_gross > 0 and credits > 0:
        pis_credit_share = (credits * (pis_gross / total_gross)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        cofins_credit_share = (credits * (cofins_gross / total_gross)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        pis_credit_share = Decimal("0")
        cofins_credit_share = Decimal("0")

    pis_net = max(pis_gross - pis_credit_share, Decimal("0"))
    cofins_net = max(cofins_gross - cofins_credit_share, Decimal("0"))
    total_net = pis_net + cofins_net

    effective_rate = (total_net / monthly_revenue).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    ) if monthly_revenue > 0 else Decimal("0")

    return {
        "monthly_revenue": float(monthly_revenue),
        "regime_type": "non_cumulative" if is_non_cumulative else "cumulative",
        "pis_rate": float(pis_rate),
        "cofins_rate": float(cofins_rate),
        "pis_gross": float(pis_gross),
        "cofins_gross": float(cofins_gross),
        "pis_credit": float(pis_credit_share),
        "cofins_credit": float(cofins_credit_share),
        "pis_net": float(pis_net),
        "cofins_net": float(cofins_net),
        "total_pis_cofins": float(total_net),
        "effective_rate": float(effective_rate),
        "annual_projection": float((total_net * 12).quantize(Decimal("0.01"))),
    }


# ---------------------------------------------------------------------------
# Regime comparison orchestrator
# ---------------------------------------------------------------------------

def compare_tax_regimes(
    annual_revenue: Decimal,
    annual_costs: Decimal,
    annual_payroll: Decimal,
    activity_code: str | None = None,
    cogs: Decimal | None = None,
) -> list[dict[str, Any]]:
    """
    Compare all three Brazilian tax regimes for the given inputs.

    Returns a list of scenario dicts ordered by total_tax ascending.
    Each dict is ready to be stored as TaxScenario.
    """
    scenarios = []

    # ── Simples Nacional ─────────────────────────────────────────────────────
    table = _pick_simples_table(activity_code)
    simples_rate = _simples_efetivo(annual_revenue, table)

    if simples_rate > 0:
        simples_tax = (annual_revenue * simples_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        scenarios.append({
            "regime": "simples_nacional",
            "annual_revenue": float(annual_revenue),
            "effective_rate": float(simples_rate),
            "total_tax": float(simples_tax),
            "tax_breakdown": {
                "simples_unified": float(simples_tax),
                "note": "Imposto unificado via DAS",
            },
            "is_recommended": False,
        })
    else:
        # Revenue exceeds Simples limit
        scenarios.append({
            "regime": "simples_nacional",
            "annual_revenue": float(annual_revenue),
            "effective_rate": 0.0,
            "total_tax": 0.0,
            "tax_breakdown": {
                "note": "Receita anual superior ao limite do Simples Nacional (R$ 4.800.000)",
            },
            "is_recommended": False,
            "ineligible": True,
        })

    # ── Lucro Presumido ───────────────────────────────────────────────────────
    is_service = activity_code is not None and str(activity_code)[0] in ("6", "7", "8", "9")
    lp = _calculate_lucro_presumido(annual_revenue, annual_payroll, is_service)
    scenarios.append({
        "regime": "lucro_presumido",
        "annual_revenue": float(annual_revenue),
        "effective_rate": lp["effective_rate"],
        "total_tax": lp["total_tax"],
        "tax_breakdown": lp,
        "is_recommended": False,
    })

    # ── Lucro Real ────────────────────────────────────────────────────────────
    costs_for_lr = cogs if cogs is not None else annual_costs
    lr = _calculate_lucro_real(annual_revenue, costs_for_lr, annual_payroll, is_service)
    scenarios.append({
        "regime": "lucro_real",
        "annual_revenue": float(annual_revenue),
        "effective_rate": lr["effective_rate"],
        "total_tax": lr["total_tax"],
        "tax_breakdown": lr,
        "is_recommended": False,
    })

    # Mark cheapest eligible regime as recommended
    eligible = [s for s in scenarios if not s.get("ineligible")]
    if eligible:
        cheapest = min(eligible, key=lambda s: s["total_tax"])
        cheapest["is_recommended"] = True

    return sorted(scenarios, key=lambda s: s.get("total_tax") or float("inf"))


# ---------------------------------------------------------------------------
# Fator R / DAS Calculator
# ---------------------------------------------------------------------------

_MONTH_LABELS = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]


def _find_faixa(rbt12: Decimal, table: list) -> tuple[int, Decimal, Decimal]:
    """Return (faixa_number, aliquota_nominal, deducao) for a given RBT12."""
    for i, (upper, aliquota, deducao) in enumerate(table, start=1):
        if rbt12 <= upper:
            return i, aliquota, deducao
    # Above the last bracket — use the last faixa
    _, aliquota, deducao = table[-1]
    return len(table), aliquota, deducao


def _calc_das_for_table(
    rbt12: Decimal,
    monthly_revenues: list[Decimal],
    table: list,
    month_labels: list[str],
) -> tuple[list[dict[str, Any]], Decimal, Decimal]:
    """
    Calculate monthly DAS values for a given annex table.

    Returns (monthly_details, total_das_anual, aliquota_efetiva).
    """
    if rbt12 <= 0:
        empty = [
            {"mes": month_labels[i], "receita": float(r), "das": 0.0, "aliquota_efetiva": 0.0}
            for i, r in enumerate(monthly_revenues)
        ]
        return empty, Decimal("0"), Decimal("0")

    faixa, aliq_nominal, deducao = _find_faixa(rbt12, table)
    aliquota_efetiva = ((rbt12 * aliq_nominal) - deducao) / rbt12
    aliquota_efetiva = aliquota_efetiva.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    monthly_details: list[dict[str, Any]] = []
    total_das = Decimal("0")

    for i, receita in enumerate(monthly_revenues):
        das = (receita * aliquota_efetiva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_das += das
        monthly_details.append({
            "mes": month_labels[i] if i < len(month_labels) else f"Mês {i + 1}",
            "receita": float(receita.quantize(Decimal("0.01"))),
            "das": float(das),
            "aliquota_efetiva": float(aliquota_efetiva),
            "faixa": faixa,
        })

    return monthly_details, total_das, aliquota_efetiva


def calculate_fator_r(
    monthly_revenues: list[Decimal],
    monthly_payrolls: list[Decimal],
) -> dict[str, Any]:
    """
    Calculate Fator R and DAS for a service company under Simples Nacional.

    The Fator R determines whether the company falls under Anexo III (lower
    taxes, when payroll is >= 28% of revenue) or Anexo V (higher taxes).

    Parameters
    ----------
    monthly_revenues : list[Decimal]
        Up to 12 monthly gross revenue values.
    monthly_payrolls : list[Decimal]
        Up to 12 monthly total payroll (folha de pagamento) values.
        Must have the same length as monthly_revenues.

    Returns
    -------
    dict with rbt12, folha_12m, fator_r, anexo, monthly_details,
    total_das_anual, and a comparison dict showing the alternative annex.
    """
    num_months = len(monthly_revenues)

    # Pad to the number of months provided (no forced 12-month padding)
    month_labels = _MONTH_LABELS[:num_months] if num_months <= 12 else [
        f"Mês {i + 1}" for i in range(num_months)
    ]

    rbt12 = sum(monthly_revenues)
    folha_12m = sum(monthly_payrolls)

    # Fator R = Folha / RBT12
    if rbt12 > 0:
        fator_r = (folha_12m / rbt12).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    else:
        fator_r = Decimal("0")

    # Determine Annex
    fator_r_threshold = Decimal("0.28")
    anexo = "III" if fator_r >= fator_r_threshold else "V"
    primary_table = _SIMPLES_ANEXO_III if anexo == "III" else _SIMPLES_ANEXO_V
    alt_table = _SIMPLES_ANEXO_V if anexo == "III" else _SIMPLES_ANEXO_III
    alt_anexo = "V" if anexo == "III" else "III"

    # Calculate DAS with the determined annex
    monthly_details, total_das_anual, aliq_efetiva = _calc_das_for_table(
        rbt12, monthly_revenues, primary_table, month_labels,
    )

    # Enrich monthly_details with payroll data
    for i, detail in enumerate(monthly_details):
        detail["folha"] = float(monthly_payrolls[i].quantize(Decimal("0.01")))

    # Comparison: what-if in the other annex
    alt_details, alt_total_das, alt_aliq = _calc_das_for_table(
        rbt12, monthly_revenues, alt_table, month_labels,
    )

    if total_das_anual > 0:
        diff = total_das_anual - alt_total_das
    else:
        diff = Decimal("0")

    comparison = {
        "anexo": alt_anexo,
        "aliquota_efetiva": float(alt_aliq),
        "total_das_anual": float(alt_total_das.quantize(Decimal("0.01"))),
        "diferenca_anual": float(diff.quantize(Decimal("0.01"))),
        "monthly_details": alt_details,
    }

    fator_r_pct = (fator_r * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "rbt12": float(rbt12.quantize(Decimal("0.01"))),
        "folha_12m": float(folha_12m.quantize(Decimal("0.01"))),
        "fator_r": float(fator_r),
        "fator_r_percent": f"{fator_r_pct}%",
        "anexo": anexo,
        "monthly_details": monthly_details,
        "total_das_anual": float(total_das_anual.quantize(Decimal("0.01"))),
        "comparison": comparison,
    }
