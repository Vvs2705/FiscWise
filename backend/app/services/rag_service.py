"""
RAGService — Vector similarity search

Busca os K chunks mais relevantes para uma query usando pgvector cosine similarity.
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.services.embedding_service import EmbeddingService


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()

    async def search(self, tenant_id: uuid.UUID, query: str, top_k: int = None) -> list[str]:
        """
        Semantic search across all document_chunks for a tenant.
        Returns list of content strings ordered by cosine similarity (most similar first).
        """
        if top_k is None:
            top_k = settings.TOP_K_RESULTS

        query_embedding = await self.embedding_service.embed_query(query)

        # pgvector cosine similarity — lower <=> distance = more similar
        sql = text("""
            SELECT dc.content
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.tenant_id = :tenant_id
              AND dc.embedding IS NOT NULL
            ORDER BY dc.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

        result = await self.db.execute(sql, {
            "tenant_id": str(tenant_id),
            "embedding": str(query_embedding),
            "top_k": top_k
        })

        return [row[0] for row in result.fetchall()]
