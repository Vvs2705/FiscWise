"""
Pydantic schemas for the WhatsApp integration.
"""

import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class WhatsAppMessageOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    inbox_id: uuid.UUID
    direction: str
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    message_type: str
    body: Optional[str] = None
    media_url: Optional[str] = None
    external_message_id: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class WhatsAppInboxOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID] = None
    phone_number: str
    customer_name: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    unread_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SendWhatsAppRequest(BaseModel):
    body: str = Field(..., description="Corpo do texto da mensagem")
    media_url: Optional[str] = Field(None, description="URL opcional de arquivo anexo")
    message_type: str = Field("text", description="text | document | image")


class LinkInboxRequest(BaseModel):
    client_id: Optional[uuid.UUID] = Field(None, description="ID do Cliente a vincular (NULL para desvincular)")


class ConvertTaskRequest(BaseModel):
    title: str = Field(..., max_length=255, description="Título da tarefa")
    due_date: date = Field(..., description="Prazo de entrega da tarefa")
    priority: str = Field("medium", description="Priority level: low | medium | high")


class WhatsAppWebhookPayload(BaseModel):
    """
    Simula uma carga útil (payload) recebida de Evolution API ou Zapi.
    """
    sender_phone: str = Field(..., description="Telefone do remetente (ex: +5511999999999)")
    sender_name: Optional[str] = Field(None, description="Nome do remetente")
    body: str = Field(..., description="Mensagem de texto ou descrição de anexo")
    message_type: str = Field("text", description="text | document | image | audio")
    media_url: Optional[str] = Field(None, description="URL do arquivo de mídia associado")
    external_message_id: Optional[str] = Field(None, description="ID único do gateway")
