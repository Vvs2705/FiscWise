"""Transactional Email Service for FiscWise (Resend provider).

Sends transactional emails (2FA email OTP, password reset, LGPD deletion
confirmation, etc.) through the Resend HTTP API using the httpx client that is
already a project dependency — NO new SDK is added.

Design goals
------------
1. Defensive configuration: credentials are read via getattr()/os.getenv() so
   this module keeps working even before the config agent adds the RESEND_*
   fields to Settings. It never assumes the fields exist.
2. Safe fallback: when the integration is disabled OR no API key is present,
   the service does NOT call the network. It logs (current behaviour) and
   returns False, so dev / tests / CI run without any credential and nothing
   breaks.
3. Never leak secrets: the email HTML body (which may contain an OTP code or a
   reset link) is NEVER written to the logs. Only high-level metadata (subject,
   recipient, delivery id) is logged.

Environment / Settings (all optional):
  RESEND_API_KEY   — Resend API key (Bearer token). Empty → fallback mode.
  RESEND_FROM      — Sender, e.g. 'FiscWise <nao-responda@fiscwise.com.br>'.
  RESEND_ENABLED   — 'true' to enable real sending. Anything else → fallback.
"""

import os
import logging
import uuid
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Try to import settings, but degrade gracefully if it is unavailable for any
# reason (import cycles, partial config, etc.). We read fields defensively.
try:  # pragma: no cover - trivial import guard
    from app.core.config import settings as _settings
except Exception:  # pragma: no cover
    _settings = None

RESEND_API_URL = "https://api.resend.com/emails"
_HTTP_TIMEOUT_SECONDS = 10.0
_DEFAULT_SENDER = "FiscWise <nao-responda@fiscwise.com.br>"


def _get_api_key() -> str:
    """Read the Resend API key defensively (settings first, then env)."""
    key = getattr(_settings, "RESEND_API_KEY", "") if _settings else ""
    return key or os.getenv("RESEND_API_KEY", "")


def _get_sender() -> str:
    """Read the sender address defensively, with a sane default."""
    sender = getattr(_settings, "RESEND_FROM", "") if _settings else ""
    return sender or os.getenv("RESEND_FROM", "") or _DEFAULT_SENDER


def _is_enabled() -> bool:
    """Whether real sending is turned on (settings flag OR env == 'true')."""
    flag = getattr(_settings, "RESEND_ENABLED", False) if _settings else False
    return bool(flag) or os.getenv("RESEND_ENABLED", "") == "true"


async def send_email(
    to: str,
    subject: str,
    html: str,
    idempotency_key: Optional[str] = None,
) -> bool:
    """Send a transactional email via Resend.

    Returns True only when the provider accepted the message (HTTP 2xx).
    Returns False in every fallback / error case WITHOUT raising, so callers
    (login, reset, LGPD deletion) never break because of email delivery.

    The HTML body is never logged — it may carry an OTP code or reset link.
    """
    enabled = _is_enabled()
    api_key = _get_api_key()

    # ── Safe fallback: no credential or disabled → log & return False ────────
    if not enabled or not api_key:
        logger.info(
            "Email not sent (provider disabled or no RESEND_API_KEY). "
            "to=%s subject=%r [fallback mode — body redacted]",
            to,
            subject,
        )
        return False

    sender = _get_sender()
    if idempotency_key is None:
        idempotency_key = str(uuid.uuid4())

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Resend uses the Idempotency-Key header to de-duplicate retries.
        "Idempotency-Key": idempotency_key,
    }
    payload = {
        "from": sender,
        "to": [to],
        "subject": subject,
        "html": html,
    }

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            resp = await client.post(RESEND_API_URL, json=payload, headers=headers)

        if 200 <= resp.status_code < 300:
            # Log only non-sensitive metadata (no body, no OTP).
            delivery_id = None
            try:
                delivery_id = resp.json().get("id")
            except Exception:
                pass
            logger.info(
                "Email sent via Resend. to=%s subject=%r id=%s",
                to,
                subject,
                delivery_id,
            )
            return True

        # Non-2xx: log status + a short, non-sensitive snippet of the error.
        logger.warning(
            "Resend returned non-2xx. to=%s subject=%r status=%s detail=%s",
            to,
            subject,
            resp.status_code,
            (resp.text or "")[:300],
        )
        return False

    except httpx.HTTPError as exc:
        logger.warning(
            "Resend request failed (network/timeout). to=%s subject=%r error=%s",
            to,
            subject,
            exc,
        )
        return False
    except Exception as exc:  # pragma: no cover - defensive catch-all
        logger.error(
            "Unexpected error sending email. to=%s subject=%r error=%s",
            to,
            subject,
            exc,
        )
        return False


# ─────────────────────────────────────────────────────────────────────────────
# HTML templates — minimal, inline-styled, sober, no external assets.
# The FiscWise brand orange (#F97316) is used sparingly for accents.
# ─────────────────────────────────────────────────────────────────────────────

_BRAND = "#F97316"
_INK = "#111827"
_MUTED = "#6B7280"
_BG = "#F9FAFB"
_CARD = "#FFFFFF"
_BORDER = "#E5E7EB"


def _base_layout(inner_html: str) -> str:
    """Wrap content in a sober, self-contained email shell (no external CSS)."""
    return f"""\
<div style="margin:0;padding:24px 0;background-color:{_BG};font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:480px;margin:0 auto;">
    <tr>
      <td style="padding:0 0 16px 0;">
        <span style="font-size:20px;font-weight:700;color:{_INK};">Fisc<span style="color:{_BRAND};">Wise</span></span>
      </td>
    </tr>
    <tr>
      <td style="background-color:{_CARD};border:1px solid {_BORDER};border-radius:12px;padding:28px;">
        {inner_html}
      </td>
    </tr>
    <tr>
      <td style="padding:16px 4px 0 4px;color:{_MUTED};font-size:12px;line-height:1.5;">
        Este é um e-mail automático do FiscWise. Por favor, não responda.
      </td>
    </tr>
  </table>
</div>"""


def render_otp_email(code: str) -> str:
    """HTML for the 2FA login email OTP."""
    inner = f"""\
<h1 style="margin:0 0 12px 0;font-size:18px;color:{_INK};">Seu código de verificação</h1>
<p style="margin:0 0 20px 0;font-size:14px;line-height:1.6;color:{_MUTED};">
  Use o código abaixo para concluir o seu acesso. Ele expira em 10 minutos.
</p>
<div style="text-align:center;margin:0 0 20px 0;">
  <span style="display:inline-block;font-size:30px;font-weight:700;letter-spacing:8px;color:{_INK};background-color:{_BG};border:1px solid {_BORDER};border-radius:10px;padding:14px 22px;">{code}</span>
</div>
<p style="margin:0;font-size:13px;line-height:1.6;color:{_MUTED};">
  Se você não solicitou este código, ignore este e-mail e considere trocar a sua senha.
</p>"""
    return _base_layout(inner)


def render_password_reset_email(reset_link: str) -> str:
    """HTML for a password reset email (link-based).

    Provided for when a reset-password endpoint is added; not currently wired
    because the codebase has no reset flow yet.
    """
    inner = f"""\
<h1 style="margin:0 0 12px 0;font-size:18px;color:{_INK};">Redefinição de senha</h1>
<p style="margin:0 0 20px 0;font-size:14px;line-height:1.6;color:{_MUTED};">
  Recebemos um pedido para redefinir a sua senha. Clique no botão abaixo para
  criar uma nova senha. O link expira em breve.
</p>
<div style="text-align:center;margin:0 0 20px 0;">
  <a href="{reset_link}" style="display:inline-block;background-color:{_BRAND};color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;padding:12px 24px;border-radius:8px;">Redefinir senha</a>
</div>
<p style="margin:0;font-size:13px;line-height:1.6;color:{_MUTED};">
  Se você não fez este pedido, ignore este e-mail — a sua senha continua a mesma.
</p>"""
    return _base_layout(inner)


def render_lgpd_deletion_email(deadline_business_days: int = 15) -> str:
    """HTML confirming receipt of an LGPD data-deletion request."""
    inner = f"""\
<h1 style="margin:0 0 12px 0;font-size:18px;color:{_INK};">Solicitação de exclusão recebida</h1>
<p style="margin:0 0 16px 0;font-size:14px;line-height:1.6;color:{_MUTED};">
  Recebemos a sua solicitação de exclusão de dados, conforme a Lei Geral de
  Proteção de Dados (LGPD — Art. 18, Inciso VI).
</p>
<p style="margin:0 0 16px 0;font-size:14px;line-height:1.6;color:{_MUTED};">
  Nossa equipe processará o pedido em até <strong style="color:{_INK};">{deadline_business_days} dias úteis</strong>.
</p>
<p style="margin:0;font-size:13px;line-height:1.6;color:{_MUTED};">
  Observação: documentos fiscais podem ser retidos por até <strong style="color:{_INK};">5 anos</strong>,
  conforme exigência da Receita Federal (legislação tributária brasileira).
</p>"""
    return _base_layout(inner)
