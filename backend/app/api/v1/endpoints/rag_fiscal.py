"""
RAG Fiscal API Router for FiscWise.
Provides access to managing custom procedures, manuals, FAQs, and searching them.
"""

import uuid
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[RagDocument]:
    """
    Lista todos os documentos da base de conhecimento RAG do tenant.
    """
    stmt = select(RagDocument).where(RagDocument.tenant_id == current_user.tenant_id).order_by(desc(RagDocument.created_at))
    if category:
        stmt = stmt.where(RagDocument.category == category)
        
    result = await db.execute(stmt)
    return list(result.scalars().all())


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
