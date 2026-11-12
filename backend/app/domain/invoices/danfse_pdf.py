"""DANFSe simplificado (fpdf2), gerado sob demanda a partir dos dados da nota.

Não substitui o DANFSe oficial do provedor. Notas emitidas pelo provider
simulado saem marcadas "SIMULACAO - SEM VALOR FISCAL".
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fpdf import FPDF

from app.domain.invoices.models import Invoice

_STATUS = {
    "issued": "Emitida",
    "cancelled": "Cancelada",
    "cancel_requested": "Cancelamento solicitado",
}


def _latin1(text: Optional[str]) -> str:
    if not text:
        return ""
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


def _money(value: Optional[Decimal]) -> str:
    if value is None:
        return "-"
    raw = f"{Decimal(value):,.2f}"
    return "R$ " + raw.replace(",", "X").replace(".", ",").replace("X", ".")


def _dt(value: Optional[datetime]) -> str:
    return value.strftime("%d/%m/%Y %H:%M") if value else "-"


def is_simulated(invoice: Invoice) -> bool:
    raw = invoice.provider_response or {}
    return raw.get("provider") == "mock" or bool(raw.get("mock")) or (
        (invoice.provider_protocol or "").startswith("MOCK-")
    )


def _row(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(55, 7, _latin1(label), border=1)
    pdf.set_font("helvetica", "", 9)
    pdf.multi_cell(0, 7, _latin1(value) or "-", border=1, new_x="LMARGIN", new_y="NEXT")


def render_danfse_pdf(invoice: Invoice) -> bytes:
    simulated = is_simulated(invoice)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("helvetica", "B", 15)
    pdf.cell(0, 10, _latin1("DANFSe - Documento Auxiliar da NFS-e"), new_x="LMARGIN", new_y="NEXT")
    if simulated:
        pdf.set_text_color(200, 30, 30)
        pdf.set_font("helvetica", "B", 13)
        pdf.cell(0, 9, _latin1("SIMULAÇÃO - SEM VALOR FISCAL"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    issuer = invoice.issuer
    _row(pdf, "Número", invoice.numero or "-")
    _row(pdf, "Situação", _STATUS.get(invoice.status, invoice.status))
    _row(pdf, "Protocolo", invoice.provider_protocol or "-")
    _row(pdf, "Emitida em", _dt(invoice.issued_at))
    if invoice.cancelled_at:
        _row(pdf, "Cancelada em", _dt(invoice.cancelled_at))
    _row(pdf, "Competência", invoice.competencia.strftime("%m/%Y"))
    pdf.ln(2)
    _row(pdf, "Prestador (CNPJ)", issuer.cnpj if issuer else "-")
    _row(pdf, "Inscrição municipal", (issuer.inscricao_municipal if issuer else None) or "-")
    _row(pdf, "Tomador", invoice.tomador_nome or "-")
    _row(pdf, "CPF/CNPJ do tomador", invoice.tomador_cpf_cnpj or "-")
    pdf.ln(2)
    _row(pdf, "Discriminação", invoice.descricao_servico)
    _row(pdf, "Valor do serviço", _money(invoice.valor_servico))
    _row(pdf, "Deduções", _money(invoice.valor_deducoes))
    _row(pdf, "ISS", _money(invoice.valor_iss))

    pdf.ln(4)
    pdf.set_font("helvetica", "I", 8)
    pdf.multi_cell(
        0,
        5,
        _latin1(
            "Documento gerado pelo FiscWise a partir dos dados da nota. "
            + ("Emitido em ambiente de simulação: não tem validade fiscal." if simulated
               else "Consulte o DANFSe oficial no portal do provedor de NFS-e.")
        ),
    )
    return bytes(pdf.output())
