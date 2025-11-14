"""Service for handling chat streaming and agent interactions."""

import asyncio
import json
import traceback
from uuid import UUID
from collections.abc import AsyncIterator

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

    async def stream_chat_response(
        self, message: str, conversation_id: UUID | None = None
    ):
        """
        Stream chat response using SSE.
        Ensures final message is saved even if client disconnects.

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
        
        # Use a queue to pass events from background task to generator
        event_queue = asyncio.Queue()
        SAVE_INTERVAL = 100  # Save every 100 characters to ensure persistence

        async def process_agent_stream():
            """Process agent stream in background - continues even if generator stops."""
            full_response = ""
            assistant_message_id = None
            last_save_length = 0
            # Track which tool calls have been saved to prevent duplicates
            saved_tool_call_ids: set[str] = set()
            
            try:
                # Prepare agent input with chat history
                agent_input = {
                    "input": message,
                    "chat_history": chat_history,
                }

                # Process agent events completely, regardless of client connection
                async for event in self.agent.astream_events(agent_input, version="v2"):
                    event_type = event.get("event")
                    name = event.get("name", "")

                    # Handle LLM token streaming
                    if event_type == "on_chat_model_stream" and name == "ChatOpenAI":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            content = chunk.content
                            if content:
                                full_response += content
                                
                                # Put event in queue for generator to yield
                                # If queue is full or closed, continue processing (background task continues)
                                try:
                                    await event_queue.put({
                                        "type": "content_delta",
                                        "content": content
                                    })
                                except Exception:
                                    pass
                                
                                # Save message incrementally
                                if assistant_message_id is None:
                                    assistant_message_id = self.conversation_service.save_message(
                                        conversation_id=conversation_id,
                                        role="assistant",
                                        content=full_response,
                                    )
                                    # Save any tool calls that have been completed so far
                                    if assistant_message_id and tool_calls_data:
                                        for tool_call in tool_calls_data:
                                            # Only save if it has a result (completed) and hasn't been saved yet
                                            tool_call_id = f"{tool_call['tool_name']}_{hash(str(tool_call.get('input', {})))}"
                                            if tool_call.get("result") is not None and tool_call_id not in saved_tool_call_ids:
                                                try:
                                                    self.conversation_service.save_tool_call(
                                                        message_id=assistant_message_id,
                                                        tool_name=tool_call["tool_name"],
                                                        input_data=tool_call["input"],
                                                        result=tool_call["result"],
                                                    )
                                                    saved_tool_call_ids.add(tool_call_id)
                                                except Exception:
                                                    pass  # Tool call might already be saved
                                elif len(full_response) - last_save_length >= SAVE_INTERVAL:
                                    self.conversation_service.save_message(
                                        conversation_id=conversation_id,
                                        role="assistant",
                                        content=full_response,
                                        message_id=assistant_message_id,
                                    )
                                    last_save_length = len(full_response)
                                    # Save any new tool calls that have been completed
                                    if assistant_message_id and tool_calls_data:
                                        for tool_call in tool_calls_data:
                                            # Only save if it has a result (completed) and hasn't been saved yet
                                            tool_call_id = f"{tool_call['tool_name']}_{hash(str(tool_call.get('input', {})))}"
                                            if tool_call.get("result") is not None and tool_call_id not in saved_tool_call_ids:
                                                try:
                                                    self.conversation_service.save_tool_call(
                                                        message_id=assistant_message_id,
                                                        tool_name=tool_call["tool_name"],
                                                        input_data=tool_call["input"],
                                                        result=tool_call["result"],
                                                    )
                                                    saved_tool_call_ids.add(tool_call_id)
                                                except Exception:
                                                    pass  # Tool call might already be saved

                    # Handle tool calls
                    elif event_type == "on_tool_start":
                        tool_name = event.get("name", "unknown")
                        tool_input = event.get("data", {}).get("input", {})
                        tool_calls_data.append(
                            {"tool_name": tool_name, "input": tool_input, "result": None}
                        )
                        # Put event in queue for generator to yield
                        try:
                            await event_queue.put({
                                "type": "tool_call",
                                "tool": tool_name,
                                "input": tool_input
                            })
                        except Exception:
                            pass

                    # Handle tool results
                    elif event_type == "on_tool_end":
                        tool_name = event.get("name", "unknown")
                        output = event.get("data", {}).get("output", "")
                        tool_result_str = str(output)[:500]
                        for tc in tool_calls_data:
                            if tc["tool_name"] == tool_name and tc["result"] is None:
                                tc["result"] = tool_result_str
                                break
                        # Save tool call immediately when result is available
                        if assistant_message_id:
                            for tc in tool_calls_data:
                                if tc["tool_name"] == tool_name and tc["result"] is not None:
                                    # Check if this tool call has already been saved
                                    tool_call_id = f"{tc['tool_name']}_{hash(str(tc.get('input', {})))}"
                                    if tool_call_id not in saved_tool_call_ids:
                                        try:
                                            self.conversation_service.save_tool_call(
                                                message_id=assistant_message_id,
                                                tool_name=tc["tool_name"],
                                                input_data=tc["input"],
                                                result=tc["result"],
                                            )
                                            saved_tool_call_ids.add(tool_call_id)
                                        except Exception:
                                            pass  # Tool call might already be saved
                        # Put event in queue for generator to yield
                        try:
                            await event_queue.put({
                                "type": "tool_result",
                                "tool": tool_name,
                                "result": tool_result_str
                            })
                        except Exception:
                            pass

                    # Handle final agent output - THIS IS THE COMPLETE RESPONSE
                    elif event_type == "on_chain_end" and name == "AgentExecutor":
                        output = event.get("data", {}).get("output", {})
                        if isinstance(output, dict) and "output" in output:
                            final_output = output["output"]
                            if final_output:
                                if not isinstance(final_output, str):
                                    final_output = str(final_output)
                                
                                # Update with complete final output
                                full_response = final_output
                                
                                # Save final complete message
                                try:
                                    if assistant_message_id:
                                        self.conversation_service.save_message(
                                            conversation_id=conversation_id,
                                            role="assistant",
                                            content=full_response,
                                            message_id=assistant_message_id,
                                        )
                                    else:
                                        assistant_message_id = self.conversation_service.save_message(
                                            conversation_id=conversation_id,
                                            role="assistant",
                                            content=full_response,
                                        )

                                    # Save any remaining tool calls that haven't been saved yet
                                    if assistant_message_id and tool_calls_data:
                                        for tool_call in tool_calls_data:
                                            # Only save if it has a result (completed) and hasn't been saved yet
                                            tool_call_id = f"{tool_call['tool_name']}_{hash(str(tool_call.get('input', {})))}"
                                            if tool_call.get("result") is not None and tool_call_id not in saved_tool_call_ids:
                                                try:
                                                    self.conversation_service.save_tool_call(
                                                        message_id=assistant_message_id,
                                                        tool_name=tool_call["tool_name"],
                                                        input_data=tool_call["input"],
                                                        result=tool_call["result"],
                                                    )
                                                    saved_tool_call_ids.add(tool_call_id)
                                                except Exception:
                                                    pass  # Tool call might already be saved
                                    
                                    print(f"✓ Final complete message saved (length: {len(full_response)}) for conversation {conversation_id}")
                                except Exception as save_err:
                                    print(f"✗ Failed to save final message: {save_err}")
                                    import traceback
                                    traceback.print_exc()
                                
                                # Put done event in queue
                                try:
                                    await event_queue.put({"type": "done"})
                                except Exception:
                                    pass
                                
                                return  # Exit background task
                
            except Exception as e:
                print(f"Error in background agent processing: {e}")
                import traceback
                traceback.print_exc()
                # Save partial message on error
                if full_response and assistant_message_id:
                    try:
                        self.conversation_service.save_message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=full_response,
                            message_id=assistant_message_id,
                        )
                    except Exception as save_err:
                        print(f"Failed to save partial message on error: {save_err}")
                # Put error event in queue
                try:
                    await event_queue.put({"type": "error", "message": str(e)})
                except Exception:
                    pass
        
        # Start background task to process agent stream completely
        # This ensures the final message is saved even if client disconnects
        # Using asyncio.create_task() ensures it runs independently of the generator
        # The task will continue even if the generator is cancelled (client disconnects)
        background_task = asyncio.create_task(process_agent_stream())

        # Send conversation_id in the stream
        try:
            yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': str(conversation_id)})}\n\n"
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Client disconnected - background task continues processing independently
            pass

        # Yield events from queue (produced by background task)
        # Background task continues processing even if generator stops here
        while True:
            try:
                # Get event from queue (with timeout to check if background task is done)
                event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                
                # Yield event to client
                try:
                    yield f"data: {json.dumps(event)}\n\n"
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    # Client disconnected - background task continues independently
                    break
                
                # If done event, exit loop
                if event.get("type") == "done":
                    break
                if event.get("type") == "error":
                    break
                    
            except asyncio.TimeoutError:
                # Check if background task is done
                if background_task.done():
                    break
                # Otherwise continue waiting for events
                continue
            except Exception as stream_err:
                # Log error but continue - background task handles processing
                print(f"Error in generator stream: {stream_err}")
                break

        # Send completion event (if client still connected)
        try:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Client disconnected - background task already saved final message
            pass
