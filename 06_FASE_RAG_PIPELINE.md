# FASE 06 — RAG Pipeline: Embedding + Ingest + Knowledge API

## CONTEXTO DO PROJETO
Stack: FastAPI + SQLAlchemy 2.0 async + PostgreSQL + pgvector + Redis
Deploy: Railway (auto-deploy no push para main)
Repo: github.com/Vvs2705/SAAS-B2B

## REGRAS ABSOLUTAS
1. NUNCA usar `from app.core.auth import ...` → SEMPRE usar `from app.core.deps import get_current_user, get_db`
2. Embeddings: Voyage AI (voyage-2, 1024 dims) — NÃO OpenAI
3. Se criar rota pública → adicionar prefix em `_EXCLUDED_PREFIXES` no `app/core/middleware.py`
4. Uma migration por mudança de schema

## ASSINATURAS REAIS (copie exatamente)
```python
# deps.py
from app.core.deps import get_current_user, get_db
# get_current_user retorna User ORM object
# get_db retorna AsyncSession

# security.py
create_access_token(user_id: str, tenant_id: str, role: str) -> str
```

---

## TAREFA

### 1. requirements.txt — Adicionar após `pgvector==0.2.5`:
```
voyageai==0.2.3
anthropic==0.34.2
aiofiles==24.1.0
python-magic==0.4.27
PyPDF2==3.0.1
httpx==0.27.2
```
(httpx já existe, não duplicar)

---

### 2. app/core/config.py — Adicionar campos na classe Settings:
```python
# AI Services
ANTHROPIC_API_KEY: str = ""
VOYAGE_API_KEY: str = ""

# RAG Config
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 200
TOP_K_RESULTS: int = 5
EMBEDDING_DIMENSIONS: int = 1024
```

---

### 3. Migration — Alterar embedding de vector(1536) para vector(1024)
Criar migration `alembic revision --autogenerate -m "alter_embedding_dim_to_1024"`

No arquivo gerado, implementar manualmente:
```python
def upgrade() -> None:
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1024)")

def downgrade() -> None:
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536)")
```

Também atualizar `app/models/knowledge.py`:
- Linha `Vector(1536)` → `Vector(1024)`
- Atualizar comment: `"Vector embedding (1024 dimensions - Voyage AI voyage-2)"`

---

### 4. Criar `app/services/embedding_service.py`
```python
"""
EmbeddingService — Voyage AI voyage-2 (1024 dims)

Responsável por converter texto em vetores de embedding.
"""
import voyageai
from app.core.config import settings

class EmbeddingService:
    def __init__(self):
        self.client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        self.model = "voyage-2"
        self.dimensions = 1024

    async def embed_text(self, text: str) -> list[float]:
        """Embed single text. Returns list of 1024 floats."""
        result = self.client.embed([text], model=self.model, input_type="document")
        return result.embeddings[0]

    async def embed_query(self, query: str) -> list[float]:
        """Embed a query (search). Returns list of 1024 floats."""
        result = self.client.embed([query], model=self.model, input_type="query")
        return result.embeddings[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call."""
        result = self.client.embed(texts, model=self.model, input_type="document")
        return result.embeddings
```

---

### 5. Criar `app/services/ingest_service.py`
```python
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
        return result.scalars().all()

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
```

---

### 6. Criar `app/schemas/knowledge.py`
```python
import uuid
from datetime import datetime
from pydantic import BaseModel, HttpUrl
from typing import Optional
from app.models.knowledge import DocumentStatus


class IngestTextRequest(BaseModel):
    title: str
    content: str

class IngestURLRequest(BaseModel):
    url: str
    title: Optional[str] = None

class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    content_type: str
    status: DocumentStatus
    created_at: datetime
    chunk_count: int = 0

    class Config:
        from_attributes = True

class IngestResponse(BaseModel):
    document_id: uuid.UUID
    title: str
    status: DocumentStatus
    chunks_created: int
    message: str
```

---

### 7. Criar `app/api/v1/endpoints/knowledge.py`
Rotas AUTENTICADAS (requerem Bearer token + X-Tenant-ID header):

```
POST /api/v1/knowledge/ingest/text   → IngestTextRequest → IngestResponse
POST /api/v1/knowledge/ingest/url    → IngestURLRequest  → IngestResponse
GET  /api/v1/knowledge/sources       → list[DocumentResponse]
DELETE /api/v1/knowledge/sources/{id} → {"message": "Document deleted"}
```

Importações obrigatórias no endpoint:
```python
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.ingest_service import IngestService
from app.schemas.knowledge import IngestTextRequest, IngestURLRequest, IngestResponse, DocumentResponse
```

No endpoint POST ingest, retornar `IngestResponse` com `chunks_created = len(document.chunks)`.

---

### 8. Registrar em `app/api/v1/api.py`
Adicionar import e include_router:
```python
from app.api.v1.endpoints import auth, onboarding, knowledge

api_router.include_router(
    knowledge.router,
    prefix="/knowledge",
    tags=["Knowledge Base"]
)
```

---

## VALIDAÇÃO FINAL
Após implementar, executar:
```bash
cd backend
alembic upgrade head
python -c "from app.api.v1.endpoints.knowledge import router; print('✅ knowledge router OK')"
```

Verificar no /docs que os endpoints `/api/v1/knowledge/*` aparecem.
