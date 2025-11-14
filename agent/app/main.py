"""FastAPI application with SSE support for chat streaming."""

import json

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agent import create_macbook_agent
from app.models.schemas import ChatRequest

# Load environment variables
load_dotenv()

app = FastAPI(
    title="MacBook Air Chatbot API",
    description="Chatbot agent specialized in MacBook Air questions with RAG and web search",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize agent (can be done at startup for better performance)
agent = None


@app.on_event("startup")
async def startup_event():
    """Initialize the agent on application startup."""
    global agent
    try:
        agent = create_macbook_agent()
        print("Agent initialized successfully")
    except Exception as e:
        print(f"Error initializing agent: {e!s}")
        raise


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "MacBook Air Chatbot API",
        "version": "1.0.0",
        "endpoints": {"chat": "/chat (POST) - Stream chat responses via SSE"},
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent_initialized": agent is not None}


@app.post("/chat")
async def chat_stream(request: ChatRequest):
    """
    Chat endpoint with Server-Sent Events (SSE) streaming.

    Args:
        request: ChatRequest with user message

    Returns:
        StreamingResponse with SSE format
    """
    if agent is None:
        raise HTTPException(
            status_code=503, detail="Agent not initialized. Please check server logs."
        )

    async def generate_response():
        """Generator function for SSE streaming."""
        try:
            # Use astream_events for better streaming granularity
            full_response = ""
            async for event in agent.astream_events({"input": request.message}, version="v2"):
                event_type = event.get("event")
                name = event.get("name", "")

                # Handle LLM token streaming
                if event_type == "on_chat_model_stream" and name == "ChatOpenAI":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        if content:
                            data = {"type": "content_delta", "content": content}
                            yield f"data: {json.dumps(data)}\n\n"
                            full_response += content

                # Handle tool calls
                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    tool_input = event.get("data", {}).get("input", {})
                    tool_data = {"type": "tool_call", "tool": tool_name, "input": tool_input}
                    yield f"data: {json.dumps(tool_data)}\n\n"

                # Handle tool results
                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    output = event.get("data", {}).get("output", "")
                    tool_result_data = {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": str(output)[:500],
                    }
                    yield f"data: {json.dumps(tool_result_data)}\n\n"

                # Handle final agent output
                elif event_type == "on_chain_end" and name == "AgentExecutor":
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict) and "output" in output:
                        final_output = output["output"]
                        if final_output and final_output != full_response:
                            # Send any remaining content
                            remaining = final_output[len(full_response) :]
                            if remaining:
                                data = {"type": "content_delta", "content": remaining}
                                yield f"data: {json.dumps(data)}\n\n"
                                full_response = final_output

            # Send final complete response
            if full_response:
                data = {"type": "content", "content": full_response}
                yield f"data: {json.dumps(data)}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            import traceback

            error_data = {"type": "error", "message": str(e), "traceback": traceback.format_exc()}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
