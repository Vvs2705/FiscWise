# FASE 07 — Chat Service: Claude + SSE Streaming + Sessions API

## PRÉ-REQUISITO
Fase 06 concluída: `voyageai`, `anthropic`, EmbeddingService, IngestService e tabela `document_chunks` com `vector(1024)` operacionais.

## CONTEXTO DO PROJETO
Stack: FastAPI + SQLAlchemy 2.0 async + PostgreSQL + pgvector + Redis + Anthropic Claude
Deploy: Railway (auto-deploy no push para main)

## REGRAS ABSOLUTAS
1. SEMPRE usar `from app.core.deps import get_current_user, get_db`
2. ChatService usa 3 parâmetros: `ChatService(db: AsyncSession, rag_service: RAGService, redis_client)`
3. Método de streaming: `stream_response()` — NÃO `generate_response()`
4. SSE: usar `StreamingResponse` com `media_type="text/event-stream"`

---

## TAREFA

### 1. Criar `app/models/chat.py`
Modelos:
- `ChatSession(Base, TenantBase)` — campos: `title: str(200)`, `message_count: int default 0`
- `ChatMessage(Base)` — campos: `id UUID PK`, `session_id UUID FK(chat_sessions.id CASCADE)`, `role: str(20)` (user/assistant), `content: Text`, `tokens_used: int default 0`, `created_at DateTime`
- `TokenUsageLog(Base, TenantBase)` — campos: `input_tokens: int`, `output_tokens: int`, `model: str(100)`, `endpoint: str(100)`

Exportar os 3 modelos em `app/models/__init__.py`.

Criar migration: `alembic revision --autogenerate -m "add_chat_tables"`

---

### 2. Criar `app/services/rag_service.py`
```python
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
```

---

### 3. Criar `app/services/chat_service.py`
```python
"""
ChatService — Anthropic Claude + RAG + SSE Streaming

Método principal: stream_response() — retorna AsyncGenerator para SSE.
"""
import uuid
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import anthropic

from app.core.config import settings
from app.models.chat import ChatSession, ChatMessage, TokenUsageLog
from app.services.rag_service import RAGService


class ChatService:
    def __init__(self, db: AsyncSession, rag_service: RAGService, redis_client=None):
        self.db = db
        self.rag_service = rag_service
        self.redis_client = redis_client
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-haiku-20241022"

    async def create_session(self, tenant_id: uuid.UUID, title: str = "Nova conversa") -> ChatSession:
        session = ChatSession(id=uuid.uuid4(), tenant_id=tenant_id, title=title)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_sessions(self, tenant_id: uuid.UUID) -> list[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.tenant_id == tenant_id)
            .order_by(ChatSession.created_at.desc())
        )
        return result.scalars().all()

    async def get_messages(self, session_id: uuid.UUID, tenant_id: uuid.UUID) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .join(ChatSession)
            .where(
                ChatMessage.session_id == session_id,
                ChatSession.tenant_id == tenant_id
            )
            .order_by(ChatMessage.created_at.asc())
        )
        return result.scalars().all()

    async def stream_response(
        self,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        message: str
    ) -> AsyncGenerator[str, None]:
        """
        Main method: RAG search → Claude streaming → save to DB → yield SSE events.
        
        SSE format:
          data: <token>\n\n
          data: [DONE]\n\n
        """
        # 1. Get context from RAG
        context_chunks = await self.rag_service.search(tenant_id=tenant_id, query=message)
        context = "\n\n".join(context_chunks) if context_chunks else ""

        # 2. Get conversation history (last 10 messages)
        history = await self.get_messages(session_id, tenant_id)
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in history[-10:]
        ]
        messages.append({"role": "user", "content": message})

        # 3. Build system prompt
        system_prompt = (
            "Você é um assistente inteligente. Responda em português brasileiro.\n"
            "Use o contexto abaixo quando relevante para responder às perguntas.\n\n"
            f"CONTEXTO:\n{context}"
            if context else
            "Você é um assistente inteligente. Responda em português brasileiro."
        )

        # 4. Save user message to DB
        user_msg = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role="user",
            content=message
        )
        self.db.add(user_msg)
        await self.db.flush()

        # 5. Stream Claude response
        full_response = ""
        input_tokens = 0
        output_tokens = 0

        with self.client.messages.stream(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield f"data: {text}\n\n"

            usage = stream.get_final_message().usage
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens

        # 6. Save assistant message to DB
        assistant_msg = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role="assistant",
            content=full_response,
            tokens_used=output_tokens
        )
        self.db.add(assistant_msg)

        # 7. Log token usage
        token_log = TokenUsageLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
            endpoint="chat"
        )
        self.db.add(token_log)
        await self.db.commit()

        yield "data: [DONE]\n\n"
```

---

### 4. Criar `app/schemas/chat.py`
```python
import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "Nova conversa"

class SessionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    message_count: int
    created_at: datetime
    class Config:
        from_attributes = True

class ChatMessageRequest(BaseModel):
    message: str

class MessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    tokens_used: int
    created_at: datetime
    class Config:
        from_attributes = True
```

---

### 5. Criar `app/api/v1/endpoints/chat.py`
Rotas AUTENTICADAS (Bearer token + X-Tenant-ID):

```
POST /api/v1/chat/sessions                           → SessionResponse
GET  /api/v1/chat/sessions                           → list[SessionResponse]
POST /api/v1/chat/sessions/{session_id}/messages     → StreamingResponse (SSE)
GET  /api/v1/chat/sessions/{session_id}/messages     → list[MessageResponse]
```

O endpoint POST messages deve retornar `StreamingResponse`:
```python
from fastapi.responses import StreamingResponse

@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    body: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    rag_service = RAGService(db)
    chat_service = ChatService(db=db, rag_service=rag_service, redis_client=None)
    
    return StreamingResponse(
        chat_service.stream_response(
            session_id=session_id,
            tenant_id=current_user.tenant_id,
            message=body.message
        ),
        media_type="text/event-stream"
    )
```

---

### 6. Registrar em `app/api/v1/api.py`
```python
from app.api.v1.endpoints import auth, onboarding, knowledge, chat

api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
```

---

## VALIDAÇÃO FINAL
```bash
cd backend
alembic upgrade head
python -c "from app.services.chat_service import ChatService; print('✅ ChatService OK')"
python -c "from app.api.v1.endpoints.chat import router; print('✅ chat router OK')"
```

Verificar `/docs` que endpoints `/api/v1/chat/*` aparecem.
