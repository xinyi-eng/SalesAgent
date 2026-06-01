"""
知识库索引 - 向量检索支持
用于知识库的构建和检索
"""
import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class KnowledgeChunk:
    """知识块"""
    id: str
    text: str
    category: str  # framework | objection | script | case
    source: str
    chapter: str
    section: str
    spin_stage: Optional[str] = None
    metadata: dict = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "text": self.text,
            "category": self.category,
            "source": self.source,
            "chapter": self.chapter,
            "section": self.section,
            "spin_stage": self.spin_stage,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "KnowledgeChunk":
        return cls(
            id=data.get("id", ""),
            text=data.get("text", ""),
            category=data.get("category", ""),
            source=data.get("source", ""),
            chapter=data.get("chapter", ""),
            section=data.get("section", ""),
            spin_stage=data.get("spin_stage"),
            metadata=data.get("metadata", {})
        )


class KnowledgeIndex:
    """
    知识库索引

    当前版本：内存存储 + 关键词检索
    后续版本：可扩展为向量检索（FAISS/Milvus）
    """

    def __init__(self):
        self.chunks: List[KnowledgeChunk] = []
        self.category_index: Dict[str, List[int]] = {}  # category -> [chunk_ids]
        self.spin_index: Dict[str, List[int]] = {}  # spin_stage -> [chunk_ids]
        self.source_index: Dict[str, List[int]] = {}  # source -> [chunk_ids]

    def add_chunk(self, chunk: KnowledgeChunk):
        """添加知识块"""
        self.chunks.append(chunk)

        # 更新索引
        if chunk.category not in self.category_index:
            self.category_index[chunk.category] = []
        self.category_index[chunk.category].append(len(self.chunks) - 1)

        if chunk.spin_stage:
            if chunk.spin_stage not in self.spin_index:
                self.spin_index[chunk.spin_stage] = []
            self.spin_index[chunk.spin_stage].append(len(self.chunks) - 1)

        if chunk.source not in self.source_index:
            self.source_index[chunk.source] = []
        self.source_index[chunk.source].append(len(self.chunks) - 1)

    def add_chunks(self, chunks: List[KnowledgeChunk]):
        """批量添加知识块"""
        for chunk in chunks:
            self.add_chunk(chunk)

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        spin_stage: Optional[str] = None,
        top_k: int = 5
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """
        搜索知识块

        当前版本：关键词匹配 + 简单评分
        后续版本：向量相似度检索
        """
        query_lower = query.lower()
        query_terms = set(re.findall(r'\w+', query_lower))

        scored_chunks: List[Tuple[KnowledgeChunk, float]] = []

        # 过滤条件
        candidate_ids = set(range(len(self.chunks)))

        if category:
            candidate_ids &= set(self.category_index.get(category, []))

        if spin_stage:
            candidate_ids &= set(self.spin_index.get(spin_stage, []))

        # 评分
        for idx in candidate_ids:
            chunk = self.chunks[idx]
            score = 0.0

            # 文本匹配
            text_lower = chunk.text.lower()
            text_terms = set(re.findall(r'\w+', text_lower))

            # 精确匹配得分
            if query_lower in text_lower:
                score += 10.0

            # 词项重叠得分
            overlap = query_terms & text_terms
            if overlap:
                score += len(overlap) / max(len(query_terms), 1) * 5.0

            # 标题匹配
            if chunk.section and query_lower in chunk.section.lower():
                score += 3.0

            # 来源匹配
            if chunk.source and query_lower in chunk.source.lower():
                score += 1.0

            if score > 0:
                scored_chunks.append((chunk, score))

        # 排序并返回top_k
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

    def search_by_spin_stage(
        self,
        spin_stage: str,
        top_k: int = 5
    ) -> List[KnowledgeChunk]:
        """按SPIN阶段搜索"""
        results = self.search("", spin_stage=spin_stage, top_k=top_k)
        return [chunk for chunk, score in results]

    def search_by_category(
        self,
        category: str,
        top_k: int = 5
    ) -> List[KnowledgeChunk]:
        """按类别搜索"""
        results = self.search("", category=category, top_k=top_k)
        return [chunk for chunk, score in results]

    def get_categories(self) -> List[str]:
        """获取所有类别"""
        return list(self.category_index.keys())

    def get_spin_stages(self) -> List[str]:
        """获取所有SPIN阶段"""
        return list(self.spin_index.keys())

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_chunks": len(self.chunks),
            "categories": {
                cat: len(ids) for cat, ids in self.category_index.items()
            },
            "spin_stages": {
                stage: len(ids) for stage, ids in self.spin_index.items()
            },
            "sources": {
                source: len(ids) for source, ids in self.source_index.items()
            }
        }

    def export_to_json(self, output_path: str):
        """导出到JSON文件"""
        data = {
            "stats": self.get_stats(),
            "chunks": [c.to_dict() for c in self.chunks]
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_json(cls, json_path: str) -> "KnowledgeIndex":
        """从JSON文件加载"""
        index = cls()
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        chunks = [KnowledgeChunk.from_dict(c) for c in data.get("chunks", [])]
        index.add_chunks(chunks)
        return index

    def build_from_markdown(self, markdown_path: str, book_name: str) -> int:
        """
        从Markdown文件构建索引

        处理书籍格式：
        - ## 4.1 背景问题 -> SPIN stage
        - ## 标题 -> section
        """
        from app.services.knowledge.process_markdown import MarkdownKnowledgeProcessor

        processor = MarkdownKnowledgeProcessor()

        if "SPIN" in book_name:
            chunks = processor.process_spin_book(markdown_path)
        elif "解决方案销售" in book_name:
            chunks = processor.process_solution_selling_book(markdown_path)
        elif "战略营销" in book_name:
            chunks = processor.process_strategic_marketing_book(markdown_path)
        else:
            return 0

        self.add_chunks(chunks)
        return len(chunks)


# 单例
_knowledge_index: Optional[KnowledgeIndex] = None


def get_knowledge_index() -> KnowledgeIndex:
    """获取知识索引单例"""
    global _knowledge_index
    if _knowledge_index is None:
        _knowledge_index = KnowledgeIndex()
    return _knowledge_index