"""
Knowledge Base Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class ChunkBase(BaseModel):
    """Base chunk schema."""
    text: str = Field(..., description="Chunk text content")
    source: Optional[str] = Field(None, description="Source document name")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Additional metadata")


class ChunkCreate(ChunkBase):
    """Schema for creating a chunk."""
    document_id: str = Field(..., description="Parent document ID")


class ChunkResponse(ChunkBase):
    """Schema for chunk response."""
    id: str
    document_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    """Base document schema."""
    name: str = Field(..., description="Document name")
    source_type: str = Field(..., description="Type: pdf, doc, url")


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""
    file_path: Optional[str] = None


class DocumentResponse(DocumentBase):
    """Schema for document response."""
    id: str
    chunk_count: int = 0
    status: str = "pending"  # pending, processing, completed, failed
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeSearchRequest(BaseModel):
    """Schema for knowledge base search request."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, description="Number of results to return", ge=1, le=20)
    source_filter: Optional[str] = Field(None, description="Filter by source")
    category: Optional[str] = Field(None, description="Filter by category (spin, solution_selling, etc.)")


class KnowledgeSearchResult(BaseModel):
    """Schema for a single search result."""
    id: str
    text: str = Field(..., description="Chunk text content")
    source: str = Field(..., description="Source document name")
    score: float = Field(..., description="Relevance score (0-1)")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class KnowledgeSearchResponse(BaseModel):
    """Schema for knowledge base search response."""
    results: List[KnowledgeSearchResult]
    query: str
    total: int


class KnowledgeIngestRequest(BaseModel):
    """Schema for ingesting a new document."""
    file_path: str = Field(..., description="Path to the file to ingest")
    category: str = Field(..., description="Category: spin, strategic_marketing, solution_selling")


class KnowledgeIngestResponse(BaseModel):
    """Schema for ingest response."""
    document_id: str
    status: str  # processing, completed, failed
    chunk_count: int = 0
    message: str


class KnowledgeStats(BaseModel):
    """Schema for knowledge base statistics."""
    total_documents: int = 0
    total_chunks: int = 0
    documents_by_category: Dict[str, int] = {}
    chunks_by_source: Dict[str, int] = {}


class SPINQuestionRequest(BaseModel):
    """Schema for SPIN question generation request."""
    customer_industry: str = Field(..., description="Customer's industry")
    customer_scale: str = Field(..., description="Customer's company scale")
    pain_points: List[str] = Field(..., description="Customer's pain points")
    context: Optional[str] = Field(None, description="Additional context")


class SPINQuestionResponse(BaseModel):
    """Schema for SPIN question generation response."""
    situation_questions: List[str]
    problem_questions: List[str]
    implication_questions: List[str]
    need_payoff_questions: List[str]
    context_used: List[str] = Field(default_factory=list, description="Knowledge chunks used as context")


class ConversationContextRequest(BaseModel):
    """Schema for retrieving conversation context."""
    scenario_type: str = Field(..., description="Type of scenario")
    customer_profile: Dict = Field(..., description="Customer profile details")
    topic_focus: Optional[str] = Field(None, description="Specific topic to focus on")


class ConversationContextResponse(BaseModel):
    """Schema for conversation context retrieval."""
    relevant_knowledge: List[KnowledgeSearchResult]
    suggested_topics: List[str]
    talking_points: List[str] = Field(default_factory=list, description="Suggested talking points")