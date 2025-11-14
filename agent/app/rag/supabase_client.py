"""Supabase client for RAG vector search."""

from typing import Any

from supabase import Client, create_client

from app.rag.embeddings import EmbeddingGenerator


class SupabaseRAGClient:
    """Client for performing RAG operations with Supabase."""

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        openai_api_key: str,
        table_name: str = "macbook_facts",
    ):
        """
        Initialize the Supabase RAG client.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key
            openai_api_key: OpenAI API key for embeddings
            table_name: Name of the table storing facts
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.embedding_generator = EmbeddingGenerator(openai_api_key)
        self.table_name = table_name

    def search_similar(
        self, query: str, top_k: int = 5, threshold: float = 0.7
    ) -> list[dict[str, Any]]:
        """
        Search for similar documents using vector similarity.

        Args:
            query: Search query text
            top_k: Number of results to return
            threshold: Similarity threshold (0-1)

        Returns:
            List of matching documents with content and metadata
        """
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_generator.generate_embedding(query)

            # Perform vector similarity search using Supabase RPC
            response = self.supabase.rpc(
                "match_macbook_facts",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": top_k,
                },
            ).execute()

            if response.data:
                return response.data

        except Exception as e:
            print(f"Error in vector search: {e!s}")

    def format_context(self, documents: list[dict[str, Any]]) -> str:
        """
        Format retrieved documents into context string.

        Args:
            documents: List of retrieved documents

        Returns:
            Formatted context string
        """
        if not documents:
            return ""

        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            context_part = f"[Source {i}]"
            if metadata:
                source = metadata.get("source", "Unknown")
                context_part += f" Source: {source}\n"
            context_part += f"{content}\n"
            context_parts.append(context_part)

        return "\n\n".join(context_parts)
