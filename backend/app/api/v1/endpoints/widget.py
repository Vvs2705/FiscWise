"""
Widget Endpoints for ContaFlow

Public embeddable chat widget — no authentication required.
Tenant is identified by tenant_id in the URL path.

Routes:
  GET  /api/v1/widget/{tenant_id}.js           → JS snippet (text/javascript)
  GET  /api/v1/widget/{tenant_id}/chat         → Chat UI (text/html)
  POST /api/v1/widget/{tenant_id}/chat/message → SSE streaming response
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import get_db
from app.models.tenant import Tenant
from app.models.chat import ChatSession
from app.schemas.widget import WidgetMessageRequest
from app.services.rag_service import RAGService
from app.services.chat_service import ChatService


router = APIRouter()


@router.get("/{tenant_id}.js", tags=["Widget"])
async def widget_script(tenant_id: uuid.UUID):
    """
    Returns the embeddable JavaScript widget snippet.
    Clients add this to their website: <script src=".../{tenant_id}.js"></script>
    """
    widget_url = f"{settings.PUBLIC_URL}/api/v1/widget/{tenant_id}/chat"
    script = f"""(function() {{
  if (document.getElementById('contaflow-widget')) return;
  var iframe = document.createElement('iframe');
  iframe.src = '{widget_url}';
  iframe.id = 'contaflow-widget';
  iframe.style.cssText = 'position:fixed;bottom:20px;right:20px;width:380px;height:520px;border:none;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.18);z-index:99999;display:block;';
  iframe.allow = 'clipboard-write';
  document.body.appendChild(iframe);
}})();"""
    return Response(content=script, media_type="text/javascript")


@router.get("/{tenant_id}/chat", response_class=HTMLResponse, tags=["Widget"])
async def widget_chat_ui(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns the HTML chat interface for the widget iframe.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    api_url = f"{settings.PUBLIC_URL}/api/v1/widget/{tenant_id}/chat/message"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Chat — {tenant.name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
      background: #f8f9fa;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    #header {{
      background: #2563eb;
      color: white;
      padding: 14px 16px;
      font-size: 15px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    #header .dot {{
      width: 8px; height: 8px;
      background: #4ade80;
      border-radius: 50%;
    }}
    #messages {{
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .msg {{
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.5;
      word-break: break-word;
    }}
    .msg.user {{
      background: #2563eb;
      color: white;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }}
    .msg.bot {{
      background: white;
      color: #1f2937;
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .msg.bot.typing {{
      color: #9ca3af;
      font-style: italic;
    }}
    #input-area {{
      padding: 12px 16px;
      background: white;
      border-top: 1px solid #e5e7eb;
      display: flex;
      gap: 8px;
    }}
    #msg-input {{
      flex: 1;
      padding: 10px 14px;
      border: 1px solid #d1d5db;
      border-radius: 24px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }}
    #msg-input:focus {{ border-color: #2563eb; }}
    #send-btn {{
      background: #2563eb;
      color: white;
      border: none;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      transition: background 0.2s;
    }}
    #send-btn:hover {{ background: #1d4ed8; }}
    #send-btn:disabled {{ background: #93c5fd; cursor: not-allowed; }}
    .welcome {{
      text-align: center;
      color: #6b7280;
      font-size: 13px;
      margin-top: 20px;
    }}
  </style>
</head>
<body>
  <div id="header">
    <div class="dot"></div>
    {tenant.name} — Assistente IA
  </div>
  <div id="messages">
    <p class="welcome">Olá! Como posso ajudar você hoje?</p>
  </div>
  <div id="input-area">
    <input id="msg-input" type="text" placeholder="Digite sua mensagem..." autocomplete="off" />
    <button id="send-btn">&#10148;</button>
  </div>
  <script>
    const messagesDiv = document.getElementById('messages');
    const input = document.getElementById('msg-input');
    const sendBtn = document.getElementById('send-btn');
    let sessionId = localStorage.getItem('contaflow_session_id') || crypto.randomUUID();
    localStorage.setItem('contaflow_session_id', sessionId);

    function addMessage(text, isUser) {{
      const msg = document.createElement('div');
      msg.className = 'msg ' + (isUser ? 'user' : 'bot');
      msg.textContent = text;
      messagesDiv.appendChild(msg);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
      return msg;
    }}

    async function sendMessage() {{
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      sendBtn.disabled = true;

      addMessage(text, true);
      const botMsg = addMessage('Digitando...', false);
      botMsg.classList.add('typing');

      try {{
        const response = await fetch('{api_url}', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ message: text, session_id: sessionId }})
        }});

        if (!response.ok) throw new Error('Erro na resposta');
        if (!response.body) throw new Error('Sem corpo de resposta');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        botMsg.textContent = '';
        botMsg.classList.remove('typing');

        while (true) {{
          const {{ done, value }} = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, {{ stream: true }});
          const lines = chunk.split('\\n');
          for (const line of lines) {{
            if (line.startsWith('data: ')) {{
              const token = line.slice(6);
              if (token.trim() === '[DONE]') break;
              fullText += token;
              botMsg.textContent = fullText;
              messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }}
          }}
        }}
      }} catch (err) {{
        botMsg.textContent = 'Erro ao processar mensagem. Tente novamente.';
        botMsg.classList.remove('typing');
      }} finally {{
        sendBtn.disabled = false;
        input.focus();
      }}
    }}

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {{
      if (e.key === 'Enter') sendMessage();
    }});
    input.focus();
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/{tenant_id}/chat/message", tags=["Widget"])
async def widget_chat_message(
    tenant_id: uuid.UUID,
    request: WidgetMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Handles chat messages from the widget (SSE streaming).
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Auto-create session if it doesn't exist (widget generates session_id client-side)
    session_uuid = uuid.UUID(request.session_id)
    existing = await db.execute(select(ChatSession).where(ChatSession.id == session_uuid))
    if not existing.scalar_one_or_none():
        db.add(ChatSession(id=session_uuid, tenant_id=tenant_id, title="Widget Chat"))
        await db.commit()

    rag_service = RAGService(db)
    chat_service = ChatService(db=db, rag_service=rag_service)

    async def event_generator():
        async for chunk in chat_service.stream_response(
            session_id=session_uuid,
            tenant_id=tenant_id,
            message=request.message,
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
