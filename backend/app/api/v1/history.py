"""
Practice history API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.practice import PracticeSession, PracticeSummary
from app.core.security import get_current_user

router = APIRouter(prefix="/users/me/history", tags=["练习历史"])


class HistorySessionResponse(BaseModel):
    """Practice session for history list"""
    id: str
    scenario_name: str
    scenario_type: str
    role_config: dict
    status: str
    current_phase: str
    score: Optional[float]
    duration_minutes: int
    message_count: int
    created_at: datetime
    ended_at: Optional[datetime]


# Fix import
from pydantic import BaseModel


class HistorySessionResponse(BaseModel):
    """Practice session for history list"""
    id: str
    scenario_name: str
    scenario_type: str
    role_config: dict
    status: str
    current_phase: str
    score: Optional[float]
    duration_minutes: int
    message_count: int
    created_at: datetime
    ended_at: Optional[datetime]

    class Config:
        from_attributes = True


class HistoryListResponse(BaseModel):
    """List of practice history"""
    data: List[HistorySessionResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=HistoryListResponse)
async def get_practice_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scenario_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user practice history with pagination

    - Filter by scenario_type, date range
    - Sort by created_at desc
    """
    query = db.query(PracticeSession).filter(
        PracticeSession.user_id == current_user.id
    )

    # Apply filters
    if scenario_type:
        query = query.filter(PracticeSession.scenario.has(type=scenario_type))

    if start_date:
        query = query.filter(PracticeSession.created_at >= start_date)

    if end_date:
        query = query.filter(PracticeSession.created_at <= end_date)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    sessions = query.order_by(
        PracticeSession.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()

    # Build response
    history_data = []
    for session in sessions:
        # Calculate duration
        duration = 0
        if session.started_at and session.ended_at:
            duration = int((session.ended_at - session.started_at).seconds / 60)

        # Get latest score if summary exists
        score = None
        latest_summary = db.query(PracticeSummary).filter(
            PracticeSummary.session_id == session.id
        ).order_by(PracticeSummary.created_at.desc()).first()
        if latest_summary:
            score = latest_summary.overall_score

        history_data.append(HistorySessionResponse(
            id=str(session.id),
            scenario_name=session.scenario.name if session.scenario else "Unknown",
            scenario_type=session.scenario.type if session.scenario else "",
            role_config=session.role_config or {},
            status=session.status,
            current_phase=session.current_phase,
            score=score,
            duration_minutes=duration,
            message_count=session.message_count or 0,
            created_at=session.created_at,
            ended_at=session.ended_at
        ))

    return HistoryListResponse(
        data=history_data,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/summary")
async def get_history_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get practice history summary (last 30 days, 90 days, all time)
    """
    now = datetime.utcnow()

    def get_summary(days: int) -> dict:
        start = now - timedelta(days=days)
        sessions = db.query(PracticeSession).filter(
            PracticeSession.user_id == current_user.id,
            PracticeSession.created_at >= start
        ).all()

        total_duration = 0
        total_messages = 0
        completed = 0
        scores = []

        for s in sessions:
            if s.started_at and s.ended_at:
                total_duration += (s.ended_at - s.started_at).seconds / 60
            total_messages += s.message_count or 0
            if s.status == 'completed':
                completed += 1

            # Get average score from summaries
            summary = db.query(PracticeSummary).filter(
                PracticeSummary.session_id == s.id
            ).first()
            if summary and summary.overall_score:
                scores.append(summary.overall_score)

        avg_score = sum(scores) / len(scores) if scores else None

        return {
            "sessions": len(sessions),
            "completed": completed,
            "duration_minutes": int(total_duration),
            "messages": total_messages,
            "avg_score": round(avg_score, 1) if avg_score else None
        }

    return {
        "last_30_days": get_summary(30),
        "last_90_days": get_summary(90),
        "all_time": {
            "sessions": db.query(PracticeSession).filter(
                PracticeSession.user_id == current_user.id
            ).count(),
            "duration_minutes": 0,
            "messages": 0,
            "avg_score": None
        }
    }