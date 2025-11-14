"""FastAPI application with SSE support for chat streaming."""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent import create_macbook_agent
from app.routes import chat, conversations, health, suggestions
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.suggestion_service import SuggestionService

# Load environment variables
load_dotenv()

# Global services (initialized at startup)
agent = None
conversation_service: ConversationService | None = None
chat_service: ChatService | None = None
suggestion_service: SuggestionService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global agent, conversation_service, chat_service, suggestion_service

    # Startup
    try:
        agent = create_macbook_agent()
        conversation_service = ConversationService()
        chat_service = ChatService(agent, conversation_service)
        suggestion_service = SuggestionService()
        print("Agent and services initialized successfully")
    except Exception as e:
        print(f"Error initializing services: {e!s}")
        raise

    yield

    # Shutdown (if needed)
    pass


app = FastAPI(
    title="MacBook Air Chatbot API",
    description="Chatbot agent specialized in MacBook Air questions with RAG and web search",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(suggestions.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
