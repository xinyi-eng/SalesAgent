"""
Vector Store - Store and search embeddings in Milvus or in-memory fallback
"""
import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class VectorChunk:
    """A chunk with its embedding vector."""
    id: str
    text: str
    embedding: List[float]
    source: str
    metadata: Dict
    created_at: str

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'VectorChunk':
        return cls(**data)


class VectorStore:
    """
    Vector store supporting Milvus or in-memory fallback.
    For production, use Milvus. For development, use in-memory.
    """

    def __init__(
        self,
        use_milvus: bool = False,
        milvus_host: str = "localhost",
        milvus_port: int = 19530,
        collection_name: str = "salesagent_knowledge"
    ):
        """
        Initialize VectorStore.

        Args:
            use_milvus: Whether to use Milvus (requires running Milvus)
            milvus_host: Milvus server host
            milvus_port: Milvus server port
            collection_name: Name of the collection
        """
        self.use_milvus = use_milvus
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.collection_name = collection_name
        self._milvus_client = None
        self._collection = None

        # In-memory fallback store
        self._memory_store: Dict[str, VectorChunk] = {}
        self._memory_vectors: List[List[float]] = []
        self._memory_ids: List[str] = []

        if use_milvus:
            self._init_milvus()

    def _init_milvus(self):
        """Initialize Milvus connection."""
        try:
            from pymilvus import MilvusClient
            self._milvus_client = MilvusClient(
                uri=f"http://{self.milvus_host}:{self.milvus_port}"
            )
            # Try to connect and create collection
            if not self._milvus_client.has_collection(self.collection_name):
                self._milvus_client.create_collection(
                    collection_name=self.collection_name,
                    dimension=384,  # Match embedding dimension
                    primary_field="id",
                    vector_field="embedding"
                )
            self._collection = self._milvus_client
            print(f"Connected to Milvus at {self.milvus_host}:{self.milvus_port}")
        except ImportError:
            print("pymilvus not installed, falling back to in-memory store")
            self.use_milvus = False
        except Exception as e:
            print(f"Failed to connect to Milvus: {e}, falling back to in-memory store")
            self.use_milvus = False

    def add_chunks(self, chunks: List[Dict]) -> int:
        """
        Add chunks to the vector store.

        Args:
            chunks: List of chunk dicts with 'id', 'text', 'embedding', 'source', 'metadata'

        Returns:
            Number of chunks added
        """
        if self.use_milvus:
            return self._add_chunks_milvus(chunks)
        else:
            return self._add_chunks_memory(chunks)

    def _add_chunks_milvus(self, chunks: List[Dict]) -> int:
        """Add chunks to Milvus."""
        if not self._milvus_client:
            return 0

        data = []
        for chunk in chunks:
            data.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "embedding": chunk["embedding"],
                "source": chunk.get("source", ""),
                "metadata": json.dumps(chunk.get("metadata", {}))
            })

        self._milvus_client.insert(
            collection_name=self.collection_name,
            data=data
        )
        return len(chunks)

    def _add_chunks_memory(self, chunks: List[Dict]) -> int:
        """Add chunks to in-memory store."""
        count = 0
        for chunk in chunks:
            vector_chunk = VectorChunk(
                id=chunk["id"],
                text=chunk["text"],
                embedding=chunk["embedding"],
                source=chunk.get("source", ""),
                metadata=chunk.get("metadata", {}),
                created_at=datetime.now().isoformat()
            )
            self._memory_store[chunk["id"]] = vector_chunk
            self._memory_vectors.append(chunk["embedding"])
            self._memory_ids.append(chunk["id"])
            count += 1
        return count

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        source_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for similar chunks.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            source_filter: Optional source filter

        Returns:
            List of matching chunks with scores
        """
        if self.use_milvus:
            return self._search_milvus(query_embedding, top_k, source_filter)
        else:
            return self._search_memory(query_embedding, top_k, source_filter)

    def _search_milvus(
        self,
        query_embedding: List[float],
        top_k: int,
        source_filter: Optional[str]
    ) -> List[Dict]:
        """Search in Milvus."""
        if not self._milvus_client:
            return []

        results = self._milvus_client.search(
            collection_name=self.collection_name,
            data=[query_embedding],
            limit=top_k,
            output_fields=["id", "text", "source", "metadata"]
        )

        return [
            {
                "id": hit["id"],
                "text": hit["text"],
                "source": hit["source"],
                "metadata": json.loads(hit["metadata"]) if hit.get("metadata") else {},
                "score": 1 - hit.get("distance", 0)  # Convert distance to similarity
            }
            for hit in results[0]
        ]

    def _search_memory(
        self,
        query_embedding: List[float],
        top_k: int,
        source_filter: Optional[str]
    ) -> List[Dict]:
        """Search in memory using cosine similarity."""
        if not self._memory_vectors:
            return []

        # Compute similarities
        scores = []
        for i, emb in enumerate(self._memory_vectors):
            sim = self._cosine_similarity(query_embedding, emb)
            chunk = self._memory_store[self._memory_ids[i]]

            # Apply source filter
            if source_filter and chunk.source != source_filter:
                continue

            scores.append((sim, chunk))

        # Sort by score descending
        scores.sort(key=lambda x: x[0], reverse=True)

        # Return top_k results
        return [
            {
                "id": chunk.id,
                "text": chunk.text,
                "source": chunk.source,
                "metadata": chunk.metadata,
                "score": score
            }
            for score, chunk in scores[:top_k]
        ]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a ** 2 for a in vec1) ** 0.5
        norm2 = sum(b ** 2 for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def get_by_source(self, source: str) -> List[Dict]:
        """Get all chunks from a specific source."""
        if self.use_milvus:
            return self._get_by_source_milvus(source)
        else:
            return self._get_by_source_memory(source)

    def _get_by_source_milvus(self, source: str) -> List[Dict]:
        """Get chunks by source from Milvus."""
        # Milvus doesn't support direct filtering well, return empty
        # In production, use a separate metadata database
        return []

    def _get_by_source_memory(self, source: str) -> List[Dict]:
        """Get chunks by source from memory."""
        return [
            chunk.to_dict()
            for chunk in self._memory_store.values()
            if chunk.source == source
        ]

    def delete_by_source(self, source: str) -> int:
        """Delete all chunks from a specific source."""
        if self.use_milvus:
            # Would need to implement in Milvus
            return 0

        to_delete = [
            chunk_id for chunk_id, chunk in self._memory_store.items()
            if chunk.source == source
        ]

        for chunk_id in to_delete:
            idx = self._memory_ids.index(chunk_id)
            del self._memory_store[chunk_id]
            del self._memory_vectors[idx]
            del self._memory_ids[idx]

        return len(to_delete)

    def count(self) -> Dict:
        """Get count of chunks by source."""
        counts = {"total": len(self._memory_store)}
        for chunk in self._memory_store.values():
            source = chunk.source or "unknown"
            counts[source] = counts.get(source, 0) + 1
        return counts

    def clear(self):
        """Clear all chunks (use with caution)."""
        if self.use_milvus and self._milvus_client:
            self._milvus_client.drop_collection(self.collection_name)
            self._milvus_client.create_collection(
                collection_name=self.collection_name,
                dimension=384,
                primary_field="id",
                vector_field="embedding"
            )

        self._memory_store.clear()
        self._memory_vectors.clear()
        self._memory_ids.clear()