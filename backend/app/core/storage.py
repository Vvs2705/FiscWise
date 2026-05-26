# TODO: aguardar equipe Claude
import logging

logger = logging.getLogger(__name__)

async def get_signed_url(bucket: str, path: str, ttl: int = 300) -> str:
    """Stub for getting signed URLs from private storage, to be implemented by Claude team."""
    logger.debug("get_signed_url stub called: bucket=%s path=%s ttl=%s", bucket, path, ttl)
    return f"https://storage.example.com/{bucket}/{path}?token=mock_signed_token"
