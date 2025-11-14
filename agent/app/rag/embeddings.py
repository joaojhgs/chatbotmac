"""Embedding generation using OpenAI."""

from openai import OpenAI


class EmbeddingGenerator:
    """Generate embeddings using OpenAI's embedding models."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """
        Initialize the embedding generator.

        Args:
            api_key: OpenAI API key
            model: Embedding model to use (default: text-embedding-3-small)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = self.client.embeddings.create(model=self.model, input=text)
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Error generating embedding: {e!s}") from e

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            response = self.client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            raise Exception(f"Error generating embeddings: {e!s}") from e
