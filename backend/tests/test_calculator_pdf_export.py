"""POST /calculator/export-pdf — the PDF must carry the simulation body, not just the title."""

import io
from datetime import datetime, timezone

import pdfplumber
import pytest

from app.core.plan_access import PLAN_PREMIUM
from app.models.calculator import CalculatorSimulation, SimulationType
from app.services.calculator_pdf import render_simulation_pdf


def _text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _sim(sim_type, input_data, result_data, ai=None, title="Simulação de teste"):
    return CalculatorSimulation(
        simulation_type=sim_type,
        title=title,
        input_data=input_data,
        result_data=result_data,
        ai_recommendation=ai,
        created_at=datetime(2026, 11, 12, 10, 30, tzinfo=timezone.utc),
    )


_REGIME_RESULT = {
    "scenarios": [
        {"regime": "simples_nacional", "effective_rate": 0.06, "total_tax": 7200.0, "is_recommended": True},
        {"regime": "lucro_presumido", "effective_rate": 0.1133, "total_tax": 13596.0, "is_recommended": False},
        {"regime": "lucro_real", "effective_rate": 0.15, "total_tax": 18000.0, "is_recommended": False},
    ]
}


@pytest.mark.asyncio
async def test_export_pdf_endpoint_renders_rows(client_with_auth_a, test_db):
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_PREMIUM
    await test_db.commit()

    sim = CalculatorSimulation(
        tenant_id=user_a.tenant_id,
        simulation_type=SimulationType.REGIME,
        title="Comparação anual",
        input_data={"annual_revenue": 120000, "annual_costs": 40000, "activity_code": "6201500"},
        result_data=_REGIME_RESULT,
        ai_recommendation="Manter o Simples Nacional é a opção mais econômica.",
    )
    test_db.add(sim)
    await test_db.commit()
    await test_db.refresh(sim)

    resp = client.post(
        "/api/v1/calculator/export-pdf",
        json={"simulation_id": str(sim.id), "include_ai_recommendation": True},
    )
    assert resp.status_code == 200
    text = _text(resp.content)
    assert "FiscWise" in text
    assert "Comparação de regimes tributários" in text  # accents survive
    assert "Receita bruta anual" in text and "R$ 120.000,00" in text
    assert "Simples Nacional" in text and "R$ 7.200,00" in text and "6,00%" in text
    assert "Lucro Presumido" in text and "Lucro Real" in text
    assert "Recomendado" in text
    assert "Recomendação da IA" in text and "mais econômica" in text
    assert "sem valor legal" in text


def test_pdf_without_ai_flag_omits_ai_block():
    sim = _sim(SimulationType.REGIME, {"annual_revenue": 1}, _REGIME_RESULT, ai="Texto da IA")
    text = _text(render_simulation_pdf(sim, include_ai=False))
    assert "Texto da IA" not in text
    assert "Simples Nacional" in text


def test_pdf_fator_r_has_specific_labels():
    result = {
        "rbt12": 360000.0,
        "folha_12m": 108000.0,
        "fator_r": 0.3,
        "fator_r_percent": "30.00%",
        "anexo": "III",
        "monthly_details": [
            {"mes": "01/2026", "receita": 30000.0, "folha": 9000.0, "das": 1800.0, "aliquota_efetiva": 0.06},
        ],
        "total_das_anual": 21600.0,
        "comparison": {"anexo": "V", "total_das_anual": 55000.0, "diferenca_anual": -33400.0},
    }
    sim = _sim(SimulationType.FATOR_R, {"months": [{"month": "01/2026"}]}, result)
    text = _text(render_simulation_pdf(sim, include_ai=True))
    assert "Simulação de Fator R / DAS" in text
    assert "RBT12" in text and "R$ 360.000,00" in text
    assert "Fator R" in text and "30.00%" in text
    assert "Anexo III" in text and "Anexo V" in text
    assert "01/2026" in text and "R$ 1.800,00" in text
    assert "N/A" not in text


def test_pdf_icms_and_pis_cofins_rows():
    icms = _sim(
        SimulationType.ICMS,
        {"ncm_code": "84713012", "origin_state": "SP", "destination_state": "BA",
         "operation_value": 1000, "is_buyer_taxpayer": False},
        {"interstate_rate": 0.07, "icms_interstate": 70.0, "difal_total": 135.0, "effective_rate": 0.205},
    )
    t = _text(render_simulation_pdf(icms, include_ai=False))
    assert "UF de destino" in t and "BA" in t and "DIFAL total" in t and "R$ 135,00" in t
    assert "Comprador contribuinte" in t and "Não" in t

    pis = _sim(
        SimulationType.PIS_COFINS,
        {"monthly_revenue": 100000, "is_non_cumulative": False},
        {"pis_net": 650.0, "cofins_net": 3000.0, "total_pis_cofins": 3650.0, "effective_rate": 0.0365},
    )
    t = _text(render_simulation_pdf(pis, include_ai=False))
    assert "Total PIS/COFINS (mês)" in t and "R$ 3.650,00" in t and "3,65%" in t
