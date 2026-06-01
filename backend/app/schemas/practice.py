"""
Practice module - Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


# Scenario schemas
class ScenarioBase(BaseModel):
    """Base scenario schema"""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    type: str = Field(..., max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    sub_category: Optional[str] = Field(None, max_length=50)
    default_role_config: dict = Field(default_factory=dict)


class ScenarioCreate(ScenarioBase):
    """Create scenario schema"""
    pass


class ScenarioUpdate(BaseModel):
    """Update scenario schema"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    type: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    sub_category: Optional[str] = Field(None, max_length=50)
    default_role_config: Optional[dict] = None


class ScenarioResponse(ScenarioBase):
    """Scenario response schema"""
    id: UUID
    is_builtin: bool
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    """Scenario list response schema"""
    data: List[ScenarioResponse]
    total: int


# Role config schemas
class RoleConfig(BaseModel):
    """Role configuration schema"""
    position_level: str = Field(..., description="岗位级别")
    personality: str = Field(..., description="性格特征")
    decision_style: str = Field(..., description="决策风格")


# Session schemas
class SessionCreate(BaseModel):
    """Create practice session schema"""
    scenario_id: UUID
    role_config: RoleConfig


class SessionResponse(BaseModel):
    """Session response schema"""
    id: UUID
    scenario_id: UUID
    user_id: UUID
    role_config: dict
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionCreateResponse(BaseModel):
    """Session create response with first message"""
    session_id: UUID
    websocket_url: str
    first_message: str


# Practice message schemas
class MessageResponse(BaseModel):
    """Practice message response"""
    id: UUID
    session_id: UUID
    role: str
    content: str
    audio_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# AI Client Role schemas
class AIClientRoleBase(BaseModel):
    """Base AI client role schema"""
    position_level: str = Field(..., max_length=50)
    personality: str = Field(..., max_length=50)
    decision_style: str = Field(..., max_length=50)
    context_window: Optional[str] = None


class AIClientRoleCreate(AIClientRoleBase):
    """Create AI client role schema"""
    pass


class AIClientRoleResponse(AIClientRoleBase):
    """AI client role response"""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Summary schemas
class SummaryCreate(BaseModel):
    """Create summary schema"""
    trigger: str = Field(..., description="auto or manual")
    rounds: int = Field(default=3, description="Number of rounds to summarize")


class SummaryResponse(BaseModel):
    """Summary response schema"""
    id: UUID
    session_id: UUID
    trigger_type: str
    rounds: str
    good_points: List[str]
    improvements: List[str]
    suggestions: List[str]
    positive_ratio: float
    created_at: datetime

    class Config:
        from_attributes = True


# Report schemas
class ReportResponse(BaseModel):
    """Report response schema"""
    id: UUID
    session_id: UUID
    communication_score: float
    persuasion_score: float
    closing_score: float
    spin_score: float
    summary: Optional[str]
    key_points: List[str]
    improvements: List[str]
    pdf_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Session List schemas
class SessionListItem(BaseModel):
    """Session list item schema"""
    id: UUID
    scenario_id: UUID
    scenario_name: Optional[str] = None
    scenario_type: Optional[str] = None
    user_id: Optional[str] = None
    role_config: dict
    status: str
    current_phase: Optional[str] = None
    score: Optional[float] = None
    message_count: int = 0
    duration_minutes: int = 0
    created_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Session list response schema"""
    data: List[SessionListItem]
    total: int
    page: int
    page_size: int


class DashboardStats(BaseModel):
    """Dashboard statistics schema"""
    total_sessions: int = 0
    total_time_minutes: int = 0
    avg_score: Optional[float] = None
    improvement_rate: float = 0.0
    this_week_sessions: int = 0
    this_week_time: int = 0
    this_week_score: Optional[float] = None
    streak_days: int = 0


class HistoryStats(BaseModel):
    """History statistics schema"""
    sessions: int = 0
    completed: int = 0
    duration_minutes: int = 0
    messages: int = 0
    avg_score: Optional[float] = None


class HistoryStatsResponse(BaseModel):
    """History stats response schema"""
    last_30_days: HistoryStats
    last_90_days: HistoryStats


# WebSocket message schemas
class WSUserMessage(BaseModel):
    """WebSocket user message"""
    type: str = "user_message"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSAIMessage(BaseModel):
    """WebSocket AI message"""
    type: str = "ai_message"
    content: str
    audio_url: Optional[str] = None
    stream: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)