"""Health check and root routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "MacBook Air Chatbot API",
        "version": "1.0.0",
        "endpoints": {"chat": "/chat (POST) - Stream chat responses via SSE"},
    }


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status
    """
    from app.main import agent

    return {"status": "healthy", "agent_initialized": agent is not None}

