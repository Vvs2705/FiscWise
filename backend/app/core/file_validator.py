# TODO: aguardar equipe Claude
import logging

logger = logging.getLogger(__name__)

def validate_file_mime(file_bytes: bytes, allowed_mimes: list[str]) -> bool:
    """Stub for validating file MIME type based on magic bytes, to be implemented by Claude team."""
    logger.debug("validate_file_mime stub called for %d bytes against %s", len(file_bytes), allowed_mimes)
    return True
