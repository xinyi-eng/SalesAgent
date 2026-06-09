"""
Embedding服务 - 文本向量化
"""
import os
from typing import List, Optional
from abc import ABC, abstractmethod


class _BGEMeanPoolModel:
    """
    Lightweight BGE embedder using transformers + manual mean pooling.

    BAAI/bge-base-zh-v1.5 is just a BERT encoder with:
      - mean pooling (attention-mask weighted)
      - L2 normalization
    This sidesteps sentence_transformers' CrossEncoder/PreTrainedModel
    import chain which breaks on Windows when torchvision is missing
    or version-mismatched.
    """

    def __init__(self, model_name: str = "BAAI/bge-base-zh-v1.5"):
        import torch
        from transformers import AutoTokenizer, AutoModel

        cache = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache)
        # Force safetensors loader: pytorch_model.bin requires torch>=2.6
        # due to a CVE restriction in transformers 4.57+. BGE ships both,
        # so safetensors is the path of least resistance on this env.
        self.model = AutoModel.from_pretrained(
            model_name, cache_dir=cache, use_safetensors=True
        )
        self.model.eval()
        self.dim = int(self.model.config.hidden_size)

    def _mean_pool(self, last_hidden, attention_mask):
        import torch
        mask = attention_mask.unsqueeze(-1).float()
        summed = (last_hidden * mask).sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1e-9)
        return summed / counts

    def _embed_one(self, text: str) -> List[float]:
        import torch
        with torch.no_grad():
            encoded = self.tokenizer(
                [text], padding=True, truncation=True, max_length=512, return_tensors="pt"
            )
            out = self.model(**encoded)
            pooled = self._mean_pool(out.last_hidden_state, encoded["attention_mask"])
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return pooled[0].cpu().tolist()

    def encode(self, texts) -> List[List[float]]:
        """Mimic sentence_transformers.encode() for drop-in compat."""
        return [self._embed_one(t) for t in texts]

    def get_sentence_embedding_dimension(self) -> int:
        return self.dim


class EmbeddingModel(ABC):
    """Embedding模型抽象基类"""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """将文本列表转换为向量"""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """将单个查询文本转换为向量"""
        pass


class LocalEmbeddingModel(EmbeddingModel):
    """
    本地Embedding模型

    使用 sentence-transformers 加载本地模型
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._is_loaded = False

    def _load_model(self):
        """懒加载模型"""
        if self._is_loaded:
            return

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._is_loaded = True
            print(f"Loaded embedding model: {self.model_name}")
        except ImportError:
            print("sentence-transformers not installed, using mock embedding")
            self._is_loaded = True

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量文本向量化"""
        self._load_model()

        if self._model is None:
            # Mock embedding for testing
            return [[0.1] * 384 for _ in texts]

        return self._model.encode(texts).tolist()

    def embed_query(self, query: str) -> List[float]:
        """单个查询向量化"""
        return self.embed([query])[0]


class HashEmbeddingModel(EmbeddingModel):
    """
    基于Hash的确定性Embedding - 生成一致的正则化向量

    用于离线环境或无法下载模型时，提供确定性的向量搜索
    基于文本的hash生成pseudo-embeddings，虽然不是语义向量，
    但能支持向量数据库的相似度搜索（至少相似文本会有相似的向量）
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self._rng_seed = 42  # 固定种子保证一致性

    def _hash_text(self, text: str) -> List[float]:
        """基于文本hash生成确定性向量，使用字符n-gram提高相似文本的相似度"""
        import hashlib
        import re

        # 使用多个hash函数增加随机性
        vectors = []

        # 提取中文词汇作为特征（简单分词）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        english_words = re.findall(r'[a-zA-Z]+', text)
        all_features = []
        for chars in chinese_chars:
            all_features.extend(list(chars))  # 单字作为特征
        all_features.extend(english_words)  # 英文词作为特征

        for i in range(self.dimension):
            # 基于文本特征和维度索引的hash
            # 使用不同的seed增加变化
            seed_input = f"{text}_{i}_sales_agent_vector"
            hash_obj = hashlib.md5(seed_input.encode('utf-8'))
            # 取hash的前4字节转换为float
            hash_bytes = hash_obj.digest()
            val = int.from_bytes(hash_bytes[:4], byteorder='big') / (2**32 - 1)
            vectors.append(val)

        # 基于特征字符的额外向量（让相似文本有相似向量）
        if all_features:
            char_vector = [0.0] * self.dimension
            for char_idx, char in enumerate(all_features[:100]):  # 限制特征数量
                char_hash = hashlib.md5(char.encode('utf-8')).digest()
                for vec_idx in range(min(16, self.dimension)):
                    idx = (char_idx * 17 + vec_idx) % self.dimension
                    byte_val = char_hash[vec_idx % 4] / 255.0
                    char_vector[idx] += byte_val

            # 归一化
            magnitude = sum(v * v for v in char_vector) ** 0.5
            if magnitude > 0:
                char_vector = [v / magnitude for v in char_vector]

            # 混合原始向量和字符向量
            for i in range(self.dimension):
                vectors[i] = 0.7 * vectors[i] + 0.3 * char_vector[i]

        return vectors

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量文本向量化"""
        return [self._hash_text(text) for text in texts]

    def embed_query(self, query: str) -> List[float]:
        """单个查询向量化"""
        return self._hash_text(query)


class MockEmbeddingModel(EmbeddingModel):
    """
    MockEmbedding - 用于测试或无GPU环境

    返回固定维度随机向量
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed(self, texts: List[str]) -> List[List[float]]:
        """返回随机向量"""
        import random
        return [
            [random.random() for _ in range(self.dimension)]
            for _ in texts
        ]

    def embed_query(self, query: str) -> List[float]:
        """返回随机向量"""
        return self.embed([query])[0]


class ChineseEmbeddingModel(EmbeddingModel):
    """
    中文Embedding模型

    使用 text2vec-base-chinese 或 m3e
    离线时使用 HashEmbeddingModel 作为后备
    """

    def __init__(self, model_name: str = "BAAI/bge-base-zh-v1.5"):
        self.model_name = model_name
        self._model = None
        self._is_loaded = False
        # 环境变量控制是否离线模式
        # Default: BGE 已经在本地缓存（HF_ENDPOINT=https://hf-mirror.com），
        # 走在线模式。如果 chromadb 已有数据但模型没下，可以临时
        # 设 EMBEDDING_OFFLINE=true 跳过下载。
        self._offline = os.getenv("EMBEDDING_OFFLINE", "false").lower() == "true"
        # 本地模型路径（如果有的话）
        self._local_model_path = os.getenv("EMBEDDING_MODEL_PATH", None)
        # HF 镜像（中国大陆常用 hf-mirror.com 解决 SSL/访问问题）
        self._hf_endpoint = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
        # Hash embedding后备
        self._hash_embedding = HashEmbeddingModel(dimension=768)

    def _load_model(self):
        """懒加载模型

        优先用 sentence_transformers（封装的 mean pooling + 归一化）。
        如果它在 Windows 上因为 torchvision / transformers 版本不匹配
        失败，回退到 transformers + 手写 mean pooling —— BGE 本质就是
        BERT + masked mean pooling + L2 norm，几十行就能写完。
        """
        if self._is_loaded:
            return

        if self._offline:
            print("Embedding offline mode - using hash embeddings")
            self._is_loaded = True
            return

        # Windows 上 PyTorch 原生库不在 PATH 上，先补上
        try:
            import torch, os.path as _p
            torch_lib = _p.join(_p.dirname(torch.__file__), "lib")
            if _p.isdir(torch_lib):
                if hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(torch_lib)
                os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")
        except Exception:
            pass

        os.environ.setdefault("HF_ENDPOINT", self._hf_endpoint)
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "0")

        # 路径 1：sentence_transformers（封装好 mean pooling）
        try:
            from sentence_transformers import SentenceTransformer
            cache_folder = os.path.join(os.path.expanduser("~"), ".cache", "sentence_transformers")
            print(f"Loading embedding model (sentence_transformers): {self.model_name}")
            self._model = SentenceTransformer(self.model_name, cache_folder=cache_folder)
            print(f"[OK] Loaded BGE via sentence_transformers (dim={self._model.get_sentence_embedding_dimension()})")
            self._is_loaded = True
            return
        except Exception as e:
            print(f"[WARN] sentence_transformers load failed: {e}, falling back to transformers+mean-pooling")

        # 路径 2：transformers AutoModel + 手写 mean pooling
        try:
            self._model = _BGEMeanPoolModel(self.model_name)
            print(f"[OK] Loaded BGE via transformers+mean-pooling (dim={self._model.dim})")
            self._is_loaded = True
        except Exception as e:
            print(f"[FAIL] Failed to load Chinese embedding model: {e}")
            print(f"  Falling back to hash embeddings.")
            self._is_loaded = True

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量文本向量化"""
        self._load_model()

        if self._model is None:
            return self._hash_embedding.embed(texts)

        out = self._model.encode(texts)
        # SentenceTransformer returns a numpy array; _BGEMeanPoolModel
        # returns a Python list. Coerce both to a list-of-list-of-floats.
        try:
            return out.tolist()  # numpy / tensor
        except AttributeError:
            return [list(v) for v in out]  # already python list

    def embed_query(self, query: str) -> List[float]:
        """单个查询向量化"""
        self._load_model()

        if self._model is None:
            return self._hash_embedding.embed_query(query)

        return self.embed([query])[0]


# 单例
_embedding_model: Optional[EmbeddingModel] = None


def get_embedding_model() -> EmbeddingModel:
    """获取Embedding模型单例"""
    global _embedding_model
    if _embedding_model is None:
        # 根据环境变量选择模型
        model_type = os.getenv("EMBEDDING_MODEL", "chinese")

        if model_type == "chinese":
            _embedding_model = ChineseEmbeddingModel()
        elif model_type == "local":
            _embedding_model = LocalEmbeddingModel()
        else:
            _embedding_model = MockEmbeddingModel()

    return _embedding_model


def reset_embedding_model():
    """重置Embedding模型（用于切换模型）"""
    global _embedding_model
    _embedding_model = None