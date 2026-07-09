"""Validação de arquivos por magic bytes (não confiar no content-type do cliente).

Antes era um stub que retornava sempre True — upload malicioso passava batido.
Agora inspeciona os bytes reais e só aceita se a assinatura casar com um dos
MIME types permitidos pelo caller.
"""
import logging

logger = logging.getLogger(__name__)

# Assinaturas (magic bytes) por MIME. Só cobre tipos que o produto aceita em
# upload; tipos sem assinatura binária confiável (text/*, csv) são tratados à parte.
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF",),  # RIFF....WEBP (checagem do WEBP abaixo)
    # ZIP-based (xlsx/docx/odt) começam com PK
    "application/zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (b"PK\x03\x04",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (b"PK\x03\x04",),
}

# MIME textuais: não têm magic byte confiável, valida só que é texto decodificável.
_TEXT_MIMES = {"text/plain", "text/csv", "application/xml", "text/xml"}


def _matches(file_bytes: bytes, mime: str) -> bool:
    if mime in _TEXT_MIMES:
        try:
            file_bytes[:4096].decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    sigs = _SIGNATURES.get(mime)
    if not sigs:
        # MIME permitido sem assinatura conhecida: não conseguimos validar,
        # deixa passar (não bloqueia funcionalidade legítima).
        return True
    head = file_bytes[:16]
    if mime == "image/webp":
        return head[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP"
    return any(head.startswith(sig) for sig in sigs)


def validate_file_mime(file_bytes: bytes, allowed_mimes: list[str]) -> bool:
    """True se os bytes casarem com pelo menos um dos MIME permitidos.

    Bytes vazios → False (não há o que validar; evita upload vazio).
    """
    if not file_bytes:
        logger.warning("validate_file_mime: arquivo vazio rejeitado")
        return False
    ok = any(_matches(file_bytes, m) for m in allowed_mimes)
    if not ok:
        logger.warning(
            "validate_file_mime: assinatura não casa com %s (primeiros bytes: %r)",
            allowed_mimes, file_bytes[:8],
        )
    return ok


def _selfcheck() -> None:
    assert validate_file_mime(b"%PDF-1.7\n...", ["application/pdf"]) is True
    assert validate_file_mime(b"\x89PNG\r\n\x1a\n", ["image/png"]) is True
    assert validate_file_mime(b"\xff\xd8\xff\xe0", ["image/jpeg", "image/png"]) is True
    # PDF disfarçado de imagem é rejeitado
    assert validate_file_mime(b"%PDF-1.7", ["image/png", "image/jpeg"]) is False
    # executável Windows (MZ) rejeitado onde só PDF é permitido
    assert validate_file_mime(b"MZ\x90\x00", ["application/pdf"]) is False
    # vazio rejeitado
    assert validate_file_mime(b"", ["application/pdf"]) is False
    # csv válido aceito
    assert validate_file_mime(b"a,b,c\n1,2,3", ["text/csv"]) is True
    print("file_validator selfcheck OK")


if __name__ == "__main__":
    _selfcheck()
