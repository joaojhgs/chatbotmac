"""Pydantic models for request/response schemas."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., description="User message")
    conversation_id: str | None = Field(None, description="Optional conversation ID for context")


class ChatResponse(BaseModel):
    """Chat response model (for non-streaming endpoints)."""

    response: str = Field(..., description="Agent response")
    sources: list[str] | None = Field(None, description="Sources used in the response")
