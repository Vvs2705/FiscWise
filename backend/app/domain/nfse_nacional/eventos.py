"""Pedido de registro de evento (pedRegEvento, leiaute 1.01) — cancelamento.

Fonte: XSD oficial pedRegEvento_v1.01.xsd / tiposEventos_v1.01.xsd:
- ``<pedRegEvento versao="1.01">`` com ``infPedReg/@Id``;
- Id (TSIdPedRegEvt, até 59 posições) = "PRE" + chave de acesso (50) +
  código do evento (6). Cancelamento = 101101;
- autor: CNPJAutor ou CPFAutor; ``chNFSe``; grupo ``e101101`` com
  ``xDesc`` fixo "Cancelamento de NFS-e", ``cMotivo`` (1 erro na emissão,
  2 serviço não prestado, 9 outros) e ``xMotivo`` (15 a 255 caracteres).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lxml import etree

from app.domain.nfse_nacional.dps import NS_NFSE, VERSAO_LEIAUTE, DpsInvalida, _agora_br

EVENTO_CANCELAMENTO = "101101"
MOTIVOS_CANCELAMENTO = {"1", "2", "9"}


@dataclass
class EventoMontado:
    id_evento: str
    xml: bytes


def montar_cancelamento(
    *,
    chave_acesso: str,
    documento_autor: str,
    motivo: str,
    codigo_motivo: str = "1",
    ambiente: str = "2",
    versao_aplicativo: str = "FiscWise-1.0",
) -> EventoMontado:
    chave = str(chave_acesso or "").strip()
    if not re.fullmatch(r"[0-9]{6}[0-9A-Z]{14}[0-9]{30}", chave):
        raise DpsInvalida("Chave de acesso da NFS-e inválida para cancelamento.")
    texto = " ".join(str(motivo or "").split())
    if len(texto) < 15:
        raise DpsInvalida("O motivo do cancelamento precisa ter pelo menos 15 caracteres.")
    texto = texto[:255]
    codigo = str(codigo_motivo)
    if codigo not in MOTIVOS_CANCELAMENTO:
        raise DpsInvalida("Código do motivo de cancelamento inválido (1, 2 ou 9).")
    autor = re.sub(r"\D", "", str(documento_autor or ""))
    if len(autor) not in (11, 14):
        raise DpsInvalida("CNPJ/CPF do autor do cancelamento inválido.")

    id_evento = f"PRE{chave}{EVENTO_CANCELAMENTO}"
    raiz = etree.Element(f"{{{NS_NFSE}}}pedRegEvento", nsmap={None: NS_NFSE})
    raiz.set("versao", VERSAO_LEIAUTE)
    inf = etree.SubElement(raiz, f"{{{NS_NFSE}}}infPedReg")
    inf.set("Id", id_evento)

    def sub(pai, nome, texto_=None):
        el = etree.SubElement(pai, f"{{{NS_NFSE}}}{nome}")
        if texto_ is not None:
            el.text = str(texto_)
        return el

    sub(inf, "tpAmb", ambiente)
    sub(inf, "verAplic", versao_aplicativo[:20])
    sub(inf, "dhEvento", _agora_br())
    sub(inf, "CNPJAutor" if len(autor) == 14 else "CPFAutor", autor)
    sub(inf, "chNFSe", chave)
    ev = sub(inf, f"e{EVENTO_CANCELAMENTO}")
    sub(ev, "xDesc", "Cancelamento de NFS-e")
    sub(ev, "cMotivo", codigo)
    sub(ev, "xMotivo", texto)
    return EventoMontado(
        id_evento=id_evento,
        xml=etree.tostring(raiz, xml_declaration=True, encoding="UTF-8"),
    )
