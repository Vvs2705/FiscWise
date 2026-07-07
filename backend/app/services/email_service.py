"""Transactional e-mail for FiscWise via Resend HTTP API.

Environment variables (read at call time so tests/env changes take effect):
  EMAIL_PROVIDER  — must be 'resend' to enable sending
  RESEND_API_KEY  — Resend API key
  EMAIL_FROM      — sender address (default: noreply@fiscwise.com.br)

Without provider/key: logs a warning and returns False (graceful no-op in dev).
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send a transactional e-mail. Returns True on success, False otherwise.

    Never raises — callers must not break when e-mail is unavailable.
    """
    provider = os.getenv("EMAIL_PROVIDER", "").lower().strip()
    api_key = os.getenv("RESEND_API_KEY", "")

    if provider != "resend" or not api_key:
        logger.warning(
            "E-mail NAO enviado (EMAIL_PROVIDER/RESEND_API_KEY ausentes): to=%s subject=%r",
            to, subject,
        )
        return False

    email_from = os.getenv("EMAIL_FROM", "noreply@fiscwise.com.br")

    # ponytail: sem retry — Resend é confiável e o caller trata False; adicionar retry se houver falhas reais
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"from": email_from, "to": [to], "subject": subject, "html": html},
            )
        if resp.status_code in (200, 201):
            return True
        logger.error(
            "Resend retornou %d ao enviar para %s: %s",
            resp.status_code, to, resp.text[:300],
        )
        return False
    except httpx.HTTPError as exc:
        logger.error("Falha HTTP ao enviar e-mail para %s: %s", to, exc)
        return False
