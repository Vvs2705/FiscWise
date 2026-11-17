"""Cofre de certificados A1 e liberação da emissão de NFS-e por emissor.

Rotas:
- POST   /certificados                      envia .pfx/.p12 + senha (multipart)
- GET    /certificados                      lista metadados (filtros escopo, client_id)
- DELETE /certificados/{id}                 apaga (emissores que usavam ficam bloqueados)
- POST   /certificados/{id}/bloquear        bloqueia o uso
- POST   /certificados/{id}/desbloquear     libera de novo (exige novo teste)
- GET    /certificados/emissao/{issuer_id}  estado da emissão daquele emissor
- PUT    /certificados/emissao/{issuer_id}  escolhe modo e certificado
- POST   /certificados/emissao/{issuer_id}/testar  testa com o padrão nacional

Só dono e admin enviam, apagam, bloqueiam, configuram e testam; membros veem.
Arquivo e senha nunca voltam em nenhuma resposta.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.deps import get_current_user, get_db
from app.domain.certificados import servico
from app.domain.certificados.models import CertificadoA1
from app.domain.certificados.validacao import TAMANHO_MAXIMO
from app.domain.invoices.models import InvoiceIssuer
from app.models.user import User

router = APIRouter(prefix="/certificados", tags=["Certificados"])


class CertificadoOut(BaseModel):
    id: uuid.UUID
    escopo: str
    client_id: Optional[uuid.UUID] = None
    titular_nome: str
    documento: Optional[str] = None
    tipo_documento: Optional[str] = None
    emissor: str
    valido_de: Optional[datetime] = None
    valido_ate: datetime
    status: str
    motivo_bloqueio: Optional[str] = None
    ultimo_uso: Optional[datetime] = None
    created_at: Optional[datetime] = None
    dias_para_vencer: Optional[int] = None


class EstadoEmissaoOut(BaseModel):
    issuer_id: uuid.UUID
    modo_certificado: Optional[str] = None
    certificado_id: Optional[uuid.UUID] = None
    certificado: Optional[CertificadoOut] = None
    procuracao_confirmada_em: Optional[datetime] = None
    ultimo_teste_em: Optional[datetime] = None
    ultimo_teste_ok: Optional[bool] = None
    ultimo_teste_mensagem: Optional[str] = None
    emissao_liberada: bool
    pendencias: List[str]
    avisos: List[str] = []


class ConfigEmissaoIn(BaseModel):
    modo_certificado: Optional[str] = None
    certificado_id: Optional[uuid.UUID] = None
    procuracao_confirmada: Optional[bool] = None


class BloqueioIn(BaseModel):
    motivo: Optional[str] = None


def _exigir_gestor(user: User) -> None:
    if not user.is_admin_or_owner():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Só o responsável ou um administrador do escritório pode fazer isso.",
        )


def _erro(exc: servico.ErroRegra) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=str(exc))


async def _cert_ou_404(db: AsyncSession, cert_id: uuid.UUID, tenant_id: uuid.UUID) -> CertificadoA1:
    cert = (
        await db.execute(
            select(CertificadoA1).where(CertificadoA1.id == cert_id, CertificadoA1.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificado não encontrado.")
    return cert


async def _issuer_ou_404(db: AsyncSession, issuer_id: uuid.UUID, tenant_id: uuid.UUID) -> InvoiceIssuer:
    issuer = (
        await db.execute(
            select(InvoiceIssuer).where(InvoiceIssuer.id == issuer_id, InvoiceIssuer.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if issuer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emissor não encontrado.")
    return issuer


@router.post("", response_model=CertificadoOut, status_code=status.HTTP_201_CREATED)
async def enviar_certificado(
    arquivo: UploadFile = File(...),
    senha: str = Form(...),
    escopo: str = Form(...),
    client_id: Optional[uuid.UUID] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _exigir_gestor(current_user)
    conteudo = await arquivo.read(TAMANHO_MAXIMO + 1)
    try:
        cert = await servico.salvar_certificado(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            conteudo=conteudo,
            senha=senha,
            escopo=(escopo or "").strip().lower(),
            client_id=client_id,
        )
    except servico.ErroRegra as exc:
        await db.rollback()
        raise _erro(exc)
    await db.commit()
    await db.refresh(cert)
    await audit_log(
        action="certificado.enviado",
        tenant_id=str(current_user.tenant_id),
        entity_type="certificado",
        details={"certificado_id": str(cert.id), "escopo": cert.escopo, "por": str(current_user.id)},
    )
    return servico.metadados(cert)


@router.get("", response_model=List[CertificadoOut])
async def listar_certificados(
    escopo: Optional[str] = Query(None),
    client_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CertificadoA1).where(CertificadoA1.tenant_id == current_user.tenant_id)
    if escopo:
        stmt = stmt.where(CertificadoA1.escopo == escopo)
    if client_id:
        stmt = stmt.where(CertificadoA1.client_id == client_id)
    stmt = stmt.order_by(CertificadoA1.valido_ate.asc())
    return [servico.metadados(c) for c in (await db.execute(stmt)).scalars()]


@router.delete("/{cert_id}")
async def apagar_certificado(
    cert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _exigir_gestor(current_user)
    cert = await _cert_ou_404(db, cert_id, current_user.tenant_id)
    afetados = await servico.apagar_certificado(db, cert)
    await db.commit()
    await audit_log(
        action="certificado.apagado",
        tenant_id=str(current_user.tenant_id),
        entity_type="certificado",
        details={"certificado_id": str(cert_id), "emissores_afetados": afetados},
    )
    return {"apagado": True, "emissores_afetados": afetados}


@router.post("/{cert_id}/bloquear", response_model=CertificadoOut)
async def bloquear_certificado(
    cert_id: uuid.UUID,
    payload: Optional[BloqueioIn] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _exigir_gestor(current_user)
    cert = await _cert_ou_404(db, cert_id, current_user.tenant_id)
    await servico.bloquear(db, cert, payload.motivo if payload else None)
    await db.commit()
    await db.refresh(cert)
    return servico.metadados(cert)


@router.post("/{cert_id}/desbloquear", response_model=CertificadoOut)
async def desbloquear_certificado(
    cert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _exigir_gestor(current_user)
    cert = await _cert_ou_404(db, cert_id, current_user.tenant_id)
    await servico.desbloquear(db, cert)
    await db.commit()
    await db.refresh(cert)
    return servico.metadados(cert)


@router.get("/emissao/{issuer_id}", response_model=EstadoEmissaoOut)
async def estado_emissao(
    issuer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    issuer = await _issuer_ou_404(db, issuer_id, current_user.tenant_id)
    return await servico.estado_emissao(db, issuer)


@router.put("/emissao/{issuer_id}", response_model=EstadoEmissaoOut)
async def configurar_emissao(
    issuer_id: uuid.UUID,
    payload: ConfigEmissaoIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _exigir_gestor(current_user)
    issuer = await _issuer_ou_404(db, issuer_id, current_user.tenant_id)
    try:
        await servico.configurar_emissao(
            db,
            issuer,
            modo_certificado=payload.modo_certificado,
            certificado_id=payload.certificado_id,
            procuracao_confirmada=payload.procuracao_confirmada,
        )
    except servico.ErroRegra as exc:
        await db.rollback()
        raise _erro(exc)
    await db.commit()
    await db.refresh(issuer)
    return await servico.estado_emissao(db, issuer)


@router.post("/emissao/{issuer_id}/testar", response_model=EstadoEmissaoOut)
async def testar_emissao(
    issuer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _exigir_gestor(current_user)
    issuer = await _issuer_ou_404(db, issuer_id, current_user.tenant_id)
    try:
        estado = await servico.testar_emissao(db, issuer)
    except servico.ErroRegra as exc:
        await db.rollback()
        raise _erro(exc)
    await db.commit()
    return estado
