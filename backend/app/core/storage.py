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

import httpx

from app.core.config import settings

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
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, content=file_bytes, headers=headers)
    if resp.status_code not in (200, 201):
        logger.error("Supabase upload falhou: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Falha no upload para storage ({resp.status_code})")
    return path


async def get_signed_url(bucket: str, path: str, ttl: int = 300) -> str:
    """URL assinada temporária para um objeto privado. TTL em segundos."""
    if not _config_or_degrade(f"signed url {bucket}/{path}"):
        return f"https://storage.local.dev/{bucket}/{path}?dev=1"
    url = f"{settings.SUPABASE_URL}/storage/v1/object/sign/{bucket}/{path}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json={"expiresIn": ttl}, headers=_headers())
    if resp.status_code != 200:
        logger.error("Supabase sign falhou: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Falha ao assinar URL ({resp.status_code})")
    body = resp.json()
    signed = body.get("signedURL") or body.get("signedUrl")
    if not signed:
        raise RuntimeError("Resposta de sign sem signedURL")
    return f"{settings.SUPABASE_URL}/storage/v1{signed}"


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
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json={"expiresIn": ttl, "paths": unique}, headers=_headers())
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
