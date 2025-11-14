"""Suggestion generation routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.services.conversation_service import ConversationService
from app.services.suggestion_service import SuggestionService

router = APIRouter()


def get_conversation_service() -> ConversationService | None:
    """Dependency to get conversation service."""
    from app.main import conversation_service

    return conversation_service


def get_suggestion_service() -> SuggestionService:
    """Dependency to get suggestion service."""
    from app.main import suggestion_service

    if suggestion_service is None:
        return SuggestionService()  # Can create on-demand
    return suggestion_service


@router.get("/conversations/{conversation_id}/suggestions")
async def get_suggestions(
    conversation_id: str,
    conversation_service: ConversationService | None = Depends(get_conversation_service),
    suggestion_service: SuggestionService = Depends(get_suggestion_service),
):
    """
    Get prompt suggestions based on conversation history.
    Uses LLM to generate suggestions if conversation has history, otherwise returns defaults.

    Args:
        conversation_id: Conversation ID
        conversation_service: Conversation service instance (dependency injection)
        suggestion_service: Suggestion service instance (dependency injection)

    Returns:
        List of prompt suggestions
    """
    # Return defaults if conversation service not initialized
    if conversation_service is None:
        return {"suggestions": suggestion_service.get_default_suggestions()}

    try:
        conv_id = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    # Get last 3 messages for context
    history = conversation_service.get_conversation_history(conv_id, limit=3)

    # Generate suggestions using the service
    suggestions = await suggestion_service.generate_suggestions(history)

    return {"suggestions": suggestions}
