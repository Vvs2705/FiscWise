"""Supabase Storage — upload e URLs assinadas reais.

Antes era um stub que devolvia URLs falsas (`storage.example.com/...?token=mock`),
o que quebrava download de arquivos e mascarava a falta de persistência.
Agora fala com a REST do Supabase Storage usando a service key.

Comportamento por ambiente (mesma filosofia do webhook fail-closed):
  - configurado  → upload/sign reais no Supabase;
  - sem config em produção/staging → levanta (falha alto, não mascara);
  - sem config em dev/test → degrada com placeholder (não há Supabase local).
"""
import logging
import os

from app.core.config import settings
from app.core.http_client import raise_for_upstream_status, request_with_retry

logger = logging.getLogger(__name__)

_ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower().strip()
_IS_PROD = _ENVIRONMENT in ("production", "prod", "staging")


def _storage_configured() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SECRET_KEY)


def _config_or_degrade(what: str) -> bool:
    """True → storage real disponível. False → degradar (dev). Levanta em prod."""
    if _storage_configured():
        return True
    if _IS_PROD:
        raise RuntimeError(
            f"Supabase Storage não configurado em {_ENVIRONMENT} "
            f"(SUPABASE_URL/SUPABASE_SECRET_KEY) — {what} indisponível"
        )
    logger.warning("Storage não configurado (%s) — %s degradado", _ENVIRONMENT, what)
    return False


def _headers(content_type: str | None = None) -> dict[str, str]:
    h = {
        "apikey": settings.SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


async def upload_bytes(
    bucket: str, path: str, file_bytes: bytes, content_type: str = "application/octet-stream",
    *, upsert: bool = False,
) -> str:
    """Sobe bytes para `{bucket}/{path}`. Retorna o path salvo. Levanta em falha (prod)."""
    if not _config_or_degrade(f"upload {bucket}/{path}"):
        return path  # dev: não persiste, mas mantém o fluxo
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    headers = _headers(content_type)
    headers["x-upsert"] = "true" if upsert else "false"
    # Não idempotente: só repete se a conexão nem abriu (com x-upsert=false, um
    # reenvio depois de gravado daria 409).
    resp = await request_with_retry(
        "POST", url, service="supabase_storage", idempotent=False,
        read_timeout=30.0, content=file_bytes, headers=headers,
    )
    raise_for_upstream_status(resp, "supabase_storage")
    if resp.status_code not in (200, 201):
        logger.error("Supabase upload falhou: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Falha no upload para storage ({resp.status_code})")
    return path


async def get_signed_url(bucket: str, path: str, ttl: int = 300) -> str:
    """URL assinada temporária para um objeto privado. TTL em segundos."""
    if not _config_or_degrade(f"signed url {bucket}/{path}"):
        return f"https://storage.local.dev/{bucket}/{path}?dev=1"
    url = f"{settings.SUPABASE_URL}/storage/v1/object/sign/{bucket}/{path}"
    # Assinar URL não altera nada no servidor: pode repetir.
    resp = await request_with_retry(
        "POST", url, service="supabase_storage", idempotent=True,
        read_timeout=15.0, json={"expiresIn": ttl}, headers=_headers(),
    )
    raise_for_upstream_status(resp, "supabase_storage")
    if resp.status_code != 200:
        logger.error("Supabase sign falhou: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Falha ao assinar URL ({resp.status_code})")
    body = resp.json()
    signed = body.get("signedURL") or body.get("signedUrl")
    if not signed:
        raise RuntimeError("Resposta de sign sem signedURL")
    return f"{settings.SUPABASE_URL}/storage/v1{signed}"


async def download_bytes(bucket: str, path: str) -> bytes | None:
    """Baixa `{bucket}/{path}` com a service key. None quando o storage não
    está configurado (dev/test) — o chamador decide como degradar."""
    if not _config_or_degrade(f"download {bucket}/{path}"):
        return None
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    resp = await request_with_retry(
        "GET", url, service="supabase_storage", read_timeout=30.0, headers=_headers(),
    )
    raise_for_upstream_status(resp, "supabase_storage")
    if resp.status_code != 200:
        logger.error("Supabase download falhou: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Falha no download do storage ({resp.status_code})")
    return resp.content


async def get_signed_urls(bucket: str, paths: list[str], ttl: int = 300) -> dict[str, str]:
    """Assina vários objetos numa chamada só (endpoint em lote do Supabase).

    Retorna {path: url_assinada}. Path que o Supabase não assinou (objeto
    inexistente, por exemplo) fica fora do dict — o caller decide o fallback.
    """
    unique = list(dict.fromkeys(p for p in paths if p))
    if not unique:
        return {}
    if not _config_or_degrade(f"signed urls {bucket} ({len(unique)})"):
        return {p: f"https://storage.local.dev/{bucket}/{p}?dev=1" for p in unique}
    url = f"{settings.SUPABASE_URL}/storage/v1/object/sign/{bucket}"
    # Assinar em lote também não altera nada no servidor: pode repetir.
    resp = await request_with_retry(
        "POST", url, service="supabase_storage", idempotent=True,
        read_timeout=15.0, json={"expiresIn": ttl, "paths": unique}, headers=_headers(),
    )
    raise_for_upstream_status(resp, "supabase_storage")
    if resp.status_code != 200:
        logger.error("Supabase sign em lote falhou: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Falha ao assinar URLs ({resp.status_code})")
    out: dict[str, str] = {}
    for item in resp.json() or []:
        signed = item.get("signedURL") or item.get("signedUrl")
        path = item.get("path")
        if path and signed and not item.get("error"):
            out[path] = f"{settings.SUPABASE_URL}/storage/v1{signed}"
    return out


async def list_prefix(bucket: str, prefix: str, *, page_size: int = 1000) -> list[str] | None:
    """Paths completos dos objetos em `{bucket}/{prefix}` (um nível; os uploads do
    projeto gravam `<tenant_id>/<arquivo>`). None quando o storage não está
    configurado (dev/test)."""
    if not _config_or_degrade(f"list {bucket}/{prefix}"):
        return None
    url = f"{settings.SUPABASE_URL}/storage/v1/object/list/{bucket}"
    clean = prefix.strip("/")
    out: list[str] = []
    offset = 0
    while True:
        # Listar não altera nada: pode repetir.
        resp = await request_with_retry(
            "POST", url, service="supabase_storage", idempotent=True, read_timeout=30.0,
            json={"prefix": clean, "limit": page_size, "offset": offset}, headers=_headers(),
        )
        raise_for_upstream_status(resp, "supabase_storage")
        if resp.status_code != 200:
            logger.error("Supabase list falhou: %s %s", resp.status_code, resp.text)
            raise RuntimeError(f"Falha ao listar o storage ({resp.status_code})")
        items = resp.json() or []
        for item in items:
            name = item.get("name")
            # Pasta (sem id) não é objeto: o projeto não usa subpastas no prefixo.
            if name and item.get("id"):
                out.append(f"{clean}/{name}")
        if len(items) < page_size:
            return out
        offset += page_size


async def remove_objects(bucket: str, paths: list[str]) -> int:
    """Apaga objetos de `bucket`. Devolve quantos o Supabase confirmou (0 em dev)."""
    unique = list(dict.fromkeys(p for p in paths if p))
    if not unique:
        return 0
    if not _config_or_degrade(f"remove {bucket} ({len(unique)})"):
        return 0
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}"
    removed = 0
    for start in range(0, len(unique), 500):
        lote = unique[start:start + 500]
        # Apagar o que já foi apagado não dá erro: pode repetir.
        resp = await request_with_retry(
            "DELETE", url, service="supabase_storage", idempotent=True, read_timeout=30.0,
            json={"prefixes": lote}, headers=_headers(),
        )
        raise_for_upstream_status(resp, "supabase_storage")
        if resp.status_code != 200:
            logger.error("Supabase remove falhou: %s %s", resp.status_code, resp.text)
            raise RuntimeError(f"Falha ao apagar do storage ({resp.status_code})")
        removed += len(resp.json() or [])
    return removed
