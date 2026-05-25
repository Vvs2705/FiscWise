"""
RAG Fiscal Service for FiscWise.
Provides keyword term similarity search and CRUD operations on custom tax rules, manuals, and procedures.
"""

import uuid
import re
import math
import logging
from typing import List, Tuple, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag_fiscal import RagDocument
from app.schemas.rag_fiscal import RagDocumentCreate, RagDocumentUpdate

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    """Normalize text by lowercasing and stripping non-alphanumeric chars."""
    if not text:
        return ""
    # simple lower, remove punctuation/special characters
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return text


def calculate_similarity(query: str, doc_title: str, doc_content: str) -> float:
    """Calculates term frequency overlap score between query and document."""
    query_norm = _normalize_text(query)
    title_norm = _normalize_text(doc_title)
    content_norm = _normalize_text(doc_content)
    
    # Extract keywords with length > 2 (ignoring typical short prepositions/articles)
    query_words = [w for w in query_norm.split() if len(w) > 2]
    if not query_words:
        return 0.0
        
    score = 0.0
    for word in query_words:
        # Give higher weight to matches in the title
        title_count = title_norm.count(word)
        content_count = content_norm.count(word)
        
        score += title_count * 5.0
        score += content_count * 1.0
        
    # Penalize overly long documents slightly to favor specific matches
    doc_len = len(content_norm.split()) + 1
    length_penalty = math.log10(doc_len) + 1.0
    
    return score / length_penalty


async def search_knowledge_base(
    db: AsyncSession,
    query: str,
    tenant_id: uuid.UUID,
    limit: int = 3
) -> List[Tuple[RagDocument, float]]:
    """
    Searches the tenant's knowledge base using native TF similarity score.
    Returns matched documents and their calculated confidence level (50%-95%).
    """
    stmt = select(RagDocument).where(RagDocument.tenant_id == tenant_id)
    res = await db.execute(stmt)
    docs = res.scalars().all()
    
    scored_docs = []
    for doc in docs:
        score = calculate_similarity(query, doc.title, doc.content)
        if score > 0.05:
            # Map similarity score to a confidence percentage (50% to 95%)
            confidence = min(95.0, 50.0 + (score * 5.0))
            scored_docs.append((doc, confidence))
            
    # Sort by confidence descending
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return scored_docs[:limit]


async def create_rag_document(
    db: AsyncSession,
    payload: RagDocumentCreate,
    tenant_id: uuid.UUID
) -> RagDocument:
    """Creates a new RAG document in the knowledge base."""
    new_doc = RagDocument(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        title=payload.title,
        content=payload.content,
        source=payload.source,
        category=payload.category
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    return new_doc


async def update_rag_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    payload: RagDocumentUpdate,
    tenant_id: uuid.UUID
) -> Optional[RagDocument]:
    """Updates an existing RAG document."""
    stmt = select(RagDocument).where(
        (RagDocument.id == document_id) &
        (RagDocument.tenant_id == tenant_id)
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    
    if not doc:
        return None
        
    if payload.title is not None:
        doc.title = payload.title
    if payload.content is not None:
        doc.content = payload.content
    if payload.source is not None:
        doc.source = payload.source
    if payload.category is not None:
        doc.category = payload.category
        
    await db.commit()
    await db.refresh(doc)
    return doc


async def delete_rag_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> bool:
    """Deletes a RAG document."""
    stmt = select(RagDocument).where(
        (RagDocument.id == document_id) &
        (RagDocument.tenant_id == tenant_id)
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    
    if not doc:
        return False
        
    await db.delete(doc)
    await db.commit()
    return True
