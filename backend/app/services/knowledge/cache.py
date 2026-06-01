"""
知识检索缓存 - 5分钟短期缓存
FR-6: 知识检索结果缓存
"""
import time
import hashlib
from typing import Optional, Dict, Any
from threading import Lock


class KnowledgeCache:
    """知识检索结果缓存"""

    def __init__(self, ttl_seconds: int = 300):  # 5分钟TTL
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
        self._lock = Lock()

    def _make_key(self, query: str, category: str, top_k: int) -> str:
        """生成缓存key"""
        raw = f"{query}:{category}:{top_k}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, query: str, category: str, top_k: int) -> Optional[str]:
        """获取缓存结果"""
        key = self._make_key(query, category, top_k)

        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                # 检查是否过期
                if time.time() - entry["timestamp"] < self._ttl:
                    return entry["result"]
                else:
                    # 已过期，删除
                    del self._cache[key]

        return None

    def set(self, query: str, category: str, top_k: int, result: str):
        """设置缓存"""
        key = self._make_key(query, category, top_k)

        with self._lock:
            self._cache[key] = {
                "result": result,
                "timestamp": time.time()
            }

    def clear_expired(self):
        """清理过期缓存"""
        with self._lock:
            now = time.time()
            expired_keys = [
                k for k, v in self._cache.items()
                if now - v["timestamp"] >= self._ttl
            ]
            for k in expired_keys:
                del self._cache[k]

    def clear_all(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            now = time.time()
            valid_entries = [
                k for k, v in self._cache.items()
                if now - v["timestamp"] < self._ttl
            ]
            return {
                "total_entries": len(self._cache),
                "valid_entries": len(valid_entries),
                "expired_entries": len(self._cache) - len(valid_entries)
            }


# 全局缓存实例
knowledge_cache = KnowledgeCache(ttl_seconds=300)