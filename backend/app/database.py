"""
Database connection and session management
"""
import uuid as _uuid
from sqlalchemy import create_engine, event, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# 注册 UUID type 的 SQLite adapter — 避免 SQLAlchemy 2.0 + SQLite
# 报 "type 'UUID' is not supported"。Models 里把 UUID 字段都当
# CHAR(36) 字符串存，Python 端保持 UUID 对象。
class _UUIDString(types.TypeDecorator):
    impl = types.CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, _uuid.UUID):
            return str(value)
        return str(_uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, _uuid.UUID):
            return value
        return _uuid.UUID(value)


# 在所有 model import 之前，把 sqlalchemy.types.UUID 替换成我们的实现
# 这样现有 model 不用改
import sqlalchemy.types as _st
_st.UUID = _UUIDString

# SQLite 需要 busy_timeout + WAL 模式来应对并发锁。
# APScheduler 跑 industry_brief 时会和 FastAPI 请求争用同一文件，
# 默认 lock_immediate 会立刻抛 "database is locked"。
# busy_timeout=30 让 SQLite 内部重试 30 秒，把冲突从错误变成延迟。
_engine_kwargs = {"echo": settings.DEBUG}
if settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"timeout": 30, "check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """在每个 SQLite 连接上启用 WAL + busy_timeout"""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    # WAL 模式：读写并发不互斥
    cursor.execute("PRAGMA journal_mode=WAL")
    # busy_timeout：被锁时等待 30 秒再报错
    cursor.execute("PRAGMA busy_timeout=30000")
    # 外键约束
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()