"""
Vector Store - Store and search embeddings in ChromaDB.

NOTE: Used to support Milvus or in-memory fallback. Both modes
required re-embedding all 10k chunks on every server restart, and
Milvus wasn't actually running. The collection is now a thin wrapper
around the persisted ChromaDB collection used by the chat flow
(`app.services.knowledge.vector_store_chroma`), so:

  - Embeddings are stored on disk across restarts
  - The same BGE vectors are reused by both /api/v1/knowledge/search
    and the chat conversation handler
  - Top-k search returns the same chunks the chat sees
"""
import os
import json
from typing import List, Dict, Optional
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
    Wrapper around the project-wide ChromaDB collection. Kept the
    same interface as before (Milvus/in-memory) so callers don't need
    to change.
    """

    def __init__(
        self,
        use_milvus: bool = False,
        milvus_host: str = "localhost",
        milvus_port: int = 19530,
        collection_name: str = "sales_knowledge"
    ):
        # We always go to ChromaDB now — Milvus path is kept only to
        # avoid breaking old call sites.
        self.use_milvus = False
        self.collection_name = collection_name
        self._chroma = None  # Lazy: chromadb.PersistentClient
        self._collection = None

    def _connect(self):
        if self._collection is not None:
            return
        # 直接创建 chromadb.PersistentClient，不绕道 knowledge 栈。
        # 用 get_collection（不是 get_or_create），避免因为 metadata
        # 不匹配而被自动创建一个空的同名 collection。
        import chromadb
        import os.path as _p
        data_dir = _p.abspath(_p.join(_p.dirname(__file__), "..", "..", "..", "data", "chroma"))
        os.makedirs(data_dir, exist_ok=True)
        self._chroma = chromadb.PersistentClient(path=data_dir)
        try:
            self._collection = self._chroma.get_collection(self.collection_name)
        except Exception:
            # 第一次启动 / collection 还没建 — 创建
            self._collection = self._chroma.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Sales Agent Knowledge Base"}
            )

    def add_chunks(self, chunks: List[Dict]) -> int:
        """
        Add chunks to ChromaDB. Re-uses the BGE-backed add_chunks from
        the knowledge stack so we get batching + dedup for free.
        """
        from app.services.knowledge.vector_store_chroma import ChromaVectorStore
        from app.services.knowledge.document_processor import TextChunk

        self._connect()
        # Convert dicts → TextChunk so we can call the existing
        # add_chunks which handles BGE embedding + batch split.
        chroma = ChromaVectorStore(collection_name=self.collection_name)
        chroma._connect()

        text_chunks = []
        for c in chunks:
            text_chunks.append(TextChunk(
                id=c["id"],
                text=c.get("text", ""),
                source=c.get("source", ""),
                category=c.get("metadata", {}).get("category", ""),
                chapter=c.get("metadata", {}).get("chapter", ""),
                section=c.get("metadata", {}).get("section", ""),
                spin_stage=c.get("metadata", {}).get("spin_stage", ""),
            ))

        before = chroma._collection.count()
        chroma.add_chunks(text_chunks)
        after = chroma._collection.count()
        added = max(0, after - before)
        return added

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        source_filter: Optional[str] = None
    ) -> List[Dict]:
        """Search by query embedding (cosine, top_k)."""
        self._connect()
        where = {"source": source_filter} if source_filter else None
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        out: List[Dict] = []
        if not results["ids"]:
            return out
        for i, cid in enumerate(results["ids"][0]):
            distance = results["distances"][0][i]
            # chromadb cosine distance for L2-normalized vectors:
            #   cosine_dist = 1 - dot_product, in [0, 2]
            #   dot_product in [-1, 1]  (1 == identical, -1 == opposite)
            #   so  dot_product = 1 - distance
            # Map to [0, 1] for the API's `score` field:
            #   score = (1 - distance + 1) / 2 = 1 - distance/2
            score = 1.0 - distance / 2.0
            out.append({
                "id": cid,
                "text": (results["documents"][0][i] if results["documents"] else ""),
                "source": (results["metadatas"][0][i].get("source", "")
                           if results["metadatas"] else ""),
                "metadata": (results["metadatas"][0][i] if results["metadatas"] else {}),
                "score": score,
            })
        return out

    def get_by_source(self, source: str) -> List[Dict]:
        self._connect()
        results = self._collection.get(
            where={"source": source},
            include=["documents", "metadatas"],
        )
        out = []
        for i, cid in enumerate(results["ids"]):
            meta = results["metadatas"][i] if results["metadatas"] else {}
            out.append({
                "id": cid,
                "text": results["documents"][i] if results["documents"] else "",
                "source": meta.get("source", ""),
                "metadata": meta,
            })
        return out

    def delete_by_source(self, source: str) -> int:
        self._connect()
        results = self._collection.get(
            where={"source": source},
            include=[],
        )
        ids = results["ids"]
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def count(self) -> Dict:
        self._connect()
        total = self._collection.count()
        return {"total": total, "chromadb": True}

    def clear(self):
        self._connect()
        # Drop and recreate — destructive
        self._chroma.delete_collection(self.collection_name)
        self._collection = self._chroma.create_collection(
            name=self.collection_name,
            metadata={"description": "Sales Agent Knowledge Base (RAG stack)"}
        )
