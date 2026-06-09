"""
Embedding Service - Generate embeddings for text chunks

NOTE: This used to call MiniMax's embedding API. That endpoint now
returns an unexpected response shape ("data" key missing) and the
service was silently returning demo vectors, breaking /knowledge/search.

The model of record for this project is now BAAI/bge-base-zh-v1.5
(managed in app.services.knowledge.embedding). This class is a thin
async-compatible wrapper around the BGE model so legacy code paths
that expect `await embed_service.embed_text(text)` still work.
"""
import asyncio
from typing import List, Dict, Optional


class EmbeddingService:
    """
    Async wrapper around the BGE Chinese embedding model.

    BGE produces 768-dim L2-normalized vectors. The old interface
    expected 384-dim for Milvus — if any caller still assumes 384,
    it will need updating. None of the live API paths do, so this
    is safe.
    """

    def __init__(self, model: str = "BAAI/bge-base-zh-v1.5", **_unused):
        self.model = model
        # Backing embedder is created lazily on first call.
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None:
            from app.services.knowledge.embedding import get_embedding_model
            self._embedder = get_embedding_model()
        return self._embedder

    async def embed_text(self, text: str) -> List[float]:
        """Embed a single string (async-compatible)."""
        return await asyncio.to_thread(self._get_embedder().embed_query, text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of strings."""
        return await asyncio.to_thread(self._get_embedder().embed, texts)

    async def embed_with_metadata(
        self,
        chunks: List[Dict],
        source_name: str = ""
    ) -> List[Dict]:
        """Embed chunks and return enriched dicts."""
        texts = [c["text"] for c in chunks]
        embeddings = await self.embed_batch(texts)
        result = []
        for chunk, emb in zip(chunks, embeddings):
            c = {**chunk}
            c["embedding"] = emb
            c["embedding_model"] = self.model
            c["source"] = source_name or chunk.get("source", "")
            result.append(c)
        return result

    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Cosine similarity between two equal-dim vectors."""
        if not embedding1 or not embedding2:
            return 0.0
        if len(embedding1) != len(embedding2):
            # different dim — fall back to 0 rather than crash
            return 0.0
        dot = sum(a * b for a, b in zip(embedding1, embedding2))
        n1 = sum(a * a for a in embedding1) ** 0.5
        n2 = sum(b * b for b in embedding2) ** 0.5
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)
