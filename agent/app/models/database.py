"""Database models for conversations and messages."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class Conversation(BaseModel):
    """Conversation model."""

    id: UUID = Field(..., description="Conversation ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class Message(BaseModel):
    """Message model."""

    id: UUID = Field(..., description="Message ID")
    conversation_id: UUID = Field(..., description="Conversation ID")
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Creation timestamp")


class ToolCall(BaseModel):
    """Tool call model."""

    id: UUID = Field(..., description="Tool call ID")
    message_id: UUID = Field(..., description="Associated message ID")
    tool_name: str = Field(..., description="Tool name")
    input: dict[str, Any] = Field(default_factory=dict, description="Tool input")
    result: str | None = Field(None, description="Tool result")
    created_at: datetime = Field(..., description="Creation timestamp")


class MessageWithToolCalls(BaseModel):
    """Message with associated tool calls."""

    message_id: UUID
    role: str
    content: str
    created_at: datetime
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
