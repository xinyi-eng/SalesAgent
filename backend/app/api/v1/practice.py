"""
Practice API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.database import get_db
from app.models.practice import Scenario, PracticeSession, AIClientRole, PracticeMessage
from app.schemas.practice import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioResponse,
    ScenarioListResponse,
    SessionCreate,
    SessionResponse,
    SessionCreateResponse,
    SessionListItem,
    SessionListResponse,
    DashboardStats,
    HistoryStats,
    HistoryStatsResponse,
    AIClientRoleCreate,
    AIClientRoleResponse
)

router = APIRouter(prefix="/practice", tags=["话术对练"])


# ============== Scenario Endpoints ==============

@router.get("/scenarios", response_model=ScenarioListResponse)
async def get_scenarios(
    category: Optional[str] = None,
    sub_category: Optional[str] = None,
    type: Optional[str] = None,
    is_builtin: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    获取场景列表

    - 支持按行业分类、产品线分类、场景类型筛选
    - 内置场景优先展示
    """
    query = db.query(Scenario).filter(Scenario.status == "approved")

    if category:
        query = query.filter(Scenario.category == category)
    if sub_category:
        query = query.filter(Scenario.sub_category == sub_category)
    if type:
        query = query.filter(Scenario.type == type)
    if is_builtin is not None:
        query = query.filter(Scenario.is_builtin == is_builtin)

    scenarios = query.order_by(Scenario.is_builtin.desc(), Scenario.created_at.desc()).all()

    return ScenarioListResponse(
        data=[ScenarioResponse.model_validate(s) for s in scenarios],
        total=len(scenarios)
    )


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(scenario_id: UUID, db: Session = Depends(get_db)):
    """获取单个场景详情"""
    scenario = db.query(Scenario).filter(Scenario.id == str(scenario_id)).first()
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="场景不存在"
        )
    return scenario


@router.post("/scenarios", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    scenario: ScenarioCreate,
    db: Session = Depends(get_db)
):
    """创建新场景（管理员/PM/FAE）"""
    db_scenario = Scenario(**scenario.model_dump())
    db.add(db_scenario)
    db.commit()
    db.refresh(db_scenario)
    return db_scenario


@router.put("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: UUID,
    scenario_update: ScenarioUpdate,
    db: Session = Depends(get_db)
):
    """更新场景"""
    db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not db_scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="场景不存在"
        )

    update_data = scenario_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_scenario, key, value)

    db.commit()
    db.refresh(db_scenario)
    return db_scenario


@router.delete("/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(scenario_id: UUID, db: Session = Depends(get_db)):
    """删除场景（仅非内置场景）"""
    db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not db_scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="场景不存在"
        )

    if db_scenario.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="内置场景不能删除"
        )

    db.delete(db_scenario)
    db.commit


# ============== Session Endpoints ==============

@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(
    session_data: SessionCreate,
    user_id: Optional[UUID] = None,  # Optional: defaults to "anonymous" if not provided
    db: Session = Depends(get_db)
):
    """
    创建对练会话

    - 验证场景存在
    - 初始化会话
    - 生成WebSocket URL
    - 触发AI客户首句话
    """
    # Verify scenario exists
    scenario = db.query(Scenario).filter(
        Scenario.id == str(session_data.scenario_id),
        Scenario.status == "approved"
    ).first()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="场景不存在或未审核通过"
        )

    # Create practice session
    # Use default anonymous user if not provided
    effective_user_id = user_id or "anonymous"
    db_session = PracticeSession(
        scenario_id=str(session_data.scenario_id),
        user_id=effective_user_id,
        role_config=session_data.role_config.model_dump(),
        status="active"
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # In production, this would trigger LLM to generate first message
    # For now, return placeholder
    first_message = f"您好，我是{scenario.name}场景的AI客户。请问您想了解什么？"

    return SessionCreateResponse(
        session_id=db_session.id,
        websocket_url=f"/ws/practice/{db_session.id}",
        first_message=first_message
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID, db: Session = Depends(get_db)):
    """获取会话详情"""
    session = db.query(PracticeSession).filter(PracticeSession.id == str(session_id)).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # Get conversation context from session manager
    from app.websocket.manager import session_manager
    context = session_manager.get_context(str(session_id))

    if not context:
        return {
            "session_id": str(session_id),
            "overall_score": 0,
            "situation_score": 0,
            "problem_score": 0,
            "implication_score": 0,
            "need_payoff_score": 0,
            "key_strengths": [],
            "areas_for_improvement": [],
            "next_practice_focus": "暂无对话记录"
        }

    # Map "ai" to "assistant" for MiniMax API
    for msg in context:
        if msg.get("role") == "ai":
            msg["role"] = "assistant"

    # Call handler to generate SPIN evaluation
    from app.services.conversation.handler import get_conversation_handler
    handler = get_conversation_handler()

    # Get customer type from session
    role_config = session.role_config or {}
    personality = role_config.get("personality", "decisive")
    personality_map = {
        "rational": "analytical",
        "emotional": "expressive",
        "hesitant": "amiable",
        "decisive": "assertive"
    }
    customer_type = personality_map.get(personality, "assertive")

    # Generate evaluation
    evaluation = await handler.evaluate_conversation(context, customer_type)

    # Parse evaluation result (simplified - in production would parse structured JSON)
    try:
        import re
        situation_match = re.search(r'[Ss]ituation.*?(\d+)', evaluation)
        problem_match = re.search(r'[Pp]roblem.*?(\d+)', evaluation)
        implication_match = re.search(r'[Ii]mplication.*?(\d+)', evaluation)
        need_payoff_match = re.search(r'need[- ]payoff.*?(\d+)', evaluation)

        situation_score = int(situation_match.group(1)) if situation_match else 7
        problem_score = int(problem_match.group(1)) if problem_match else 7
        implication_score = int(implication_match.group(1)) if implication_match else 7
        need_payoff_score = int(need_payoff_match.group(1)) if need_payoff_match else 7
    except:
        situation_score = 7
        problem_score = 7
        implication_score = 7
        need_payoff_score = 7

    overall_score = (situation_score + problem_score + implication_score + need_payoff_score) / 4 * 10

    return {
        "session_id": str(session_id),
        "overall_score": round(overall_score, 1),
        "situation_score": situation_score * 10,
        "problem_score": problem_score * 10,
        "implication_score": implication_score * 10,
        "need_payoff_score": need_payoff_score * 10,
        "key_strengths": [
            "开场破冰自然，能快速建立信任"
        ],
        "areas_for_improvement": [
            "需求挖掘深度可以加强"
        ],
        "next_practice_focus": "建议加强Implication（影响）阶段，多追问'这会对您造成什么影响？'"
    }


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: UUID, db: Session = Depends(get_db)):
    """结束对练会话"""
    session = db.query(PracticeSession).filter(PracticeSession.id == str(session_id)).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # Get conversation context from session manager
    from app.websocket.manager import session_manager
    context = session_manager.get_context(str(session_id))

    if not context:
        return {
            "session_id": str(session_id),
            "overall_score": 0,
            "situation_score": 0,
            "problem_score": 0,
            "implication_score": 0,
            "need_payoff_score": 0,
            "key_strengths": [],
            "areas_for_improvement": [],
            "next_practice_focus": "暂无对话记录"
        }

    # Map "ai" to "assistant" for MiniMax API
    for msg in context:
        if msg.get("role") == "ai":
            msg["role"] = "assistant"

    # Call handler to generate SPIN evaluation
    from app.services.conversation.handler import get_conversation_handler
    handler = get_conversation_handler()

    # Get customer type from session
    role_config = session.role_config or {}
    personality = role_config.get("personality", "decisive")
    personality_map = {
        "rational": "analytical",
        "emotional": "expressive",
        "hesitant": "amiable",
        "decisive": "assertive"
    }
    customer_type = personality_map.get(personality, "assertive")

    # Generate evaluation
    evaluation = await handler.evaluate_conversation(context, customer_type)

    # Parse evaluation result (simplified - in production would parse structured JSON)
    try:
        import re
        situation_match = re.search(r'[Ss]ituation.*?(\d+)', evaluation)
        problem_match = re.search(r'[Pp]roblem.*?(\d+)', evaluation)
        implication_match = re.search(r'[Ii]mplication.*?(\d+)', evaluation)
        need_payoff_match = re.search(r'need[- ]payoff.*?(\d+)', evaluation)

        situation_score = int(situation_match.group(1)) if situation_match else 7
        problem_score = int(problem_match.group(1)) if problem_match else 7
        implication_score = int(implication_match.group(1)) if implication_match else 7
        need_payoff_score = int(need_payoff_match.group(1)) if need_payoff_match else 7
    except:
        situation_score = 7
        problem_score = 7
        implication_score = 7
        need_payoff_score = 7

    overall_score = (situation_score + problem_score + implication_score + need_payoff_score) / 4 * 10

    return {
        "session_id": str(session_id),
        "overall_score": round(overall_score, 1),
        "situation_score": situation_score * 10,
        "problem_score": problem_score * 10,
        "implication_score": implication_score * 10,
        "need_payoff_score": need_payoff_score * 10,
        "key_strengths": [
            "开场破冰自然，能快速建立信任"
        ],
        "areas_for_improvement": [
            "需求挖掘深度可以加强"
        ],
        "next_practice_focus": "建议加强Implication（影响）阶段，多追问'这会对您造成什么影响？'"
    }

    session.status = "completed"
    db.commit()

    return {"message": "会话已结束", "session_id": str(session_id)}


# ============== AI Client Role Endpoints ==============

@router.get("/roles", response_model=List[AIClientRoleResponse])
async def get_roles(db: Session = Depends(get_db)):
    """获取AI客户角色列表"""
    roles = db.query(AIClientRole).all()
    return roles


@router.post("/roles", response_model=AIClientRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(role: AIClientRoleCreate, db: Session = Depends(get_db)):
    """创建AI客户角色配置"""
    db_role = AIClientRole(**role.model_dump())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


@router.get("/roles/{role_id}", response_model=AIClientRoleResponse)
async def get_role(role_id: UUID, db: Session = Depends(get_db)):
    """获取单个角色详情"""
    role = db.query(AIClientRole).filter(AIClientRole.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    return role


# ============== Phase Summary Endpoints ==============

@router.post("/sessions/{session_id}/phases/{phase}/summary")
async def get_phase_summary(
    session_id: UUID,
    phase: str,
    db: Session = Depends(get_db)
):
    """
    获取指定阶段的AI总结

    - phase: opening | discovery | needs | proposal | closing
    - 基于该阶段的消息生成AI总结
    """
    session = db.query(PracticeSession).filter(PracticeSession.id == str(session_id)).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # Get conversation context from session manager
    from app.websocket.manager import session_manager
    context = session_manager.get_context(str(session_id))

    # Fallback to database if session manager has no context
    if not context:
        db_messages = db.query(PracticeMessage).filter(
            PracticeMessage.session_id == str(session_id)
        ).order_by(PracticeMessage.created_at).all()

        if db_messages:
            context = [
                {"role": msg.role, "content": msg.content, "timestamp": msg.created_at.isoformat()}
                for msg in db_messages
            ]
            # Also populate session manager with database context
            for msg in db_messages:
                session_manager.add_message(str(session_id), msg.role, msg.content)

    if not context:
        return {
            "session_id": str(session_id),
            "overall_score": 0,
            "situation_score": 0,
            "problem_score": 0,
            "implication_score": 0,
            "need_payoff_score": 0,
            "key_strengths": [],
            "areas_for_improvement": [],
            "next_practice_focus": "暂无对话记录"
        }

    # Map "ai" to "assistant" for MiniMax API
    for msg in context:
        if msg.get("role") == "ai":
            msg["role"] = "assistant"

    # Call handler to generate SPIN evaluation
    from app.services.conversation.handler import get_conversation_handler
    handler = get_conversation_handler()

    # Get customer type from session
    role_config = session.role_config or {}
    personality = role_config.get("personality", "decisive")
    personality_map = {
        "rational": "analytical",
        "emotional": "expressive",
        "hesitant": "amiable",
        "decisive": "assertive"
    }
    customer_type = personality_map.get(personality, "assertive")

    # Generate evaluation using knowledge base
    evaluation = await handler.evaluate_conversation(context, customer_type)

    # Parse evaluation result from LLM JSON response
    try:
        import re
        import json as json_lib

        # Try to extract JSON from LLM response (handle markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?})\s*```', evaluation)
        if not json_match:
            json_match = re.search(r'(\{[\s\S]*\})', evaluation)

        if json_match:
            try:
                eval_data = json_lib.loads(json_match.group(1))
                situation_score = eval_data.get('situation_score', 7) * 10
                problem_score = eval_data.get('problem_score', 7) * 10
                implication_score = eval_data.get('implication_score', 7) * 10
                need_payoff_score = eval_data.get('need_payoff_score', 7) * 10
                good_points = eval_data.get('key_strengths', ["开场时问候语得体"])
                improvements = eval_data.get('areas_for_improvement', ["在挖掘需求时可以更针对性地提问"])
                suggestions = eval_data.get('next_practice_focus', ["建议增加开放式问题了解客户背景"])
                if isinstance(good_points, str):
                    good_points = [good_points]
                if isinstance(improvements, str):
                    improvements = [improvements]
                if isinstance(suggestions, str):
                    suggestions = [suggestions]
            except json_lib.JSONDecodeError:
                # JSON found but couldn't parse, use regex fallback
                json_match = None

        if not json_match:
            # Fallback to regex parsing if no JSON found
            situation_match = re.search(r'[Ss]ituation[_\s]*score["\s:]+(\d+)', evaluation)
            problem_match = re.search(r'[Pp]roblem[_\s]*score["\s:]+(\d+)', evaluation)
            implication_match = re.search(r'[Ii]mplication[_\s]*score["\s:]+(\d+)', evaluation)
            need_payoff_match = re.search(r'need[_ ]payoff[_\s]*score["\s:]+(\d+)', evaluation)

            situation_score = int(situation_match.group(1)) * 10 if situation_match else 70
            problem_score = int(problem_match.group(1)) * 10 if problem_match else 70
            implication_score = int(implication_match.group(1)) * 10 if implication_match else 70
            need_payoff_score = int(need_payoff_match.group(1)) * 10 if need_payoff_match else 70
            good_points = ["开场时问候语得体"]
            improvements = ["在挖掘需求时可以更针对性地提问"]
            suggestions = ["建议增加开放式问题了解客户背景"]
    except Exception as e:
        print(f"Error parsing evaluation: {e}")
        situation_score = 70
        problem_score = 70
        implication_score = 70
        need_payoff_score = 70
        good_points = ["开场时问候语得体"]
        improvements = ["在挖掘需求时可以更针对性地提问"]
        suggestions = ["建议增加开放式问题了解客户背景"]

    overall_score = (situation_score + problem_score + implication_score + need_payoff_score) / 4

    # Get phase label
    phase_labels = {
        "opening": "开场破冰",
        "discovery": "需求挖掘",
        "needs": "方案呈现",
        "proposal": "促成成交",
        "closing": "复盘总结"
    }

    return {
        "session_id": str(session_id),
        "phase": phase,
        "phase_label": phase_labels.get(phase, phase),
        "overall_score": round(overall_score, 1),
        "situation_score": situation_score,
        "problem_score": problem_score,
        "implication_score": implication_score,
        "need_payoff_score": need_payoff_score,
        "good_points": good_points,
        "improvements": improvements,
        "suggestions": suggestions
    }


@router.get("/sessions/{session_id}/summary")
async def get_session_summary(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """
    获取会话的整体总结 - 基于SPIN评价
    """
    session = db.query(PracticeSession).filter(PracticeSession.id == str(session_id)).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # Get conversation context from session manager
    from app.websocket.manager import session_manager
    context = session_manager.get_context(str(session_id))

    if not context:
        return {
            "session_id": str(session_id),
            "overall_score": 0,
            "situation_score": 0,
            "problem_score": 0,
            "implication_score": 0,
            "need_payoff_score": 0,
            "key_strengths": [],
            "areas_for_improvement": [],
            "next_practice_focus": "暂无对话记录"
        }

    # Map "ai" to "assistant" for MiniMax API
    for msg in context:
        if msg.get("role") == "ai":
            msg["role"] = "assistant"

    # Call handler to generate SPIN evaluation
    from app.services.conversation.handler import get_conversation_handler
    handler = get_conversation_handler()

    # Get customer type from session
    role_config = session.role_config or {}
    personality = role_config.get("personality", "decisive")
    personality_map = {
        "rational": "analytical",
        "emotional": "expressive",
        "hesitant": "amiable",
        "decisive": "assertive"
    }
    customer_type = personality_map.get(personality, "assertive")

    # Generate evaluation
    evaluation = await handler.evaluate_conversation(context, customer_type)

    # Parse evaluation result (simplified - in production would parse structured JSON)
    try:
        import re
        situation_match = re.search(r'[Ss]ituation.*?(\d+)', evaluation)
        problem_match = re.search(r'[Pp]roblem.*?(\d+)', evaluation)
        implication_match = re.search(r'[Ii]mplication.*?(\d+)', evaluation)
        need_payoff_match = re.search(r'need[- ]payoff.*?(\d+)', evaluation)

        situation_score = int(situation_match.group(1)) if situation_match else 7
        problem_score = int(problem_match.group(1)) if problem_match else 7
        implication_score = int(implication_match.group(1)) if implication_match else 7
        need_payoff_score = int(need_payoff_match.group(1)) if need_payoff_match else 7
    except:
        situation_score = 7
        problem_score = 7
        implication_score = 7
        need_payoff_score = 7

    overall_score = (situation_score + problem_score + implication_score + need_payoff_score) / 4 * 10

    return {
        "session_id": str(session_id),
        "overall_score": round(overall_score, 1),
        "situation_score": situation_score * 10,
        "problem_score": problem_score * 10,
        "implication_score": implication_score * 10,
        "need_payoff_score": need_payoff_score * 10,
        "key_strengths": [
            "开场破冰自然，能快速建立信任"
        ],
        "areas_for_improvement": [
            "需求挖掘深度可以加强"
        ],
        "next_practice_focus": "建议加强Implication（影响）阶段，多追问'这会对您造成什么影响？'"
    }

# ============== Session List Endpoints ==============
# NOTE: Using /sessions-list to avoid route conflict with /{session_id}

@router.get("/sessions-list", response_model=SessionListResponse)
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    scenario_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取会话列表（分页）

    - 支持按状态、场景类型筛选
    - 关联场景信息
    """
    query = db.query(PracticeSession)

    if status:
        query = query.filter(PracticeSession.status == status)
    if scenario_type:
        query = query.join(Scenario).filter(Scenario.type == scenario_type)

    total = query.count()
    sessions = query.order_by(PracticeSession.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Build session list with scenario info
    session_items = []
    for s in sessions:
        scenario = db.query(Scenario).filter(Scenario.id == str(s.scenario_id)).first()
        session_items.append(SessionListItem(
            id=s.id,
            scenario_id=s.scenario_id,
            scenario_name=scenario.name if scenario else None,
            scenario_type=scenario.type if scenario else None,
            user_id=s.user_id,
            role_config=s.role_config or {},
            status=s.status,
            current_phase=None,
            score=None,
            message_count=0,
            duration_minutes=0,
            created_at=s.created_at,
            ended_at=s.ended_at
        ))

    return SessionListResponse(
        data=session_items,
        total=total,
        page=page,
        page_size=page_size
    )


# ============== Dashboard Stats Endpoints ==============

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取仪表盘统计数据
    """
    # Base query - filter by user_id if provided (for logged-in users)
    query = db.query(PracticeSession)
    if user_id:
        query = query.filter(PracticeSession.user_id == user_id)

    # Total sessions
    total_sessions = query.count()

    # Calculate total time (in minutes)
    sessions_for_time = query.all()
    total_time_minutes = 0
    for s in sessions_for_time:
        if s.started_at and s.ended_at:
            duration = (s.ended_at - s.started_at).total_seconds() / 60
            total_time_minutes += int(duration)

    # Calculate avg score (for completed sessions with scores)
    completed_sessions = query.filter(PracticeSession.status == "completed").all()
    scored_sessions = [s for s in completed_sessions if s.ended_at]  # Simplified scoring check
    avg_score = 75.0 if scored_sessions else None  # Placeholder - real impl would query Report table

    # This week stats
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    this_week_query = query.filter(PracticeSession.created_at >= week_ago)
    this_week_sessions = this_week_query.count()

    this_week_time = 0
    for s in this_week_query.all():
        if s.started_at and s.ended_at:
            duration = (s.ended_at - s.started_at).total_seconds() / 60
            this_week_time += int(duration)

    # Calculate improvement rate (comparing last 7 days avg vs previous 7 days avg)
    improvement_rate = 5.0  # Placeholder

    # Streak days (simplified - just count consecutive days with sessions)
    streak_days = min(this_week_sessions, 7) if this_week_sessions > 0 else 0

    return DashboardStats(
        total_sessions=total_sessions,
        total_time_minutes=total_time_minutes,
        avg_score=avg_score,
        improvement_rate=improvement_rate,
        this_week_sessions=this_week_sessions,
        this_week_time=this_week_time,
        this_week_score=avg_score,
        streak_days=streak_days
    )


# ============== History Stats Endpoints ==============

@router.get("/history/stats", response_model=HistoryStatsResponse)
async def get_history_stats(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取历史统计数据
    """
    from datetime import datetime, timedelta

    # Base query
    base_query = db.query(PracticeSession)
    if user_id:
        base_query = base_query.filter(PracticeSession.user_id == user_id)

    # Last 30 days
    days_30_ago = datetime.utcnow() - timedelta(days=30)
    last_30_query = base_query.filter(PracticeSession.created_at >= days_30_ago)
    sessions_30 = last_30_query.all()
    completed_30 = [s for s in sessions_30 if s.status == "completed"]

    last_30_duration = 0
    for s in sessions_30:
        if s.started_at and s.ended_at:
            duration = (s.ended_at - s.started_at).total_seconds() / 60
            last_30_duration += int(duration)

    last_30_stats = HistoryStats(
        sessions=len(sessions_30),
        completed=len(completed_30),
        duration_minutes=last_30_duration,
        messages=len(sessions_30) * 20,  # Placeholder
        avg_score=75.0 if completed_30 else None
    )

    # Last 90 days
    days_90_ago = datetime.utcnow() - timedelta(days=90)
    last_90_query = base_query.filter(PracticeSession.created_at >= days_90_ago)
    sessions_90 = last_90_query.all()
    completed_90 = [s for s in sessions_90 if s.status == "completed"]

    last_90_duration = 0
    for s in sessions_90:
        if s.started_at and s.ended_at:
            duration = (s.ended_at - s.started_at).total_seconds() / 60
            last_90_duration += int(duration)

    last_90_stats = HistoryStats(
        sessions=len(sessions_90),
        completed=len(completed_90),
        duration_minutes=last_90_duration,
        messages=len(sessions_90) * 20,
        avg_score=74.0 if completed_90 else None
    )

    return HistoryStatsResponse(
        last_30_days=last_30_stats,
        last_90_days=last_90_stats
    )
