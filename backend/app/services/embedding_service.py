"""
EmbeddingService — Voyage AI voyage-2 (1024 dims)

Responsável por converter texto em vetores de embedding.
"""
import voyageai
from app.core.config import settings


class EmbeddingService:
    def __init__(self):
        self.client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        self.model = "voyage-2"
        self.dimensions = 1024

    async def embed_text(self, text: str) -> list[float]:
        """Embed single text. Returns list of 1024 floats."""
        result = self.client.embed([text], model=self.model, input_type="document")
        return result.embeddings[0]

    async def embed_query(self, query: str) -> list[float]:
        """Embed a query (search). Returns list of 1024 floats."""
        result = self.client.embed([query], model=self.model, input_type="query")
        return result.embeddings[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call."""
        result = self.client.embed(texts, model=self.model, input_type="document")
        return result.embeddings
