"""
SPIN Schemas - Pydantic models for SPIN question generation
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID


class CustomerContext(BaseModel):
    """Customer background information for SPIN generation"""
    industry: str = Field(..., description="客户行业，如：制造业、医疗、教育、零售")
    scale: str = Field(..., description="客户规模，如：中小企业、中大型企业、集团企业")
    pain_points: List[str] = Field(..., description="客户痛点列表")


class SpinQuestionsRequest(BaseModel):
    """Request for SPIN question generation"""
    customer: CustomerContext


class SpinQuestionList(BaseModel):
    """SPIN question list response"""
    question_list_id: str = Field(..., description="问题清单ID")
    situation_questions: List[str] = Field(default_factory=list, description="Situation问题-了解现状")
    problem_questions: List[str] = Field(default_factory=list, description="Problem问题-发现痛点")
    implication_questions: List[str] = Field(default_factory=list, description="Implication问题-放大影响")
    need_payoff_questions: List[str] = Field(default_factory=list, description="Need-payoff问题-引导价值")
    customer_context: CustomerContext
    created_at: str


class SpinQuestionResponse(BaseModel):
    """Response for SPIN question generation"""
    success: bool
    data: Optional[SpinQuestionList] = None
    error: Optional[str] = None
