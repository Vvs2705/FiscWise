"""DPS — Declaração de Prestação de Serviço (padrão nacional, leiaute 1.01).

Fonte do leiaute: XSD oficial DPS_v1.01.xsd / tiposComplexos_v1.01.xsd /
tiposSimples_v1.01.xsd (empacotados no nfelib, MIT). Pontos do XSD usados aqui:

- raiz ``<DPS versao="1.01" xmlns="http://www.sped.fazenda.gov.br/nfse">``;
- ``infDPS/@Id`` = "DPS" + cód. município IBGE (7) + tipo de inscrição
  (1 = CPF, 2 = CNPJ) + inscrição (14, CPF com zeros à esquerda) + série (5)
  + número da DPS (15), com zeros à esquerda (TSIdDPS);
- ``finNFSe`` é obrigatório no 1.01 (0 = NFS-e regular);
- ``cTribNac`` tem 6 dígitos: item (2) + subitem (2) da LC 116/2003 +
  desdobro nacional (2);
- ``totTrib``: usamos ``indTotTrib = 0`` (não informar tributos aproximados,
  Decreto 8.264/2014), aceito para qualquer regime pelo XSD.

Contrato de ``invoice_data`` (o serviço de notas monta; veja
``montar_invoice_data``):

    cnpj_emissor (ou cpf_emissor), inscricao_municipal, municipio_ibge,
    regime_tributario ("mei" | "simples" | "lucro_presumido" | "lucro_real" | ...),
    cod_servico_lc116 ("01.07", "0107" ou o código nacional de 6 dígitos),
    aliquota_iss (fração 0.05 ou percentual 5), retencao_iss (bool),
    competencia (date ou "AAAA-MM-DD"), valor_servico, descricao_servico,
    tomador_cpf_cnpj, tomador_nome, tomador_email (opcionais),
    serie_dps, numero_dps (OBRIGATÓRIO, sequencial por emissor e série — o
    serviço reserva o número antes de transmitir; reenviar o mesmo número é
    o que torna a emissão idempotente na Sefin),
    municipio_prestacao_ibge (opcional; padrão = município do emissor).

Campos de IBS/CBS (grupo IBSCBS, NT 004) ficam de fora por padrão: o Sistema
Nacional ainda aceita DPS sem o grupo. Quando passar a ser obrigatório,
preencher em ``_grupo_ibscbs``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from typing import Any, Optional

import pytz
from lxml import etree

NS_NFSE = "http://www.sped.fazenda.gov.br/nfse"
VERSAO_LEIAUTE = "1.01"
TZ_BR = pytz.timezone("America/Sao_Paulo")

AMBIENTE_PRODUCAO = "1"
AMBIENTE_HOMOLOGACAO = "2"  # produção restrita

# Situação perante o Simples Nacional (TSOpSimpNac).
OP_SIMPLES_NAO_OPTANTE = "1"
OP_SIMPLES_MEI = "2"
OP_SIMPLES_ME_EPP = "3"


class DpsInvalida(ValueError):
    """Dados insuficientes ou fora do leiaute oficial: a DPS não sai."""


@dataclass
class DpsMontada:
    id_dps: str
    xml: bytes  # DPS sem assinatura, UTF-8
    avisos: list[str] = field(default_factory=list)


def _digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _dec2(valor: Any) -> str:
    d = Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if d < 0:
        raise DpsInvalida("Valor negativo não é aceito na DPS.")
    texto = f"{d:.2f}"
    return "0" if texto == "0.00" else texto


def _data(valor: Any) -> str:
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor or "").strip()[:10]
    try:
        return date.fromisoformat(texto).isoformat()
    except ValueError as exc:
        raise DpsInvalida(f"Data de competência inválida: {valor!r}") from exc


def _agora_br() -> str:
    """dhEmi no formato do XSD (AAAA-MM-DDThh:mm:ss-03:00)."""
    agora = datetime.now(TZ_BR).replace(microsecond=0)
    texto = agora.isoformat()
    return texto


def codigo_tributacao_nacional(codigo: Any) -> tuple[str, Optional[str]]:
    """LC 116 → cTribNac (6 dígitos). Devolve (código, aviso).

    Aceita o código nacional pronto (6 dígitos) ou o item/subitem da LC 116
    ("1.07", "01.07", "0107"). Sem o desdobro, usa "01" e avisa: o desdobro
    nacional muda conforme o serviço e precisa ser conferido pelo contador.
    """
    bruto = str(codigo or "").strip()
    if not bruto:
        raise DpsInvalida("Informe o código do serviço (item da LC 116 ou código de tributação nacional).")
    if re.fullmatch(r"\d{6}", bruto):
        return bruto, None
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{1,2}))?", bruto)
    if m:
        item, sub, desd = m.group(1), m.group(2), m.group(3)
    elif re.fullmatch(r"\d{4}", bruto):
        item, sub, desd = bruto[:2], bruto[2:], None
    else:
        raise DpsInvalida(f"Código de serviço não reconhecido: {bruto!r}")
    aviso = None
    if desd is None:
        desd = "01"
        aviso = (
            f"Código de serviço {bruto} sem desdobro nacional: usado {int(item):02d}{int(sub):02d}01. "
            "Confira o desdobro na tabela do Sistema Nacional."
        )
    return f"{int(item):02d}{int(sub):02d}{int(desd):02d}", aviso


def _op_simples(regime: str) -> str:
    regime = (regime or "").strip().lower()
    if regime == "mei":
        return OP_SIMPLES_MEI
    if regime in ("simples", "simples_nacional", "me_epp"):
        return OP_SIMPLES_ME_EPP
    return OP_SIMPLES_NAO_OPTANTE


def _aliquota_percentual(valor: Any) -> Optional[str]:
    if valor in (None, ""):
        return None
    d = Decimal(str(valor))
    if d <= 0:
        return None
    if d < 1:  # gravado como fração (0.05 = 5%)
        d = d * 100
    d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if d >= 10:
        raise DpsInvalida(f"Alíquota de ISS fora do leiaute (máximo 9,99%): {d}%")
    return f"{d:.2f}"


def montar_id_dps(municipio_ibge: str, documento: str, serie: str, numero: str) -> str:
    mun = _digitos(municipio_ibge)
    doc = _digitos(documento)
    if len(mun) != 7:
        raise DpsInvalida("Código IBGE do município do emissor deve ter 7 dígitos.")
    if len(doc) == 14:
        tipo = "2"
    elif len(doc) == 11:
        tipo, doc = "1", doc.zfill(14)
    else:
        raise DpsInvalida("CNPJ/CPF do emissor inválido.")
    serie_d, numero_d = _digitos(serie), _digitos(numero)
    if not serie_d or len(serie_d) > 5:
        raise DpsInvalida("Série da DPS inválida.")
    if not numero_d or len(numero_d) > 15 or int(numero_d) == 0:
        raise DpsInvalida("Número da DPS inválido (1 a 15 dígitos, maior que zero).")
    return f"DPS{mun}{tipo}{doc}{serie_d.zfill(5)}{numero_d.zfill(15)}"


def _sub(pai: etree._Element, nome: str, texto: Any = None) -> etree._Element:
    el = etree.SubElement(pai, f"{{{NS_NFSE}}}{nome}")
    if texto is not None:
        el.text = str(texto)
    return el


def _pessoa_documento(pai: etree._Element, documento: str) -> None:
    doc = _digitos(documento)
    if len(doc) == 14:
        _sub(pai, "CNPJ", doc)
    elif len(doc) == 11:
        _sub(pai, "CPF", doc)
    else:
        raise DpsInvalida("CPF/CNPJ do tomador inválido.")


def montar_dps(
    invoice_data: dict,
    *,
    ambiente: str = AMBIENTE_HOMOLOGACAO,
    versao_aplicativo: str = "FiscWise-1.0",
    serie_padrao: str = "1",
) -> DpsMontada:
    """Monta a DPS (sem assinatura) a partir dos dados da nota."""
    avisos: list[str] = []
    documento = _digitos(invoice_data.get("cnpj_emissor") or invoice_data.get("cpf_emissor"))
    municipio = _digitos(invoice_data.get("municipio_ibge"))
    serie = _digitos(invoice_data.get("serie_dps") or serie_padrao)
    numero = _digitos(invoice_data.get("numero_dps"))
    if not numero:
        raise DpsInvalida("Número da DPS não reservado: o serviço deve informar numero_dps.")
    id_dps = montar_id_dps(municipio, documento, serie, numero)

    descricao = str(invoice_data.get("descricao_servico") or "").strip()
    if not descricao:
        raise DpsInvalida("Descrição do serviço é obrigatória.")
    if len(descricao) > 2000:
        raise DpsInvalida("Descrição do serviço passa de 2.000 caracteres.")

    valor = Decimal(str(invoice_data.get("valor_servico") or 0))
    if valor <= 0:
        raise DpsInvalida("Valor do serviço deve ser maior que zero.")

    deducoes = Decimal(str(invoice_data.get("valor_deducoes") or 0))
    if deducoes > 0:
        avisos.append(
            "Deduções da base de cálculo ainda não são enviadas na DPS pelo FiscWise; "
            "a nota sai com a base cheia."
        )

    c_trib, aviso_trib = codigo_tributacao_nacional(invoice_data.get("cod_servico_lc116"))
    if aviso_trib:
        avisos.append(aviso_trib)

    raiz = etree.Element(f"{{{NS_NFSE}}}DPS", nsmap={None: NS_NFSE})
    raiz.set("versao", VERSAO_LEIAUTE)
    inf = _sub(raiz, "infDPS")
    inf.set("Id", id_dps)
    _sub(inf, "tpAmb", ambiente)
    _sub(inf, "dhEmi", invoice_data.get("dh_emissao") or _agora_br())
    _sub(inf, "verAplic", versao_aplicativo[:20])
    _sub(inf, "serie", str(int(serie)))
    _sub(inf, "nDPS", str(int(numero)))
    _sub(inf, "dCompet", _data(invoice_data.get("competencia")))
    _sub(inf, "tpEmit", "1")  # 1 = prestador
    _sub(inf, "finNFSe", "0")  # NFS-e regular
    _sub(inf, "cLocEmi", municipio)

    prest = _sub(inf, "prest")
    if len(documento) == 14:
        _sub(prest, "CNPJ", documento)
    else:
        _sub(prest, "CPF", documento)
    im = str(invoice_data.get("inscricao_municipal") or "").strip()
    if im:
        _sub(prest, "IM", im[:15])
    op_simples = _op_simples(invoice_data.get("regime_tributario"))
    reg = _sub(prest, "regTrib")
    _sub(reg, "opSimpNac", op_simples)
    if op_simples == OP_SIMPLES_ME_EPP:
        # 1 = tributos federais e municipal apurados pelo Simples Nacional.
        _sub(reg, "regApTribSN", str(invoice_data.get("regime_apuracao_sn") or "1"))
    _sub(reg, "regEspTrib", str(invoice_data.get("regime_especial") or "0"))

    tomador_doc = _digitos(invoice_data.get("tomador_cpf_cnpj"))
    if tomador_doc:
        toma = _sub(inf, "toma")
        _pessoa_documento(toma, tomador_doc)
        nome = str(invoice_data.get("tomador_nome") or "").strip()
        if nome:
            _sub(toma, "xNome", nome[:300])
        email = str(invoice_data.get("tomador_email") or "").strip()
        if email:
            _sub(toma, "email", email[:80])
    else:
        avisos.append("Nota sem tomador identificado.")

    serv = _sub(inf, "serv")
    loc = _sub(serv, "locPrest")
    loc_prest = _digitos(invoice_data.get("municipio_prestacao_ibge")) or municipio
    _sub(loc, "cLocPrestacao", loc_prest)
    cserv = _sub(serv, "cServ")
    _sub(cserv, "cTribNac", c_trib)
    _sub(cserv, "xDescServ", descricao)

    valores = _sub(inf, "valores")
    vsp = _sub(valores, "vServPrest")
    _sub(vsp, "vServ", _dec2(valor))
    trib = _sub(valores, "trib")
    trib_mun = _sub(trib, "tribMun")
    _sub(trib_mun, "tribISSQN", "1")  # operação tributável
    _sub(trib_mun, "tpRetISSQN", "2" if invoice_data.get("retencao_iss") else "1")
    aliquota = _aliquota_percentual(invoice_data.get("aliquota_iss"))
    if aliquota and op_simples != OP_SIMPLES_MEI:
        _sub(trib_mun, "pAliq", aliquota)
    tot = _sub(trib, "totTrib")
    _sub(tot, "indTotTrib", "0")

    xml = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")
    return DpsMontada(id_dps=id_dps, xml=xml, avisos=avisos)


def montar_invoice_data(invoice: Any, issuer: Any, *, numero_dps: int | str, serie_dps: str | None = None) -> dict:
    """Converte Invoice + InvoiceIssuer (modelos do FiscWise) no ``invoice_data``."""
    return {
        "cnpj_emissor": getattr(issuer, "cnpj", None),
        "inscricao_municipal": getattr(issuer, "inscricao_municipal", None),
        "municipio_ibge": getattr(issuer, "municipio_ibge", None),
        "regime_tributario": getattr(issuer, "regime_tributario", None),
        "cod_servico_lc116": getattr(issuer, "cod_servico_lc116", None),
        "aliquota_iss": getattr(issuer, "aliquota_iss", None),
        "retencao_iss": bool(getattr(issuer, "retencao_iss", False)),
        "competencia": getattr(invoice, "competencia", None),
        "valor_servico": getattr(invoice, "valor_servico", None),
        "valor_deducoes": getattr(invoice, "valor_deducoes", None),
        "descricao_servico": getattr(invoice, "descricao_servico", None),
        "tomador_cpf_cnpj": getattr(invoice, "tomador_cpf_cnpj", None),
        "tomador_nome": getattr(invoice, "tomador_nome", None),
        "tomador_email": getattr(invoice, "tomador_email", None),
        "numero_dps": str(numero_dps),
        "serie_dps": serie_dps,
    }


# ---------------------------------------------------------------------------
# Validação no XSD oficial (arquivos do nfelib)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=4)
def _schema(nome_arquivo: str) -> etree.XMLSchema:
    from importlib import resources

    pasta = resources.files("nfelib.nfse.schemas.v1_0")
    caminho = pasta / nome_arquivo
    parser = etree.XMLParser(no_network=True, resolve_entities=False, load_dtd=False)
    with resources.as_file(caminho) as arquivo:
        doc = etree.parse(str(arquivo), parser)
        return etree.XMLSchema(doc)


def validar_xml(xml: bytes, nome_xsd: str = "DPS_v1.01.xsd") -> None:
    """Valida no XSD oficial; levanta DpsInvalida com as mensagens do schema."""
    schema = _schema(nome_xsd)
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    doc = etree.fromstring(xml, parser)
    if not schema.validate(doc):
        erros = "; ".join(f"linha {e.line}: {e.message}" for e in list(schema.error_log)[:5])
        raise DpsInvalida(f"DPS fora do leiaute oficial: {erros}")
