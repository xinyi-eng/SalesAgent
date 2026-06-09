"""
知识库加载器 - 从文档加载知识到向量数据库
"""
import os
import re
from typing import List, Optional
from app.services.knowledge.document_processor import DocumentProcessor, TextChunk
from app.services.knowledge.vector_store import get_vector_store, VectorStore


class KnowledgeLoader:
    """
    知识库加载器

    从预处理好的Markdown文件加载知识到向量数据库
    """

    _instance = None
    _loaded = False

    def __new__(cls):
        """单例模式，确保只有一个loader实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.doc_processor = DocumentProcessor()
        self.vector_store = get_vector_store()
        self._ensure_loaded()

    def _ensure_loaded(self):
        """确保知识库已加载

        关键：只在 ChromaDB 真的为空时才嵌入。
        已索引的 chunks 直接复用（避免每次启动都跑 90s 嵌入）。
        """
        if KnowledgeLoader._loaded:
            return

        # 1. 先检查 ChromaDB 是不是已经有数据了
        #    强制 vector_store 连接（init 时是 lazy 的）
        try:
            self.vector_store._connect()
            existing = 0
            if self.vector_store._collection is not None:
                existing = self.vector_store._collection.count()
        except Exception as e:
            print(f"[KnowledgeLoader] vector_store connect failed: {e}")
            existing = 0

        if existing > 0:
            print(f"[KnowledgeLoader] ChromaDB already has {existing} chunks — "
                  f"skipping re-embedding. Embedding happens only once per dataset.")
            KnowledgeLoader._loaded = True
            return

        # 2. 真的空，扫描原始数据目录并嵌入
        path = __file__
        for _ in range(5):
            path = os.path.dirname(path)
        project_root = path
        data_dir = os.path.join(project_root, '原始数据')

        if os.path.exists(data_dir):
            print(f"[KnowledgeLoader] ChromaDB empty, loading from {data_dir} ...")
            stats = self.load_all_books(data_dir)
            print(f"[KnowledgeLoader] Initial load done: {stats}")
        else:
            print(f"[KnowledgeLoader] data dir not found: {data_dir}")

        KnowledgeLoader._loaded = True

    def load_markdown_files(self, md_dir: str, book_name: str) -> int:
        """
        加载Markdown文件到向量库

        Args:
            md_dir: Markdown文件目录
            book_name: 书籍名称

        Returns:
            加载的chunk数量
        """
        chunks = self.doc_processor.process_markdown(md_dir, book_name)
        if chunks:
            self.vector_store.add_chunks(chunks)
        return len(chunks)

    def load_all_books(self, data_dir: str) -> dict:
        """
        加载所有书籍到向量库

        Args:
            data_dir: 原始数据目录

        Returns:
            加载统计信息
        """
        stats = {
            "total_chunks": 0,
            "books": {}
        }

        # SPIN销售巨人
        spin_files = [
            f for f in os.listdir(data_dir)
            if f.startswith("MinerU_markdown_07-SPIN销售巨人")
            and f.endswith(".md")
        ]
        for md_file in spin_files:
            md_path = os.path.join(data_dir, md_file)
            chunks = self.doc_processor.process_markdown(md_path, "SPIN销售巨人")
            if chunks:
                self.vector_store.add_chunks(chunks)
                stats["books"]["SPIN销售巨人"] = len(chunks)
                stats["total_chunks"] += len(chunks)

        # 新解决方案销售
        solution_files = [
            f for f in os.listdir(data_dir)
            if f.startswith("MinerU_markdown_新解决方案销售")
            and f.endswith(".md")
        ]
        for md_file in solution_files:
            md_path = os.path.join(data_dir, md_file)
            chunks = self.doc_processor.process_markdown(md_path, "新解决方案销售")
            if chunks:
                self.vector_store.add_chunks(chunks)
                stats["books"]["新解决方案销售"] = len(chunks)
                stats["total_chunks"] += len(chunks)

        # 战略营销
        strategy_files = [
            f for f in os.listdir(data_dir)
            if f.startswith("MinerU_markdown_[新战略营销")
            and f.endswith(".md")
        ]
        for md_file in strategy_files:
            md_path = os.path.join(data_dir, md_file)
            chunks = self.doc_processor.process_markdown(md_path, "战略营销")
            if chunks:
                self.vector_store.add_chunks(chunks)
                stats["books"]["战略营销"] = len(chunks)
                stats["total_chunks"] += len(chunks)

        return stats

    def search_knowledge(self, query: str, category: Optional[str] = None, top_k: int = 5) -> List[TextChunk]:
        """
        搜索知识库

        Args:
            query: 搜索关键词
            category: 知识类别过滤
            top_k: 返回数量

        Returns:
            相关文本块列表
        """
        results = self.vector_store.search(query, top_k=top_k, category=category)
        return [r.chunk for r in results]

    def get_stats(self) -> dict:
        """获取知识库统计信息"""
        return self.vector_store.get_stats()


def load_knowledge_to_vectorstore(data_dir: str = None) -> dict:
    """
    批量加载知识到向量库

    Args:
        data_dir: 原始数据目录，默认使用项目目录下的原始数据

    Returns:
        加载统计信息
    """
    if data_dir is None:
        path = __file__
        for _ in range(5):
            path = os.path.dirname(path)
        project_root = path
        data_dir = os.path.join(project_root, '原始数据')

    loader = KnowledgeLoader()
    return loader.load_all_books(data_dir)


def search_sales_knowledge(query: str, category: str = None, top_k: int = 5) -> List[dict]:
    """
    便捷搜索函数

    Args:
        query: 搜索关键词
        category: 知识类别
        top_k: 返回数量

    Returns:
        搜索结果列表
    """
    loader = KnowledgeLoader()
    chunks = loader.search_knowledge(query, category=category, top_k=top_k)

    return [
        {
            "text": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
            "source": chunk.source,
            "chapter": chunk.chapter,
            "section": chunk.section,
            "category": chunk.category
        }
        for chunk in chunks
    ]


def reset_knowledge_loader():
    """重置知识库加载器（用于测试）"""
    KnowledgeLoader._instance = None
    KnowledgeLoader._loaded = False
    from app.services.knowledge.vector_store import reset_vector_store
    reset_vector_store()


if __name__ == "__main__":
    # 测试加载
    path = __file__
    for _ in range(5):
        path = os.path.dirname(path)
    project_root = path
    data_dir = os.path.join(project_root, '原始数据')

    print("开始加载知识库...")
    stats = load_knowledge_to_vectorstore(data_dir)
    print(f"加载完成: {stats}")

    # 测试搜索
    print("\n测试搜索 '价格异议':")
    results = search_sales_knowledge("价格异议", top_k=3)
    for r in results:
        print(f"  - [{r['source']}] {r['text'][:100]}...")