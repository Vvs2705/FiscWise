"""
Chat Endpoints for ContaFlow

Handles chat sessions and messages with RAG-enhanced responses.
All routes require authentication and tenant isolation.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.rag_service import RAGService
from app.services.chat_service import ChatService
from app.schemas.chat import (
    CreateSessionRequest,
    SessionResponse,
    ChatMessageRequest,
    MessageResponse
)


router = APIRouter()


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED, summary="Create Chat Session")
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """
    Create a new chat session for the current tenant.
    
    Args:
        request: Session creation request with optional title
        current_user: Authenticated user
        db: Database session
        
    Returns:
        SessionResponse: Created session data
    """
    rag_service = RAGService(db)
    chat_service = ChatService(db=db, rag_service=rag_service, redis_client=None)
    
    session = await chat_service.create_session(
        tenant_id=current_user.tenant_id,
        title=request.title
    )
    
    return SessionResponse.model_validate(session)


@router.get("/sessions", response_model=list[SessionResponse], summary="List Chat Sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[SessionResponse]:
    """
    List all chat sessions for the current tenant.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        list[SessionResponse]: List of chat sessions
    """
    rag_service = RAGService(db)
    chat_service = ChatService(db=db, rag_service=rag_service, redis_client=None)
    
    sessions = await chat_service.get_sessions(current_user.tenant_id)
    
    return [SessionResponse.model_validate(session) for session in sessions]


@router.post("/sessions/{session_id}/messages", summary="Send Chat Message (SSE Streaming)")
async def send_message(
    session_id: uuid.UUID,
    body: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message to a chat session and receive streaming response.
    
    Returns Server-Sent Events (SSE) stream with the AI response.
    
    SSE Format:
        data: <text_token>\\n\\n
        data: [DONE]\\n\\n
    
    Args:
        session_id: UUID of the chat session
        body: Message request with text content
        current_user: Authenticated user
        db: Database session
        
    Returns:
        StreamingResponse: SSE stream with AI response
    """
    rag_service = RAGService(db)
    chat_service = ChatService(db=db, rag_service=rag_service, redis_client=None)
    
    return StreamingResponse(
        chat_service.stream_response(
            session_id=session_id,
            tenant_id=current_user.tenant_id,
            message=body.message
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse], summary="Get Chat History")
async def get_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[MessageResponse]:
    """
    Get all messages from a chat session.
    
    Returns the complete conversation history for the session.
    
    Args:
        session_id: UUID of the chat session
        current_user: Authenticated user
        db: Database session
        
    Returns:
        list[MessageResponse]: List of messages in chronological order
    """
    rag_service = RAGService(db)
    chat_service = ChatService(db=db, rag_service=rag_service, redis_client=None)
    
    messages = await chat_service.get_messages(session_id, current_user.tenant_id)
    
    return [MessageResponse.model_validate(msg) for msg in messages]
