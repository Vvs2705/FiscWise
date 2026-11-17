from abc import ABC, abstractmethod
from typing import Any, Optional


class TransientEmissionError(Exception):
    """O provedor não recebeu o pedido (falha de conexão): a nota volta para
    `queued` e a fila tenta de novo. O provider nacional levanta isto em
    falhas de rede; o handler `invoice.emit` também converte falhas de
    conexão nela."""


class NfseProvider(ABC):
    """Contrato dos provedores de NFS-e.

    ``material`` é o ``MaterialCertificado`` do cofre
    (app.domain.certificados.cofre): certificado/chave em PEM, em memória.
    O mock aceita ``None``; o provider nacional exige.

    Retorno de ``emit``::

        {"status": "issued" | "rejected" | "failed",
         "protocol": chave de acesso, "numero": nº da NFS-e,
         "xml": NFS-e autorizada, "id_dps": ...,
         "rejeicoes": [{"codigo", "descricao", "complemento"}],
         "codigo_rejeicao", "descricao" (1ª rejeição, compatível com o serviço),
         "avisos": [...], "raw": {...}}
    """

    @abstractmethod
    async def emit(self, invoice_data: dict, material: Optional[Any] = None) -> dict:
        """Envia a NFS-e."""

    @abstractmethod
    async def cancel(self, protocol: str, reason: str, material: Optional[Any] = None, **kwargs: Any) -> dict:
        """Cancela a NFS-e pela chave/protocolo. Retorno: {"status": "cancelled"|"rejected"|"failed", ...}"""

    @abstractmethod
    async def query_status(self, protocol: str, material: Optional[Any] = None) -> dict:
        """Consulta a NFS-e pela chave/protocolo."""

    async def testar_conexao(self, material: Optional[Any], issuer: Any) -> dict:
        """Testa se o certificado é aceito pelo provedor.

        Retorno: {"ok": bool, "mensagem": str, "detalhes": dict}.
        """
        return {"ok": False, "mensagem": "Teste de conexão não disponível neste provedor.", "detalhes": {}}
