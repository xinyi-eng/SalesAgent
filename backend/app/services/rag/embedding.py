"""
Embedding Service - Generate embeddings for text chunks
"""
import os
from typing import List, Dict, Optional, Union
import httpx


class EmbeddingService:
    """Generate text embeddings using MiniMax API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "emb-model",
        base_url: str = "https://api.minimax.chat/v1"
    ):
        """
        Initialize EmbeddingService.

        Args:
            api_key: MiniMax API key (defaults to env MINIMAX_API_KEY)
            model: Embedding model name
            base_url: MiniMax API base URL
        """
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.model = model
        self.base_url = base_url

        if not self.api_key:
            print("Warning: MINIMAX_API_KEY not set, embeddings will use demo mode")

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (list of floats)
        """
        if not self.api_key:
            return self._demo_embedding(len(text))

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "input": text[:8192]  # Limit input length
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]
                else:
                    print(f"Embedding API error: {response.status_code}")
                    return self._demo_embedding(len(text))

        except Exception as e:
            print(f"Embedding failed: {e}")
            return self._demo_embedding(len(text))

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not self.api_key:
            return [self._demo_embedding(len(t)) for t in texts]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Process in batches of 10
                embeddings = []
                batch_size = 10

                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    truncated_batch = [t[:8192] for t in batch]

                    response = await client.post(
                        f"{self.base_url}/embeddings",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.model,
                            "input": truncated_batch
                        }
                    )

                    if response.status_code == 200:
                        data = response.json()
                        embeddings.extend([item["embedding"] for item in data["data"]])
                    else:
                        print(f"Embedding API error: {response.status_code}")
                        embeddings.extend([self._demo_embedding(len(t)) for t in batch])

                return embeddings

        except Exception as e:
            print(f"Batch embedding failed: {e}")
            return [self._demo_embedding(len(t)) for t in texts]

    def _demo_embedding(self, text_length: int) -> List[float]:
        """
        Generate a demo embedding for testing without API.
        Uses deterministic values based on text length for consistency.
        """
        # Generate a 384-dimensional vector
        import hashlib

        # Create a seed from text length
        seed = text_length % 1000
        vec = []

        for i in range(384):
            # Deterministic but varied values
            val = ((seed * (i + 1) * 17) % 100) / 100
            vec.append(val * 2 - 1)  # Range [-1, 1]

        # Normalize
        norm = sum(v ** 2 for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    async def embed_with_metadata(
        self,
        chunks: List[Dict],
        source_name: str = ""
    ) -> List[Dict]:
        """
        Generate embeddings for chunks with metadata.

        Args:
            chunks: List of chunk dictionaries with 'text' field
            source_name: Source document name

        Returns:
            List of chunks with added 'embedding' field
        """
        texts = [chunk["text"] for chunk in chunks]
        embeddings = await self.embed_batch(texts)

        result = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_copy = {**chunk}
            chunk_copy["embedding"] = embedding
            chunk_copy["embedding_model"] = self.model
            chunk_copy["source"] = source_name or chunk.get("source", "")
            result.append(chunk_copy)

        return result

    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-1)
        """
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a ** 2 for a in embedding1) ** 0.5
        norm2 = sum(b ** 2 for b in embedding2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)