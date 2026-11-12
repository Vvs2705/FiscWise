"""Renders a calculator simulation as a real PDF (fpdf2).

Mirrors the pattern of app/domain/monthly_closing/dossier_pdf.py: core PDF
fonts are latin-1 only, hence the sanitizer — Portuguese accents survive,
exotic glyphs degrade to '?' instead of raising.

Presentation only: values are read from the persisted simulation
(input_data / result_data); nothing is recalculated here.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from fpdf import FPDF

_TYPE_LABELS = {
    "regime": "Comparação de regimes tributários",
    "icms": "Simulação de ICMS",
    "pis_cofins": "Simulação de PIS/COFINS",
    "fator_r": "Simulação de Fator R / DAS",
}

_REGIME_LABELS = {
    "simples_nacional": "Simples Nacional",
    "lucro_presumido": "Lucro Presumido",
    "lucro_real": "Lucro Real",
}

_INPUT_LABELS: dict[str, dict[str, str]] = {
    "regime": {
        "annual_revenue": "Receita bruta anual",
        "annual_costs": "Custos anuais",
        "annual_payroll": "Folha anual",
        "activity_code": "CNAE",
        "cogs": "CMV",
        "gross_profit": "Lucro bruto",
    },
    "icms": {
        "ncm_code": "NCM",
        "origin_state": "UF de origem",
        "destination_state": "UF de destino",
        "operation_value": "Valor da operação",
        "is_buyer_taxpayer": "Comprador contribuinte",
    },
    "pis_cofins": {
        "monthly_revenue": "Receita mensal",
        "is_non_cumulative": "Regime não cumulativo",
        "deductible_credits": "Créditos dedutíveis",
        "activity_description": "Atividade",
    },
}

_MONEY_INPUTS = {
    "annual_revenue", "annual_costs", "annual_payroll", "cogs", "gross_profit",
    "operation_value", "monthly_revenue", "deductible_credits",
}

_ICMS_RESULT_ROWS = [
    ("interstate_rate", "Alíquota interestadual", "pct"),
    ("internal_destination_rate", "Alíquota interna no destino", "pct"),
    ("icms_interstate", "ICMS interestadual", "money"),
    ("difal_total", "DIFAL total", "money"),
    ("difal_origin", "DIFAL origem", "money"),
    ("difal_destination", "DIFAL destino", "money"),
    ("effective_rate", "Alíquota efetiva", "pct"),
]

_PIS_COFINS_RESULT_ROWS = [
    ("pis_rate", "Alíquota PIS", "pct"),
    ("cofins_rate", "Alíquota COFINS", "pct"),
    ("pis_gross", "PIS bruto", "money"),
    ("cofins_gross", "COFINS bruto", "money"),
    ("pis_credit", "Crédito PIS", "money"),
    ("cofins_credit", "Crédito COFINS", "money"),
    ("pis_net", "PIS a pagar", "money"),
    ("cofins_net", "COFINS a pagar", "money"),
    ("total_pis_cofins", "Total PIS/COFINS (mês)", "money"),
    ("effective_rate", "Alíquota efetiva", "pct"),
    ("annual_projection", "Projeção anual", "money"),
]

DISCLAIMER = "Simulação, sem valor legal. Valide com o responsável técnico antes de decidir."


def _latin1(text: Any) -> str:
    if text is None or text == "":
        return ""
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


def _num(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> str:
    n = _num(value)
    if n is None:
        return "-"
    s = f"{n:,.2f}"  # 1,234.56 -> 1.234,56
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(value: Any) -> str:
    n = _num(value)
    if n is None:
        return "-"
    return f"{n * 100:.2f}%".replace(".", ",")


def _fmt(kind: str, value: Any) -> str:
    if kind == "money":
        return _money(value)
    if kind == "pct":
        return _pct(value)
    return "-" if value is None else str(value)


def _fmt_input(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return "Sim" if value else "Não"
    if value is None or value == "":
        return "-"
    if key in _MONEY_INPUTS:
        return _money(value)
    return str(value)


class _SimulationPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 16)
        self.set_text_color(30, 30, 30)
        self.cell(0, 10, _latin1("FiscWise - Relatório de Simulação Fiscal"), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(6)

    def footer(self):
        self.set_y(-18)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, _latin1(DISCLAIMER), align="C", new_x="LMARGIN", new_y="NEXT")
        generated = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        self.cell(0, 5, _latin1(f"Gerado pelo FiscWise em {generated} - página {self.page_no()}"), align="C")


def _section_title(pdf: FPDF, title: str) -> None:
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, _latin1(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _kv_row(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(65, 7, _latin1(label))
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 7, _latin1(value), new_x="LMARGIN", new_y="NEXT")


def _table(pdf: FPDF, headers: list[str], widths: list[float], rows: list[list[str]]) -> None:
    pdf.set_font("helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 235)
    last = len(headers) - 1
    for i, (h, w) in enumerate(zip(headers, widths)):
        kw = {"new_x": "LMARGIN", "new_y": "NEXT"} if i == last else {}
        pdf.cell(w, 7, _latin1(h), border=1, fill=True, **kw)
    pdf.set_font("helvetica", "", 9)
    for row in rows:
        for i, (cell, w) in enumerate(zip(row, widths)):
            kw = {"new_x": "LMARGIN", "new_y": "NEXT"} if i == last else {}
            pdf.cell(w, 7, _latin1(cell), border=1, **kw)


def _render_inputs(pdf: FPDF, sim_type: str, input_data: dict) -> None:
    _section_title(pdf, "Dados de entrada")
    if sim_type == "fator_r":
        months = input_data.get("months") or []
        _kv_row(pdf, "Meses informados", str(len(months)))
    else:
        labels = _INPUT_LABELS.get(sim_type, {})
        for key, value in input_data.items():
            if key == "title":
                continue
            _kv_row(pdf, labels.get(key, key), _fmt_input(key, value))
    pdf.ln(3)


def _render_regime(pdf: FPDF, result: dict) -> Optional[str]:
    scenarios = result.get("scenarios") or []
    rows = []
    recommended = None
    for s in scenarios:
        label = _REGIME_LABELS.get(s.get("regime"), str(s.get("regime") or "-"))
        if s.get("ineligible"):
            rows.append([label, "-", "-", "Inelegível"])
            continue
        flag = "Recomendado" if s.get("is_recommended") else ""
        if s.get("is_recommended"):
            recommended = label
        rows.append([label, _pct(s.get("effective_rate")), _money(s.get("total_tax")), flag])
    _table(pdf, ["Regime", "Alíquota efetiva", "Imposto anual", ""], [60, 40, 50, 40], rows)
    return recommended


def _render_rows(pdf: FPDF, result: dict, spec: list[tuple[str, str, str]]) -> None:
    rows = [[label, _fmt(kind, result.get(key))] for key, label, kind in spec if key in result]
    _table(pdf, ["Item", "Valor"], [110, 80], rows)


def _render_fator_r(pdf: FPDF, result: dict) -> None:
    _kv_row(pdf, "Receita bruta 12 meses (RBT12)", _money(result.get("rbt12")))
    _kv_row(pdf, "Folha 12 meses", _money(result.get("folha_12m")))
    _kv_row(pdf, "Fator R", str(result.get("fator_r_percent") or _pct(result.get("fator_r"))))
    _kv_row(pdf, "Anexo do Simples", f"Anexo {result.get('anexo', '-')}")
    _kv_row(pdf, "DAS anual estimado", _money(result.get("total_das_anual")))
    comparison = result.get("comparison") or {}
    if comparison:
        _kv_row(pdf, f"DAS anual no Anexo {comparison.get('anexo', '-')}", _money(comparison.get("total_das_anual")))
        _kv_row(pdf, "Diferença anual", _money(comparison.get("diferenca_anual")))
    details = result.get("monthly_details") or []
    if details:
        pdf.ln(2)
        rows = [
            [
                str(d.get("mes", "-")),
                _money(d.get("receita")),
                _money(d.get("folha")),
                _pct(d.get("aliquota_efetiva")),
                _money(d.get("das")),
            ]
            for d in details
        ]
        _table(pdf, ["Mês", "Receita", "Folha", "Alíquota", "DAS"], [30, 45, 45, 30, 40], rows)


def render_simulation_pdf(simulation, include_ai: bool) -> bytes:
    sim_type = getattr(simulation.simulation_type, "value", simulation.simulation_type)
    input_data = simulation.input_data or {}
    result = simulation.result_data or {}

    pdf = _SimulationPDF()
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()

    _section_title(pdf, "Simulação")
    _kv_row(pdf, "Tipo", _TYPE_LABELS.get(sim_type, "Simulação fiscal"))
    _kv_row(pdf, "Título", simulation.title or "-")
    created = simulation.created_at.strftime("%d/%m/%Y %H:%M") if simulation.created_at else "-"
    _kv_row(pdf, "Data", created)
    pdf.ln(3)

    _render_inputs(pdf, sim_type, input_data)

    _section_title(pdf, "Resultado")
    recommended = None
    if sim_type == "regime":
        recommended = _render_regime(pdf, result)
    elif sim_type == "icms":
        _render_rows(pdf, result, _ICMS_RESULT_ROWS)
    elif sim_type == "pis_cofins":
        _render_rows(pdf, result, _PIS_COFINS_RESULT_ROWS)
    elif sim_type == "fator_r":
        _render_fator_r(pdf, result)
    pdf.ln(4)

    if recommended:
        _section_title(pdf, "Recomendação")
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, _latin1(f"Regime de menor carga estimada: {recommended}."))
        pdf.ln(2)

    if include_ai and simulation.ai_recommendation:
        _section_title(pdf, "Recomendação da IA")
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, _latin1(simulation.ai_recommendation))

    return bytes(pdf.output())
