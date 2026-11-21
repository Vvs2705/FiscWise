"""Cifra de campo para segredos curtos guardados no banco (hoje: segredo TOTP).

Mesma chave e mesmo algoritmo do cofre de certificados A1 (AES-256-GCM com
CERT_ENCRYPTION_KEY, app/domain/certificados/cofre.py). Os dados associados
levam o nome do campo e o dono da linha ("totp:<user_id>"): um valor copiado
para outro usuário não decifra.

Formato guardado: "enc:v1:" + base64(nonce de 12 bytes + texto cifrado).

Compatibilidade:
- valor sem o prefixo é legado (texto puro) e continua sendo lido, para
  ninguém perder o 2FA; ele é cifrado na próxima gravação;
- ambiente sem CERT_ENCRYPTION_KEY grava em texto puro, como antes.
"""

from __future__ import annotations

import base64
import binascii
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIXO = "enc:v1:"


class CampoIlegivel(RuntimeError):
    """Valor cifrado que não abre (chave trocada ou valor adulterado)."""


def _chave() -> Optional[bytes]:
    from app.core.config import settings

    bruto = (settings.CERT_ENCRYPTION_KEY or "").strip()
    if not bruto:
        return None
    try:
        chave = base64.b64decode(bruto, validate=True)
    except (binascii.Error, ValueError):
        return None
    return chave if len(chave) == 32 else None


def esta_cifrado(valor: Optional[str]) -> bool:
    return bool(valor) and valor.startswith(PREFIXO)


def cifrar(valor: str, *, contexto: str) -> str:
    """Cifra `valor`; sem chave configurada devolve o próprio valor."""
    chave = _chave()
    if chave is None:
        return valor
    nonce = os.urandom(12)
    blob = nonce + AESGCM(chave).encrypt(nonce, valor.encode("utf-8"), contexto.encode())
    return PREFIXO + base64.b64encode(blob).decode()


def decifrar(guardado: Optional[str], *, contexto: str) -> Optional[str]:
    """Valor em claro. Legado sem prefixo volta como está."""
    if not guardado:
        return guardado
    if not esta_cifrado(guardado):
        return guardado
    chave = _chave()
    if chave is None:
        raise CampoIlegivel("CERT_ENCRYPTION_KEY ausente: não dá para abrir o valor cifrado.")
    try:
        blob = base64.b64decode(guardado[len(PREFIXO):], validate=True)
        return AESGCM(chave).decrypt(blob[:12], blob[12:], contexto.encode()).decode("utf-8")
    except Exception as exc:  # noqa: BLE001 — InvalidTag, base64 ruim
        raise CampoIlegivel("Valor cifrado ilegível.") from exc


def contexto_totp(user_id: object) -> str:
    return f"totp:{user_id}"


__all__ = ["CampoIlegivel", "PREFIXO", "cifrar", "contexto_totp", "decifrar", "esta_cifrado"]
