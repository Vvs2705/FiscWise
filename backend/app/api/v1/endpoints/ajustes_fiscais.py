"""Solicitações de ajuste fiscal (escritório) e análise pela equipe FiscWise.

Escritório (/ajustes-fiscais):
- feriado e prazo valem NA HORA só para o escritório, na UF/município
  informado, e entram na fila da equipe; nova obrigação e "outro" só vão para
  a fila.
Equipe FiscWise (/equipe/ajustes-fiscais, users.equipe_fiscwise):
- vê as solicitações de todos, analisa, recusa ou promove a regra geral
  (tenant_id NULL), que continua limitada à UF/município da regra.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.ajustes_fiscais import (
    STATUS_SOLICITACAO,
    TIPOS_APLICAVEIS,
    TIPOS_SOLICITACAO,
    FiscalAdjustmentRequest,
    FiscalCalendarAdjustment,
)
from app.models.obligation import ObligationRule
from app.models.rag_fiscal import RagDocument
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ajustes_fiscais import UFS, carregar_ajustes, recalcular_vencimentos

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ajustes-fiscais", tags=["Ajustes fiscais"])
router_equipe = APIRouter(prefix="/equipe/ajustes-fiscais", tags=["Equipe FiscWise"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SolicitacaoIn(BaseModel):
    tipo: str
    uf: str = Field(..., min_length=2, max_length=2)
    municipio_ibge: Optional[str] = None
    municipio_nome: Optional[str] = Field(None, max_length=120)
    data: Optional[date] = None
    recorrente_anual: bool = False
    obrigacao_code: Optional[str] = Field(None, max_length=50)
    due_day: Optional[int] = None
    descricao: str = Field(..., min_length=5, max_length=5000)
    fonte: Optional[str] = Field(None, max_length=2000)
    knowledge_doc_id: Optional[uuid.UUID] = None


class RespostaIn(BaseModel):
    resposta: Optional[str] = Field(None, max_length=5000)


class RecusaIn(BaseModel):
    resposta: str = Field(..., min_length=5, max_length=5000)


def _iso(v) -> Optional[str]:
    return v.isoformat() if v is not None else None


def _out(req: FiscalAdjustmentRequest, doc_title: Optional[str] = None, **extra) -> dict:
    return {
        "id": str(req.id),
        "tipo": req.tipo,
        "uf": req.uf,
        "municipio_ibge": req.municipio_ibge,
        "municipio_nome": req.municipio_nome,
        "data": _iso(req.data),
        "recorrente_anual": bool(req.recorrente_anual),
        "obrigacao_code": req.obrigacao_code,
        "due_day": req.due_day,
        "descricao": req.descricao,
        "fonte": req.fonte,
        "knowledge_doc_id": str(req.knowledge_doc_id) if req.knowledge_doc_id else None,
        "knowledge_doc_title": doc_title,
        "status": req.status,
        "resposta_equipe": req.resposta_equipe,
        "created_at": _iso(req.created_at),
        "reviewed_at": _iso(req.reviewed_at),
        **extra,
    }


def _validar(body: SolicitacaoIn) -> SolicitacaoIn:
    if body.tipo not in TIPOS_SOLICITACAO:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Tipo inválido.")
    body.uf = body.uf.upper()
    if body.uf not in UFS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "UF inválida.")
    if body.municipio_ibge:
        body.municipio_ibge = body.municipio_ibge.strip()
        if not re.fullmatch(r"\d{7}", body.municipio_ibge):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Código IBGE do município deve ter 7 dígitos."
            )
    else:
        body.municipio_ibge = None
    if body.tipo == "feriado" and body.data is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe a data do feriado.")
    if body.tipo == "prazo":
        if not body.obrigacao_code:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe a obrigação.")
        if not body.due_day or not 1 <= body.due_day <= 31:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe o dia de vencimento (1 a 31)."
            )
        body.obrigacao_code = body.obrigacao_code.strip().upper()
    return body


def _ajuste_de(req: FiscalAdjustmentRequest, tenant_id: Optional[uuid.UUID]) -> FiscalCalendarAdjustment:
    """Ajuste do calendário a partir da solicitação (do escritório ou geral)."""
    a = FiscalCalendarAdjustment(
        tenant_id=tenant_id,
        tipo=req.tipo,
        uf=req.uf,
        municipio_ibge=req.municipio_ibge,
        nome=(req.descricao or "")[:200],
        ativo=True,
        origem_request_id=req.id,
    )
    if req.tipo == "feriado" and req.data:
        a.mes, a.dia = req.data.month, req.data.day
        a.ano = None if req.recorrente_anual else req.data.year
    if req.tipo == "prazo":
        a.obrigacao_code = req.obrigacao_code
        a.due_day = req.due_day
    return a


def _exigir_gestor(user: User) -> None:
    if not user.is_admin_or_owner():
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Só o responsável ou um administrador do escritório pode fazer isso.",
        )


async def _titulos(db: AsyncSession, ids: set) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    res = await db.execute(select(RagDocument.id, RagDocument.title).where(RagDocument.id.in_(ids)))
    return {r[0]: r[1] for r in res.all()}


# ─── Escritório ───────────────────────────────────────────────────────────────

@router.get("/obrigacoes", summary="Obrigações que podem ter o prazo ajustado")
async def listar_obrigacoes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    res = await db.execute(
        select(ObligationRule.code, ObligationRule.name)
        .where(ObligationRule.active.is_(True))
        .order_by(ObligationRule.code)
    )
    return [{"code": c, "name": n} for c, n in res.all()]


@router.get("/ajustes-ativos", summary="Feriados e prazos ajustados que valem para o escritório")
async def ajustes_ativos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    ajustes = await carregar_ajustes(db, current_user.tenant_id)
    ajustes.sort(key=lambda a: (a.uf, a.municipio_ibge or "", a.tipo, a.mes or 0, a.dia or 0))
    return [
        {
            "id": str(a.id),
            "escopo": "geral" if a.tenant_id is None else "escritorio",
            "tipo": a.tipo,
            "uf": a.uf,
            "municipio_ibge": a.municipio_ibge,
            "mes": a.mes,
            "dia": a.dia,
            "ano": a.ano,
            "nome": a.nome,
            "obrigacao_code": a.obrigacao_code,
            "due_day": a.due_day,
            "origem_request_id": str(a.origem_request_id) if a.origem_request_id else None,
        }
        for a in ajustes
    ]


@router.get("", summary="Solicitações do escritório")
async def listar_solicitacoes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    res = await db.execute(
        select(FiscalAdjustmentRequest)
        .where(FiscalAdjustmentRequest.tenant_id == current_user.tenant_id)
        .order_by(FiscalAdjustmentRequest.created_at.desc())
    )
    itens = list(res.scalars().all())
    titulos = await _titulos(db, {i.knowledge_doc_id for i in itens})
    return [_out(i, titulos.get(i.knowledge_doc_id)) for i in itens]


@router.post("", status_code=status.HTTP_201_CREATED, summary="Nova solicitação de ajuste fiscal")
async def criar_solicitacao(
    body: SolicitacaoIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _exigir_gestor(current_user)
    body = _validar(body)

    doc_title = None
    if body.knowledge_doc_id:
        doc = (
            await db.execute(
                select(RagDocument).where(
                    RagDocument.id == body.knowledge_doc_id,
                    RagDocument.tenant_id == current_user.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento da base de conhecimento não encontrado.")
        doc_title = doc.title

    req = FiscalAdjustmentRequest(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        created_by_user_id=current_user.id,
        tipo=body.tipo,
        uf=body.uf,
        municipio_ibge=body.municipio_ibge,
        municipio_nome=(body.municipio_nome or None),
        data=body.data,
        recorrente_anual=body.recorrente_anual,
        obrigacao_code=body.obrigacao_code,
        due_day=body.due_day,
        descricao=body.descricao.strip(),
        fonte=(body.fonte or None),
        knowledge_doc_id=body.knowledge_doc_id,
        status="aplicada_no_escritorio" if body.tipo in TIPOS_APLICAVEIS else "em_analise",
    )
    db.add(req)
    await db.flush()

    recalculadas = 0
    if body.tipo in TIPOS_APLICAVEIS:
        db.add(_ajuste_de(req, current_user.tenant_id))
        await db.flush()
        recalculadas = await recalcular_vencimentos(
            db, uf=req.uf, municipio_ibge=req.municipio_ibge, tenant_id=current_user.tenant_id
        )
    await db.commit()
    await db.refresh(req)
    logger.info("ajuste_fiscal criado tenant=%s tipo=%s uf=%s recalculadas=%s",
                current_user.tenant_id, req.tipo, req.uf, recalculadas)
    return _out(req, doc_title, recalculadas=recalculadas)


@router.get("/{solicitacao_id}", summary="Detalhe de uma solicitação do escritório")
async def obter_solicitacao(
    solicitacao_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    req = await _do_escritorio(db, solicitacao_id, current_user.tenant_id)
    titulos = await _titulos(db, {req.knowledge_doc_id})
    return _out(req, titulos.get(req.knowledge_doc_id))


@router.delete("/{solicitacao_id}", summary="Desfaz o ajuste do escritório e apaga a solicitação")
async def apagar_solicitacao(
    solicitacao_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Desfaz só o ajuste do próprio escritório. Regra geral já criada continua."""
    _exigir_gestor(current_user)
    req = await _do_escritorio(db, solicitacao_id, current_user.tenant_id)
    uf, mun = req.uf, req.municipio_ibge
    proprios = (
        await db.execute(
            select(FiscalCalendarAdjustment).where(
                FiscalCalendarAdjustment.origem_request_id == req.id,
                FiscalCalendarAdjustment.tenant_id == current_user.tenant_id,
            )
        )
    ).scalars().all()
    for a in proprios:
        await db.delete(a)
    await db.delete(req)
    await db.flush()
    recalculadas = 0
    if proprios:
        recalculadas = await recalcular_vencimentos(
            db, uf=uf, municipio_ibge=mun, tenant_id=current_user.tenant_id
        )
    await db.commit()
    return {"status": "apagada", "recalculadas": recalculadas}


async def _do_escritorio(db: AsyncSession, solicitacao_id: uuid.UUID, tenant_id) -> FiscalAdjustmentRequest:
    req = (
        await db.execute(
            select(FiscalAdjustmentRequest).where(
                FiscalAdjustmentRequest.id == solicitacao_id,
                FiscalAdjustmentRequest.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitação não encontrada.")
    return req


# ─── Equipe FiscWise ──────────────────────────────────────────────────────────

async def _limpar_contexto_escritorio(db: AsyncSession) -> None:
    """A equipe trabalha com as solicitações de TODOS os escritórios.

    get_current_user prende a sessão ao escritório do usuário (RLS forçada).
    Aqui a sessão volta ao modo "rotina do sistema": tira o escritório da
    sessão (o hook after_begin não o reaplica) e zera o contexto da transação
    aberta — current_app_tenant_id() trata '' como NULL.
    """
    db.info.pop("tenant_id", None)
    try:
        bind = db.get_bind()
        if getattr(getattr(bind, "dialect", None), "name", None) != "postgresql":
            return
    except Exception:
        return
    if db.in_transaction():
        await db.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))


async def exigir_equipe(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not getattr(current_user, "equipe_fiscwise", False):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Área restrita à equipe FiscWise.")
    await _limpar_contexto_escritorio(db)
    return current_user


async def _qualquer(db: AsyncSession, solicitacao_id: uuid.UUID) -> FiscalAdjustmentRequest:
    req = (
        await db.execute(select(FiscalAdjustmentRequest).where(FiscalAdjustmentRequest.id == solicitacao_id))
    ).scalar_one_or_none()
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitação não encontrada.")
    return req


async def _nome_escritorio(db: AsyncSession, tenant_id) -> Optional[str]:
    return (await db.execute(select(Tenant.name).where(Tenant.id == tenant_id))).scalar_one_or_none()


def _marcar_revisao(req: FiscalAdjustmentRequest, user: User, resposta: Optional[str]) -> None:
    req.reviewed_by_user_id = user.id
    req.reviewed_at = datetime.now(timezone.utc)
    if resposta is not None:
        req.resposta_equipe = resposta.strip() or None


@router_equipe.get("", summary="Equipe: solicitações de todos os escritórios")
async def equipe_listar(
    status_: Optional[str] = Query(None, alias="status"),
    uf: Optional[str] = Query(None, min_length=2, max_length=2),
    tipo: Optional[str] = Query(None),
    equipe: User = Depends(exigir_equipe),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    stmt = (
        select(FiscalAdjustmentRequest, Tenant.name)
        .join(Tenant, Tenant.id == FiscalAdjustmentRequest.tenant_id)
        .order_by(FiscalAdjustmentRequest.created_at.desc())
    )
    if status_:
        if status_ not in STATUS_SOLICITACAO:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Status inválido.")
        stmt = stmt.where(FiscalAdjustmentRequest.status == status_)
    if uf:
        stmt = stmt.where(FiscalAdjustmentRequest.uf == uf.upper())
    if tipo:
        stmt = stmt.where(FiscalAdjustmentRequest.tipo == tipo)
    linhas = (await db.execute(stmt)).all()
    titulos = await _titulos(db, {r.knowledge_doc_id for r, _ in linhas})
    return [
        _out(r, titulos.get(r.knowledge_doc_id), tenant_id=str(r.tenant_id), tenant_name=nome)
        for r, nome in linhas
    ]


@router_equipe.get("/{solicitacao_id}", summary="Equipe: detalhe, com o arquivo anexado")
async def equipe_obter(
    solicitacao_id: uuid.UUID,
    equipe: User = Depends(exigir_equipe),
    db: AsyncSession = Depends(get_db),
) -> dict:
    req = await _qualquer(db, solicitacao_id)
    doc_out = None
    titulo = None
    if req.knowledge_doc_id:
        doc = (
            await db.execute(select(RagDocument).where(RagDocument.id == req.knowledge_doc_id))
        ).scalar_one_or_none()
        if doc is not None:
            titulo = doc.title
            url = None
            if doc.file_path:
                from app.core import storage as _storage
                from app.core.document_links import DOCUMENTS_BUCKET, SIGNED_URL_TTL

                try:
                    url = await _storage.get_signed_url(DOCUMENTS_BUCKET, doc.file_path, ttl=SIGNED_URL_TTL)
                except RuntimeError:
                    url = None
            doc_out = {
                "title": doc.title,
                "content_preview": (doc.content or "")[:3000],
                "download_url": url,
            }
    return _out(
        req, titulo,
        tenant_id=str(req.tenant_id),
        tenant_name=await _nome_escritorio(db, req.tenant_id),
        knowledge_doc=doc_out,
    )


@router_equipe.post("/{solicitacao_id}/em-analise", summary="Equipe: marca como em análise")
async def equipe_em_analise(
    solicitacao_id: uuid.UUID,
    body: RespostaIn | None = None,
    equipe: User = Depends(exigir_equipe),
    db: AsyncSession = Depends(get_db),
) -> dict:
    req = await _qualquer(db, solicitacao_id)
    if req.status == "regra_geral":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta solicitação já virou regra geral.")
    req.status = "em_analise"
    _marcar_revisao(req, equipe, body.resposta if body else None)
    await db.commit()
    await db.refresh(req)
    return _out(req)


@router_equipe.post("/{solicitacao_id}/regra-geral", summary="Equipe: transforma em regra geral")
async def equipe_regra_geral(
    solicitacao_id: uuid.UUID,
    body: RespostaIn | None = None,
    equipe: User = Depends(exigir_equipe),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cria o ajuste geral (tenant_id NULL), limitado à UF/município da
    solicitação, e recalcula as obrigações abertas de todos os escritórios
    com clientes ali."""
    req = await _qualquer(db, solicitacao_id)
    if req.tipo not in TIPOS_APLICAVEIS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Só feriado e prazo viram regra geral automática. Nova obrigação e outros "
            "pedidos precisam de implementação: marque em análise e responda o escritório.",
        )
    ja_existe = (
        await db.execute(
            select(FiscalCalendarAdjustment.id).where(
                and_(
                    FiscalCalendarAdjustment.origem_request_id == req.id,
                    FiscalCalendarAdjustment.tenant_id.is_(None),
                )
            )
        )
    ).first()
    if not ja_existe:
        db.add(_ajuste_de(req, None))
    req.status = "regra_geral"
    _marcar_revisao(req, equipe, body.resposta if body else None)
    await db.flush()
    recalculadas = await recalcular_vencimentos(db, uf=req.uf, municipio_ibge=req.municipio_ibge)
    await db.commit()
    await db.refresh(req)
    logger.info("ajuste_fiscal regra_geral req=%s uf=%s mun=%s recalculadas=%s",
                req.id, req.uf, req.municipio_ibge, recalculadas)
    return _out(req, recalculadas=recalculadas)


@router_equipe.post("/{solicitacao_id}/recusar", summary="Equipe: recusa virar regra geral")
async def equipe_recusar(
    solicitacao_id: uuid.UUID,
    body: RecusaIn,
    equipe: User = Depends(exigir_equipe),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Recusar = não vira regra geral. O ajuste do próprio escritório continua
    valendo até ele apagar a solicitação."""
    req = await _qualquer(db, solicitacao_id)
    if req.status == "regra_geral":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta solicitação já virou regra geral.")
    req.status = "recusada"
    _marcar_revisao(req, equipe, body.resposta)
    await db.commit()
    await db.refresh(req)
    return _out(req)
