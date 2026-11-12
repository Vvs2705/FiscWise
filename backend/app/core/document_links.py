"""Links de arquivo de documentos: o banco guarda a referência, a API assina.

Antes `file_url` guardava a URL pública do bucket `documents`
(`/object/public/documents/...`): qualquer um com o link baixava contrato,
folha, nota — sem login e sem expirar (LGPD). Agora:

  - gravação: `file_url` guarda a referência `documents/<tenant_id>/<arquivo>`
    (sem migration — o campo continua String(1024));
  - leitura: a resposta troca a referência por uma URL assinada de curta
    duração. O frontend continua lendo `file_url` sem mudança.

Compatibilidade com registros antigos:
  - URL pública do nosso próprio bucket, no prefixo do tenant → também vira
    assinada (assim o bucket pode ficar privado sem quebrar o histórico);
  - outra URL http(s) (mídia externa, link colado) → mantida como está;
  - qualquer outra coisa (referência de outro tenant, `javascript:`, lixo)
    → None, nunca é devolvida ao navegador.
"""
from __future__ import annotations

import logging
import uuid
from typing import Iterable, Protocol

from app.core import storage as _storage
from app.core.config import settings

logger = logging.getLogger(__name__)

DOCUMENTS_BUCKET = "documents"
SIGNED_URL_TTL = 15 * 60  # segundos; a lista fica aberta na tela alguns minutos
_REF_PREFIX = f"{DOCUMENTS_BUCKET}/"


def storage_ref(object_path: str) -> str:
    """Referência que vai para `file_url` (bucket + path do objeto)."""
    return f"{_REF_PREFIX}{object_path}"


def _public_prefix() -> str | None:
    base = (settings.SUPABASE_URL or "").rstrip("/")
    if not base:
        return None
    return f"{base}/storage/v1/object/public/{DOCUMENTS_BUCKET}/"


def object_path_for(file_url: str | None, tenant_id: uuid.UUID | str) -> str | None:
    """Path do objeto no bucket se `file_url` aponta para arquivo nosso do tenant."""
    if not file_url:
        return None
    raw = file_url.strip()
    pub = _public_prefix()
    if pub and raw.startswith(pub):
        path = raw[len(pub):].split("?", 1)[0]
    elif raw.startswith(_REF_PREFIX):
        path = raw[len(_REF_PREFIX):]
    else:
        return None
    if ".." in path.split("/") or not path.startswith(f"{tenant_id}/"):
        return None
    return path


def _is_external_http(file_url: str) -> bool:
    low = file_url.strip().lower()
    return low.startswith("https://") or low.startswith("http://")


class _HasFileUrl(Protocol):
    file_url: str | None


async def sign_file_urls(items: Iterable[_HasFileUrl], tenant_id: uuid.UUID | str) -> None:
    """Troca, no lugar, `file_url` de cada schema de resposta por URL assinada.

    Recebe schemas Pydantic (nunca objetos ORM: mudar o ORM gravaria a URL
    assinada no banco). Falha do storage não derruba a listagem: o item fica
    sem link e o erro vai para o log.
    """
    items = list(items)
    paths: dict[int, str] = {}
    for i, item in enumerate(items):
        path = object_path_for(item.file_url, tenant_id)
        if path:
            paths[i] = path
    signed: dict[str, str] = {}
    if paths:
        try:
            signed = await _storage.get_signed_urls(
                DOCUMENTS_BUCKET, list(paths.values()), ttl=SIGNED_URL_TTL
            )
        except Exception:  # noqa: BLE001 — storage fora não pode derrubar a lista
            logger.exception("Falha ao assinar URLs de documentos (tenant %s)", tenant_id)
    for i, item in enumerate(items):
        if i in paths:
            item.file_url = signed.get(paths[i])
        elif item.file_url and not _is_external_http(item.file_url):
            item.file_url = None
