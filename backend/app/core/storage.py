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
    """Baixa `{bucket}/{path}` com a service key. None se storage não configurado (dev)."""
    if not _config_or_degrade(f"download {bucket}/{path}"):
        return None
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
        resp = await client.get(url, headers=_headers())
    if resp.status_code != 200:
        logger.error("Supabase download falhou: %s %s/%s", resp.status_code, bucket, path)
        raise RuntimeError(f"Falha ao baixar do storage ({resp.status_code})")
    return resp.content
