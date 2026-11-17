"""Provider real da NFS-e pelo padrão nacional (Sefin Nacional).

Fluxo de emissão: monta a DPS (leiaute 1.01) → valida no XSD oficial → assina
com o certificado do cofre → envia (gzip+base64, TLS mútuo) → lê a NFS-e
autorizada. Se a resposta se perder depois do envio (timeout), consulta a DPS
pelo Id antes de desistir: o Id é fixo para série+número, então reenviar ou
consultar nunca gera nota em dobro.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from lxml import etree

from app.core.config import settings
from app.domain.invoices.providers.base import NfseProvider, TransientEmissionError
from app.domain.nfse_nacional.assinatura import AssinaturaInvalida, assinar_xml
from app.domain.nfse_nacional.cliente import ClienteNfseNacional, ErroConexaoNfse, RespostaSefin, de_gzip_b64
from app.domain.nfse_nacional.dps import (
    AMBIENTE_HOMOLOGACAO,
    AMBIENTE_PRODUCAO,
    DpsInvalida,
    montar_dps,
    montar_id_dps,
    validar_xml,
)
from app.domain.nfse_nacional.eventos import montar_cancelamento

logger = logging.getLogger(__name__)

SEM_CERTIFICADO = "Certificado digital não configurado para este emissor."


def _ambiente() -> str:
    return AMBIENTE_PRODUCAO if (settings.NFSE_AMBIENTE or "").lower() == "producao" else AMBIENTE_HOMOLOGACAO


def _base_url() -> str:
    if _ambiente() == AMBIENTE_PRODUCAO:
        return settings.NFSE_SEFIN_URL_PRODUCAO
    return settings.NFSE_SEFIN_URL_RESTRITA


def _numero_nfse(xml: bytes) -> Optional[str]:
    try:
        raiz = etree.fromstring(xml, etree.XMLParser(no_network=True, resolve_entities=False))
    except etree.XMLSyntaxError:
        return None
    el = raiz.find(".//{*}nNFSe")
    return el.text.strip() if el is not None and el.text else None


def _get(obj: Any, nome: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(nome)
    return getattr(obj, nome, None)


class NfseNacionalProvider(NfseProvider):
    def __init__(self, transport: Any = None) -> None:
        # transport: só para testes (httpx.MockTransport).
        self._transport = transport

    def _cliente(self, material: Any) -> ClienteNfseNacional:
        return ClienteNfseNacional(
            base_url=_base_url(),
            material=material,
            timeout=settings.NFSE_TIMEOUT_SECONDS,
            ca_bundle=settings.NFSE_CA_BUNDLE,
            transport=self._transport,
        )

    @staticmethod
    def _rejeitada(resp: RespostaSefin, id_dps: Optional[str] = None, avisos: Optional[list] = None) -> dict:
        rejeicoes = resp.erros or [{
            "codigo": str(resp.status_code),
            "descricao": "A Sefin Nacional recusou o pedido sem detalhar o motivo.",
            "complemento": "",
        }]
        primeira = rejeicoes[0]
        return {
            "status": "rejected",
            "protocol": None,
            "id_dps": id_dps,
            "rejeicoes": rejeicoes,
            "codigo_rejeicao": primeira.get("codigo"),
            "descricao": " — ".join(x for x in (primeira.get("descricao"), primeira.get("complemento")) if x),
            "avisos": avisos or [],
            "raw": {"http_status": resp.status_code, "erros": resp.erros, "alertas": resp.alertas},
        }

    async def _emitida(self, resp: RespostaSefin, id_dps: str, avisos: list, cliente: ClienteNfseNacional) -> dict:
        chave = resp.campo("chaveAcesso", "chave")
        xml_b64 = resp.campo("nfseXmlGZipB64")
        xml = de_gzip_b64(xml_b64) if xml_b64 else None
        if xml is None and chave:
            consulta = await cliente.consultar_nfse(chave)
            b64 = consulta.campo("nfseXmlGZipB64")
            xml = de_gzip_b64(b64) if b64 else None
        return {
            "status": "issued",
            "protocol": chave,
            "numero": _numero_nfse(xml) if xml else None,
            "xml": xml.decode("utf-8") if xml else None,
            "id_dps": id_dps,
            "rejeicoes": [],
            "avisos": avisos + [a.get("descricao", "") for a in resp.alertas if a.get("descricao")],
            "raw": {"http_status": resp.status_code, "chaveAcesso": chave, "idDps": resp.campo("idDps") or id_dps,
                    "alertas": resp.alertas},
        }

    async def emit(self, invoice_data: dict, material: Optional[Any] = None) -> dict:
        if material is None:
            return {"status": "failed", "protocol": None, "descricao": SEM_CERTIFICADO,
                    "rejeicoes": [{"codigo": "CERT", "descricao": SEM_CERTIFICADO, "complemento": ""}], "raw": {}}
        try:
            dps = montar_dps(
                invoice_data,
                ambiente=_ambiente(),
                versao_aplicativo=settings.NFSE_VERSAO_APLICATIVO,
                serie_padrao=settings.NFSE_SERIE_DPS,
            )
            validar_xml(dps.xml, "DPS_v1.01.xsd")
            assinado = assinar_xml(
                dps.xml, referencia_id=dps.id_dps, chave_pem=material.chave_pem, cert_pem=material.cert_pem
            )
        except (DpsInvalida, AssinaturaInvalida) as exc:
            return {"status": "rejected", "protocol": None, "codigo_rejeicao": "FISCWISE",
                    "descricao": str(exc),
                    "rejeicoes": [{"codigo": "FISCWISE", "descricao": str(exc), "complemento": ""}],
                    "raw": {"etapa": "montagem"}}

        cliente = self._cliente(material)
        try:
            resp = await cliente.enviar_dps(assinado)
        except ErroConexaoNfse as exc:
            if exc.certificado_recusado:
                return {"status": "failed", "protocol": None, "id_dps": dps.id_dps, "descricao": str(exc),
                        "rejeicoes": [{"codigo": "TLS", "descricao": str(exc), "complemento": ""}], "raw": {}}
            # Pode ter chegado: confere pela DPS antes de pedir nova tentativa.
            try:
                consulta = await cliente.consultar_dps(dps.id_dps)
            except ErroConexaoNfse:
                raise TransientEmissionError(str(exc)) from exc
            if consulta.ok and consulta.campo("chaveAcesso", "chave"):
                return await self._emitida(consulta, dps.id_dps, dps.avisos, cliente)
            raise TransientEmissionError(str(exc)) from exc

        if resp.ok:
            return await self._emitida(resp, dps.id_dps, dps.avisos, cliente)
        if resp.status_code >= 500:
            raise TransientEmissionError(f"Sefin Nacional indisponível (HTTP {resp.status_code}).")
        if resp.status_code in (401, 403, 495, 496):
            return {"status": "failed", "protocol": None, "id_dps": dps.id_dps,
                    "descricao": "Certificado não autorizado a emitir por este CNPJ (confira procuração ou certificado da empresa).",
                    "rejeicoes": resp.erros, "raw": {"http_status": resp.status_code, "erros": resp.erros}}
        return self._rejeitada(resp, dps.id_dps, dps.avisos)

    async def cancel(self, protocol: str, reason: str, material: Optional[Any] = None, **kwargs: Any) -> dict:
        if material is None:
            return {"status": "failed", "descricao": SEM_CERTIFICADO, "raw": {}}
        autor = kwargs.get("documento_autor") or getattr(material, "documento", None)
        try:
            evento = montar_cancelamento(
                chave_acesso=protocol,
                documento_autor=autor,
                motivo=reason,
                codigo_motivo=str(kwargs.get("codigo_motivo") or "1"),
                ambiente=_ambiente(),
                versao_aplicativo=settings.NFSE_VERSAO_APLICATIVO,
            )
            validar_xml(evento.xml, "pedRegEvento_v1.01.xsd")
            assinado = assinar_xml(
                evento.xml, referencia_id=evento.id_evento, chave_pem=material.chave_pem, cert_pem=material.cert_pem
            )
        except (DpsInvalida, AssinaturaInvalida) as exc:
            return {"status": "rejected", "descricao": str(exc),
                    "rejeicoes": [{"codigo": "FISCWISE", "descricao": str(exc), "complemento": ""}], "raw": {}}
        try:
            resp = await self._cliente(material).registrar_evento(protocol, assinado)
        except ErroConexaoNfse as exc:
            return {"status": "failed", "descricao": str(exc), "raw": {"transitorio": exc.transitorio}}
        if resp.ok:
            return {"status": "cancelled", "protocol": protocol, "raw": {"http_status": resp.status_code}}
        r = self._rejeitada(resp)
        return {"status": "rejected", "protocol": protocol, "descricao": r["descricao"],
                "rejeicoes": r["rejeicoes"], "raw": r["raw"]}

    async def query_status(self, protocol: str, material: Optional[Any] = None) -> dict:
        if material is None:
            return {"status": "failed", "descricao": SEM_CERTIFICADO, "raw": {}}
        try:
            resp = await self._cliente(material).consultar_nfse(protocol)
        except ErroConexaoNfse as exc:
            return {"status": "failed", "descricao": str(exc), "raw": {}}
        if resp.ok:
            b64 = resp.campo("nfseXmlGZipB64")
            xml = de_gzip_b64(b64) if b64 else None
            return {"status": "issued", "protocol": protocol, "numero": _numero_nfse(xml) if xml else None,
                    "xml": xml.decode("utf-8") if xml else None, "raw": {"http_status": resp.status_code}}
        if resp.status_code == 404:
            return {"status": "not_found", "protocol": protocol, "raw": {"http_status": 404}}
        return {"status": "failed", "protocol": protocol, "descricao": "; ".join(e["descricao"] for e in resp.erros),
                "raw": {"http_status": resp.status_code, "erros": resp.erros}}

    async def testar_conexao(self, material: Optional[Any], issuer: Any) -> dict:
        """Chamada leve autenticada: consulta uma DPS que não existe.

        404 (ou 200) = o TLS mútuo foi aceito e a API respondeu: o certificado é
        reconhecido pelo Sistema Nacional. 401/403 = recusado. Não emite nada.
        """
        if material is None:
            return {"ok": False, "mensagem": SEM_CERTIFICADO, "detalhes": {}}
        cnpj = re.sub(r"\D", "", str(_get(issuer, "cnpj") or _get(issuer, "documento") or ""))
        municipio = re.sub(r"\D", "", str(_get(issuer, "municipio_ibge") or ""))
        detalhes: dict[str, Any] = {
            "ambiente": "producao" if _ambiente() == AMBIENTE_PRODUCAO else "producao_restrita",
            "documento_certificado": getattr(material, "documento", None),
            "documento_emissor": cnpj or None,
        }
        if cnpj and getattr(material, "documento", None) and re.sub(r"\D", "", material.documento) != cnpj:
            detalhes["modo"] = "procurador"
        try:
            id_teste = montar_id_dps(municipio, cnpj, "9999", "999999999999999")
        except DpsInvalida as exc:
            return {"ok": False, "mensagem": f"Dados do emissor incompletos: {exc}", "detalhes": detalhes}
        try:
            resp = await self._cliente(material).consultar_dps(id_teste)
        except ErroConexaoNfse as exc:
            detalhes["certificado_recusado"] = exc.certificado_recusado
            return {"ok": False, "mensagem": str(exc), "detalhes": detalhes}
        detalhes["http_status"] = resp.status_code
        if resp.status_code in (200, 404):
            return {"ok": True, "mensagem": "Conexão aceita: o Sistema Nacional NFS-e reconheceu o certificado.",
                    "detalhes": detalhes}
        if resp.status_code in (401, 403, 495, 496):
            return {"ok": False,
                    "mensagem": "O Sistema Nacional recusou o certificado para este CNPJ. Confira se o certificado "
                                "é da empresa ou se a procuração eletrônica para NFS-e está cadastrada na Receita.",
                    "detalhes": detalhes | {"erros": resp.erros}}
        if resp.status_code >= 500:
            return {"ok": False, "mensagem": "O Sistema Nacional NFS-e está indisponível agora. Tente de novo em instantes.",
                    "detalhes": detalhes}
        msg = "; ".join(e["descricao"] for e in resp.erros) or f"Resposta inesperada (HTTP {resp.status_code})."
        return {"ok": False, "mensagem": msg, "detalhes": detalhes | {"erros": resp.erros}}
