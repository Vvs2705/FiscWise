"""
IngestService — Chunking + Embedding + Storage

Responsável por:
1. Extrair texto de URLs, arquivos PDF, texto bruto
2. Dividir em chunks (CHUNK_SIZE / CHUNK_OVERLAP do settings)
3. Gerar embeddings via EmbeddingService
4. Salvar Document + DocumentChunks no PostgreSQL
"""
import uuid
import httpx
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.knowledge import Document, DocumentChunk, DocumentStatus
from app.services.embedding_service import EmbeddingService


class IngestService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        text = text.strip()
        while start < len(text):
            end = start + settings.CHUNK_SIZE
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start += settings.CHUNK_SIZE - settings.CHUNK_OVERLAP
        return chunks

    async def _fetch_url_content(self, url: str) -> str:
        """Fetch text content from a URL."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def ingest_text(
        self,
        tenant_id: uuid.UUID,
        title: str,
        content: str,
        content_type: str = "text"
    ) -> Document:
        """
        Ingest raw text content into the knowledge base.
        Creates Document, chunks it, generates embeddings, saves all to DB.
        """
        # Create Document record
        document = Document(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            title=title,
            content_type=content_type,
            status=DocumentStatus.PROCESSING
        )
        self.db.add(document)
        await self.db.flush()

        try:
            chunks = self._chunk_text(content)
            if not chunks:
                raise ValueError("No content to process")

            embeddings = await self.embedding_service.embed_batch(chunks)

            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document.id,
                    content=chunk_text,
                    embedding=embedding
                )
                self.db.add(chunk)

            document.status = DocumentStatus.PROCESSED
            await self.db.commit()
            await self.db.refresh(document)
            return document

        except Exception as e:
            document.status = DocumentStatus.FAILED
            await self.db.commit()
            raise e

    async def ingest_url(
        self,
        tenant_id: uuid.UUID,
        url: str,
        title: Optional[str] = None
    ) -> Document:
        """Fetch URL content and ingest it."""
        content = await self._fetch_url_content(url)
        return await self.ingest_text(
            tenant_id=tenant_id,
            title=title or url,
            content=content,
            content_type="url"
        )

    async def get_documents(self, tenant_id: uuid.UUID) -> list[Document]:
        """List all documents for a tenant."""
        result = await self.db.execute(
            select(Document).where(Document.tenant_id == tenant_id).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_document(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Delete a document and all its chunks (CASCADE)."""
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return False
        await self.db.delete(document)
        await self.db.commit()
        return True
