"""
Widget Schemas for ContaFlow

Pydantic models for the embeddable chat widget API.
"""

from pydantic import BaseModel


class WidgetMessageRequest(BaseModel):
    """Request body for widget chat message."""
    message: str
    session_id: str  # UUID string generated in frontend, maintains local history


class WidgetMessageResponse(BaseModel):
    """Response body for widget chat message (non-streaming fallback)."""
    response: str
    session_id: str
