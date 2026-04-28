# FASE 09 — Widget Embeddable (JS + HTML + Chat Público)

## PRÉ-REQUISITO
Fase 07 concluída: ChatService e RAGService operacionais.

## CONTEXTO DO PROJETO
Stack: FastAPI + SQLAlchemy 2.0 async + PostgreSQL
Deploy: Railway

## REGRAS ABSOLUTAS
1. Rotas do widget são PÚBLICAS — adicionar `/api/v1/widget` em `_EXCLUDED_PREFIXES` no `app/core/middleware.py`
2. Chat do widget NÃO cria ChatSession nem usa JWT — é sessão anônima com session_id gerado no frontend
3. Tenant identificado pelo `tenant_id` na URL path (não header)

---

## TAREFA

### 1. Atualizar `app/core/middleware.py`
Adicionar em `_EXCLUDED_PREFIXES`:
```python
"/api/v1/widget",
```

---

### 2. Criar `app/schemas/widget.py`
```python
from pydantic import BaseModel
import uuid

class WidgetMessageRequest(BaseModel):
    message: str
    session_id: str  # UUID gerado no frontend, mantém histórico local

class WidgetMessageResponse(BaseModel):
    response: str
    session_id: str
```

---

### 3. Criar `app/api/v1/endpoints/widget.py`
Rotas PÚBLICAS (sem autenticação):

```
GET  /api/v1/widget/{tenant_id}.js           → JavaScript snippet (text/javascript)
GET  /api/v1/widget/{tenant_id}/chat         → HTML interface (text/html)
POST /api/v1/widget/{tenant_id}/chat/message → StreamingResponse SSE
```

**GET /{tenant_id}.js** — retornar `Response` com `media_type="text/javascript"`:
```javascript
// Widget script — injeta iframe flutuante no site do cliente
(function() {
  var iframe = document.createElement('iframe');
  iframe.src = 'WIDGET_BASE_URL/api/v1/widget/TENANT_ID/chat';
  iframe.style.cssText = 'position:fixed;bottom:20px;right:20px;width:380px;height:500px;border:none;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.18);z-index:99999;';
  iframe.id = 'contaflow-widget';
  document.body.appendChild(iframe);
})();
```
Substituir `WIDGET_BASE_URL` com `settings.PUBLIC_URL` (adicionar ao config.py: `PUBLIC_URL: str = "https://solo-os-api-production.up.railway.app"`).
Substituir `TENANT_ID` com o `tenant_id` da URL.

**GET /{tenant_id}/chat** — retornar `HTMLResponse` com interface de chat completa:
- Caixa de mensagens com histórico
- Input de texto + botão enviar
- JavaScript que faz `fetch` para `POST /api/v1/widget/{tenant_id}/chat/message`
- Parseia SSE: ler `data:` tokens e concatenar na tela em tempo real
- Design limpo: branco/cinza, fonte Arial, mobile-friendly
- session_id gerado com `crypto.randomUUID()` e armazenado em `sessionStorage`

**POST /{tenant_id}/chat/message** — StreamingResponse SSE:
```python
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from app.models.tenant import Tenant
from app.services.rag_service import RAGService
from app.services.chat_service import ChatService

@router.post("/{tenant_id}/chat/message")
async def widget_chat(
    tenant_id: uuid.UUID,
    body: WidgetMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    # Validate tenant exists
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Use anonymous session — create ephemeral session for this request
    rag_service = RAGService(db)
    chat_service = ChatService(db=db, rag_service=rag_service, redis_client=None)
    
    # Create or get session for widget
    sessions = await chat_service.get_sessions(tenant_id)
    # Find session by title matching session_id (widget uses session_id as title)
    session = next((s for s in sessions if s.title == f"widget:{body.session_id}"), None)
    if not session:
        session = await chat_service.create_session(
            tenant_id=tenant_id,
            title=f"widget:{body.session_id}"
        )

    return StreamingResponse(
        chat_service.stream_response(
            session_id=session.id,
            tenant_id=tenant_id,
            message=body.message
        ),
        media_type="text/event-stream"
    )
```

---

### 4. Registrar em `app/api/v1/api.py`
```python
from app.api.v1.endpoints import auth, onboarding, knowledge, chat, analytics, widget

api_router.include_router(widget.router, prefix="/widget", tags=["Widget"])
```

---

### 5. Adicionar ao `app/core/config.py`
```python
PUBLIC_URL: str = "https://solo-os-api-production.up.railway.app"
```

---

## VALIDAÇÃO FINAL
```bash
python -c "from app.api.v1.endpoints.widget import router; print('✅ widget router OK')"
```
Testar no browser: `GET /api/v1/widget/{tenant_id}/chat` deve retornar página HTML do chat.
