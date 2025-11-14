"""RAG tool for retrieving MacBook Air facts from Supabase."""

from langchain.tools import tool

from app.rag.supabase_client import SupabaseRAGClient


def create_rag_tool(rag_client: SupabaseRAGClient):
    """
    Create a RAG retrieval tool for the agent.

    Args:
        rag_client: Initialized SupabaseRAGClient instance

    Returns:
        LangChain tool for RAG retrieval
    """

    @tool
    def retrieve_macbook_facts(query: str) -> str:
        """Retrieve relevant facts about MacBook Air from stored knowledge base.

        Use this tool when you need:
        - Technical specifications
        - Historical information
        - Feature descriptions
        - Comparison details
        - General product information

        This tool searches through a curated database of MacBook Air facts.
        For current information (prices, availability, news), use the web_search tool instead.

        Args:
            query: The search query to find relevant facts

        Returns:
            Retrieved facts formatted as a string
        """
        try:
            # Search for similar documents
            documents = rag_client.search_similar(query, top_k=30)

            if not documents:
                return "No relevant facts found in the knowledge base."

            # Format the context
            context = rag_client.format_context(documents)
            return f"Retrieved facts about MacBook Air:\n\n{context}"

        except Exception as e:
            return f"Error retrieving facts: {e!s}"

    return retrieve_macbook_facts
