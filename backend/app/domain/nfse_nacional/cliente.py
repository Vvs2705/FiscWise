"""Cliente da API da Sefin Nacional (NFS-e padrão nacional), com TLS mútuo.

Endpoints (guia oficial "APIs — produção restrita e produção"):
- produção:          https://sefin.nfse.gov.br/SefinNacional
- produção restrita: https://sefin.producaorestrita.nfse.gov.br/API/SefinNacional

Rotas usadas:
- POST /nfse                 {"dpsXmlGZipB64": ...}  → gera a NFS-e (síncrono)
- GET  /nfse/{chaveAcesso}                           → NFS-e gerada
- GET  /dps/{idDps}                                  → chave da NFS-e de uma DPS
- POST /nfse/{chave}/eventos {"pedidoRegistroEventoXmlGZipB64": ...}

Autenticação: TLS mútuo com o certificado A1 (ICP-Brasil). O ``ssl`` do Python
só carrega certificado de arquivo; o cert/chave são escritos num diretório
temporário privado (0700, arquivos 0600, em /dev/shm quando existe), lidos
pelo contexto e apagados na hora — a chave fica só na memória do contexto.

Nada do conteúdo (XML, chave, certificado) vai para log.
"""

from __future__ import annotations

import base64
import gzip
import json
import logging
import os
import re
import ssl
import tempfile
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class ErroConexaoNfse(RuntimeError):
    """Pedido não chegou à Sefin (rede, TLS). ``transitorio`` diz se vale repetir."""

    def __init__(self, mensagem: str, *, transitorio: bool, certificado_recusado: bool = False):
        super().__init__(mensagem)
        self.transitorio = transitorio
        self.certificado_recusado = certificado_recusado


@dataclass
class RespostaSefin:
    status_code: int
    corpo: Optional[dict]
    erros: list[dict] = field(default_factory=list)
    alertas: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def campo(self, *nomes: str) -> Any:
        """Lê um campo do JSON sem depender de maiúsculas/minúsculas."""
        if not isinstance(self.corpo, dict):
            return None
        mapa = {k.lower(): v for k, v in self.corpo.items()}
        for nome in nomes:
            if nome.lower() in mapa:
                return mapa[nome.lower()]
        return None


def gzip_b64(xml: bytes | str) -> str:
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    return base64.b64encode(gzip.compress(xml)).decode("ascii")


def de_gzip_b64(valor: str) -> bytes:
    return gzip.decompress(base64.b64decode(valor))


def _normaliza_mensagens(valor: Any) -> list[dict]:
    if not valor:
        return []
    if isinstance(valor, dict):
        valor = [valor]
    saida = []
    for item in valor if isinstance(valor, list) else []:
        if isinstance(item, dict):
            m = {k.lower(): v for k, v in item.items()}
            saida.append({
                "codigo": str(m.get("codigo") or m.get("code") or ""),
                "descricao": str(m.get("descricao") or m.get("mensagem") or m.get("message") or ""),
                "complemento": str(m.get("complemento") or ""),
            })
        else:
            saida.append({"codigo": "", "descricao": str(item), "complemento": ""})
    return saida


def _dir_privado() -> Optional[str]:
    return "/dev/shm" if os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK) else None


def contexto_tls(cert_pem: bytes, chave_pem: bytes, cadeia_pem: bytes = b"", ca_bundle: str = "") -> ssl.SSLContext:
    """SSLContext com o certificado do cliente (mTLS) carregado em memória."""
    if ca_bundle:
        ctx = ssl.create_default_context(cafile=ca_bundle)
    else:
        try:
            import certifi

            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:  # pragma: no cover
            ctx = ssl.create_default_context()
    with tempfile.TemporaryDirectory(prefix="nfse-", dir=_dir_privado()) as pasta:
        os.chmod(pasta, 0o700)
        caminho_cert = os.path.join(pasta, "c.pem")
        caminho_chave = os.path.join(pasta, "k.pem")
        for caminho, conteudo in ((caminho_cert, cert_pem + (b"\n" + cadeia_pem if cadeia_pem else b"")), (caminho_chave, chave_pem)):
            fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(conteudo)
        ctx.load_cert_chain(caminho_cert, caminho_chave)
    return ctx


def _eh_erro_tls(exc: BaseException) -> bool:
    atual: Optional[BaseException] = exc
    while atual is not None:
        if isinstance(atual, ssl.SSLError):
            return True
        if re.search(r"ssl|certificate|handshake|tlsv1 alert", str(atual), re.I):
            return True
        atual = atual.__cause__ or atual.__context__
    return False


class ClienteNfseNacional:
    def __init__(
        self,
        *,
        base_url: str,
        material: Any = None,
        timeout: float = 30.0,
        ca_bundle: str = "",
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.material = material
        self.timeout = timeout
        self.ca_bundle = ca_bundle
        self._transport = transport

    def _cliente(self) -> httpx.AsyncClient:
        kwargs: dict[str, Any] = {
            "timeout": httpx.Timeout(self.timeout, connect=min(10.0, self.timeout)),
            "headers": {"Accept": "application/json"},
        }
        if self._transport is not None:
            kwargs["transport"] = self._transport
        else:
            if self.material is None:
                raise ErroConexaoNfse("Certificado digital não configurado para este emissor.", transitorio=False)
            kwargs["verify"] = contexto_tls(
                self.material.cert_pem,
                self.material.chave_pem,
                getattr(self.material, "cadeia_pem", b"") or b"",
                self.ca_bundle,
            )
        return httpx.AsyncClient(**kwargs)

    async def _req(self, metodo: str, caminho: str, *, json_body: Optional[dict] = None, tentativas: int = 1) -> RespostaSefin:
        url = f"{self.base_url}{caminho}"
        ultimo: Optional[BaseException] = None
        for tentativa in range(max(1, tentativas)):
            try:
                async with self._cliente() as cliente:
                    resp = await cliente.request(metodo, url, json=json_body)
                break
            except httpx.TimeoutException as exc:
                ultimo = exc
                if metodo != "GET" or tentativa + 1 >= tentativas:
                    raise ErroConexaoNfse(
                        "A Sefin Nacional não respondeu a tempo.", transitorio=True
                    ) from exc
            except httpx.TransportError as exc:
                ultimo = exc
                if _eh_erro_tls(exc):
                    raise ErroConexaoNfse(
                        "A conexão segura com a Sefin Nacional foi recusada: confira se o certificado "
                        "é ICP-Brasil, está dentro da validade e tem a cadeia completa.",
                        transitorio=False,
                        certificado_recusado=True,
                    ) from exc
                if metodo != "GET" or tentativa + 1 >= tentativas:
                    raise ErroConexaoNfse(
                        "Não foi possível conectar à Sefin Nacional.", transitorio=True
                    ) from exc
        else:  # pragma: no cover
            raise ErroConexaoNfse("Falha de conexão.", transitorio=True) from ultimo

        logger.info("sefin_nacional %s %s -> %s", metodo, re.sub(r"/[0-9A-Z]{20,}", "/…", caminho), resp.status_code)
        corpo: Optional[dict] = None
        try:
            dados = resp.json()
            corpo = dados if isinstance(dados, dict) else {"lista": dados}
        except (ValueError, json.JSONDecodeError):
            corpo = None
        r = RespostaSefin(status_code=resp.status_code, corpo=corpo)
        r.erros = _normaliza_mensagens(r.campo("erros", "erro"))
        r.alertas = _normaliza_mensagens(r.campo("alertas", "alerta"))
        return r

    async def enviar_dps(self, dps_assinada: bytes) -> RespostaSefin:
        return await self._req("POST", "/nfse", json_body={"dpsXmlGZipB64": gzip_b64(dps_assinada)})

    async def consultar_nfse(self, chave: str) -> RespostaSefin:
        return await self._req("GET", f"/nfse/{chave}", tentativas=2)

    async def consultar_dps(self, id_dps: str) -> RespostaSefin:
        return await self._req("GET", f"/dps/{id_dps}", tentativas=2)

    async def registrar_evento(self, chave: str, evento_assinado: bytes) -> RespostaSefin:
        return await self._req(
            "POST",
            f"/nfse/{chave}/eventos",
            json_body={"pedidoRegistroEventoXmlGZipB64": gzip_b64(evento_assinado)},
        )
