"""
Practice module - database models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Float, JSON, Integer
from sqlalchemy.orm import relationship
from app.database import Base

# Use JSON for SQLite compatibility
JSONB = JSON


class Scenario(Base):
    """Scenario model for practice sessions"""
    __tablename__ = "scenarios"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)  # 初次拜访/产品讲解/价格谈判/竞品对比/异议处理/促成成交/售后维护
    category = Column(String(50), nullable=True)  # 行业分类
    sub_category = Column(String(50), nullable=True)  # 产品线分类
    default_role_config = Column(JSON, default={})  # 默认角色配置
    is_builtin = Column(Boolean, default=True)  # 是否内置
    status = Column(String(20), default="approved")  # pending/approved/rejected
    created_by = Column(String(36), nullable=True)
    approved_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    practice_sessions = relationship("PracticeSession", back_populates="scenario")


class PracticeSession(Base):
    """Practice session model"""
    __tablename__ = "practice_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scenario_id = Column(String(36), ForeignKey("scenarios.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)  # Nullable for anonymous users
    role_config = Column(JSON, default={})  # 角色配置
    customer_context = Column(JSON, default=None)  # SPIN客户背景（行业、规模、痛点）
    investigation_result = Column(JSON, default=None)  # AI调查的客户详细信息
    user_context = Column(JSON, default=None)  # 销售员自填的练习档案（职级/年限/重点/难度/备注）
    status = Column(String(20), default="active")  # active/completed/archived
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    current_phase = Column(String(20), default="discovery")  # Current practice phase
    message_count = Column(Integer, default=0)  # Message count

    # Relationships
    scenario = relationship("Scenario", back_populates="practice_sessions")
    user = relationship("User", back_populates="practice_sessions")
    messages = relationship("PracticeMessage", back_populates="session")


class PracticeMessage(Base):
    """Practice message model"""
    __tablename__ = "practice_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("practice_sessions.id"), nullable=False)
    role = Column(String(10), nullable=False)  # user/ai
    content = Column(Text, nullable=False)
    audio_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("PracticeSession", back_populates="messages")


class AIClientRole(Base):
    """AI Client role configuration model"""
    __tablename__ = "ai_client_roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    position_level = Column(String(50), nullable=False)  # 岗位级别
    personality = Column(String(50), nullable=False)  # 性格特征
    decision_style = Column(String(50), nullable=False)  # 决策风格
    context_window = Column(Text, nullable=True)  # 上下文记忆
    created_at = Column(DateTime, default=datetime.utcnow)


class PracticeSummary(Base):
    """Practice phase summary model"""
    __tablename__ = "practice_summaries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("practice_sessions.id"), nullable=False)
    trigger_type = Column(String(20), nullable=False)  # auto/manual
    rounds = Column(String(10), nullable=False)  # 总结的轮次
    good_points = Column(JSON, default=[])  # 做得好
    improvements = Column(JSON, default=[])  # 需改进
    suggestions = Column(JSON, default=[])  # 建议
    positive_ratio = Column(Float, default=0.0)  # 正向比率
    scores = Column(JSON, default={})  # 各维度评分
    created_at = Column(DateTime, default=datetime.utcnow)


class PracticeReport(Base):
    """Practice report model"""
    __tablename__ = "practice_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("practice_sessions.id"), nullable=False)
    communication_score = Column(Float, default=0.0)  # 沟通力 25%
    persuasion_score = Column(Float, default=0.0)  # 说服力 30%
    closing_score = Column(Float, default=0.0)  # 成单导向 25%
    spin_score = Column(Float, default=0.0)  # SPIN运用 20%
    summary = Column(Text, nullable=True)  # 整体总结
    key_points = Column(JSON, default=[])  # 对话要点
    improvements = Column(JSON, default=[])  # 改进建议
    pdf_url = Column(String(500), nullable=True)
    share_token = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IndustryBrief(Base):
    """Industry brief / 行业简报 model.

    A brief is a collection of structured news items on a given industry
    or topic, generated on demand (MVP) by an LLM. Future iterations may
    also pull from real RSS/feed sources.
    """
    __tablename__ = "industry_briefs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)            # e.g. "AI 芯片 行业动态 (2026-06-04)"
    industry = Column(String(80), nullable=True)           # e.g. "科技软件"
    keywords = Column(String(500), nullable=True)          # free-form keywords used to scope the brief
    summary = Column(Text, nullable=True)                  # 1-2 段 executive summary
    items = Column(JSON, default=[])                       # list of {title, url, source, source_level, published_at, raw_excerpt, summary}
    key_takeaways = Column(JSON, default=[])              # list of strings
    # === 真实新闻字段 ===
    brief_date = Column(DateTime, nullable=True)            # 简报"日期"（按推送日）
    news_count = Column(Integer, default=0)                # 该简报含多少条新闻
    is_legacy_ai = Column(Boolean, default=False)           # True=旧 LLM 编造版（要加 disclaimer）
    status = Column(String(20), default="ready")           # generating/ready/failed
    error = Column(Text, nullable=True)
    generated_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    """站内通知 — 简报推送、报告生成等事件"""
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)            # brief_ready | report_ready | system
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    link = Column(String(500), nullable=True)             # 点击跳转 URL
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
