"""Document Parsing Service for FiscWise

Handles parsing of different document formats (PDF, Excel, Word, XML de
NF-e/NFS-e, CSV, OFX). Extracts text and structured data from uploaded documents.

Formatos que não lemos (imagem sem OCR, .doc/.xls binários, .zip) não são
"falha": voltam como `skipped` com o motivo (ver `skipped_result`). Nada é
inventado — campo não encontrado no arquivo fica None.
"""

import csv
import re
import xml.etree.ElementTree as ET
from datetime import date
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

SKIPPED_KEY = "skipped_reason"

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".bmp", ".tif", ".tiff"}
_SKIP_REASONS = {
    ".doc": "arquivo .doc (Word binário antigo) não é lido; envie .docx ou PDF",
    ".xls": "planilha .xls (Excel binário antigo) não é lida; envie .xlsx ou CSV",
    ".zip": "arquivo compactado (.zip) não é aberto; envie os arquivos separados",
}
_IMAGE_REASON = "imagem sem OCR"


def skipped_result(file_type: str, reason: str) -> Dict[str, Any]:
    """parsed_data de um arquivo aceito que o parser não lê (não é erro)."""
    return {"type": file_type, SKIPPED_KEY: reason}


def is_skipped(parsed_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Motivo do skip, se o parser pulou o arquivo; None caso contrário."""
    if isinstance(parsed_data, dict):
        reason = parsed_data.get(SKIPPED_KEY)
        if isinstance(reason, str) and reason:
            return reason
    return None


async def parse_document(file_path: str, file_name: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parse document based on file type.

    Args:
        file_path: Path to uploaded file
        file_name: Original file name

    Returns:
        Tuple of (parsed_data, error_message)
        parsed_data is a dict with extracted content
        error_message is set if parsing failed
    """
    try:
        file_ext = Path(file_name).suffix.lower()

        if file_ext == ".pdf":
            return await _parse_pdf(file_path)
        elif file_ext in _SKIP_REASONS:
            return skipped_result(file_ext.lstrip("."), _SKIP_REASONS[file_ext]), None
        elif file_ext in _IMAGE_EXTS:
            return skipped_result("image", _IMAGE_REASON), None
        elif file_ext == ".xlsx":
            return await _parse_excel(file_path)
        elif file_ext == ".docx":
            return await _parse_word(file_path)
        elif file_ext == ".txt":
            return await _parse_text(file_path)
        elif file_ext == ".xml":
            return await _parse_xml(file_path)
        elif file_ext == ".csv":
            return await _parse_csv(file_path)
        elif file_ext == ".ofx":
            return await _parse_ofx(file_path)
        else:
            return None, f"Unsupported file format: {file_ext}"

    except Exception as e:
        logger.error(f"Error parsing document: {str(e)}")
        return None, str(e)


async def _parse_pdf(file_path: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse PDF file and extract text."""
    try:
        import pdfplumber

        data = {
            "type": "pdf",
            "pages": [],
            "total_pages": 0,
            "full_text": ""
        }

        with pdfplumber.open(file_path) as pdf:
            data["total_pages"] = len(pdf.pages)

            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                data["pages"].append({
                    "page": page_num,
                    "text": text[:1000]  # First 1000 chars per page
                })
                data["full_text"] += text + "\n"

        # Truncate full text to first 5000 chars
        data["full_text"] = data["full_text"][:5000]
        return data, None

    except ImportError:
        return None, "pdfplumber library not installed"
    except Exception as e:
        return None, f"PDF parsing error: {str(e)}"


async def _parse_excel(file_path: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse Excel file and extract data."""
    try:
        from openpyxl import load_workbook

        data = {
            "type": "excel",
            "sheets": [],
            "total_sheets": 0
        }

        wb = load_workbook(file_path, data_only=True)
        data["total_sheets"] = len(wb.sheetnames)

        # Parse first 3 sheets
        for sheet_name in wb.sheetnames[:3]:
            ws = wb[sheet_name]
            sheet_data = {
                "name": sheet_name,
                "rows": []
            }

            # Extract first 20 rows
            for row_idx, row in enumerate(ws.iter_rows(max_row=20, values_only=True), 1):
                sheet_data["rows"].append({
                    "row": row_idx,
                    "values": [str(v) if v is not None else "" for v in row]
                })

            data["sheets"].append(sheet_data)

        return data, None

    except ImportError:
        return None, "openpyxl library not installed"
    except Exception as e:
        return None, f"Excel parsing error: {str(e)}"


async def _parse_word(file_path: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse Word document and extract text."""
    try:
        from docx import Document

        data = {
            "type": "word",
            "paragraphs": [],
            "tables": [],
            "full_text": ""
        }

        doc = Document(file_path)

        # Extract paragraphs
        for para_idx, para in enumerate(doc.paragraphs):
            if para.text.strip():
                data["paragraphs"].append({
                    "index": para_idx,
                    "text": para.text[:500]
                })
                data["full_text"] += para.text + "\n"

        # Extract tables
        for table_idx, table in enumerate(doc.tables[:5]):  # First 5 tables
            table_data = {
                "index": table_idx,
                "rows": []
            }
            for row in table.rows[:10]:  # First 10 rows
                table_data["rows"].append([
                    cell.text[:100] for cell in row.cells
                ])
            data["tables"].append(table_data)

        # Truncate full text
        data["full_text"] = data["full_text"][:5000]
        return data, None

    except ImportError:
        return None, "python-docx library not installed"
    except Exception as e:
        return None, f"Word parsing error: {str(e)}"


async def _parse_text(file_path: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse plain text file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        data = {
            "type": "text",
            "content": content[:5000],
            "total_length": len(content)
        }

        return data, None

    except Exception as e:
        return None, f"Text parsing error: {str(e)}"


# ---------------------------------------------------------------------------
# XML (NF-e / NFS-e)
# ---------------------------------------------------------------------------

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
_MAX_ITEMS = 20
_DTD_RE = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(el: Optional[ET.Element], *names: str) -> Optional[ET.Element]:
    """Desce por nomes locais (ignora namespace): _child(nfe, "ide", "nNF")."""
    cur = el
    for name in names:
        if cur is None:
            return None
        cur = next((c for c in cur if _local(c.tag) == name), None)
    return cur


def _text(el: Optional[ET.Element], *names: str) -> Optional[str]:
    node = _child(el, *names) if names else el
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None


def _find(el: ET.Element, name: str) -> Optional[ET.Element]:
    """Primeiro descendente com esse nome local (qualquer profundidade)."""
    return next((e for e in el.iter() if _local(e.tag) == name), None)


def _iso_date(value: Optional[str]) -> Optional[str]:
    if not value or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def _party(el: Optional[ET.Element]) -> Optional[Dict[str, Optional[str]]]:
    if el is None:
        return None
    return {
        "cnpj": _text(el, "CNPJ"),
        "cpf": _text(el, "CPF"),
        "razao_social": _text(el, "xNome"),
    }


def _read_xml_root(file_path: str) -> ET.Element:
    with open(file_path, "rb") as f:
        raw = f.read()
    # NF-e/NFS-e nunca têm DTD; recusar DOCTYPE/ENTITY corta XXE e "billion laughs".
    if _DTD_RE.search(raw):
        raise ValueError("XML com DOCTYPE/ENTITY não é aceito")
    return ET.fromstring(raw)


def _parse_nfe(root: ET.Element) -> Dict[str, Any]:
    inf = _find(root, "infNFe")
    if inf is None:
        raise ValueError("XML sem infNFe")
    chave = _text(_find(root, "infProt"), "chNFe")
    if not chave:
        id_attr = inf.get("Id") or ""
        digits = id_attr[3:] if id_attr.startswith("NFe") else id_attr
        chave = digits if len(digits) == 44 and digits.isdigit() else None
    ide = _child(inf, "ide")
    itens = []
    for det in (c for c in inf if _local(c.tag) == "det"):
        if len(itens) >= _MAX_ITEMS:
            break
        prod = _child(det, "prod")
        itens.append({
            "descricao": _text(prod, "xProd"),
            "ncm": _text(prod, "NCM"),
            "cfop": _text(prod, "CFOP"),
            "valor": _text(prod, "vProd"),
        })
    total_itens = sum(1 for c in inf if _local(c.tag) == "det")
    return {
        "type": "nfe",
        "chave_acesso": chave,
        "numero": _text(ide, "nNF"),
        "serie": _text(ide, "serie"),
        "modelo": _text(ide, "mod"),
        "data_emissao": _iso_date(_text(ide, "dhEmi") or _text(ide, "dEmi")),
        "natureza_operacao": _text(ide, "natOp"),
        "emitente": _party(_child(inf, "emit")),
        "destinatario": _party(_child(inf, "dest")),
        "valor_total": _text(inf, "total", "ICMSTot", "vNF"),
        "itens": itens,
        "total_itens": total_itens,
    }


def _first_text(root: ET.Element, *names: str) -> Optional[str]:
    for name in names:
        value = _text(_find(root, name))
        if value:
            return value
    return None


def _nfse_party(el: Optional[ET.Element]) -> Optional[Dict[str, Optional[str]]]:
    if el is None:
        return None
    return {
        "cnpj": _first_text(el, "CNPJ", "Cnpj"),
        "cpf": _first_text(el, "CPF", "Cpf"),
        "razao_social": _first_text(el, "xNome", "RazaoSocial"),
    }


def _parse_nfse(root: ET.Element) -> Dict[str, Any]:
    """NFS-e: padrão nacional (infNFSe) e ABRASF (InfNfse). Só o que achar."""
    prest = next(
        (e for e in root.iter() if _local(e.tag) in ("PrestadorServico", "Prestador", "prest", "emit")),
        None,
    )
    toma = next(
        (e for e in root.iter() if _local(e.tag) in ("TomadorServico", "Tomador", "toma")),
        None,
    )
    return {
        "type": "nfse",
        "chave_acesso": _first_text(root, "chNFSe", "CodigoVerificacao"),
        "numero": _first_text(root, "nNFSe", "Numero"),
        "serie": _first_text(root, "serie", "Serie"),
        "data_emissao": _iso_date(_first_text(root, "dhEmi", "DataEmissao", "dhProc")),
        "emitente": _nfse_party(prest),
        "destinatario": _nfse_party(toma),
        "valor_total": _first_text(root, "vLiq", "ValorLiquidoNfse", "vServ", "ValorServicos"),
        "itens": [],
        "total_itens": 0,
    }


async def _parse_xml(file_path: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """XML: NF-e (portalfiscal), NFS-e ou XML genérico (só a tag raiz)."""
    try:
        root = _read_xml_root(file_path)
    except ValueError as e:
        return None, f"XML parsing error: {e}"
    except ET.ParseError as e:
        return None, f"XML parsing error: {e}"
    if _find(root, "infNFe") is not None:
        return _parse_nfe(root), None
    if any(_local(e.tag) in ("infNFSe", "InfNfse", "CompNfse", "NFSe", "Nfse") for e in root.iter()):
        return _parse_nfse(root), None
    namespace = root.tag[1:].split("}")[0] if root.tag.startswith("{") else None
    return {"type": "xml", "root": _local(root.tag), "namespace": namespace}, None


# ---------------------------------------------------------------------------
# CSV (só metadados) e OFX
# ---------------------------------------------------------------------------

def _read_text_any(file_path: str) -> str:
    with open(file_path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


async def _parse_csv(file_path: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """CSV: colunas, nº de linhas e delimitador. Conteúdo não é copiado."""
    try:
        content = _read_text_any(file_path)
        sample = content[:8192]
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
        except csv.Error:
            delimiter = ";" if sample.count(";") > sample.count(",") else ","
        rows = csv.reader(content.splitlines(), delimiter=delimiter)
        header = next(rows, None)
        total = sum(1 for r in rows if any(cell.strip() for cell in r))
        columns = [c.strip() for c in header][:50] if header else []
        return {
            "type": "csv",
            "delimiter": delimiter,
            "columns": columns,
            "total_columns": len(header) if header else 0,
            "total_rows": total,
        }, None
    except Exception as e:
        return None, f"CSV parsing error: {str(e)}"


def _ofx_tag(content: str, tag: str) -> Optional[str]:
    # OFX 1.x (SGML) não fecha tags: valor vai até o próximo "<" ou fim da linha.
    m = re.search(rf"<{tag}>\s*([^<\r\n]+)", content, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _ofx_date(value: Optional[str]) -> Optional[str]:
    if not value or len(value) < 8 or not value[:8].isdigit():
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:8])).isoformat()
    except ValueError:
        return None


async def _parse_ofx(file_path: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """OFX (extrato): banco, conta, período, saldo e nº de lançamentos."""
    try:
        content = _read_text_any(file_path)
        if "<OFX>" not in content.upper():
            return None, "OFX parsing error: arquivo sem bloco <OFX>"
        ledger = re.search(r"<LEDGERBAL>(.*?)(</LEDGERBAL>|<AVAILBAL>|</STMTRS>|$)", content, re.IGNORECASE | re.DOTALL)
        ledger_txt = ledger.group(1) if ledger else ""
        return {
            "type": "ofx",
            "banco": _ofx_tag(content, "BANKID"),
            "agencia": _ofx_tag(content, "BRANCHID"),
            "conta": _ofx_tag(content, "ACCTID"),
            "moeda": _ofx_tag(content, "CURDEF"),
            "periodo_inicio": _ofx_date(_ofx_tag(content, "DTSTART")),
            "periodo_fim": _ofx_date(_ofx_tag(content, "DTEND")),
            "saldo": _ofx_tag(ledger_txt, "BALAMT") if ledger_txt else None,
            "data_saldo": _ofx_date(_ofx_tag(ledger_txt, "DTASOF")) if ledger_txt else None,
            "total_lancamentos": len(re.findall(r"<STMTTRN>", content, re.IGNORECASE)),
        }, None
    except Exception as e:
        return None, f"OFX parsing error: {str(e)}"
