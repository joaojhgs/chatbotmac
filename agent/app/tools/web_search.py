"""Web search tool using LangChain's Brave search."""

import os

from langchain.tools import tool
from langchain_community.tools import BraveSearch


def create_web_search_tool():
    """Create and return a web search tool for the agent."""
    # Get Brave Search API key from environment
    brave_api_key = os.getenv("BRAVE_SEARCH_API_KEY")

    if not brave_api_key:
        raise ValueError(
            "BRAVE_SEARCH_API_KEY environment variable is required. "
            "Get your API key from https://brave.com/search/api/"
        )

    # Initialize Brave Search tool
    search = BraveSearch.from_api_key(api_key=brave_api_key)

    @tool
    def web_search(query: str) -> str:
        """Search the web for current information about MacBook Air using Brave Search.

        Use this tool when you need:
        - Current prices and availability
        - Latest news and updates
        - Recent reviews and comparisons
        - Up-to-date specifications
        - Current promotions or deals

        Args:
            query: The search query string

        Returns:
            Search results as a string
        """
        try:
            return search.invoke(query)
        except Exception as e:
            return f"Error performing web search: {e!s}"

    return web_search
