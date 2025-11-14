"""Web search tool using LangChain's Brave search."""

import os

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

    # Create Brave Search tool directly and customize its name and description
    search_tool = BraveSearch.from_api_key(api_key=brave_api_key)
    
    # Override the name to be "web_search" instead of "brave_search"
    search_tool.name = "web_search"
    search_tool.description = """Search the web for current information about MacBook Air using Brave Search.

Use this tool when you need:
- Current prices and availability
- Latest news and updates
- Recent reviews and comparisons
- Up-to-date specifications
- Current promotions or deals

Args:
    query: The search query string

Returns:
    Search results as a string"""

    return search_tool
