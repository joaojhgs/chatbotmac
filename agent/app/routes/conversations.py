"""Conversation management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.services.conversation_service import ConversationService

router = APIRouter()


def get_conversation_service() -> ConversationService:
    """Dependency to get conversation service."""
    from app.main import conversation_service

    if conversation_service is None:
        raise HTTPException(
            status_code=503, detail="Conversation service not initialized"
        )
    return conversation_service


@router.post("/conversations")
async def create_conversation(
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    Create a new conversation.

    Args:
        conversation_service: Conversation service instance (dependency injection)

    Returns:
        Conversation ID
    """
    conversation_id = conversation_service.create_conversation()
    return {"conversation_id": str(conversation_id)}


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    Get conversation history with messages and tool calls.

    Args:
        conversation_id: Conversation ID
        conversation_service: Conversation service instance (dependency injection)

    Returns:
        List of messages with tool calls
    """
    try:
        conv_id = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    history = conversation_service.get_conversation_history(conv_id, limit=100)

    return {
        "messages": [
            {
                "id": str(msg.message_id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "tool_calls": msg.tool_calls,
            }
            for msg in history
        ]
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    Delete a conversation and all associated messages.

    Args:
        conversation_id: Conversation ID to delete
        conversation_service: Conversation service instance (dependency injection)

    Returns:
        Success status
    """
    try:
        conv_id = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    conversation_service.delete_conversation(conv_id)
    return {"success": True}

