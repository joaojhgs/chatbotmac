"""Service for generating prompt suggestions using LLM."""

import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.models.database import MessageWithToolCalls

# Load environment variables
load_dotenv()

# Default suggestions when no conversation history
DEFAULT_SUGGESTIONS = [
    "Tell me about the latest MacBook Air",
    "Compare the latest against older models",
    "What are the current prices?",
]


class SuggestionService:
    """Service for generating contextual prompt suggestions."""

    def __init__(self, llm_model: str = "gpt-4o-mini", temperature: float = 0.7):
        """
        Initialize the suggestion service.

        Args:
            llm_model: OpenAI model to use for suggestions
            temperature: Temperature for LLM generation
        """
        self.llm_model = llm_model
        self.temperature = temperature
        self.api_key = os.getenv("OPENAI_API_KEY")

    def get_default_suggestions(self) -> list[str]:
        """
        Get default suggestions.

        Returns:
            List of default suggestion strings
        """
        return DEFAULT_SUGGESTIONS.copy()

    async def generate_suggestions(
        self, history: list[MessageWithToolCalls]
    ) -> list[str]:
        """
        Generate contextual suggestions based on conversation history.

        Args:
            history: List of messages from conversation history

        Returns:
            List of suggestion strings
        """
        # If no history, return defaults
        if not history:
            return self.get_default_suggestions()

        try:
            llm = ChatOpenAI(
                model=self.llm_model,
                temperature=self.temperature,
                api_key=self.api_key,
            )

            # Format conversation history for context
            history_text = "\n".join([
                f"{'User' if msg.role == 'user' else 'Assistant'}: {msg.content[:200]}"
                for msg in history[-3:]  # Last 3 messages
            ])

            prompt = f"""You are a helpful assistant for a MacBook Air chatbot. Based on the conversation history below, generate 3 relevant follow-up question suggestions that would be helpful for the user.

Conversation History:
{history_text}

Generate exactly 3 short (up to 10 words), specific questions in place of the user, asking a specialized agent for help, (each should be a complete question, not just keywords). Make them relevant to the MacBook Air and the conversation context. Return only the questions, one per line, without numbering or bullets."""

            response = await llm.ainvoke([
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content=prompt),
            ])

            # Parse LLM response into list of suggestions
            llm_suggestions = [
                line.strip()
                for line in response.content.strip().split("\n")
                if line.strip() and len(line.strip()) > 10  # Filter out empty or too short lines
            ][:3]  # Take first 3

            # Fallback to defaults if LLM didn't generate good suggestions
            if len(llm_suggestions) >= 2:
                return llm_suggestions
            else:
                return self.get_default_suggestions()

        except Exception as e:
            print(f"Error generating LLM suggestions: {e}")
            # Fallback to defaults on error
            return self.get_default_suggestions()

