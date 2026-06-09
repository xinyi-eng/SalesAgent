"""
向量数据库集成 - ChromaDB (默认)
"""
import os
import uuid
from typing import List, Optional
from dataclasses import dataclass

from app.services.knowledge.document_processor import TextChunk
from app.services.knowledge.embedding import get_embedding_model, EmbeddingModel


@dataclass
class SearchResult:
    """搜索结果"""
    chunk: TextChunk
    score: float


class VectorStore:
    """向量存储抽象接口"""

    def add_chunks(self, chunks: List[TextChunk]) -> bool:
        """添加文本块到向量库"""
        raise NotImplementedError

    def search(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[SearchResult]:
        """向量相似度搜索"""
        raise NotImplementedError

    def get_stats(self) -> dict:
        """获取统计信息"""
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    """
    ChromaDB向量存储实现

    使用 Chroma 本地向量数据库进行向量存储和检索
    """

    def __init__(self, collection_name: str = "sales_knowledge"):
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._chunks: List[TextChunk] = []

    def _connect(self):
        """连接ChromaDB"""
        if self._collection is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            # 数据目录
            data_dir = os.path.join(os.path.dirname(__file__), "../../../data/chroma")
            os.makedirs(data_dir, exist_ok=True)

            # 创建客户端 (持久化)
            self._client = chromadb.PersistentClient(path=data_dir)

            # 获取或创建集合
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Sales Agent Knowledge Base"}
            )

            print(f"Connected to ChromaDB: {self.collection_name}")

        except ImportError:
            print("chromadb not installed, using in-memory fallback")
        except Exception as e:
            print(f"ChromaDB connection failed: {e}, using in-memory fallback")

    def add_chunks(self, chunks: List[TextChunk]) -> bool:
        """添加文本块到向量库"""
        self._connect()

        if not chunks:
            return True

        # 如果没有collection，使用内存存储
        if self._collection is None:
            self._chunks.extend(chunks)
            return True

        try:
            from app.services.knowledge.embedding import get_embedding_model

            # 获取embedding模型
            embedder = get_embedding_model()

            # ChromaDB 单次 .add() 的 batch size 上限是 5461
            # 超过会抛 "Batch size of N is greater than max batch size of 5461"
            # 分批处理
            CHROMA_BATCH_LIMIT = 5000

            for batch_start in range(0, len(chunks), CHROMA_BATCH_LIMIT):
                batch = chunks[batch_start:batch_start + CHROMA_BATCH_LIMIT]
                ids = []
                texts = []
                embeddings = []
                metadatas = []

                for chunk in batch:
                    ids.append(chunk.id)
                    texts.append(chunk.text)
                    embeddings.append(embedder.embed_query(chunk.text))
                    metadatas.append({
                        "source": chunk.source,
                        "category": chunk.category,
                        "chapter": chunk.chapter,
                        "section": chunk.section,
                        "spin_stage": chunk.spin_stage or ""
                    })

                self._collection.add(
                    ids=ids,
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                print(f"Added {len(batch)} chunks to ChromaDB "
                      f"(batch {batch_start//CHROMA_BATCH_LIMIT + 1})")

            self._chunks.extend(chunks)
            return True

        except Exception as e:
            print(f"Failed to add chunks to ChromaDB: {e}")
            self._chunks.extend(chunks)
            return True

    def search(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[SearchResult]:
        """向量相似度搜索"""
        self._connect()

        # 如果没有collection连接，使用关键词搜索
        if self._collection is None:
            return self._keyword_search(query, top_k, category)

        try:
            from app.services.knowledge.embedding import get_embedding_model

            # 获取query embedding
            embedder = get_embedding_model()
            query_vector = embedder.embed_query(query)

            # 构建where条件
            where = {"category": category} if category else None

            # 搜索
            results = self._collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            # 转换结果 - 直接从ChromaDB结果重建chunk
            search_results = []
            ids = results.get("ids", [[]])[0]
            docs = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for i, doc_id in enumerate(ids):
                if i >= len(docs):
                    continue

                # 直接从结果重建TextChunk，避免依赖self._chunks
                metadata = metadatas[i] if i < len(metadatas) else {}
                chunk = TextChunk(
                    id=doc_id,
                    text=docs[i],
                    source=metadata.get("source", ""),
                    category=metadata.get("category", "general"),
                    chapter=metadata.get("chapter", ""),
                    section=metadata.get("section", ""),
                    spin_stage=metadata.get("spin_stage") or None
                )

                distance = distances[i]
                search_results.append(SearchResult(chunk=chunk, score=1.0 - distance))

            return search_results

        except Exception as e:
            print(f"ChromaDB search failed: {e}, using keyword fallback")
            return self._keyword_search(query, top_k, category)

    def _keyword_search(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[SearchResult]:
        """关键词回退搜索"""
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        scored = []
        for chunk in self._chunks:
            if category and chunk.category != category:
                continue

            text_lower = chunk.text.lower()
            score = sum(1 for term in query_terms if term in text_lower)

            if score > 0:
                scored.append(SearchResult(chunk=chunk, score=float(score)))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def get_stats(self) -> dict:
        """获取统计信息"""
        self._connect()

        if self._collection is not None:
            try:
                count = self._collection.count()
                return {
                    "total_chunks": count,
                    "chroma_active": True
                }
            except:
                pass

        return {
            "total_chunks": len(self._chunks),
            "in_memory": True
        }


class InMemoryVectorStore(VectorStore):
    """
    内存向量存储 - 测试或无向量数据库环境使用

    使用简单的关键词匹配
    """

    def __init__(self):
        self._chunks: List[TextChunk] = []

    def add_chunks(self, chunks: List[TextChunk]) -> bool:
        """添加文本块"""
        self._chunks.extend(chunks)
        return True

    def search(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[SearchResult]:
        """关键词搜索"""
        return self._keyword_search(query, top_k, category)

    def _keyword_search(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[SearchResult]:
        """关键词搜索实现"""
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        scored = []
        for chunk in self._chunks:
            if category and chunk.category != category:
                continue

            text_lower = chunk.text.lower()

            # 精确匹配
            if query_lower in text_lower:
                score = 10.0
            else:
                # 词项重叠
                overlap = query_terms & set(text_lower.split())
                score = len(overlap) / max(len(query_terms), 1) * 5.0

            if score > 0:
                scored.append(SearchResult(chunk=chunk, score=score))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def get_stats(self) -> dict:
        """获取统计信息"""
        categories = {}
        sources = {}

        for chunk in self._chunks:
            categories[chunk.category] = categories.get(chunk.category, 0) + 1
            sources[chunk.source] = sources.get(chunk.source, 0) + 1

        return {
            "total_chunks": len(self._chunks),
            "categories": categories,
            "sources": sources,
            "in_memory": True
        }


# 单例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取向量存储单例"""
    global _vector_store
    if _vector_store is None:
        # 优先使用ChromaDB
        try:
            _vector_store = ChromaVectorStore()
        except Exception as e:
            print(f"ChromaDB init failed: {e}, using in-memory fallback")
            _vector_store = InMemoryVectorStore()

    return _vector_store


def reset_vector_store():
    """重置向量存储"""
    global _vector_store
    _vector_store = None