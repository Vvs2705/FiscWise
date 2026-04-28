# FASE 08 — Analytics API

## PRÉ-REQUISITO
Fase 07 concluída: tabelas `chat_sessions`, `chat_messages`, `token_usage_logs` operacionais.

## CONTEXTO DO PROJETO
Stack: FastAPI + SQLAlchemy 2.0 async + PostgreSQL
Deploy: Railway

## REGRAS ABSOLUTAS
1. SEMPRE usar `from app.core.deps import get_current_user, get_db`
2. Todos os endpoints são AUTENTICADOS (Bearer + X-Tenant-ID)
3. Queries usam `current_user.tenant_id` para isolamento multi-tenant

---

## TAREFA

### 1. Criar `app/schemas/analytics.py`
```python
from pydantic import BaseModel
from typing import Optional
from datetime import date

class UsageSummaryResponse(BaseModel):
    period_days: int
    total_sessions: int
    total_messages: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_documents: int
    total_chunks: int

class DailyUsageItem(BaseModel):
    date: date
    sessions: int
    messages: int
    tokens: int

class DailyUsageResponse(BaseModel):
    period_days: int
    daily: list[DailyUsageItem]

class ChatStatsResponse(BaseModel):
    total_sessions: int
    total_messages: int
    avg_messages_per_session: float
    avg_tokens_per_message: float

class KnowledgeStatsResponse(BaseModel):
    total_documents: int
    processed_documents: int
    failed_documents: int
    total_chunks: int
    avg_chunks_per_document: float
```

---

### 2. Criar `app/api/v1/endpoints/analytics.py`
Rotas AUTENTICADAS:

```
GET /api/v1/analytics/usage              → UsageSummaryResponse  (últimos 30 dias)
GET /api/v1/analytics/usage/daily        → DailyUsageResponse    (breakdown diário, últimos 30 dias)
GET /api/v1/analytics/chat-stats         → ChatStatsResponse
GET /api/v1/analytics/knowledge-stats    → KnowledgeStatsResponse
```

Imports obrigatórios:
```python
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage, TokenUsageLog
from app.models.knowledge import Document, DocumentChunk, DocumentStatus
from app.schemas.analytics import (
    UsageSummaryResponse, DailyUsageResponse, DailyUsageItem,
    ChatStatsResponse, KnowledgeStatsResponse
)
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
```

**GET /usage** — usar SQLAlchemy aggregate queries:
- `select(func.count(ChatSession.id))` filtrado por `tenant_id` e `created_at >= (now - 30 days)`
- `select(func.sum(TokenUsageLog.input_tokens), func.sum(TokenUsageLog.output_tokens))` filtrado por `tenant_id`
- `select(func.count(Document.id))`, `select(func.count(DocumentChunk.id))` via JOIN

**GET /usage/daily** — agrupar por `func.date(ChatMessage.created_at)` nos últimos 30 dias.

**GET /chat-stats** — calcular `avg_messages_per_session = total_messages / total_sessions` (handle division by zero → 0.0).

**GET /knowledge-stats** — `func.count` filtrado por `DocumentStatus.PROCESSED`, `DocumentStatus.FAILED`, e total chunks.

---

### 3. Registrar em `app/api/v1/api.py`
```python
from app.api.v1.endpoints import auth, onboarding, knowledge, chat, analytics

api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
```

---

## VALIDAÇÃO FINAL
```bash
python -c "from app.api.v1.endpoints.analytics import router; print('✅ analytics router OK')"
```
Verificar `/docs` que endpoints `/api/v1/analytics/*` aparecem.
