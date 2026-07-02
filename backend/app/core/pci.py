"""PCI guardrails — card-data rejection and sensitive-data redaction.

Two independent objectives, framework-agnostic (importable in any layer):

1. ``contains_card_data`` / ``card_data_reason``: detect PAN/CVV and forbidden
   fields in payloads that reach the backend. FiscWise uses Mercado Pago
   Checkout Pro / hosted checkout — NO card data must ever transit this API.
   The billing router rejects such payloads with HTTP 400.
2. ``redact_sensitive``: recursively mask sensitive keys (Authorization,
   Cookie, tokens, secrets, card fields, Pix QR) before logging or persisting.
   Defence in depth: no log/event carries a secret or card number.

Ported from SessãoInk (``app/core/pci.py``), adapted to English naming.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

# Keys whose VALUE must never appear in logs/persisted payloads. Comparison is
# normalised: lowercase, without ``_``/``-``/space.
_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "setcookie",
    "password",
    "senha",
    "secret",
    "token",
    "accesstoken",
    "refreshtoken",
    "mercadopagoaccesstoken",
    "mercadopagowebhooksecret",
    "webhooksecret",
    "cardnumber",
    "cvv",
    "cvc",
    "securitycode",
    "qrcode",
    "qrcodebase64",
    "ticketurl",
}

# Forbidden fields in a payment payload (card data / authentication).
_CARD_KEYS = {
    "cardnumber",
    "number",
    "pan",
    "cvv",
    "cvc",
    "cvv2",
    "securitycode",
    "cardpassword",
    "card",
    "track1",
    "track2",
    "magstripe",
}

# Likely PAN: 13–19 digits (optional separators). Luhn-validated to reduce
# false positives with long ids.
_PAN_RE = re.compile(r"(?:\d[ -]?){13,19}")


def _norm(key: str) -> str:
    return re.sub(r"[ _\-]", "", key).lower()


def _luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not (13 <= len(digits) <= 19):
        return False
    total = 0
    even = False
    for d in reversed(digits):
        if even:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        even = not even
    return total % 10 == 0


def _value_looks_like_pan(value: str) -> bool:
    for m in _PAN_RE.finditer(value):
        if _luhn_ok(m.group()):
            return True
    return False


def card_data_reason(obj: Any, _depth: int = 0) -> str | None:
    """Return the reason if the payload contains forbidden card data, else None."""
    if _depth > 6:
        return None
    if isinstance(obj, dict):
        for key, value in obj.items():
            if _norm(str(key)) in _CARD_KEYS:
                return f"forbidden card field: {key}"
            reason = card_data_reason(value, _depth + 1)
            if reason:
                return reason
        return None
    if isinstance(obj, (list, tuple)):
        for item in obj:
            reason = card_data_reason(item, _depth + 1)
            if reason:
                return reason
        return None
    if isinstance(obj, str) and _value_looks_like_pan(obj):
        return "value resembling a card number (PAN)"
    return None


def contains_card_data(obj: Any) -> bool:
    return card_data_reason(obj) is not None


def redact_sensitive(obj: Any, _depth: int = 0) -> Any:
    """Recursively mask values of sensitive keys. Does not mutate the original."""
    if _depth > 8:
        return obj
    if isinstance(obj, dict):
        out: dict[Any, Any] = {}
        for key, value in obj.items():
            if _norm(str(key)) in _SENSITIVE_KEYS:
                out[key] = REDACTED
            else:
                out[key] = redact_sensitive(value, _depth + 1)
        return out
    if isinstance(obj, list):
        return [redact_sensitive(item, _depth + 1) for item in obj]
    if isinstance(obj, tuple):
        return tuple(redact_sensitive(item, _depth + 1) for item in obj)
    return obj
