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
        return list(result.scalars().all())

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
        return list(result.scalars().all())

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
