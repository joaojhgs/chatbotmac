"""Service for managing conversations and messages in Supabase."""

import os
from typing import Any
from uuid import UUID, uuid4

from supabase import Client, create_client

from app.models.database import Conversation, Message, MessageWithToolCalls, ToolCall


class ConversationService:
    """Service for conversation history operations."""

    def __init__(self, supabase_url: str | None = None, supabase_key: str | None = None):
        """
        Initialize the conversation service.

        Args:
            supabase_url: Supabase project URL (defaults to env var)
            supabase_key: Supabase service role key (defaults to env var)
        """
        supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        supabase_key = supabase_key or os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be provided")

        self.supabase: Client = create_client(supabase_url, supabase_key)

    def create_conversation(self, conversation_id: UUID | None = None) -> UUID:
        """
        Create a new conversation.

        Args:
            conversation_id: Optional conversation ID to use (if provided and doesn't exist, creates it)

        Returns:
            Conversation ID (UUID)
        """
        if conversation_id is None:
            conversation_id = uuid4()
        else:
            # Check if conversation exists
            response = (
                self.supabase.table("conversations")
                .select("id")
                .eq("id", str(conversation_id))
                .execute()
            )
            if response.data:
                return conversation_id

        # Create new conversation
        self.supabase.table("conversations").insert({"id": str(conversation_id)}).execute()
        return conversation_id

    def save_message(self, conversation_id: UUID, role: str, content: str) -> UUID:
        """
        Save a message to the database.

        Args:
            conversation_id: Conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content

        Returns:
            Message ID (UUID)
        """
        message_id = uuid4()
        self.supabase.table("messages").insert(
            {
                "id": str(message_id),
                "conversation_id": str(conversation_id),
                "role": role,
                "content": content,
            }
        ).execute()
        return message_id

    def save_tool_call(
        self,
        message_id: UUID,
        tool_name: str,
        input_data: dict[str, Any],
        result: str | None = None,
    ) -> UUID:
        """
        Save a tool call to the database.

        Args:
            message_id: Associated message ID
            tool_name: Name of the tool
            input_data: Tool input data
            result: Tool result (optional)

        Returns:
            Tool call ID (UUID)
        """
        tool_call_id = uuid4()
        self.supabase.table("tool_calls").insert(
            {
                "id": str(tool_call_id),
                "message_id": str(message_id),
                "tool_name": tool_name,
                "input": input_data,
                "result": result,
            }
        ).execute()
        return tool_call_id

    def get_conversation_history(
        self, conversation_id: UUID, limit: int = 3
    ) -> list[MessageWithToolCalls]:
        """
        Get conversation history with tool calls.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve (default: 3)

        Returns:
            List of messages with tool calls, ordered by creation time (oldest first)
        """
        # Use the database function to get history with tool calls
        response = self.supabase.rpc(
            "get_conversation_history",
            {"p_conversation_id": str(conversation_id), "p_limit": limit},
        ).execute()

        if not response.data:
            return []

        # Convert to MessageWithToolCalls objects
        messages = []
        for row in reversed(response.data):  # Reverse to get oldest first
            messages.append(
                MessageWithToolCalls(
                    message_id=UUID(row["message_id"]),
                    role=row["role"],
                    content=row["content"],
                    created_at=row["created_at"],
                    tool_calls=row["tool_calls"] or [],
                )
            )

        return messages

    def delete_conversation(self, conversation_id: UUID) -> bool:
        """
        Delete a conversation and all associated messages and tool calls.

        Args:
            conversation_id: Conversation ID to delete

        Returns:
            True if successful
        """
        # Cascade delete will handle messages and tool_calls
        self.supabase.table("conversations").delete().eq("id", str(conversation_id)).execute()
        return True

    def get_all_messages(self, conversation_id: UUID) -> list[Message]:
        """
        Get all messages for a conversation (without tool calls).

        Args:
            conversation_id: Conversation ID

        Returns:
            List of messages
        """
        response = (
            self.supabase.table("messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=False)
            .execute()
        )

        if not response.data:
            return []

        return [
            Message(
                id=UUID(msg["id"]),
                conversation_id=UUID(msg["conversation_id"]),
                role=msg["role"],
                content=msg["content"],
                created_at=msg["created_at"],
            )
            for msg in response.data
        ]
