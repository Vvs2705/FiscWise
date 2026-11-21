"""Regras do cofre e da liberação da emissão por emissor (empresa).

Liberação da emissão de um emissor (`estado_emissao`):
1. modo escolhido: 'proprio' (certificado da própria empresa, mesmo CNPJ) ou
   'procuracao' (certificado do escritório + procuração eletrônica confirmada);
2. certificado válido (não vencido, bloqueado nem revogado);
3. dados mínimos do emissor (CNPJ, município IBGE, código de serviço, regime);
4. teste de emissão OK depois da última mudança (qualquer mudança zera).
A inscrição municipal é aviso (nem todo município exige na NFS-e nacional).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.certificados import cofre
from app.domain.certificados.models import (
    ESCOPO_CLIENTE,
    ESCOPO_ESCRITORIO,
    ESCOPOS,
    STATUS_BLOQUEADO,
    STATUS_VALIDO,
    CertificadoA1,
)
from app.domain.certificados.validacao import CertificadoInvalido, conferir
from app.domain.invoices.models import InvoiceIssuer
from app.models.operations import AccountingClient

MODO_PROPRIO = "proprio"
MODO_PROCURACAO = "procuracao"
MODOS = (MODO_PROPRIO, MODO_PROCURACAO)


class ErroRegra(ValueError):
    """Erro de regra com mensagem para o usuário. `status` é o HTTP sugerido."""

    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.status = status


def _digitos(valor: Optional[str]) -> str:
    return re.sub(r"\D", "", valor or "")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def metadados(cert: CertificadoA1, agora: Optional[datetime] = None) -> dict[str, Any]:
    agora = agora or _agora()
    fim = _aware(cert.valido_ate)
    return {
        "id": cert.id,
        "escopo": cert.escopo,
        "client_id": cert.client_id,
        "titular_nome": cert.titular_nome,
        "documento": cert.documento,
        "tipo_documento": cert.tipo_documento,
        "emissor": cert.emissor,
        "valido_de": _aware(cert.valido_de),
        "valido_ate": fim,
        "status": cert.status_efetivo(agora),
        "motivo_bloqueio": cert.motivo_bloqueio,
        "ultimo_uso": _aware(cert.ultimo_uso),
        "created_at": _aware(cert.created_at),
        "dias_para_vencer": (fim - agora).days if fim else None,
    }


# ---------------------------------------------------------------------------
# Envio
# ---------------------------------------------------------------------------


async def salvar_certificado(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    conteudo: bytes,
    senha: str,
    escopo: str,
    client_id: Optional[uuid.UUID],
) -> CertificadoA1:
    if escopo not in ESCOPOS:
        raise ErroRegra("Escolha se o certificado é do escritório ou de um cliente.", 422)
    if not cofre.cofre_configurado():
        raise ErroRegra(
            "Envio de certificados indisponível neste ambiente: cofre não configurado.", 503
        )

    cliente = None
    if escopo == ESCOPO_CLIENTE:
        if client_id is None:
            raise ErroRegra("Informe de qual cliente é o certificado.", 422)
        cliente = (
            await db.execute(
                select(AccountingClient).where(
                    AccountingClient.id == client_id, AccountingClient.tenant_id == tenant_id
                )
            )
        ).scalar_one_or_none()
        if cliente is None:
            raise ErroRegra("Cliente não encontrado neste escritório.", 404)
    elif client_id is not None:
        raise ErroRegra("Certificado do escritório não pertence a um cliente.", 422)

    try:
        dados = conferir(conteudo, senha)
    except CertificadoInvalido as exc:
        raise ErroRegra(str(exc), 400) from exc

    if cliente is not None:
        doc_cliente = _digitos(cliente.document)
        if not doc_cliente:
            raise ErroRegra(
                "Cadastre o CNPJ/CPF do cliente antes de enviar o certificado dele.", 400
            )
        if not dados.documento:
            raise ErroRegra(
                "Não foi possível ler o CNPJ/CPF dentro do certificado. Confira se é um e-CNPJ "
                "ou e-CPF A1 da empresa.",
                400,
            )
        if dados.documento != doc_cliente:
            raise ErroRegra(
                f"Este certificado é do documento {dados.documento}, mas o cliente está cadastrado "
                f"com {doc_cliente}. Envie o certificado da própria empresa.",
                400,
            )

    repetido = (
        await db.execute(
            select(CertificadoA1.id).where(
                CertificadoA1.tenant_id == tenant_id,
                CertificadoA1.thumbprint_sha256 == dados.thumbprint_sha256,
            )
        )
    ).first()
    if repetido:
        raise ErroRegra("Este certificado já foi enviado.", 409)

    cert_id = uuid.uuid4()
    cert = CertificadoA1(
        id=cert_id,
        tenant_id=tenant_id,
        escopo=escopo,
        client_id=client_id if escopo == ESCOPO_CLIENTE else None,
        titular_nome=dados.titular_nome,
        documento=dados.documento,
        tipo_documento=dados.tipo_documento,
        emissor=dados.emissor,
        numero_serie=dados.numero_serie,
        thumbprint_sha256=dados.thumbprint_sha256,
        valido_de=dados.valido_de,
        valido_ate=dados.valido_ate,
        pfx_cifrado=cofre.cifrar(conteudo, tenant_id=tenant_id, certificado_id=cert_id, campo="pfx"),
        senha_cifrada=cofre.cifrar(
            (senha or "").encode("utf-8"), tenant_id=tenant_id, certificado_id=cert_id, campo="senha"
        ),
        chave_versao=cofre.VERSAO_CHAVE_ATUAL,
        status=STATUS_VALIDO,
        criado_por_user_id=user_id,
    )
    db.add(cert)
    await db.flush()
    return cert


async def _issuers_que_usam(db: AsyncSession, cert_id: uuid.UUID) -> list[InvoiceIssuer]:
    return list(
        (await db.execute(select(InvoiceIssuer).where(InvoiceIssuer.certificado_id == cert_id))).scalars()
    )


def _zerar_teste(issuer: InvoiceIssuer) -> None:
    issuer.ultimo_teste_em = None
    issuer.ultimo_teste_ok = None
    issuer.ultimo_teste_mensagem = None


async def apagar_certificado(db: AsyncSession, cert: CertificadoA1) -> int:
    """Apaga o certificado (e os cifrados). Emissores que o usavam ficam sem
    certificado e com a emissão bloqueada até escolherem outro. Devolve quantos."""
    afetados = await _issuers_que_usam(db, cert.id)
    for issuer in afetados:
        issuer.certificado_id = None
        _zerar_teste(issuer)
    await db.flush()
    await db.delete(cert)
    await db.flush()
    return len(afetados)


async def bloquear(db: AsyncSession, cert: CertificadoA1, motivo: Optional[str]) -> None:
    cert.status = STATUS_BLOQUEADO
    cert.motivo_bloqueio = (motivo or "").strip()[:255] or None
    await db.flush()


async def desbloquear(db: AsyncSession, cert: CertificadoA1) -> None:
    cert.status = STATUS_VALIDO
    cert.motivo_bloqueio = None
    # Por segurança, quem usava este certificado testa de novo.
    for issuer in await _issuers_que_usam(db, cert.id):
        _zerar_teste(issuer)
    await db.flush()


# ---------------------------------------------------------------------------
# Liberação da emissão por emissor
# ---------------------------------------------------------------------------


async def _certificado(
    db: AsyncSession, cert_id: Optional[uuid.UUID], tenant_id: uuid.UUID
) -> Optional[CertificadoA1]:
    # Filtro por escritório no código, além da RLS: o certificado_id vem do
    # corpo da requisição (PUT /certificados/emissao) e, sem isto, um escritório
    # conseguiria ligar ao próprio emissor o certificado de outro se o contexto
    # RLS faltasse.
    if cert_id is None:
        return None
    return (
        await db.execute(
            select(CertificadoA1).where(
                CertificadoA1.id == cert_id, CertificadoA1.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()


def _pendencias_config(
    issuer: InvoiceIssuer, cert: Optional[CertificadoA1], agora: datetime
) -> list[str]:
    pend: list[str] = []
    modo = issuer.modo_certificado
    cnpj = _digitos(issuer.cnpj)
    if modo not in MODOS:
        pend.append(
            "Escolha como esta empresa emite: com o certificado da própria empresa ou com o "
            "certificado do escritório e procuração eletrônica."
        )
    elif cert is None:
        if modo == MODO_PROPRIO:
            pend.append(f"Envie o certificado A1 da empresa (CNPJ {cnpj}) e selecione-o aqui.")
        else:
            pend.append("Envie o certificado A1 do escritório e selecione-o aqui.")
    else:
        if modo == MODO_PROPRIO:
            if cert.escopo != ESCOPO_CLIENTE or (cert.documento or "") != cnpj:
                pend.append("O certificado escolhido não é desta empresa (o CNPJ não confere).")
        else:
            if cert.escopo != ESCOPO_ESCRITORIO:
                pend.append("No modo procuração, escolha o certificado do escritório.")
            if issuer.procuracao_confirmada_em is None:
                pend.append(
                    "Confirme que a empresa cadastrou a procuração eletrônica para o escritório no "
                    "portal da Receita Federal (serviço NFS-e)."
                )
        motivo = cofre.mensagem_indisponivel(cert, agora)
        if motivo:
            pend.append(motivo)

    if len(cnpj) != 14:
        pend.append("Informe o CNPJ do emissor.")
    if not re.fullmatch(r"\d{7}", issuer.municipio_ibge or ""):
        pend.append("Informe o código IBGE do município do emissor (7 dígitos).")
    if not (issuer.cod_servico_lc116 or "").strip():
        pend.append("Informe o código do serviço (item da lista da LC 116).")
    if not (issuer.regime_tributario or "").strip():
        pend.append("Informe o regime tributário do emissor.")
    return pend


async def estado_emissao(db: AsyncSession, issuer: InvoiceIssuer) -> dict[str, Any]:
    agora = _agora()
    cert = await _certificado(db, issuer.certificado_id, issuer.tenant_id)
    pendencias = _pendencias_config(issuer, cert, agora)
    if not pendencias:
        if issuer.ultimo_teste_ok is True:
            pass
        elif issuer.ultimo_teste_ok is False:
            pendencias.append(
                "O último teste de emissão falhou"
                + (f": {issuer.ultimo_teste_mensagem}" if issuer.ultimo_teste_mensagem else ".")
                + " Corrija e teste de novo."
            )
        else:
            pendencias.append("Faça o teste de emissão para liberar.")
    avisos: list[str] = []
    if not (issuer.inscricao_municipal or "").strip():
        avisos.append(
            "Inscrição municipal não informada. Alguns municípios exigem; se a nota for "
            "rejeitada por isso, preencha."
        )
    if cert is not None:
        dias = (_aware(cert.valido_ate) - agora).days
        if 0 <= dias <= 30:
            avisos.append(f"O certificado vence em {dias} dia(s). Renove para não parar a emissão.")
    return {
        "issuer_id": issuer.id,
        "modo_certificado": issuer.modo_certificado,
        "certificado_id": issuer.certificado_id,
        "certificado": metadados(cert, agora) if cert is not None else None,
        "procuracao_confirmada_em": _aware(issuer.procuracao_confirmada_em),
        "ultimo_teste_em": _aware(issuer.ultimo_teste_em),
        "ultimo_teste_ok": issuer.ultimo_teste_ok,
        "ultimo_teste_mensagem": issuer.ultimo_teste_mensagem,
        "emissao_liberada": not pendencias,
        "pendencias": pendencias,
        "avisos": avisos,
    }


async def configurar_emissao(
    db: AsyncSession,
    issuer: InvoiceIssuer,
    *,
    modo_certificado: Optional[str],
    certificado_id: Optional[uuid.UUID],
    procuracao_confirmada: Optional[bool],
) -> None:
    if modo_certificado is not None and modo_certificado not in MODOS:
        raise ErroRegra("Modo inválido: use 'proprio' ou 'procuracao'.", 422)
    cert = await _certificado(db, certificado_id, issuer.tenant_id) if certificado_id else None
    if certificado_id and cert is None:
        raise ErroRegra("Certificado não encontrado neste escritório.", 404)
    if cert is not None and modo_certificado == MODO_PROPRIO:
        if cert.escopo != ESCOPO_CLIENTE:
            raise ErroRegra("No modo próprio, escolha o certificado da própria empresa.", 400)
        if (cert.documento or "") != _digitos(issuer.cnpj):
            raise ErroRegra(
                "O certificado escolhido é de outro CNPJ. No modo próprio ele tem que ser da "
                "própria empresa emissora.",
                400,
            )
    if cert is not None and modo_certificado == MODO_PROCURACAO and cert.escopo != ESCOPO_ESCRITORIO:
        raise ErroRegra("No modo procuração, escolha o certificado do escritório.", 400)

    mudou = (
        issuer.modo_certificado != modo_certificado
        or issuer.certificado_id != (cert.id if cert else None)
    )
    issuer.modo_certificado = modo_certificado
    issuer.certificado_id = cert.id if cert else None
    if modo_certificado == MODO_PROCURACAO:
        if procuracao_confirmada is True and issuer.procuracao_confirmada_em is None:
            issuer.procuracao_confirmada_em = _agora()
            mudou = True
        elif procuracao_confirmada is False and issuer.procuracao_confirmada_em is not None:
            issuer.procuracao_confirmada_em = None
            mudou = True
    elif issuer.procuracao_confirmada_em is not None:
        issuer.procuracao_confirmada_em = None
        mudou = True
    if mudou:
        _zerar_teste(issuer)
    await db.flush()


async def testar_emissao(db: AsyncSession, issuer: InvoiceIssuer, provider: Any = None) -> dict[str, Any]:
    """Testa a conexão com o padrão nacional usando o certificado configurado."""
    agora = _agora()
    cert = await _certificado(db, issuer.certificado_id, issuer.tenant_id)
    pend = _pendencias_config(issuer, cert, agora)
    if pend:
        raise ErroRegra("Antes de testar: " + " ".join(pend), 409)

    ok = False
    mensagem = ""
    try:
        material = await cofre.obter_material(
            db, cert.id, tenant_id=issuer.tenant_id, finalidade="teste_emissao"
        )
        if provider is None:
            from app.domain.invoices.providers.nfse_nacional import NfseNacionalProvider

            provider = NfseNacionalProvider()
        testar = getattr(provider, "testar_conexao", None)
        if testar is None:
            mensagem = "O conector do padrão nacional ainda não está disponível neste ambiente."
        else:
            resultado = await testar(material, issuer)
            ok = bool(resultado.get("ok"))
            mensagem = str(resultado.get("mensagem") or ("Conexão aprovada." if ok else "Falhou."))
    except cofre.CertificadoIndisponivel as exc:
        mensagem = str(exc)
    except cofre.CofreIndisponivel as exc:
        mensagem = str(exc)
    except Exception as exc:  # noqa: BLE001 — qualquer falha do conector vira teste reprovado
        mensagem = f"Falha ao testar: {type(exc).__name__}: {exc}"[:500]

    issuer.ultimo_teste_em = _agora()
    issuer.ultimo_teste_ok = ok
    issuer.ultimo_teste_mensagem = mensagem[:1000]
    await db.flush()
    return await estado_emissao(db, issuer)


__all__ = [
    "ErroRegra",
    "MODOS",
    "MODO_PROCURACAO",
    "MODO_PROPRIO",
    "apagar_certificado",
    "bloquear",
    "configurar_emissao",
    "desbloquear",
    "estado_emissao",
    "metadados",
    "salvar_certificado",
    "testar_emissao",
]
