"""
Unit tests for the fiscal calculator domain service — Feature #7

Tests purely the calculation logic (no database, no network).
"""

from decimal import Decimal

import pytest

from app.services.fiscal_calculator import (
    _get_icms_internal_rate,
    calculate_icms,
    calculate_pis_cofins,
    compare_tax_regimes,
)


# ---------------------------------------------------------------------------
# Simples Nacional / Regime comparison
# ---------------------------------------------------------------------------


class TestCompareRegimes:
    def test_returns_three_scenarios(self):
        scenarios = compare_tax_regimes(
            annual_revenue=Decimal("1_200_000"),
            annual_costs=Decimal("400_000"),
            annual_payroll=Decimal("200_000"),
            activity_code="6201500",
        )
        # Always 3 scenarios (simples may be ineligible but still present)
        assert len(scenarios) == 3

    def test_cheapest_regime_is_recommended(self):
        scenarios = compare_tax_regimes(
            annual_revenue=Decimal("500_000"),
            annual_costs=Decimal("200_000"),
            annual_payroll=Decimal("60_000"),
        )
        eligible = [s for s in scenarios if not s.get("ineligible")]
        recommended = [s for s in eligible if s["is_recommended"]]
        assert len(recommended) == 1
        cheapest_total = min(s["total_tax"] for s in eligible)
        assert recommended[0]["total_tax"] == cheapest_total

    def test_simples_ineligible_above_limit(self):
        scenarios = compare_tax_regimes(
            annual_revenue=Decimal("5_000_000"),  # above R$ 4.8M limit
            annual_costs=Decimal("2_000_000"),
            annual_payroll=Decimal("500_000"),
        )
        simples = next(s for s in scenarios if s["regime"] == "simples_nacional")
        assert simples.get("ineligible") is True

    def test_effective_rate_between_0_and_100_percent(self):
        scenarios = compare_tax_regimes(
            annual_revenue=Decimal("800_000"),
            annual_costs=Decimal("300_000"),
            annual_payroll=Decimal("100_000"),
        )
        for s in scenarios:
            if not s.get("ineligible"):
                assert 0 < s["effective_rate"] < 1, (
                    f"Effective rate {s['effective_rate']} out of range for {s['regime']}"
                )

    def test_total_tax_positive(self):
        scenarios = compare_tax_regimes(
            annual_revenue=Decimal("300_000"),
            annual_costs=Decimal("100_000"),
            annual_payroll=Decimal("50_000"),
        )
        for s in scenarios:
            if not s.get("ineligible"):
                assert s["total_tax"] > 0

    def test_simples_regime_present(self):
        scenarios = compare_tax_regimes(
            annual_revenue=Decimal("200_000"),
            annual_costs=Decimal("50_000"),
            annual_payroll=Decimal("30_000"),
        )
        regimes = [s["regime"] for s in scenarios]
        assert "simples_nacional" in regimes
        assert "lucro_presumido" in regimes
        assert "lucro_real" in regimes

    def test_cogs_used_for_lucro_real(self):
        """Lucro Real uses COGS when provided, resulting in different tax."""
        s1 = compare_tax_regimes(
            annual_revenue=Decimal("2_000_000"),
            annual_costs=Decimal("1_000_000"),
            annual_payroll=Decimal("200_000"),
            cogs=None,
        )
        s2 = compare_tax_regimes(
            annual_revenue=Decimal("2_000_000"),
            annual_costs=Decimal("1_000_000"),
            annual_payroll=Decimal("200_000"),
            cogs=Decimal("1_500_000"),  # higher COGS → lower taxable profit
        )
        lr1 = next(s for s in s1 if s["regime"] == "lucro_real")
        lr2 = next(s for s in s2 if s["regime"] == "lucro_real")
        # Higher COGS → lower taxes
        assert lr2["total_tax"] <= lr1["total_tax"]


# ---------------------------------------------------------------------------
# ICMS
# ---------------------------------------------------------------------------


class TestCalculateIcms:
    def test_interstate_sp_to_rj(self):
        result = calculate_icms(
            ncm_code="8471.30.12",
            origin_state="SP",
            destination_state="RJ",
            operation_value=Decimal("100_000"),
            is_buyer_taxpayer=True,
        )
        assert result["interstate_rate"] == pytest.approx(0.12)
        assert result["icms_interstate"] == pytest.approx(12_000.0)
        assert result["difal_total"] == pytest.approx(0.0)

    def test_difal_applies_to_non_taxpayer(self):
        result = calculate_icms(
            ncm_code="8471.30.12",
            origin_state="SP",
            destination_state="RJ",
            operation_value=Decimal("100_000"),
            is_buyer_taxpayer=False,
        )
        # DIFAL = (internal_destination_rate - interstate_rate) * value
        # RJ internal = 20%, interstate SP→RJ = 12%
        expected_difal = (0.20 - 0.12) * 100_000
        assert result["difal_total"] == pytest.approx(expected_difal)
        assert result["effective_rate"] > result["interstate_rate"]

    def test_sp_to_am_uses_7_percent(self):
        """Operations from SE/S to N/NE/CO use 7% rate."""
        result = calculate_icms(
            ncm_code="8471.30.12",
            origin_state="SP",
            destination_state="AM",
            operation_value=Decimal("50_000"),
            is_buyer_taxpayer=True,
        )
        assert result["interstate_rate"] == pytest.approx(0.07)
        assert result["icms_interstate"] == pytest.approx(3_500.0)

    def test_result_keys_present(self):
        result = calculate_icms(
            ncm_code="8471.30.12",
            origin_state="MG",
            destination_state="BA",
            operation_value=Decimal("20_000"),
        )
        required_keys = {
            "ncm_code",
            "origin_state",
            "destination_state",
            "operation_value",
            "interstate_rate",
            "internal_destination_rate",
            "icms_interstate",
            "difal_total",
            "effective_rate",
            "is_buyer_taxpayer",
        }
        assert required_keys.issubset(result.keys())

    def test_unknown_state_defaults_17_percent_internal(self):
        rate = _get_icms_internal_rate("ZZ")  # non-existent state
        assert float(rate) == pytest.approx(0.17)


# ---------------------------------------------------------------------------
# PIS/COFINS
# ---------------------------------------------------------------------------


class TestCalculatePisCofins:
    def test_cumulative_rates(self):
        result = calculate_pis_cofins(
            monthly_revenue=Decimal("100_000"),
            is_non_cumulative=False,
        )
        # PIS 0.65% + COFINS 3.00% = 3.65% cumulative
        assert result["pis_rate"] == pytest.approx(0.0065)
        assert result["cofins_rate"] == pytest.approx(0.03)
        assert result["total_pis_cofins"] == pytest.approx(3_650.0)

    def test_non_cumulative_rates(self):
        result = calculate_pis_cofins(
            monthly_revenue=Decimal("100_000"),
            is_non_cumulative=True,
        )
        # PIS 1.65% + COFINS 7.60% = 9.25%
        assert result["pis_rate"] == pytest.approx(0.0165)
        assert result["cofins_rate"] == pytest.approx(0.076)
        assert result["total_pis_cofins"] == pytest.approx(9_250.0)

    def test_credits_reduce_non_cumulative(self):
        result_no_credits = calculate_pis_cofins(
            monthly_revenue=Decimal("100_000"),
            is_non_cumulative=True,
            deductible_credits=None,
        )
        result_with_credits = calculate_pis_cofins(
            monthly_revenue=Decimal("100_000"),
            is_non_cumulative=True,
            deductible_credits=Decimal("5_000"),
        )
        assert result_with_credits["total_pis_cofins"] < result_no_credits["total_pis_cofins"]

    def test_credits_ignored_in_cumulative(self):
        """In cumulative regime, credits should not reduce the tax."""
        result = calculate_pis_cofins(
            monthly_revenue=Decimal("100_000"),
            is_non_cumulative=False,
            deductible_credits=Decimal("10_000"),
        )
        assert result["pis_credit"] == pytest.approx(0.0)
        assert result["cofins_credit"] == pytest.approx(0.0)

    def test_annual_projection_is_12x_monthly(self):
        result = calculate_pis_cofins(
            monthly_revenue=Decimal("50_000"),
            is_non_cumulative=False,
        )
        assert result["annual_projection"] == pytest.approx(result["total_pis_cofins"] * 12)

    def test_effective_rate_between_zero_and_one(self):
        result = calculate_pis_cofins(
            monthly_revenue=Decimal("200_000"),
            is_non_cumulative=True,
        )
        assert 0 < result["effective_rate"] < 1

    def test_result_keys_present(self):
        result = calculate_pis_cofins(
            monthly_revenue=Decimal("80_000"),
            is_non_cumulative=False,
        )
        required_keys = {
            "monthly_revenue",
            "regime_type",
            "pis_rate",
            "cofins_rate",
            "pis_gross",
            "cofins_gross",
            "pis_net",
            "cofins_net",
            "total_pis_cofins",
            "effective_rate",
            "annual_projection",
        }
        assert required_keys.issubset(result.keys())


# ---------------------------------------------------------------------------
# Plan access
# ---------------------------------------------------------------------------


class TestPlanAccess:
    def test_require_plan_raises_on_free(self):
        from fastapi import HTTPException
        from app.core.plan_access import require_plan, PLAN_INTERMEDIARIO

        with pytest.raises(HTTPException) as exc_info:
            require_plan(None, PLAN_INTERMEDIARIO, "Chat")
        assert exc_info.value.status_code == 403
        assert "Intermediário" in exc_info.value.detail

    def test_require_plan_passes_on_matching(self):
        from app.core.plan_access import require_plan, PLAN_INTERMEDIARIO

        # Should not raise
        require_plan("intermediario", PLAN_INTERMEDIARIO, "Chat")

    def test_require_plan_passes_on_premium_for_intermediario_feature(self):
        from app.core.plan_access import require_plan, PLAN_INTERMEDIARIO

        # Premium user can access intermediario features
        require_plan("premium", PLAN_INTERMEDIARIO, "Chat")

    def test_require_plan_raises_on_intermediario_for_premium_feature(self):
        from fastapi import HTTPException
        from app.core.plan_access import require_plan, PLAN_PREMIUM

        with pytest.raises(HTTPException) as exc_info:
            require_plan("intermediario", PLAN_PREMIUM, "PDF export")
        assert exc_info.value.status_code == 403
        assert "Premium" in exc_info.value.detail

    def test_has_plan_returns_correct_booleans(self):
        from app.core.plan_access import has_plan, PLAN_INTERMEDIARIO, PLAN_PREMIUM

        assert has_plan(None, PLAN_INTERMEDIARIO) is False
        assert has_plan("free", PLAN_INTERMEDIARIO) is False
        assert has_plan("intermediario", PLAN_INTERMEDIARIO) is True
        assert has_plan("intermediario", PLAN_PREMIUM) is False
        assert has_plan("premium", PLAN_PREMIUM) is True
        assert has_plan("premium", PLAN_INTERMEDIARIO) is True
