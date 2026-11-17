"""Conferência do certificado A1 no envio (antes de cifrar e guardar).

- abre o PKCS#12 com a senha (A3 em token não tem arquivo .pfx);
- exige certificado do titular + chave privada;
- confere validade e se é ICP-Brasil (O/OU do emissor ou da cadeia);
- lê o documento do próprio certificado: e-CNPJ no otherName 2.16.76.1.3.3,
  e-CPF no 2.16.76.1.3.1 (DOC-ICP-04: 8 dígitos da data de nascimento + 11
  do CPF + ...), com reserva no CN "NOME:DOCUMENTO".
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

TAMANHO_MAXIMO = 50 * 1024  # um .pfx A1 tem poucos KB

OID_CNPJ = "2.16.76.1.3.3"
OID_DADOS_PF = "2.16.76.1.3.1"

DICA_A3 = (
    "Envie o arquivo do certificado A1 (.pfx ou .p12). Certificado A3 fica em "
    "token ou cartão e não pode ser usado para emitir pelo sistema."
)


class CertificadoInvalido(ValueError):
    """Mensagem pronta para o usuário (vira 400)."""


@dataclass(frozen=True)
class DadosCertificado:
    titular_nome: str
    documento: Optional[str]
    tipo_documento: Optional[str]  # cnpj | cpf
    emissor: str
    numero_serie: str
    thumbprint_sha256: str
    valido_de: datetime
    valido_ate: datetime
    icp_brasil: bool


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _validade(cert: x509.Certificate) -> tuple[datetime, datetime]:
    inicio = getattr(cert, "not_valid_before_utc", None) or _utc(cert.not_valid_before)
    fim = getattr(cert, "not_valid_after_utc", None) or _utc(cert.not_valid_after)
    return inicio, fim


def _atributos(nome: x509.Name, oid) -> list[str]:
    return [str(a.value) for a in nome.get_attributes_for_oid(oid)]


def _cn(nome: x509.Name) -> str:
    valores = _atributos(nome, NameOID.COMMON_NAME)
    return valores[0] if valores else nome.rfc4514_string()


def _menciona_icp(nome: x509.Name) -> bool:
    valores = _atributos(nome, NameOID.ORGANIZATION_NAME) + _atributos(
        nome, NameOID.ORGANIZATIONAL_UNIT_NAME
    )
    return any("icp-brasil" in v.lower() for v in valores)


def _conteudo_der(valor: bytes) -> bytes:
    """Desembrulha TLVs DER (ex.: [0] EXPLICIT { OCTET STRING }) até o primitivo."""
    dados = valor
    for _ in range(4):
        if len(dados) < 2:
            break
        tag = dados[0]
        tam = dados[1]
        pos = 2
        if tam & 0x80:
            n = tam & 0x7F
            if n == 0 or len(dados) < 2 + n:
                break
            tam = int.from_bytes(dados[2 : 2 + n], "big")
            pos = 2 + n
        conteudo = dados[pos : pos + tam]
        if len(conteudo) != tam:
            break
        construido = bool(tag & 0x20)
        dados = conteudo
        if not construido:
            break
    return dados


def _digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def _documento_do_san(cert: x509.Certificate) -> tuple[Optional[str], Optional[str]]:
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return None, None
    cnpj = cpf = None
    for other in san.get_values_for_type(x509.OtherName):
        oid = other.type_id.dotted_string
        try:
            texto = _conteudo_der(other.value).decode("latin-1")
        except Exception:  # noqa: BLE001
            continue
        digitos = _digitos(texto)
        if oid == OID_CNPJ and len(digitos) >= 14:
            cnpj = digitos[:14]
        elif oid == OID_DADOS_PF and len(digitos) >= 19:
            cpf = digitos[8:19]
    if cnpj:
        return cnpj, "cnpj"
    if cpf and set(cpf) != {"0"}:
        return cpf, "cpf"
    return None, None


def _documento_do_cn(cn: str) -> tuple[Optional[str], Optional[str]]:
    if ":" not in cn:
        return None, None
    digitos = _digitos(cn.rsplit(":", 1)[1])
    if len(digitos) == 14:
        return digitos, "cnpj"
    if len(digitos) == 11:
        return digitos, "cpf"
    return None, None


def abrir_pkcs12(conteudo: bytes, senha: str):
    """Abre o .pfx. Devolve (chave, certificado, cadeia) ou levanta CertificadoInvalido."""
    if not conteudo:
        raise CertificadoInvalido("Arquivo vazio. " + DICA_A3)
    if len(conteudo) > TAMANHO_MAXIMO:
        raise CertificadoInvalido("Arquivo grande demais para um certificado A1 (máximo 50 KB). " + DICA_A3)
    if conteudo[0] != 0x30:  # PKCS#12 é uma SEQUENCE DER
        raise CertificadoInvalido("O arquivo não é um certificado .pfx/.p12. " + DICA_A3)
    try:
        chave, cert, cadeia = pkcs12.load_key_and_certificates(
            conteudo, (senha or "").encode("utf-8") or None
        )
    except ValueError as exc:
        raise CertificadoInvalido("Senha do certificado incorreta.") from exc
    except Exception as exc:  # noqa: BLE001
        raise CertificadoInvalido("Não foi possível ler o certificado. " + DICA_A3) from exc
    if cert is None or chave is None:
        raise CertificadoInvalido(
            "O arquivo não traz o certificado com a chave privada. " + DICA_A3
        )
    return chave, cert, list(cadeia or [])


def conferir(conteudo: bytes, senha: str, *, agora: Optional[datetime] = None) -> DadosCertificado:
    """Confere o certificado e lê os metadados. Levanta CertificadoInvalido."""
    agora = agora or datetime.now(timezone.utc)
    _chave, cert, cadeia = abrir_pkcs12(conteudo, senha)

    inicio, fim = _validade(cert)
    if fim <= agora:
        raise CertificadoInvalido(
            f"Certificado vencido em {fim.astimezone(timezone.utc):%d/%m/%Y}. Envie o certificado renovado."
        )
    if inicio > agora:
        raise CertificadoInvalido("O certificado ainda não começou a valer.")

    nomes: Iterable[x509.Name] = [cert.issuer] + [c.subject for c in cadeia] + [c.issuer for c in cadeia]
    icp = any(_menciona_icp(n) for n in nomes)
    if not icp:
        raise CertificadoInvalido(
            "Não é um certificado ICP-Brasil. Para emitir NFS-e é preciso um e-CNPJ ou e-CPF "
            "A1 de uma certificadora credenciada."
        )

    cn = _cn(cert.subject)
    documento, tipo = _documento_do_san(cert)
    if not documento:
        documento, tipo = _documento_do_cn(cn)

    return DadosCertificado(
        titular_nome=(cn.split(":", 1)[0].strip() or cn)[:255],
        documento=documento,
        tipo_documento=tipo,
        emissor=_cn(cert.issuer)[:255],
        numero_serie=format(cert.serial_number, "x")[:80],
        thumbprint_sha256=hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest(),
        valido_de=inicio,
        valido_ate=fim,
        icp_brasil=icp,
    )


def para_pem(conteudo: bytes, senha: str) -> tuple[bytes, bytes, bytes]:
    """(cert_pem, chave_pem sem senha, cadeia_pem) — só em memória."""
    chave, cert, cadeia = abrir_pkcs12(conteudo, senha)
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    chave_pem = chave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    cadeia_pem = b"".join(c.public_bytes(serialization.Encoding.PEM) for c in cadeia)
    return cert_pem, chave_pem, cadeia_pem


__all__ = [
    "CertificadoInvalido",
    "DadosCertificado",
    "DICA_A3",
    "TAMANHO_MAXIMO",
    "abrir_pkcs12",
    "conferir",
    "para_pem",
]
