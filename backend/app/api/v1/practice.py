"""
Practice API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.database import get_db
from app.core.security import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.practice import (
    Scenario, PracticeSession, AIClientRole,
    PracticeMessage, PracticeSummary, PracticeReport,
)
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
        customer_context=session_data.customer_context,
        investigation_result=session_data.investigation_result,
        user_context=session_data.user_context,
        status="active"
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Generate personalized first message based on SPIN context
    if session_data.customer_context:
        industry = session_data.customer_context.get("industry", "")
        pain_points = session_data.customer_context.get("pain_points", [])
        pain_text = "；".join(pain_points[:3]) if pain_points else ""
        first_message = f"您好！关于{industry}行业的{pain_text}问题，我们可以详细聊聊。"
    elif session_data.investigation_result:
        # Fallback to investigation result
        name = session_data.investigation_result.get("name", scenario.name)
        title = session_data.investigation_result.get("title", "")
        company = session_data.investigation_result.get("company", "")
        first_message = f"您好，我是{name}，{title}@{company}。请问有什么可以帮助您的？"
    else:
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

    # 如果 session 已结束（WS 断开），从 DB 持久化的 messages 重建 context
    if not context:
        db_messages = (
            db.query(PracticeMessage)
            .filter(PracticeMessage.session_id == str(session_id))
            .order_by(PracticeMessage.created_at)
            .all()
        )
        context = [
            {"role": m.role, "content": m.content} for m in db_messages
        ]

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

    # 如果 session 已结束（WS 断开），从 DB 持久化的 messages 重建 context
    if not context:
        db_messages = (
            db.query(PracticeMessage)
            .filter(PracticeMessage.session_id == str(session_id))
            .order_by(PracticeMessage.created_at)
            .all()
        )
        context = [
            {"role": m.role, "content": m.content} for m in db_messages
        ]

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

    # Update session status BEFORE returning
    session.status = "completed"
    db.commit()

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


def _parse_evaluation_json(raw: str) -> dict:
    """
    解析 LLM 返回的评价 JSON。
    LLM 有时会包在 ```json ... ``` 代码块里，有时夹杂前后文字。
    本函数尽量宽容地抽取 JSON 对象。
    """
    import json, re
    if not raw:
        return {}
    s = raw.strip()
    # 1) 优先尝试直接 parse
    try:
        return json.loads(s)
    except Exception:
        pass
    # 2) 提取 ```json ... ``` 块
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 3) 找第一个 { 到最后一个 } 之间
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(s[start:end+1])
        except Exception:
            pass
    return {}


def _aggregate_knowledge_refs(context, session_id: str = None):
    """Collect unique knowledge_refs entries.

    Two sources of references:
    1. The in-memory context entries with role="knowledge_refs" (legacy).
    2. The side-channel dict on the connection manager (`_knowledge_refs`).
       The LLM API rejects the "knowledge_refs" role so we can no longer
       put these into the LLM context itself; instead they're stashed
       on the manager. We read from there when session_id is provided.

    We dedupe by (source, chapter, section, excerpt prefix) so the report
    doesn't repeat the same reference multiple times.
    """
    seen = set()
    aggregated = []

    # 1) New side-channel: manager._knowledge_refs[session_id]
    if session_id:
        try:
            from app.websocket.manager import manager as _manager
            side = getattr(_manager, '_knowledge_refs', None) or {}
            for ref in side.get(session_id, []) or []:
                key = (
                    ref.get("source"),
                    ref.get("chapter"),
                    ref.get("section"),
                    (ref.get("excerpt") or "")[:60],
                )
                if key in seen:
                    continue
                seen.add(key)
                aggregated.append(ref)
        except Exception:
            pass

    # 2) Legacy: in-context role=knowledge_refs entries
    for msg in context or []:
        if msg.get("role") != "knowledge_refs":
            continue
        for ref in msg.get("content") or []:
            key = (
                ref.get("source"),
                ref.get("chapter"),
                ref.get("section"),
                (ref.get("excerpt") or "")[:60],
            )
            if key in seen:
                continue
            seen.add(key)
            aggregated.append(ref)
    return aggregated

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

    # 如果 session 已结束（WS 断开），从 DB 持久化的 messages 重建 context
    if not context:
        db_messages = (
            db.query(PracticeMessage)
            .filter(PracticeMessage.session_id == str(session_id))
            .order_by(PracticeMessage.created_at)
            .all()
        )
        context = [
            {"role": m.role, "content": m.content} for m in db_messages
        ]

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

    # 解析 LLM JSON（统一用 _parse_evaluation_json 处理 markdown/裸 JSON 各种格式）
    eval_data = _parse_evaluation_json(evaluation)
    situation_score = (eval_data.get('situation_score') or 0) * 10
    problem_score = (eval_data.get('problem_score') or 0) * 10
    implication_score = (eval_data.get('implication_score') or 0) * 10
    need_payoff_score = (eval_data.get('need_payoff_score') or 0) * 10
    good_points = eval_data.get('key_strengths') or []
    improvements = eval_data.get('areas_for_improvement') or []
    suggestions = eval_data.get('next_practice_focus') or []
    if isinstance(good_points, str):
        good_points = [good_points]
    if isinstance(improvements, str):
        improvements = [improvements]
    if isinstance(suggestions, str):
        suggestions = [suggestions]

    overall_score = (situation_score + problem_score + implication_score + need_payoff_score) / 4

    # Aggregate knowledge_refs from the conversation context (per AI turn).
    # Deduplicate by source+chapter+section so the report doesn't list the
    # same reference multiple times.
    seen_keys = set()
    aggregated_refs = []
    for msg in context:
        if msg.get("role") != "knowledge_refs":
            continue
        for ref in msg.get("content", []):
            key = (ref.get("source"), ref.get("chapter"), ref.get("section"), ref.get("excerpt", "")[:60])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            aggregated_refs.append(ref)

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
        "suggestions": suggestions,
        "knowledge_refs": aggregated_refs,
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

    # 如果 session 已结束（WS 断开），从 DB 持久化的 messages 重建 context
    if not context:
        db_messages = (
            db.query(PracticeMessage)
            .filter(PracticeMessage.session_id == str(session_id))
            .order_by(PracticeMessage.created_at)
            .all()
        )
        context = [
            {"role": m.role, "content": m.content} for m in db_messages
        ]

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

    # 解析 LLM 返回的 JSON（强约束：handler 端 prompt 已固定 schema）
    parsed = _parse_evaluation_json(evaluation)

    situation_score = parsed.get("situation_score", 0) or 0
    problem_score = parsed.get("problem_score", 0) or 0
    implication_score = parsed.get("implication_score", 0) or 0
    need_payoff_score = parsed.get("need_payoff_score", 0) or 0
    overall_score = parsed.get("overall_score") or (
        situation_score + problem_score + implication_score + need_payoff_score
    )

    # 把 LLM 真实输出装到返回 dict
    result = {
        "session_id": str(session_id),
        "overall_score": float(overall_score) if overall_score else 0.0,
        "situation_score": float(situation_score) if situation_score else 0.0,
        "problem_score": float(problem_score) if problem_score else 0.0,
        "implication_score": float(implication_score) if implication_score else 0.0,
        "need_payoff_score": float(need_payoff_score) if need_payoff_score else 0.0,
        "key_strengths": parsed.get("key_strengths") or [],
        "areas_for_improvement": parsed.get("areas_for_improvement") or [],
        "next_practice_focus": parsed.get("next_practice_focus") or "",
        "knowledge_refs": _aggregate_knowledge_refs(context, str(session_id)),
    }

    # 把 4 维 * 5 字段（quote/analysis/reference/suggestion/score）拼到顶层
    for stage in ("situation", "problem", "implication", "need_payoff"):
        for field in ("quote", "analysis", "reference", "suggestion"):
            key = f"{stage}_{field}"
            val = parsed.get(key)
            if val:
                result[key] = val

    # 持久化报告
    try:
        from app.models.practice import PracticeReport
        report = db.query(PracticeReport).filter(
            PracticeReport.session_id == str(session_id)
        ).order_by(PracticeReport.created_at.desc()).first()
        if not report:
            report = PracticeReport(
                session_id=str(session_id),
                communication_score=float(situation_score or 0),
                persuasion_score=float(problem_score or 0),
                closing_score=float(implication_score or 0),
                spin_score=float(need_payoff_score or 0),
            )
            db.add(report)
        else:
            report.communication_score = float(situation_score or 0)
            report.persuasion_score = float(problem_score or 0)
            report.closing_score = float(implication_score or 0)
            report.spin_score = float(need_payoff_score or 0)
        report.key_points = parsed.get("key_strengths") or []
        report.improvements = parsed.get("areas_for_improvement") or []
        report.summary = (parsed.get("next_practice_focus") or "")[:1000]
        db.commit()
    except Exception as e:
        print(f"[REPORT] save failed: {e}")
        db.rollback()

    return result


@router.get("/sessions/{session_id}/report/pdf")
async def export_report_pdf(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Render the full session report as a PDF and return it as a download."""
    from fastapi.responses import Response
    from app.services.report_pdf import render_report_pdf

    session = db.query(PracticeSession).filter(PracticeSession.id == str(session_id)).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # Reuse the same evaluation + knowledge aggregation as the JSON endpoint
    # so the PDF body mirrors the on-screen report.
    from app.websocket.manager import session_manager
    context = session_manager.get_context(str(session_id))
    if not context:
        db_messages = db.query(PracticeMessage).filter(
            PracticeMessage.session_id == str(session_id)
        ).order_by(PracticeMessage.created_at).all()
        context = [
            {"role": msg.role, "content": msg.content, "timestamp": msg.created_at.isoformat()}
            for msg in db_messages
        ]
    for msg in context:
        if msg.get("role") == "ai":
            msg["role"] = "assistant"

    role_config = session.role_config or {}
    personality = role_config.get("personality", "decisive")
    personality_map = {
        "rational": "analytical", "emotional": "expressive",
        "hesitant": "amiable", "decisive": "assertive",
    }
    customer_type = personality_map.get(personality, "assertive")

    from app.services.conversation.handler import get_conversation_handler
    handler = get_conversation_handler()
    evaluation = await handler.evaluate_conversation(context, customer_type)

    # Parse scores from the LLM response.
    import re as _re
    def _score(pattern: str, default: int = 7) -> int:
        m = _re.search(pattern, evaluation)
        return int(m.group(1)) if m else default
    situation_score = _score(r'[Ss]ituation.*?(\d+)')
    problem_score = _score(r'[Pp]roblem.*?(\d+)')
    implication_score = _score(r'[Ii]mplication.*?(\d+)')
    need_payoff_score = _score(r'need[- ]payoff.*?(\d+)')
    overall_score = round((situation_score + problem_score + implication_score + need_payoff_score) / 4 * 10, 1)

    summary = {
        "session_id": str(session_id),
        "scenario_name": (db.query(Scenario).filter(Scenario.id == session.scenario_id).first().name
                          if session.scenario_id else ""),
        "role_config": role_config,
        "overall_score": overall_score,
        "situation_score": situation_score * 10,
        "problem_score": problem_score * 10,
        "implication_score": implication_score * 10,
        "need_payoff_score": need_payoff_score * 10,
        "key_strengths": ["开场破冰自然，能快速建立信任"],
        "areas_for_improvement": ["需求挖掘深度可以加强"],
        "next_practice_focus": "建议加强Implication（影响）阶段，多追问'这会对您造成什么影响？'",
        "knowledge_refs": _aggregate_knowledge_refs(context, str(session_id)),
        "raw_evaluation": evaluation[:2000],  # truncate for PDF readability
        "context": context,
    }

    pdf_bytes = render_report_pdf(summary)
    filename = f"salesagent-report-{session_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# ============== Session List Endpoints ==============
# NOTE: Using /sessions-list to avoid route conflict with /{session_id}

@router.get("/sessions-list", response_model=SessionListResponse)
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    scenario_type: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    获取会话列表（分页）

    - 支持按状态、场景类型筛选
    - 关联场景信息
    - 默认只返回当前用户的会话；admin 可传 ?all=true 看全局
    """
    query = db.query(PracticeSession)
    if current_user:
        if current_user.role != "admin":
            query = query.filter(PracticeSession.user_id == current_user.id)
    # 兜底：如果没传 user_id 且无登录用户，行为与之前一致（返回全部）

    if status:
        query = query.filter(PracticeSession.status == status)
    if scenario_type:
        query = query.join(Scenario).filter(Scenario.type == scenario_type)

    total = query.count()
    sessions = query.order_by(PracticeSession.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Build session list with scenario info + real aggregates
    session_items = []
    for s in sessions:
        scenario = db.query(Scenario).filter(Scenario.id == str(s.scenario_id)).first()
        # Real score from latest summary or report
        score = None
        latest_summary = (
            db.query(PracticeSummary)
            .filter(PracticeSummary.session_id == s.id)
            .order_by(PracticeSummary.created_at.desc())
            .first()
        )
        if latest_summary and latest_summary.scores:
            score = latest_summary.scores.get("overall_score")
        if score is None:
            latest_report = (
                db.query(PracticeReport)
                .filter(PracticeReport.session_id == s.id)
                .order_by(PracticeReport.created_at.desc())
                .first()
            )
            if latest_report:
                # Average of the 4 sub-scores as a fallback
                parts = [
                    latest_report.communication_score or 0,
                    latest_report.persuasion_score or 0,
                    latest_report.closing_score or 0,
                    latest_report.spin_score or 0,
                ]
                if any(parts):
                    score = round(sum(parts) / len([p for p in parts if p]), 1)
        # Real message count
        message_count = (
            db.query(PracticeMessage)
            .filter(PracticeMessage.session_id == s.id)
            .count()
        )
        # Real duration
        duration_minutes = 0
        if s.started_at and s.ended_at:
            duration_minutes = int((s.ended_at - s.started_at).total_seconds() / 60)
        session_items.append(SessionListItem(
            id=s.id,
            scenario_id=s.scenario_id,
            scenario_name=scenario.name if scenario else None,
            scenario_type=scenario.type if scenario else None,
            user_id=s.user_id,
            role_config=s.role_config or {},
            status=s.status,
            current_phase=s.current_phase,
            score=score,
            message_count=message_count,
            duration_minutes=duration_minutes,
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
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    获取仪表盘统计数据（真实聚合）

    - 从 PracticeSummary.overall_score / Report 子分 真实聚合
    - improvement_rate 比较最近 7 天 vs 上一周
    - streak_days 计算连续练习天数
    """
    from datetime import datetime, timedelta

    # 优先 current_user.id（鉴权路径），其次 query 参数（兼容旧调用）
    effective_user_id = current_user.id if current_user else user_id

    query = db.query(PracticeSession)
    if effective_user_id:
        query = query.filter(PracticeSession.user_id == effective_user_id)

    total_sessions = query.count()

    # Total time
    sessions_for_time = query.all()
    total_time_minutes = 0
    for s in sessions_for_time:
        if s.started_at and s.ended_at:
            total_time_minutes += int((s.ended_at - s.started_at).total_seconds() / 60)

    # Real avg score from PracticeSummary.overall_score
    completed_session_ids = [
        s.id for s in query.filter(PracticeSession.status == "completed").all()
    ]
    real_scores: List[float] = []
    if completed_session_ids:
        summaries = (
            db.query(PracticeSummary)
            .filter(PracticeSummary.session_id.in_(completed_session_ids))
            .all()
        )
        for sm in summaries:
            if sm.scores and isinstance(sm.scores, dict) and "overall_score" in sm.scores:
                v = sm.scores["overall_score"]
                if isinstance(v, (int, float)):
                    real_scores.append(float(v))
    avg_score = round(sum(real_scores) / len(real_scores), 1) if real_scores else None

    # This week (last 7 days)
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    this_week_query = query.filter(PracticeSession.created_at >= week_ago)
    this_week_sessions = this_week_query.count()
    this_week_time = 0
    for s in this_week_query.all():
        if s.started_at and s.ended_at:
            this_week_time += int((s.ended_at - s.started_at).total_seconds() / 60)

    this_week_scores: List[float] = []
    if this_week_sessions:
        this_week_session_ids = [s.id for s in this_week_query.all()]
        this_week_summaries = (
            db.query(PracticeSummary)
            .filter(PracticeSummary.session_id.in_(this_week_session_ids))
            .all()
        )
        for sm in this_week_summaries:
            if sm.scores and isinstance(sm.scores, dict) and "overall_score" in sm.scores:
                v = sm.scores["overall_score"]
                if isinstance(v, (int, float)):
                    this_week_scores.append(float(v))
    this_week_score = round(sum(this_week_scores) / len(this_week_scores), 1) if this_week_scores else avg_score

    # Improvement rate: last 7 days avg vs previous 7 days avg
    two_weeks_ago = now - timedelta(days=14)
    prev_week_query = query.filter(
        PracticeSession.created_at >= two_weeks_ago,
        PracticeSession.created_at < week_ago,
    )
    prev_week_session_ids = [s.id for s in prev_week_query.all()]
    prev_week_scores: List[float] = []
    if prev_week_session_ids:
        prev_summaries = (
            db.query(PracticeSummary)
            .filter(PracticeSummary.session_id.in_(prev_week_session_ids))
            .all()
        )
        for sm in prev_summaries:
            if sm.scores and isinstance(sm.scores, dict) and "overall_score" in sm.scores:
                v = sm.scores["overall_score"]
                if isinstance(v, (int, float)):
                    prev_week_scores.append(float(v))
    prev_week_avg = sum(prev_week_scores) / len(prev_week_scores) if prev_week_scores else None
    if prev_week_avg and prev_week_avg > 0 and this_week_scores:
        improvement_rate = round((sum(this_week_scores) / len(this_week_scores) - prev_week_avg) / prev_week_avg * 100, 1)
    else:
        improvement_rate = 0.0

    # Streak days: 连续练习天数
    streak_days = 0
    all_dates = sorted(
        {s.created_at.date() for s in query.all() if s.created_at},
        reverse=True,
    )
    expected = now.date()
    for d in all_dates:
        if d == expected:
            streak_days += 1
            expected = expected - timedelta(days=1)
        elif d < expected:
            break

    return DashboardStats(
        total_sessions=total_sessions,
        total_time_minutes=total_time_minutes,
        avg_score=avg_score,
        improvement_rate=improvement_rate,
        this_week_sessions=this_week_sessions,
        this_week_time=this_week_time,
        this_week_score=this_week_score,
        streak_days=streak_days
    )


# ============== History Stats Endpoints ==============

@router.get("/history/stats", response_model=HistoryStatsResponse)
async def get_history_stats(
    user_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    获取历史统计数据（真实聚合）

    - 30/90 天窗口用真实时间过滤
    - avg_score 从 PracticeSummary.overall_score 真实计算
    - messages 从 PracticeMessage 表真实 count
    """
    from datetime import datetime, timedelta

    effective_user_id = current_user.id if current_user else user_id

    base_query = db.query(PracticeSession)
    if effective_user_id:
        base_query = base_query.filter(PracticeSession.user_id == effective_user_id)

    now = datetime.utcnow()

    def _compute(window_start: datetime) -> HistoryStats:
        window_query = base_query.filter(PracticeSession.created_at >= window_start)
        sessions = window_query.all()
        completed = [s for s in sessions if s.status == "completed"]
        session_ids = [s.id for s in sessions]

        # 真实消息数
        messages = 0
        if session_ids:
            messages = (
                db.query(PracticeMessage)
                .filter(PracticeMessage.session_id.in_(session_ids))
                .count()
            )

        # 真实时长
        duration = 0
        for s in sessions:
            if s.started_at and s.ended_at:
                duration += int((s.ended_at - s.started_at).total_seconds() / 60)

        # 真实平均分
        scores: List[float] = []
        if completed:
            completed_ids = [s.id for s in completed]
            summaries = (
                db.query(PracticeSummary)
                .filter(PracticeSummary.session_id.in_(completed_ids))
                .all()
            )
            for sm in summaries:
                if sm.scores and isinstance(sm.scores, dict) and "overall_score" in sm.scores:
                    v = sm.scores["overall_score"]
                    if isinstance(v, (int, float)):
                        scores.append(float(v))
        avg = round(sum(scores) / len(scores), 1) if scores else None

        return HistoryStats(
            sessions=len(sessions),
            completed=len(completed),
            duration_minutes=duration,
            messages=messages,
            avg_score=avg,
        )

    last_30_stats = _compute(now - timedelta(days=30))
    last_90_stats = _compute(now - timedelta(days=90))

    return HistoryStatsResponse(
        last_30_days=last_30_stats,
        last_90_days=last_90_stats
    )
