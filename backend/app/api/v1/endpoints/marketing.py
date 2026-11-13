"""Descadastro dos e-mails de oferta (LGPD art. 18 §2º: direito de oposição).

O link do e-mail aponta para cá. Responde uma página HTML simples, sem login
e sem rota no frontend. O token é assinado (app.services.oferta) e só serve
para isto.
"""

import html
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.user import User
from app.services.oferta import ler_token_descadastro

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/marketing", tags=["Marketing"])


def _pagina(titulo: str, texto: str, status_code: int = 200) -> HTMLResponse:
    corpo = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titulo)} · FiscWise</title></head>
<body style="margin:0;padding:48px 16px;background:#F9FAFB;font-family:Arial,Helvetica,sans-serif;color:#111827;">
<div style="max-width:480px;margin:0 auto;background:#fff;border:1px solid #E5E7EB;border-radius:12px;padding:28px;">
<p style="margin:0 0 16px 0;font-size:20px;font-weight:700;">Fisc<span style="color:#F97316;">Wise</span></p>
<h1 style="margin:0 0 12px 0;font-size:18px;">{html.escape(titulo)}</h1>
<p style="margin:0;font-size:14px;line-height:1.6;color:#6B7280;">{html.escape(texto)}</p>
</div></body></html>"""
    return HTMLResponse(corpo, status_code=status_code)


@router.get("/descadastro", response_class=HTMLResponse)
async def descadastrar(
    token: str = Query(..., min_length=10, max_length=2000),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    user_id = ler_token_descadastro(token)
    user = await db.get(User, user_id) if user_id else None
    if user is None:
        return _pagina(
            "Link inválido",
            "Não conseguimos confirmar este link. Se quiser parar de receber ofertas, "
            "responda pelo suporte do FiscWise.",
            status_code=400,
        )
    if user.marketing_opt_out_at is None:
        user.marketing_opt_out_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info("marketing_opt_out user=%s", user.id)
    return _pagina(
        "Pronto, você não vai mais receber ofertas",
        "Seu e-mail saiu da lista de ofertas do FiscWise. Avisos sobre a sua conta "
        "(segurança, cobrança e prazos) continuam chegando normalmente.",
    )
