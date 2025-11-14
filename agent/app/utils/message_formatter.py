"""Utility functions for formatting messages for LangChain."""

from langchain_core.messages import AIMessage, HumanMessage

from app.models.database import MessageWithToolCalls


def format_history_for_agent(
    history: list[MessageWithToolCalls],
) -> list[HumanMessage | AIMessage]:
    """
    Format conversation history into LangChain messages.

    Args:
        history: List of messages with tool calls

    Returns:
        List of LangChain messages (HumanMessage or AIMessage)
    """
    messages = []
    for msg in history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
    return messages

