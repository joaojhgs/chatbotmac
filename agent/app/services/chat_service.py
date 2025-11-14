"""Service for handling chat streaming and agent interactions."""

import json
import traceback
from uuid import UUID

from langchain.agents import AgentExecutor
from app.models.database import MessageWithToolCalls
from app.services.conversation_service import ConversationService
from app.utils.message_formatter import format_history_for_agent


class ChatService:
    """Service for chat streaming operations."""

    def __init__(
        self,
        agent: AgentExecutor,
        conversation_service: ConversationService,
    ):
        """
        Initialize the chat service.

        Args:
            agent: LangChain agent executor
            conversation_service: Conversation service instance
        """
        self.agent = agent
        self.conversation_service = conversation_service

    async def stream_chat_response(self, message: str, conversation_id: UUID | None = None):
        """
        Stream chat response using SSE.

        Args:
            message: User message
            conversation_id: Optional conversation ID

        Yields:
            SSE formatted strings
        """
        # Get or create conversation ID
        if conversation_id:
            # Ensure conversation exists, create if it doesn't
            conversation_id = self.conversation_service.create_conversation(conversation_id)
        else:
            conversation_id = self.conversation_service.create_conversation()

        # Save user message
        self.conversation_service.save_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
        )

        # Get conversation history (last 2-3 messages for context)
        history = self.conversation_service.get_conversation_history(
            conversation_id=conversation_id, limit=3
        )
        chat_history = format_history_for_agent(history)

        # Track tool calls for this message
        tool_calls_data: list[dict] = []

        try:
            # Send conversation_id in the stream
            yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': str(conversation_id)})}\n\n"

            # Use astream_events for better streaming granularity
            full_response = ""
            assistant_message_id: UUID | None = None

            # Prepare agent input with chat history
            agent_input = {
                "input": message,
                "chat_history": chat_history,
            }

            async for event in self.agent.astream_events(agent_input, version="v2"):
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
                    tool_data = {
                        "type": "tool_call",
                        "tool": tool_name,
                        "input": tool_input,
                    }
                    tool_calls_data.append(
                        {"tool_name": tool_name, "input": tool_input, "result": None}
                    )
                    yield f"data: {json.dumps(tool_data)}\n\n"

                # Handle tool results
                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    output = event.get("data", {}).get("output", "")
                    tool_result_str = str(output)[:500]
                    tool_result_data = {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": tool_result_str,
                    }
                    # Update tool call data
                    for tc in tool_calls_data:
                        if tc["tool_name"] == tool_name and tc["result"] is None:
                            tc["result"] = tool_result_str
                            break
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

            # Save assistant message and tool calls to database
            if full_response:
                assistant_message_id = self.conversation_service.save_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                )

                # Save tool calls
                if assistant_message_id and tool_calls_data:
                    for tool_call in tool_calls_data:
                        self.conversation_service.save_tool_call(
                            message_id=assistant_message_id,
                            tool_name=tool_call["tool_name"],
                            input_data=tool_call["input"],
                            result=tool_call["result"],
                        )

            # Send completion event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_data = {
                "type": "error",
                "message": str(e),
                "traceback": traceback.format_exc(),
            }
            yield f"data: {json.dumps(error_data)}\n\n"
