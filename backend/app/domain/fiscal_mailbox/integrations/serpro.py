"""Real e-CAC/DTE provider backed by the SERPRO Integra Contador gateway.

Flow per sync:
1. Authenticate against the SERPRO OAuth endpoint (client_credentials with
   consumer key/secret; optional mTLS certificate when the contract demands).
2. For each contribuinte (active accounting client with a CNPJ), call the
   CAIXAPOSTAL system on the Integra Contador ``/Consultar`` endpoint to list
   the mailbox messages.
3. Map each raw message to the provider contract consumed by
   ``FiscalMailboxService.sync_messages`` (``external_id`` keyed, idempotent).

A failure for one contribuinte never aborts the whole sync — it is logged and
the remaining contribuintes are still fetched (partial sync beats no sync).
"""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.domain.fiscal_mailbox.integrations.base import FiscalMailboxProvider

logger = logging.getLogger(__name__)

CAIXA_POSTAL_SYSTEM = "CAIXAPOSTAL"
LIST_MESSAGES_SERVICE = "MSGCONTRIBUINTE61"

# Integra Contador "relevancia" flag → internal risk scale.
_RELEVANCE_TO_RISK = {
    "1": "high",
    "2": "medium",
    "3": "low",
}


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _parse_serpro_date(value: Any) -> Optional[str]:
    """Normalise SERPRO date formats (yyyyMMdd / yyyyMMddHHmmss / ISO) to ISO-8601 UTC."""
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        logger.warning("Unparseable SERPRO date: %r", raw)
        return None


class SerproIntegraContadorProvider(FiscalMailboxProvider):
    """Fetches e-CAC mailbox messages via SERPRO Integra Contador."""

    def __init__(
        self,
        contribuintes: List[Dict[str, str]],
        *,
        consumer_key: str,
        consumer_secret: str,
        auth_url: str,
        base_url: str,
        contratante_cnpj: str,
        autor_pedido_cnpj: str,
        cert: Optional[tuple] = None,
        timeout: float = 30.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.contribuintes = contribuintes
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.auth_url = auth_url
        self.base_url = base_url.rstrip("/")
        self.contratante_cnpj = _digits(contratante_cnpj)
        self.autor_pedido_cnpj = _digits(autor_pedido_cnpj)
        self.cert = cert
        self.timeout = timeout
        # Injectable for tests (httpx.MockTransport); owned by caller when given.
        self._external_client = http_client
        self._token: Optional[str] = None
        self._jwt_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    async def fetch_messages(self, tenant_id: str) -> List[Dict[str, Any]]:
        if self._external_client is not None:
            return await self._fetch_all(self._external_client, tenant_id)
        async with httpx.AsyncClient(timeout=self.timeout, cert=self.cert or None) as client:
            return await self._fetch_all(client, tenant_id)

    async def _fetch_all(self, client: httpx.AsyncClient, tenant_id: str) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        for contribuinte in self.contribuintes:
            cnpj = _digits(contribuinte.get("cnpj", ""))
            if not cnpj:
                continue
            try:
                raw_list = await self._list_messages(client, cnpj)
            except Exception:
                logger.exception(
                    "SERPRO mailbox fetch failed (tenant=%s contribuinte=%s)", tenant_id, cnpj
                )
                continue
            for raw in raw_list:
                mapped = self._map_message(raw, contribuinte)
                if mapped:
                    messages.append(mapped)
        return messages

    async def _ensure_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token
        response = await client.post(
            self.auth_url,
            data={"grant_type": "client_credentials"},
            auth=(self.consumer_key, self.consumer_secret),
        )
        response.raise_for_status()
        payload = response.json()
        self._token = payload["access_token"]
        self._jwt_token = payload.get("jwt_token")
        # Refresh 60s before the advertised expiry to avoid edge-of-window 401s.
        self._token_expires_at = time.monotonic() + max(int(payload.get("expires_in", 3600)) - 60, 60)
        return self._token

    async def _list_messages(self, client: httpx.AsyncClient, contribuinte_cnpj: str) -> List[Dict[str, Any]]:
        token = await self._ensure_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        if self._jwt_token:
            headers["jwt_token"] = self._jwt_token

        envelope = {
            "contratante": {"numero": self.contratante_cnpj, "tipo": 2},
            "autorPedidoDados": {"numero": self.autor_pedido_cnpj, "tipo": 2},
            "contribuinte": {"numero": contribuinte_cnpj, "tipo": 2},
            "pedidoDados": {
                "idSistema": CAIXA_POSTAL_SYSTEM,
                "idServico": LIST_MESSAGES_SERVICE,
                "versaoSistema": "1.0",
                "dados": "{}",
            },
        }
        response = await client.post(f"{self.base_url}/Consultar", json=envelope, headers=headers)
        response.raise_for_status()
        body = response.json()

        dados = body.get("dados")
        if isinstance(dados, str):
            try:
                dados = json.loads(dados) if dados else {}
            except json.JSONDecodeError:
                logger.warning("SERPRO returned non-JSON 'dados' payload for %s", contribuinte_cnpj)
                return []
        if isinstance(dados, list):
            return dados
        if isinstance(dados, dict):
            for key in ("mensagens", "listaMensagens", "conteudo"):
                value = dados.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _map_message(self, raw: Dict[str, Any], contribuinte: Dict[str, str]) -> Optional[Dict[str, Any]]:
        cnpj = _digits(contribuinte.get("cnpj", ""))
        message_id = raw.get("isn") or raw.get("isnMensagem") or raw.get("id")
        if not message_id:
            logger.warning("SERPRO message without id skipped (contribuinte=%s)", cnpj)
            return None

        relevance = str(raw.get("relevancia", "")).strip()
        subject = raw.get("assunto") or raw.get("assuntoMensagem") or "(sem assunto)"

        return {
            "external_id": f"serpro-{cnpj}-{message_id}",
            "client_name": contribuinte.get("name"),
            "client_cnpj": contribuinte.get("cnpj"),
            "subject": subject,
            "summary": raw.get("resumo") or raw.get("descricao"),
            "body": raw.get("corpo") or raw.get("conteudo"),
            "organ": raw.get("origem") or raw.get("orgao") or "Receita Federal",
            "received_at": _parse_serpro_date(raw.get("dataEnvio") or raw.get("dataRecebimento")),
            "deadline": _parse_serpro_date(raw.get("prazo") or raw.get("dataLimite")),
            "risk": _RELEVANCE_TO_RISK.get(relevance, "none"),
            "tags": [t for t in [raw.get("sistema"), raw.get("categoria")] if t],
        }
