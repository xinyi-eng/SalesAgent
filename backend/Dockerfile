"""
SalesAgent Backend Dockerfile
- 基于 python:3.12-slim
- 安装 ffmpeg（ASR 用）+ 系统依赖
- 安装 Python 依赖
- 暴露 8002 端口
"""
FROM python:3.12-slim

# 系统依赖：ffmpeg（ASR 必用）、build tools（sentence-transformers / chromadb 编译）
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      build-essential \
      gcc \
      libpq-dev \
      curl \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依赖先装（缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 数据 / 日志目录
RUN mkdir -p /app/data /app/logs /app/data/chroma

# 环境变量默认值（运行时通过 .env 覆盖）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8002 \
    HF_ENDPOINT=https://hf-mirror.com

EXPOSE 8002

# 健康检查（每 30s 探一次）
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://localhost:${PORT}/health || exit 1

# 启动
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
