"""
RAG Fiscal API Router for FiscWise.
Provides access to managing custom procedures, manuals, FAQs, and searching them.
"""

import uuid
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.pagination import Page, page_params, paginate
from app.models.user import User
from app.models.rag_fiscal import RagDocument
from app.services import rag_service
from app.schemas.rag_fiscal import (
    RagDocumentCreate,
    RagDocumentUpdate,
    RagDocumentResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["RAG Fiscal"])


@router.get("/documents", response_model=List[RagDocumentResponse])
async def list_documents(
    category: Optional[str] = Query(default=None),
    page: Page = Depends(page_params),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[RagDocument]:
    """
    Lista todos os documentos da base de conhecimento RAG do tenant.
    """
    stmt = select(RagDocument).where(RagDocument.tenant_id == current_user.tenant_id).order_by(desc(RagDocument.created_at), desc(RagDocument.id))
    if category:
        stmt = stmt.where(RagDocument.category == category)
        
    return await paginate(db, stmt, page)


@router.post("/documents", response_model=RagDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: RagDocumentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RagDocument:
    """
    Adiciona um novo documento (diretriz, FAQ ou procedimento) à base RAG.
    """
    return await rag_service.create_rag_document(
        db=db,
        payload=payload,
        tenant_id=current_user.tenant_id
    )


@router.post("/documents/upload", response_model=RagDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=2, max_length=255),
    category: str = Form("regras_fiscais", max_length=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RagDocument:
    """Sobe um arquivo (PDF, DOCX, TXT, MD até 20 MB) para a base de conhecimento.

    O arquivo fica no Storage, privado do escritório; o texto vai para `content`
    e entra na busca. A equipe FiscWise só vê o arquivo se ele for anexado a uma
    solicitação de ajuste fiscal.
    """
    import os
    import uuid as _uuid

    from app.core import storage as _storage
    from app.core.document_links import DOCUMENTS_BUCKET

    nome = os.path.basename(file.filename or "arquivo")
    ext = os.path.splitext(nome)[1].lower()
    if ext not in rag_service.RAG_UPLOAD_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de arquivo não aceito. Use PDF, DOCX, TXT ou MD.",
        )
    conteudo = await file.read(rag_service.RAG_UPLOAD_MAX_BYTES + 1)
    if not conteudo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio.")
    if len(conteudo) > rag_service.RAG_UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo maior que 20 MB.",
        )
    if not _storage._storage_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Envio de arquivos não configurado neste ambiente.",
        )

    try:
        texto = rag_service.extrair_texto_completo(conteudo, ext)
    except Exception:
        logger.warning("rag_upload: falha ao extrair texto de %s", nome, exc_info=True)
        texto = ""
    if len(texto) < 10:
        aviso = f"[Arquivo {nome} sem texto extraível — por exemplo, PDF escaneado.]"
        texto = f"{texto} {aviso}".strip()

    mime = file.content_type or rag_service.RAG_UPLOAD_EXTS[ext]
    caminho = f"{current_user.tenant_id}/conhecimento/{_uuid.uuid4().hex}-{nome}"
    try:
        await _storage.upload_bytes(DOCUMENTS_BUCKET, caminho, conteudo, mime)
    except RuntimeError:
        logger.exception("rag_upload: falha no Storage (%s)", caminho)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível guardar o arquivo agora. Tente de novo.",
        )

    doc = RagDocument(
        id=_uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        title=title.strip(),
        content=texto,
        source=nome[:255],
        category=(category or "regras_fiscais").strip()[:50],
        file_path=caminho,
        file_name=nome[:255],
        file_mime=mime[:120],
        file_size=len(conteudo),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Link temporário (15 min) para baixar o arquivo original do documento."""
    from app.core import storage as _storage
    from app.core.document_links import DOCUMENTS_BUCKET, SIGNED_URL_TTL

    doc = (
        await db.execute(
            select(RagDocument).where(
                RagDocument.id == document_id, RagDocument.tenant_id == current_user.tenant_id
            )
        )
    ).scalar_one_or_none()
    if doc is None or not doc.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado.")
    try:
        url = await _storage.get_signed_url(DOCUMENTS_BUCKET, doc.file_path, ttl=SIGNED_URL_TTL)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Download indisponível agora. Tente de novo em instantes.",
        )
    return {"url": url}


@router.put("/documents/{document_id}", response_model=RagDocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    payload: RagDocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RagDocument:
    """
    Atualiza um documento da base RAG existente.
    """
    doc = await rag_service.update_rag_document(
        db=db,
        document_id=document_id,
        payload=payload,
        tenant_id=current_user.tenant_id
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado na base de conhecimento."
        )
    return doc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exclui permanentemente um documento da base RAG.
    """
    success = await rag_service.delete_rag_document(
        db=db,
        document_id=document_id,
        tenant_id=current_user.tenant_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado na base de conhecimento."
        )
