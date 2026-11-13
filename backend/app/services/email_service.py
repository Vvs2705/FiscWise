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

import html as _html
import os
import logging
import uuid
from typing import Optional

import httpx

from app.core.http_client import ExternalServiceError, request_with_retry

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


def is_configured() -> bool:
    """True when real sending is on (RESEND_ENABLED + RESEND_API_KEY)."""
    return _is_enabled() and bool(_get_api_key())


# Nome usado pelo fluxo de senha/2FA (B-07); mesmo critério de is_configured().
email_delivery_available = is_configured


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
        # Resend honra o Idempotency-Key: reenvio não duplica o e-mail.
        resp = await request_with_retry(
            "POST", RESEND_API_URL, service="resend", idempotent=True,
            read_timeout=_HTTP_TIMEOUT_SECONDS, json=payload, headers=headers,
        )

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

    except (httpx.HTTPError, ExternalServiceError) as exc:
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

    Used by POST /auth/password-reset/request; the link is valid for 1 hour
    and only once.
    """
    inner = f"""\
<h1 style="margin:0 0 12px 0;font-size:18px;color:{_INK};">Redefinição de senha</h1>
<p style="margin:0 0 20px 0;font-size:14px;line-height:1.6;color:{_MUTED};">
  Recebemos um pedido para redefinir a sua senha. Clique no botão abaixo para
  criar uma nova senha. O link vale por 1 hora e pode ser usado uma única vez.
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


def _text_to_html(text: str) -> str:
    """Escape plain text and keep its line breaks."""
    return _html.escape(text or "").replace("\n", "<br>")


def render_client_message_email(title: str, text: str) -> str:
    """HTML for a plain-text message to an accounting client (reminders, notices).

    The text is escaped — it can carry user-typed content.
    """
    inner = f"""\
<h1 style="margin:0 0 12px 0;font-size:18px;color:{_INK};">{_html.escape(title)}</h1>
<p style="margin:0;font-size:14px;line-height:1.6;color:{_MUTED};">{_text_to_html(text)}</p>"""
    return _base_layout(inner)


def render_payment_reminder_email(
    client_name: str,
    description: str,
    amount: str,
    due_date_label: str,
    days_from_due: int,
    office_name: str,
) -> tuple[str, str]:
    """Plain-text body and HTML for a payment (honorários) reminder.

    days_from_due < 0 → vence em N dias; 0 → vence hoje; > 0 → vencida há N dias.
    """
    if days_from_due < 0:
        when = f"vence em {-days_from_due} dia(s), em {due_date_label}"
    elif days_from_due == 0:
        when = f"vence hoje, {due_date_label}"
    else:
        when = f"venceu em {due_date_label} (há {days_from_due} dia(s))"
    text = (
        f"Olá {client_name},\n\n"
        f"Lembramos que a cobrança \"{description}\" no valor de R$ {amount} {when}.\n\n"
        f"Se o pagamento já foi feito, desconsidere esta mensagem.\n\n"
        f"Atenciosamente,\n{office_name}"
    )
    return text, render_client_message_email("Lembrete de pagamento", text)


def render_aviso_teste_email(
    marco: str, fim_label: str, link_assinar: str, retencao_label: str = ""
) -> tuple[str, str]:
    """Assunto e HTML dos avisos do teste grátis.

    marco: "d3" (faltam 3 dias), "d1" (amanhã), "d0" (hoje) ou "vencido".
    """
    textos = {
        "d3": (
            "Seu teste grátis do FiscWise acaba em 3 dias",
            f"Seu teste grátis de 14 dias acaba em {fim_label}. Para continuar "
            "cadastrando e editando sem interrupção, escolha um plano.",
        ),
        "d1": (
            "Seu teste grátis do FiscWise acaba amanhã",
            f"Seu teste grátis acaba amanhã, {fim_label}. Assine agora para não "
            "perder o acesso de edição.",
        ),
        "d0": (
            "Seu teste grátis do FiscWise acaba hoje",
            "Seu teste grátis acaba hoje. Depois disso a conta fica só para "
            "leitura até você assinar um plano.",
        ),
        "vencido": (
            "Seu teste grátis do FiscWise acabou",
            "Seu teste grátis acabou e a conta ficou só para leitura: você "
            "continua vendo e exportando seus dados, mas não cadastra nem edita. "
            f"Os dados ficam guardados até {retencao_label}. Assine um plano para "
            "voltar a usar tudo.",
        ),
    }
    assunto, texto = textos[marco]
    inner = f"""\
<h1 style="margin:0 0 12px 0;font-size:18px;color:{_INK};">{_html.escape(assunto)}</h1>
<p style="margin:0 0 20px 0;font-size:14px;line-height:1.6;color:{_MUTED};">{_html.escape(texto)}</p>
<div style="text-align:center;margin:0 0 20px 0;">
  <a href="{_html.escape(link_assinar, quote=True)}" style="display:inline-block;background-color:{_BRAND};color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;padding:12px 24px;border-radius:8px;">Escolher um plano</a>
</div>
<p style="margin:0;font-size:13px;line-height:1.6;color:{_MUTED};">
  Seus dados continuam seus: em Configurações você pode exportar tudo a qualquer momento.
</p>"""
    return assunto, _base_layout(inner)


def _brl(v: float) -> str:
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_oferta_email(
    marco: str,
    *,
    precos: list[dict],
    validade_label: str,
    link_assinar: str,
    link_descadastro: str,
) -> tuple[str, str]:
    """Assunto e HTML da oferta de reconquista ("oferta" ou "lembrete").

    `precos`: uma linha por plano (app.services.oferta.precos_da_oferta).
    Traz o que o CDC pede: preço do 1º mês e o cheio depois, renovação
    automática, validade, como cancelar e o arrependimento de 7 dias; e o
    descadastro em 1 clique (LGPD art. 18 §2º).
    """
    if marco == "lembrete":
        assunto = f"Última chance: sua oferta do FiscWise vale até {validade_label}"
        abertura = (
            f"Sua oferta especial termina em {validade_label}. Depois disso, os "
            "planos voltam ao preço normal."
        )
    else:
        assunto = "Uma oferta para você voltar ao FiscWise"
        abertura = (
            "Seu teste grátis acabou e sua conta está só para leitura. Para você "
            f"voltar a usar tudo, preparamos uma oferta válida até {validade_label}:"
        )
    linhas = []
    for p in precos:
        nome = _html.escape(str(p["plan_name"]))
        linhas.append(
            f"""<li style="margin:0 0 10px 0;"><strong>{nome}</strong><br>
  Mensal no cartão: <strong>R$ {_brl(p['mensal_promo'])}</strong> no 1º mês
  ({p['mensal_desconto_pct']}% de desconto), depois R$ {_brl(p['mensal_cheio'])}/mês.<br>
  Anual: <strong>R$ {_brl(p['anual_promo'])}</strong> ({p['anual_desconto_pct']}% de desconto sobre
  R$ {_brl(p['anual_cheio'])}), no Pix ou em até {p['anual_max_parcelas']}x de
  R$ {_brl(p['anual_parcela'])} sem juros.</li>"""
        )
    inner = f"""\
<h1 style="margin:0 0 12px 0;font-size:18px;color:{_INK};">{_html.escape(assunto)}</h1>
<p style="margin:0 0 16px 0;font-size:14px;line-height:1.6;color:{_MUTED};">{_html.escape(abertura)}</p>
<ul style="margin:0 0 20px 0;padding-left:18px;font-size:14px;line-height:1.6;color:{_INK};">
{"".join(linhas)}
</ul>
<div style="text-align:center;margin:0 0 20px 0;">
  <a href="{_html.escape(link_assinar, quote=True)}" style="display:inline-block;background-color:{_BRAND};color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;padding:12px 24px;border-radius:8px;">Aproveitar a oferta</a>
</div>
<p style="margin:0 0 12px 0;font-size:12px;line-height:1.6;color:{_MUTED};">
  Condições: oferta válida até {_html.escape(validade_label)}, uma vez por escritório, e não soma
  com outros descontos. O plano mensal renova sozinho todo mês no cartão e pode ser cancelado
  a qualquer momento em Plano e assinatura, sem multa. Você pode desistir em até 7 dias após o
  pagamento e receber o valor de volta.
</p>
<p style="margin:0;font-size:12px;line-height:1.6;color:{_MUTED};">
  <a href="{_html.escape(link_descadastro, quote=True)}" style="color:{_MUTED};">Não quero mais receber ofertas</a>
</p>"""
    return assunto, _base_layout(inner)


def render_portal_magic_link_email(link: str) -> str:
    """HTML com o link de acesso (uso único, 24 h) ao portal do cliente."""
    inner = f"""\
<h1 style="margin:0 0 12px 0;font-size:18px;color:{_INK};">Seu acesso ao portal do cliente</h1>
<p style="margin:0 0 20px 0;font-size:14px;line-height:1.6;color:{_MUTED};">
  Clique no botão abaixo para entrar no portal do seu escritório contábil.
  O link vale por 24 horas e só pode ser usado uma vez.
</p>
<div style="text-align:center;margin:0 0 20px 0;">
  <a href="{link}" style="display:inline-block;background-color:{_BRAND};color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;padding:12px 24px;border-radius:8px;">Acessar o portal</a>
</div>
<p style="margin:0;font-size:13px;line-height:1.6;color:{_MUTED};">
  Se você não pediu este acesso, ignore este e-mail. Não compartilhe este link.
</p>"""
    return _base_layout(inner)


async def _send_test_email(to: str) -> bool:
    """E-mail de teste para validar o Resend (uso manual, nunca no request)."""
    return await send_email(
        to=to,
        subject="Teste de envio — FiscWise",
        html=(
            "<p>Este é um e-mail de teste do FiscWise.</p>"
            "<p>Se você recebeu, o envio pelo Resend está funcionando.</p>"
        ),
    )


if __name__ == "__main__":  # python -m app.services.email_service destino@exemplo.com
    import asyncio
    import sys

    if len(sys.argv) != 2:
        print("Uso: python -m app.services.email_service destino@exemplo.com")
        raise SystemExit(2)
    logging.basicConfig(level=logging.INFO)
    if not is_configured():
        print("Envio desligado: defina RESEND_ENABLED=true e RESEND_API_KEY.")
        raise SystemExit(1)
    ok = asyncio.run(_send_test_email(sys.argv[1]))
    print("Enviado." if ok else "Falhou: veja o log acima.")
    raise SystemExit(0 if ok else 1)
