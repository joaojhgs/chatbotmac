"""Chat streaming routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest
from app.services.chat_service import ChatService

router = APIRouter()


def get_chat_service() -> ChatService:
    """Dependency to get chat service."""
    from app.main import chat_service

    if chat_service is None:
        raise HTTPException(
            status_code=503, detail="Chat service not initialized. Please check server logs."
        )
    return chat_service


@router.post("/chat")
async def chat_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Chat endpoint with Server-Sent Events (SSE) streaming.

    Args:
        request: ChatRequest with user message and optional conversation_id
        chat_service: Chat service instance (dependency injection)

    Returns:
        StreamingResponse with SSE format
    """
    conversation_id = None
    if request.conversation_id:
        try:
            conversation_id = UUID(request.conversation_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    return StreamingResponse(
        chat_service.stream_chat_response(message=request.message, conversation_id=conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )
