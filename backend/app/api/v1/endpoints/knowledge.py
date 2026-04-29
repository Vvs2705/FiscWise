"""
Knowledge Base Endpoints for ContaFlow

Handles document ingestion, listing, and deletion for the knowledge base.
All routes require authentication and tenant isolation.
"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.ingest_service import IngestService
from app.schemas.knowledge import (
    IngestTextRequest,
    IngestURLRequest,
    IngestResponse,
    DocumentResponse
)


router = APIRouter()


@router.post("/ingest/text", response_model=IngestResponse, summary="Ingest Text Content")
async def ingest_text(
    request: IngestTextRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> IngestResponse:
    """
    Ingest raw text content into the knowledge base.
    
    Creates a document, chunks it, generates embeddings, and stores everything.
    Requires authentication and X-Tenant-ID header.
    
    Args:
        request: Text content and title
        current_user: Authenticated user
        db: Database session
        
    Returns:
        IngestResponse: Document ID, status, and chunk count
    """
    ingest_service = IngestService(db)
    
    try:
        document = await ingest_service.ingest_text(
            tenant_id=current_user.tenant_id,
            title=request.title,
            content=request.content
        )
        
        return IngestResponse(
            document_id=document.id,
            title=document.title,
            status=document.status,
            chunks_created=len(document.chunks),
            message=f"Document '{document.title}' ingested successfully with {len(document.chunks)} chunks"
        )
    except Exception as e:
        logger.error("ingest_text failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest document. Please try again."
        )


@router.post("/ingest/url", response_model=IngestResponse, summary="Ingest URL Content")
async def ingest_url(
    request: IngestURLRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> IngestResponse:
    """
    Fetch content from a URL and ingest it into the knowledge base.
    
    Downloads the URL content, chunks it, generates embeddings, and stores everything.
    Requires authentication and X-Tenant-ID header.
    
    Args:
        request: URL and optional title
        current_user: Authenticated user
        db: Database session
        
    Returns:
        IngestResponse: Document ID, status, and chunk count
    """
    ingest_service = IngestService(db)
    
    try:
        document = await ingest_service.ingest_url(
            tenant_id=current_user.tenant_id,
            url=request.url,
            title=request.title
        )
        
        return IngestResponse(
            document_id=document.id,
            title=document.title,
            status=document.status,
            chunks_created=len(document.chunks),
            message=f"URL '{document.title}' ingested successfully with {len(document.chunks)} chunks"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("ingest_url failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest URL. Please try again."
        )


@router.get("/sources", response_model=list[DocumentResponse], summary="List Knowledge Sources")
async def list_sources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[DocumentResponse]:
    """
    List all knowledge base documents for the current tenant.
    
    Returns all documents with their metadata and chunk counts.
    Requires authentication and X-Tenant-ID header.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        list[DocumentResponse]: List of documents
    """
    ingest_service = IngestService(db)
    documents = await ingest_service.get_documents(current_user.tenant_id)
    
    return [
        DocumentResponse(
            id=doc.id,
            tenant_id=doc.tenant_id,
            title=doc.title,
            content_type=doc.content_type,
            status=doc.status,
            created_at=doc.created_at,
            chunk_count=len(doc.chunks)
        )
        for doc in documents
    ]


@router.delete("/sources/{document_id}", summary="Delete Knowledge Source")
async def delete_source(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a knowledge base document and all its chunks.
    
    Permanently removes the document and all associated chunks (CASCADE).
    Requires authentication and X-Tenant-ID header.
    
    Args:
        document_id: UUID of the document to delete
        current_user: Authenticated user
        db: Database session
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: 404 if document not found
    """
    ingest_service = IngestService(db)
    deleted = await ingest_service.delete_document(document_id, current_user.tenant_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )
    
    return {"message": f"Document {document_id} deleted successfully"}
