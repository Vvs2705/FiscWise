"""Cifra e decifra os certificados A1 (AES-256-GCM).

- Chave: settings.CERT_ENCRYPTION_KEY (base64 de 32 bytes, vem do Secret
  Manager). Sem chave, nada é guardado (CofreIndisponivel → 503).
- Cada item (arquivo .pfx e senha) tem nonce próprio de 12 bytes, gravado na
  frente do texto cifrado. Dados associados = "<tenant_id>:<certificado_id>:<campo>":
  um blob copiado para outro escritório ou outro certificado não decifra.
- `chave_versao` guarda a versão da chave usada (rotação futura).

Nunca logar senha nem conteúdo; nada disto sai em API.
"""

from __future__ import annotations

import base64
import binascii
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.certificados.models import CertificadoA1, STATUS_VALIDO
from app.domain.certificados.validacao import CertificadoInvalido, para_pem

VERSAO_CHAVE_ATUAL = 1


class CofreIndisponivel(RuntimeError):
    """Chave do cofre não configurada (ou inválida) neste ambiente."""


class CertificadoIndisponivel(RuntimeError):
    """Certificado vencido, bloqueado, revogado, apagado ou ilegível."""


@dataclass(frozen=True)
class MaterialCertificado:
    certificado_id: uuid.UUID
    documento: str          # CNPJ/CPF do titular
    cert_pem: bytes         # certificado do titular em PEM
    chave_pem: bytes        # chave privada em PEM SEM senha (só em memória)
    cadeia_pem: bytes       # intermediárias em PEM (pode ser b"")

    def __repr__(self) -> str:  # nunca expor a chave em log/traceback
        return f"MaterialCertificado(certificado_id={self.certificado_id}, documento={self.documento})"


def _chave() -> bytes:
    bruto = (settings.CERT_ENCRYPTION_KEY or "").strip()
    if not bruto:
        raise CofreIndisponivel(
            "Cofre de certificados não configurado neste ambiente (CERT_ENCRYPTION_KEY)."
        )
    try:
        chave = base64.b64decode(bruto, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise CofreIndisponivel("CERT_ENCRYPTION_KEY inválida (esperado base64).") from exc
    if len(chave) != 32:
        raise CofreIndisponivel("CERT_ENCRYPTION_KEY deve ter 32 bytes (AES-256).")
    return chave


def cofre_configurado() -> bool:
    try:
        _chave()
    except CofreIndisponivel:
        return False
    return True


def _aad(tenant_id: uuid.UUID, certificado_id: uuid.UUID, campo: str) -> bytes:
    return f"{tenant_id}:{certificado_id}:{campo}".encode()


def cifrar(dados: bytes, *, tenant_id: uuid.UUID, certificado_id: uuid.UUID, campo: str) -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(_chave()).encrypt(nonce, dados, _aad(tenant_id, certificado_id, campo))


def decifrar(blob: bytes, *, tenant_id: uuid.UUID, certificado_id: uuid.UUID, campo: str) -> bytes:
    if not blob or len(blob) < 13:
        raise CertificadoIndisponivel("Certificado guardado está ilegível. Envie de novo.")
    try:
        return AESGCM(_chave()).decrypt(blob[:12], blob[12:], _aad(tenant_id, certificado_id, campo))
    except CofreIndisponivel:
        raise
    except Exception as exc:  # noqa: BLE001 — InvalidTag: chave trocada ou blob adulterado
        raise CertificadoIndisponivel(
            "Não foi possível abrir o certificado guardado. Envie o certificado de novo."
        ) from exc


def mensagem_indisponivel(cert: CertificadoA1, agora: datetime) -> str | None:
    """Motivo pelo qual o certificado não pode ser usado agora (None = pode)."""
    status_atual = cert.status_efetivo(agora)
    if status_atual == STATUS_VALIDO:
        return None
    if status_atual == "vencido":
        fim = cert.valido_ate if cert.valido_ate.tzinfo else cert.valido_ate.replace(tzinfo=timezone.utc)
        return f"O certificado de {cert.titular_nome} venceu em {fim:%d/%m/%Y}. Envie o renovado."
    if status_atual == "bloqueado":
        motivo = f" ({cert.motivo_bloqueio})" if cert.motivo_bloqueio else ""
        return f"O certificado de {cert.titular_nome} está bloqueado{motivo}."
    return f"O certificado de {cert.titular_nome} não está disponível ({status_atual})."


async def obter_material(
    db: AsyncSession, certificado_id: uuid.UUID, *, finalidade: str
) -> MaterialCertificado:
    """Decifra o certificado para uso imediato (emitir, cancelar, consultar, testar).

    A sessão `db` já está no contexto do escritório (RLS forçada): certificado
    de outro escritório não aparece. Atualiza `ultimo_uso` e registra auditoria
    sem nenhum dado sensível.
    """
    cert = (
        await db.execute(select(CertificadoA1).where(CertificadoA1.id == certificado_id))
    ).scalar_one_or_none()
    if cert is None:
        raise CertificadoIndisponivel("Certificado não encontrado. Configure a emissão de novo.")
    agora = datetime.now(timezone.utc)
    motivo = mensagem_indisponivel(cert, agora)
    if motivo:
        raise CertificadoIndisponivel(motivo)

    pfx = decifrar(cert.pfx_cifrado, tenant_id=cert.tenant_id, certificado_id=cert.id, campo="pfx")
    senha = decifrar(cert.senha_cifrada, tenant_id=cert.tenant_id, certificado_id=cert.id, campo="senha")
    try:
        cert_pem, chave_pem, cadeia_pem = para_pem(pfx, senha.decode("utf-8"))
    except CertificadoInvalido as exc:
        raise CertificadoIndisponivel(
            "O certificado guardado não abriu. Envie o certificado de novo."
        ) from exc

    cert.ultimo_uso = agora
    await db.flush()

    from app.core.audit import audit_log

    await audit_log(
        action="certificado.uso",
        tenant_id=str(cert.tenant_id),
        entity_type="certificado",
        details={"certificado_id": str(cert.id), "finalidade": finalidade, "escopo": cert.escopo},
    )
    return MaterialCertificado(
        certificado_id=cert.id,
        documento=cert.documento or "",
        cert_pem=cert_pem,
        chave_pem=chave_pem,
        cadeia_pem=cadeia_pem,
    )


__all__ = [
    "VERSAO_CHAVE_ATUAL",
    "CertificadoIndisponivel",
    "CofreIndisponivel",
    "MaterialCertificado",
    "cifrar",
    "cofre_configurado",
    "decifrar",
    "mensagem_indisponivel",
    "obter_material",
]
