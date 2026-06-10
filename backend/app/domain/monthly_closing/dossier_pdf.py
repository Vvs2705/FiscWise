"""Renders the monthly closing dossier as a real PDF (fpdf2).

The PDF is generated on demand from the current closing state, so it never
goes stale and nothing needs to be stored. Core PDF fonts are latin-1 only,
hence the sanitizer — Portuguese accents survive, exotic glyphs degrade to
'?' instead of raising.
"""

from datetime import datetime, timezone
from typing import Optional

from fpdf import FPDF

_STATUS_LABELS = {
    "not_started": "Nao iniciado",
    "in_progress": "Em andamento",
    "blocked": "Bloqueado",
    "ready_for_review": "Pronto para revisao",
    "completed": "Concluido",
}

_ITEM_STATUS_LABELS = {
    "pending": "Pendente",
    "done": "Concluido",
    "blocked": "Bloqueado",
    "na": "N/A",
}


def _latin1(text: Optional[str]) -> str:
    if not text:
        return ""
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


def _fmt_dt(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    return value.strftime("%d/%m/%Y %H:%M UTC")


class _DossierPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 16)
        self.set_text_color(30, 30, 30)
        self.cell(0, 10, "FiscWise - Dossie de Fechamento Mensal", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        generated = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        self.cell(0, 10, _latin1(f"Gerado pelo FiscWise em {generated} - pagina {self.page_no()}"), align="C")


def _section_title(pdf: FPDF, title: str) -> None:
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, _latin1(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _kv_row(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(60, 7, _latin1(label))
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 7, _latin1(value), new_x="LMARGIN", new_y="NEXT")


def render_dossier_pdf(
    closing,
    *,
    client_name: Optional[str],
    client_cnpj: Optional[str],
) -> bytes:
    pdf = _DossierPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Identification
    _section_title(pdf, "Identificacao")
    _kv_row(pdf, "Cliente", client_name or "-")
    _kv_row(pdf, "CNPJ", client_cnpj or "-")
    _kv_row(pdf, "Competencia", closing.competence)
    _kv_row(pdf, "Status", _STATUS_LABELS.get(closing.status, closing.status))
    _kv_row(pdf, "Progresso", f"{closing.score}%")
    _kv_row(pdf, "Dossie gerado em", _fmt_dt(closing.dossier_generated_at))
    pdf.ln(4)

    # Counters
    _section_title(pdf, "Resumo do periodo")
    counters = [
        ("Notas fiscais", f"{closing.invoices_count} emitidas/registradas, {closing.invoices_pending} pendentes"),
        ("Guias", f"{closing.guides_count} geradas, {closing.guides_paid} pagas"),
        ("Obrigacoes", f"{closing.obligations_done} de {closing.obligations_total} concluidas"),
        ("Pendencias e-CAC", str(closing.ecac_pendencies)),
        ("Documentos", f"{closing.documents_received} de {closing.documents_total} recebidos"),
    ]
    for label, value in counters:
        _kv_row(pdf, label, value)
    pdf.ln(4)

    # Checklist
    _section_title(pdf, "Checklist do fechamento")
    pdf.set_font("helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 235)
    pdf.cell(110, 7, "Item", border=1, fill=True)
    pdf.cell(30, 7, "Status", border=1, fill=True)
    pdf.cell(0, 7, "Notas", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9)
    for item in closing.checklist or []:
        status = _ITEM_STATUS_LABELS.get(item.get("status", "pending"), item.get("status", ""))
        pdf.cell(110, 7, _latin1(item.get("label", "")), border=1)
        pdf.cell(30, 7, _latin1(status), border=1)
        pdf.cell(0, 7, _latin1(item.get("notes") or "-"), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Blockers
    blockers = closing.blockers or []
    if blockers:
        _section_title(pdf, "Bloqueios")
        pdf.set_font("helvetica", "", 10)
        for blocker in blockers:
            pdf.cell(0, 6, _latin1(f"- {blocker}"), new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
