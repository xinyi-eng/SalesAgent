"""
SalesAgent Application Entry Point
"""
import os
import re
import json
import base64
import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 配置 logging 显示 INFO（默认 WARNING 会吞掉 scheduler/cron 日志）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("salesagent.scheduler")
from pydantic import BaseModel
from typing import List, Dict, Optional

from app.config import settings
from app.api.v1 import router as api_v1_router
from app.websocket.manager import manager, session_manager, ConversationState
from app.database import engine, Base, SessionLocal
from app.models.practice import PracticeMessage
from app.services.llm import get_minimax_service
from app.services.knowledge.service import get_knowledge_service
from app.services.audio.backchannel import backchannel_manager

# Create database tables
Base.metadata.create_all(bind=engine)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def _daily_brief_push():
    """每日 8:30 UTC 跑一遍：所有活跃用户的订阅 → 抓真实新闻 → 推送通知。"""
    from app.database import SessionLocal
    from app.models import User, Notification, IndustryBrief
    from app.services.real_brief import generate_real_brief
    from datetime import datetime as _dt

    db = SessionLocal()
    try:
        users = db.query(User).filter(User.brief_subscriptions.isnot(None)).all()
        logger.info(f"[cron] daily brief push: {len(users)} users")
        for u in users:
            if not u.brief_subscriptions:
                continue
            created = 0
            for sub in u.brief_subscriptions:
                industry = sub.get("industry", "通用")
                keywords = sub.get("keywords", "")
                try:
                    data = await generate_real_brief(
                        industry=industry, keywords=keywords, max_news=8, hours=48,
                    )
                    if data.get("news_count", 0) == 0:
                        continue
                    brief = IndustryBrief(
                        title=data["title"],
                        industry=industry,
                        keywords=keywords,
                        summary=data.get("summary", ""),
                        items=data.get("items", []),
                        key_takeaways=data.get("key_takeaways", []),
                        news_count=data.get("news_count", 0),
                        brief_date=_dt.utcnow(),
                        status="ready",
                        generated_by=u.id,
                    )
                    db.add(brief)
                    db.flush()
                    created += 1
                except Exception as e:
                    logger.warning(f"[cron] {u.id}/{industry} failed: {e}")
                    continue

            if created > 0:
                notif = Notification(
                    user_id=u.id,
                    type="brief_ready",
                    title=f"📰 今日 {created} 份行业简报已生成",
                    body=f"点击查看 {u.brief_subscriptions[0].get('industry', '')} 等行业今日动态",
                    link="/briefs",
                )
                db.add(notif)
                db.commit()
                logger.info(f"[cron] user {u.id} ({u.email}) got {created} briefs")
            else:
                db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：跑一次（让新装的服务能立即看到今天的数据）
    asyncio.create_task(_daily_brief_push())
    # 8:30 (Asia/Shanghai) 每天定时 — 早间简报推送
    scheduler.add_job(
        _daily_brief_push,
        trigger=CronTrigger(hour=8, minute=30, timezone="Asia/Shanghai"),
        id="daily_brief_push",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("[scheduler] APScheduler started: daily_brief_push @ 08:30 Asia/Shanghai")
    # 打印已注册 job 列表便于排错
    for job in scheduler.get_jobs():
        logger.info(f"[scheduler] job: id={job.id} next_run={job.next_run_time}")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Sales Agent - 话术对练、行业简报、SPIN拜访准备、PPT生成、商务文件",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_v1_router, prefix="/api/v1")


# =============================================================================
# Health endpoints
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok"}


# =============================================================================
# WebSocket helpers (module-level, no nested functions)
# =============================================================================

async def safe_send_message(session_id: str, message: dict) -> bool:
    """Send a JSON message; swallow errors if WS is already closed."""
    try:
        await manager.send_message(session_id, message)
        return True
    except Exception:
        return False


async def safe_send_status(session_id: str, state, metadata: dict = None) -> None:
    """Send a status update; swallow errors if WS is already closed."""
    try:
        await manager.send_status(session_id, state, metadata)
    except Exception:
        pass


def save_message_to_db(session_id: str, role: str, content: str) -> None:
    """Persist a single chat message to the database."""
    try:
        db = SessionLocal()
        db.add(PracticeMessage(session_id=session_id, role=role, content=content))
        db.commit()
    except Exception as e:
        print(f"[DB] Failed to save message: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass


async def send_ai_audio(websocket, session_id: str, text: str,
                         emotion: str = "neutral", voice_modify: dict = None,
                         voice: str = "male-qn-qingse") -> None:
    """Generate TTS audio for an AI response and send it as binary."""
    minimax = get_minimax_service()
    try:
        audio_bytes = await minimax.text_to_speech(
            text=text,
            model="speech-2.8-hd",
            voice=voice,
            speed=1.0,
            volume=1.0,
            pitch=1.0,
            format="mp3",
            emotion=emotion,
            voice_modify=voice_modify
        )
        await manager.send_audio_chunk(session_id, audio_bytes)
    except Exception as e:
        print(f"[TTS] Failed to send audio: {e}")


# =============================================================================
# LLM-backed helpers
# =============================================================================

async def generate_persona_for_session(scenario_name: str, role_config: dict) -> dict:
    """Generate a concrete customer persona using LLM. Falls back to a
    hard-coded persona on failure.
    """
    from app.services.conversation.persona_generator import generate_persona
    return await generate_persona(
        scenario_name=scenario_name,
        role_config=role_config
    )


async def generate_opening_message(scenario_name: str, scenario_id: str,
                                   role_config: dict,
                                   persona: Optional[dict] = None) -> str:
    """Use LLM to generate a realistic first line for the customer."""
    if persona and persona.get("name"):
        system_prompt = f"""你扮演【{persona['name']}】，{persona.get('title', '')}@{persona.get('company', '')}。
当前场景：{scenario_name}

你的背景：
{persona.get('background', '')}

你最近在忙什么：
{persona.get('current_situation', '')}

你当前的痛点：
{chr(10).join(['- ' + p for p in persona.get('pain_points', [])])}

你的说话风格：
{persona.get('speaking_style', '')}

接触场景：
{persona.get('scenario_context', '')}

【任务】
一个销售刚刚联系你/敲你办公室的门/打来电话/发来微信。
你要说出你的第一句话。

【要求】
1. 绝对不要自我介绍"我是{persona['name']}"或"我是{scenario_name}场景的AI客户"
2. 像真人接电话/被打扰时的反应
3. 一句话即可，15-30字
4. 符合你的说话风格
5. 可以带情绪（忙/被打扰/有点兴趣/没兴趣）
6. 给出具体的上下文暗示（如"正在忙""刚开完会""手头有项目"）
7. 不要问"请问您想了解什么"——你是被联系的人，不是主动询问的人
8. 不要说"你好请问有什么事"——太机械

【示例风格（不要照抄）】
- 正在忙被打扰："嗯...我现在在开会，你稍等一下，什么事？"
- 略有兴趣："行你说吧，我现在有点时间。"
- 警惕敷衍："喂？现在打电话过来？什么事？"
- 直接打断："等下，什么事，我这边有点忙。"

只输出你的第一句话。"""
    else:
        position = role_config.get("position_level", "middle")
        personality = role_config.get("personality", "rational")
        decision_style = role_config.get("decision_style", "value_oriented")
        position_label = {
            "junior": "初级客户经理", "middle": "中级采购经理", "senior": "高级总监"
        }.get(position, "采购经理")
        personality_label = {
            "rational": "理性", "emotional": "感性", "hesitant": "犹豫", "decisive": "果断"
        }.get(personality, "理性")
        style_label = {
            "price_oriented": "关注价格", "value_oriented": "关注价值",
            "relationship_oriented": "看重关系", "risk_averse": "规避风险"
        }.get(decision_style, "关注价值")
        system_prompt = f"""你扮演一位{position_label}，性格{personality_label}，{style_label}。
你正在和一位销售初次接触（电话或登门拜访）。

要求：
1. 绝对不要自我介绍"我是AI客户"或"我是模拟客户"
2. 语气要符合{personality_label}的客户特点
3. 一句话即可，15-30字
4. 像真实场景：销售打来电话/上门时，你正在忙或被打扰
5. 符合场景：{scenario_name}

只输出客户那一句话，不要任何解释。"""

    # 开场白 LLM 调用对当前模型不稳定（reasoning 模型总是把
    # 思考过程写在回复里、且 max_tokens 一卡就把答案截掉）。
    # 改用 persona × personality × industry 的多版本兜底池，
    # 既快又不会"读起来像硬编码"。
    # 如未来切到非 M-series 模型，再启用 LLM 调用。

    personality = role_config.get("personality", "rational")
    import random
    industry_hint = ""
    if persona and isinstance(persona, dict):
        industry = (persona.get("industry") or persona.get("scenario_context") or "").strip()
        if industry and len(industry) <= 12:
            industry_hint = f"，{industry}"

    pools = {
        "rational": [
            "我现在手头有个项目在选型，简单说一下你们能提供什么？",
            "行，你说你们跟市面上其他方案相比有什么不同？",
            "我对这类产品了解过一些，先讲讲你们最核心的优势。",
            "正好在做明年规划，你说说能解决哪些具体问题？",
        ],
        "emotional": [
            "嗯你好啊，对你这个挺感兴趣的，你说说看。",
            "听着挺有意思的，先发点资料给我看看吧。",
            "行呀，那你先介绍一下呗，我看看跟我们想的是不是一回事。",
            "哎呀你来得正好，最近正好在琢磨这事，你说说。",
        ],
        "hesitant": [
            "嗯...你好，我现在有点忙，要不你先发个资料过来？",
            "这个...我得跟团队商量一下，要不你先讲讲大概？",
            "我现在手头有点乱，你简单说两句，我回头细看。",
            "行吧，那你就简单说说，我看合不合适。",
        ],
        "decisive": [
            "直接说重点，什么产品，多少钱？",
            "好，简单讲讲你的方案和报价，五分钟能说完吗？",
            "别绕弯子，你们最擅长解决什么？",
            "行，我时间有限，你直入主题。",
        ],
    }
    pool = pools.get(personality, ["嗯，你好，什么事？"])
    base = random.choice(pool)
    return base + industry_hint


# =============================================================================
# User message processing (background task)
# =============================================================================

async def process_user_message(websocket, session_id: str, content: str,
                              audio_data: str = None,
                              audio_mime: str = None,
                              client_id: str = None) -> None:
    """Process a user message: ASR (optional) → LLM (with persona) → TTS → send.

    Args:
        content: User-typed text (used as fallback if ASR fails).
        audio_data: Base64-encoded recorded audio (webm/opus from browser).
        client_id: Optional id of the local user message, so the frontend can
            match the ASR ack to its placeholder bubble.
    """
    minimax = get_minimax_service()
    await safe_send_status(session_id, ConversationState.PROCESSING)

    # ASR: transcribe audio if provided.
    # Strategy (in order of accuracy):
    #   1. MiniMax Realtime WebSocket API (asr-01 model) — most accurate
    #   2. MiniMax cloud REST ASR (currently 404 on this key)
    #   3. Local faster-whisper (small) — offline fallback
    user_text = content
    asr_ok = False
    if audio_data:
        try:
            audio_bytes = base64.b64decode(audio_data)
            mime = audio_mime or "audio/webm"
            print(f"[ASR] decoding {len(audio_bytes)} bytes, mime={mime}")
            est_seconds = len(audio_bytes) / 32000
            print(f"[ASR] est_duration={est_seconds:.1f}s")
            transcribed = ""
            # Path 1: MiniMax Realtime API (best accuracy)
            try:
                transcribed = await minimax.speech_to_text_realtime(
                    audio_bytes, audio_mime=mime
                )
                print(f"[ASR] realtime result: {transcribed!r}")
            except Exception as rt_err:
                print(f"[ASR] realtime failed: {rt_err}")
            # Path 2: Cloud REST (if realtime returned empty or failed)
            if not transcribed or not transcribed.strip():
                try:
                    transcribed = await minimax.speech_to_text(
                        audio_bytes, audio_mime=mime
                    )
                    print(f"[ASR] cloud result: {transcribed!r}")
                except Exception as cloud_err:
                    print(f"[ASR] cloud failed: {cloud_err}")
            # Path 3: Local faster-whisper (last resort)
            if not transcribed or not transcribed.strip():
                print("[ASR] falling back to local faster-whisper")
                transcribed = await minimax.speech_to_text_local(
                    audio_bytes, audio_mime=mime
                )
                print(f"[ASR] local result: {transcribed!r}")
            if transcribed and transcribed.strip():
                user_text = transcribed.strip()
                asr_ok = True
            else:
                print(f"[ASR] no transcript — sending 'didn't hear' notice")
                user_text = "[系统：没听清你刚才说的内容，请重新说一遍或改用文字输入]"
        except Exception as e:
            print(f"[ASR] error: {e}")
            user_text = "[系统：语音识别出错，请重新说一遍或改用文字输入]"

    # Echo back what we understood the user said so the frontend can replace
    # any placeholder text with the canonical ASR transcript.
    if client_id:
        await safe_send_message(session_id, {
            "type": "user_message_ack",
            "id": client_id,
            "asr_text": user_text,
            "asr_ok": asr_ok,
            "timestamp": datetime.utcnow().isoformat()
        })

    session_manager.add_message(session_id, "user", user_text)
    save_message_to_db(session_id, "user", user_text)

    if not minimax.api_key:
        await _send_mock_response(session_id, "抱歉，我现在无法回答。请确保API密钥已正确配置。")
        return

    # Build context
    context = session_manager.get_context(session_id)
    session_info = session_manager.get_session_info(session_id) or {}
    role_config = session_info.get("role_config", {})
    persona = session_info.get("persona")
    # 销售员自填的练习档案（注入到 LLM prompt，让 AI 客户"看人下菜碟"）
    user_context = session_info.get("user_context")

    personality_map = {
        "rational": "analytical", "emotional": "expressive",
        "hesitant": "amiable", "decisive": "assertive"
    }
    customer_type = personality_map.get(
        role_config.get("personality", "decisive"), "assertive"
    )
    scenario = session_info.get("scenario_id", "general")

    conversation_history = context[-10:]
    for msg in conversation_history:
        if msg.get("role") == "ai":
            msg["role"] = "assistant"

    try:
        from app.services.conversation.handler import get_conversation_handler
        handler = get_conversation_handler()
        result = await handler.handle_message(
            user_message=user_text,
            conversation_history=conversation_history,
            customer_type=customer_type,
            scenario=scenario,
            persona=persona,
            user_context=user_context,
        )
        full_response = result.get("response", "")
        print(f"[LLM-RAW] {full_response!r}")
        # Strip <think>...</think> reasoning blocks (M-series wraps output)
        clean_response = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()
        # The M2.7 reasoning model often dumps its chain-of-thought OUTSIDE
        # <think> tags. Try to extract just the in-character reply: the
        # longest quoted "line" or the first paragraph that doesn't look
        # like meta-commentary.
        if clean_response and ('\n' in clean_response or '我应该' in clean_response or '特点：' in clean_response or '语音转文字' in clean_response):
            # Heuristic: keep only the first non-empty paragraph that doesn't
            # start with reasoning markers.
            lines = [l for l in clean_response.split('\n') if l.strip()]
            filtered = []
            skip_markers = ('语音转文字', '李明辉的', '我应该', '特点：', '我的任务', '作为', '你需要', '客户：')
            for line in lines:
                if any(line.strip().startswith(m) for m in skip_markers):
                    continue
                filtered.append(line.strip())
            if filtered:
                clean_response = filtered[0]
                print(f"[LLM-CLEANED] {clean_response!r}")

        if clean_response:
            session_manager.add_message(session_id, "ai", clean_response)
            save_message_to_db(session_id, "ai", clean_response)
            # Stash the references in a side-channel on the connection
            # manager (NOT in the LLM context — the LLM API rejects
            # "knowledge_refs" as a role name, so the request 400s).
            refs = result.get("knowledge_refs", [])
            if refs:
                if not hasattr(manager, '_knowledge_refs'):
                    manager._knowledge_refs = {}
                manager._knowledge_refs.setdefault(session_id, []).extend(refs)

            # Generate TTS audio so the user can replay this message later.
            audio_b64 = ""
            try:
                audio_bytes = await minimax.text_to_speech(
                    text=clean_response,
                    model="speech-2.8-hd",
                    voice="male-qn-qingse",
                    speed=1.0,
                    format="mp3",
                    emotion=result.get("emotion", "neutral"),
                    voice_modify=result.get("voice_modify", {})
                )
                audio_b64 = base64.b64encode(audio_bytes).decode()
            except Exception as tts_err:
                print(f"[TTS] Failed to generate audio for AI message: {tts_err}")

            ai_msg_id = f"msg-{session_id}-ai-{int(datetime.utcnow().timestamp() * 1000)}"
            await safe_send_message(session_id, {
                "type": "ai_message",
                "id": ai_msg_id,
                "content": clean_response,
                "audio_data": audio_b64,
                "knowledge_refs": result.get("knowledge_refs", []),
                "timestamp": datetime.utcnow().isoformat()
            })
            await _maybe_transition_phase(session_id)
        else:
            await safe_send_message(session_id, {
                "type": "ai_message",
                "content": "抱歉，我现在无法回答。请稍后再试。",
                "audio_data": ""
            })
    except Exception as e:
        print(f"[LLM] error: {e}")
        import traceback
        traceback.print_exc()
        await _send_mock_response(session_id, "抱歉，我现在无法回答。请确保API密钥已正确配置。")


async def _send_mock_response(session_id: str, content: str) -> None:
    """Send a fallback AI response when LLM is unavailable."""
    session_manager.add_message(session_id, "ai", content)
    save_message_to_db(session_id, "ai", content)
    await safe_send_message(session_id, {
        "type": "ai_message",
        "id": f"msg-{session_id}-ai-fallback",
        "content": content,
        "audio_data": "",
        "timestamp": datetime.utcnow().isoformat()
    })
    await safe_send_status(session_id, ConversationState.IDLE)


async def _maybe_transition_phase(session_id: str) -> None:
    """DEPRECATED: 硬性按消息数切阶段已废弃。

    之前按消息数 (3/6/9/12) 强行切 SPIN 阶段，导致销售员聊到一半被
    "赶" 到下一阶段，破坏自然对话节奏。已废弃，函数保留为空以
    兼容旧调用方；前端也不再消费 phase_complete 消息。
    """
    return


# =============================================================================
# First-message flow (background task)
# =============================================================================

async def _init_persona_and_first_message(websocket, session_id: str,
                                           scenario_name: str, scenario_id: str,
                                           role_config: dict) -> None:
    """Generate persona + opening message + TTS audio in background.

    If the session has an investigation_result (from SPIN pre-visit), use that
    as the persona directly instead of re-generating via LLM. This preserves
    the user's real-world research (e.g. 黄仁勋@NVIDIA).
    """
    try:
        # Check for pre-existing investigation_result (from SPIN flow)
        session_info = session_manager.get_session_info(session_id) or {}
        investigation_result = session_info.get("investigation_result")
        persona = None
        if investigation_result and investigation_result.get("name"):
            # Convert investigation_result to persona shape. Pull every field
            # the SPIN investigation endpoint returned so the LLM has full
            # context for role-playing (recent_news, media_reports, etc).
            ir = investigation_result
            recent_news = ir.get("recent_news") or ir.get("recent_activities") or []
            if isinstance(recent_news, str):
                recent_news = [recent_news]
            extra = ir.get("extra_info") or {}
            extra_lines = []
            if extra.get("leader_info"):
                extra_lines.append(f"高管/创始人信息：{extra['leader_info']}")
            if extra.get("media_reports"):
                mr = extra["media_reports"]
                if isinstance(mr, list):
                    extra_lines.append("媒体报道：" + "；".join(mr[:3]))
                else:
                    extra_lines.append(f"媒体报道：{mr}")
            if extra.get("funding_status"):
                extra_lines.append(f"融资/财务：{extra['funding_status']}")
            competitors = ir.get("competitors") or []
            background_full = ir.get("background", "")
            if competitors:
                background_full += "\n\n主要竞品：" + "、".join(competitors[:5])
            if extra_lines:
                background_full += "\n\n" + "\n".join(extra_lines)

            # Try to derive a more specific speaking_style by mapping the
            # person's title and seniority. For C-level executives we use a
            # sharp/exacting style; otherwise neutral.
            title = (ir.get("title", "") or "").lower()
            is_executive = any(kw in title for kw in [
                "ceo", "cto", "cfo", "总裁", "总监", "vp", "创始人", "founder", "chief"
            ])
            personality_picked = role_config.get("personality", "rational")
            personality_to_speaking_style = {
                "rational": "语气直接、逻辑清晰，会先质疑方案的逻辑链再决定是否接受。常用'等等'、'我想问一下'、'挺有意思的'这类口头禅。",
                "emotional": "语气温暖、有热情，会表达自己的兴奋或不满，会主动分享个人经历。常用'说实话'、'我跟你说'这类开场。",
                "hesitant": "语气谨慎、会有保留，会反复确认细节。常用'你确定吗'、'这个我得想想'。",
                "decisive": "语气干脆、决断快，会直入主题追问重点。常用'直接说'、'重点是'、'我要的是'。"
            }
            base_style = personality_to_speaking_style.get(personality_picked, personality_to_speaking_style["rational"])
            if is_executive:
                speaking_style = (
                    f"{base_style} 作为企业高管，会从战略层面和成本角度审视每个提议。"
                    f"喜欢反问，喜欢用'我们公司'/'我们团队'/'我们这个领域'的视角，"
                    f"会主动提到自己公司的产品、技术路线、合作伙伴生态。"
                )
            else:
                speaking_style = base_style

            persona = {
                "name": ir.get("name", ""),
                "gender": ir.get("gender", ""),
                "age_range": ir.get("age_range", ""),
                "title": ir.get("title", ""),
                "company": ir.get("company", ""),
                "industry": ir.get("industry", ""),
                "company_size": ir.get("company_size", ""),
                "background": background_full,
                "current_situation": ir.get("current_situation", ""),
                "pain_points": ir.get("potential_pains") or [],
                "concerns": ir.get("concerns") or [],
                "personality_traits": ir.get("personality_traits", ""),
                "speaking_style": speaking_style,
                "scenario_context": f"销售主动联系{ir.get('name', '客户')}讨论{scenario_name}相关业务",
                "recent_activities": "; ".join(recent_news[:5]) if recent_news else ""
            }
            print(f"[WS] Using investigation_result as persona: {persona.get('name')} - {persona.get('title')}@{persona.get('company')}")
        else:
            print(f"[WS] Generating persona for {session_id}...")
            persona = await generate_persona_for_session(scenario_name, role_config)
            print(f"[WS] Persona ready: {persona.get('name')} - {persona.get('title')}@{persona.get('company')}")

        session_manager.update_session_field(session_id, "persona", persona)

        first_text = await generate_opening_message(
            scenario_name=scenario_name,
            scenario_id=scenario_id,
            role_config=role_config,
            persona=persona
        )
        print(f"[WS] First message: {first_text}")

        # Add breath tags based on customer personality so TTS reads natural emotion
        try:
            from app.services.conversation.handler import add_breath_tags_to_response, detect_emotion
            # Map role_config.personality to emotion
            personality_to_emotion = {
                "rational": "neutral", "emotional": "happy",
                "hesitant": "fearful", "decisive": "angry",
            }
            opening_emotion = personality_to_emotion.get(
                role_config.get("personality", "rational"), "neutral"
            )
            print(f"[WS] DEBUG: calling add_breath_tags with emotion={opening_emotion}, text_len={len(first_text)}")
            first_text_with_tags = add_breath_tags_to_response(first_text, opening_emotion)
            print(f"[WS] First message with tags: {first_text_with_tags}")
        except Exception as e:
            import traceback
            print(f"[WS] Failed to add breath tags: {e}")
            traceback.print_exc()
            first_text_with_tags = first_text

        session_manager.add_message(session_id, "ai", first_text_with_tags)
        first_msg_id = f"msg-{session_id}-init"

        await safe_send_message(session_id, {
            "type": "ai_message",
            "id": first_msg_id,
            "content": first_text_with_tags,
            "audio_data": "",
            "persona": persona,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Background TTS - send audio update later (use tagged text so TTS reads emotion)
        try:
            minimax = get_minimax_service()
            # opening_emotion is computed earlier (line ~590) from personality.
            # Pass it to TTS so the opening audio reflects the customer's mood.
            audio_bytes = await minimax.text_to_speech(
                text=first_text_with_tags,
                model="speech-2.8-hd",
                voice="male-qn-qingse",
                speed=1.0,
                volume=1.0,
                pitch=1.0,
                format="mp3",
                emotion=opening_emotion,
                voice_modify=None,
            )
            await safe_send_message(session_id, {
                "type": "ai_message_audio",
                "id": first_msg_id,
                "audio_data": base64.b64encode(audio_bytes).decode()
            })
            print(f"[WS] First message audio sent: {len(audio_bytes)} bytes")
        except Exception as tts_err:
            print(f"[WS] First message TTS failed: {tts_err}")
    except Exception as e:
        print(f"[WS] Persona/first_message generation failed: {e}")
        import traceback
        traceback.print_exc()
        # Send a fallback
        await safe_send_message(session_id, {
            "type": "ai_message",
            "id": f"msg-{session_id}-fallback",
            "content": "嗯...你稍等一下。",
            "audio_data": "",
            "timestamp": datetime.utcnow().isoformat()
        })


# =============================================================================
# WebSocket endpoint
# =============================================================================

@app.websocket("/ws/practice/{session_id}")
async def practice_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for practice chat sessions.

    Flow:
    1. Accept connection, send "preparing" status
    2. Load or create session, fire-and-forget persona + opening message
    3. Send immediate fallback message so the UI has something to show
    4. Enter receive loop and dispatch incoming client messages
    """
    await manager.connect(websocket, session_id)
    print(f"[WS] Connected: {session_id}")

    await safe_send_status(session_id, ConversationState.IDLE,
                           {"phase": "preparing_persona"})

    # ------------------------------------------------------------------
    # Load / create session
    # ------------------------------------------------------------------
    session_info = session_manager.get_session_info(session_id)
    if not session_info:
        role_config = {}
        scenario_id = ""
        customer_context = None
        investigation_result = None
        user_context = None
        scenario_name = "AI客户"
        try:
            from app.database import get_db
            from app.models.practice import PracticeSession, Scenario
            db = next(get_db())
            db_session = db.query(PracticeSession).filter(
                PracticeSession.id == session_id
            ).first()
            if db_session:
                role_config = db_session.role_config or {}
                scenario_id = db_session.scenario_id or ""
                customer_context = db_session.customer_context
                investigation_result = db_session.investigation_result
                user_context = db_session.user_context
                if scenario_id:
                    db_scenario = db.query(Scenario).filter(
                        Scenario.id == scenario_id
                    ).first()
                    if db_scenario:
                        scenario_name = db_scenario.name
        except Exception as e:
            print(f"[WS] Failed to load session: {e}")

        session_manager.create_session(
            session_id, scenario_id, role_config,
            customer_context, investigation_result, user_context
        )
    else:
        # Reuse persisted session - load role_config from DB to be safe
        role_config = session_info.get("role_config", {})
        scenario_id = session_info.get("scenario_id", "")
        customer_context = session_info.get("customer_context")
        investigation_result = session_info.get("investigation_result")
        user_context = session_info.get("user_context")
        scenario_name = "AI客户"
        if not scenario_name or scenario_name == "AI客户":
            try:
                from app.database import get_db
                from app.models.practice import Scenario
                db = next(get_db())
                if scenario_id:
                    db_scenario = db.query(Scenario).filter(
                        Scenario.id == scenario_id
                    ).first()
                    if db_scenario:
                        scenario_name = db_scenario.name
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Fire-and-forget persona + opening message (slow LLM)
    # ------------------------------------------------------------------
    asyncio.create_task(_init_persona_and_first_message(
        websocket, session_id, scenario_name, scenario_id, role_config
    ))

    # ------------------------------------------------------------------
    # Send immediate placeholder so the UI has something to show
    # ------------------------------------------------------------------
    # Send immediate placeholder so the UI has something to show.
    # Run through add_breath_tags so even the placeholder gets a natural emotion tag.
    # ------------------------------------------------------------------
    placeholder_text = "嗯，你好，我这边手头有个项目在选型，刚开完会，你说说你们能提供什么。"
    print(f"[WS] DEBUG placeholder: personality={role_config.get('personality')!r}, role_config keys={list(role_config.keys())}")
    try:
        from app.services.conversation.handler import add_breath_tags_to_response
        personality_to_emotion = {
            "rational": "neutral", "emotional": "happy",
            "hesitant": "fearful", "decisive": "angry",
        }
        placeholder_emotion = personality_to_emotion.get(
            role_config.get("personality", "rational"), "neutral"
        )
        print(f"[WS] DEBUG placeholder: emotion={placeholder_emotion}, text_len={len(placeholder_text)}")
        placeholder_text = add_breath_tags_to_response(placeholder_text, placeholder_emotion)
        print(f"[WS] DEBUG placeholder with tags: {placeholder_text}")
    except Exception as e:
        import traceback
        print(f"[WS] DEBUG placeholder ERROR: {e}")
        traceback.print_exc()

    await safe_send_message(session_id, {
        "type": "ai_message",
        "id": f"msg-{session_id}-init",
        "content": placeholder_text,
        "audio_data": "",
        "timestamp": datetime.utcnow().isoformat()
    })

    # ------------------------------------------------------------------
    # Receive loop (single, well-defined)
    # ------------------------------------------------------------------
    try:
        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type")
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"[WS] Error receiving JSON: {e}")
                break

            if msg_type == "user_message":
                asyncio.create_task(process_user_message(
                    websocket, session_id,
                    data.get("content", ""),
                    data.get("audio_data", ""),
                    data.get("audio_mime", "audio/webm"),
                    data.get("id")
                ))
            elif msg_type == "stop_playback":
                await safe_send_status(session_id, ConversationState.IDLE)
                await safe_send_message(session_id, {"type": "playback_stopped"})
            elif msg_type == "voice_start":
                await safe_send_status(session_id, ConversationState.USER_SPEAKING)
            elif msg_type == "voice_end":
                await safe_send_status(session_id, ConversationState.IDLE)
                if session_manager.should_insert_backchannel(session_id):
                    backchannel_text = backchannel_manager.generate_backchannel_text()
                    await safe_send_message(session_id, {
                        "type": "backchannel",
                        "content": backchannel_text
                    })

            if session_manager.should_trigger_summary(session_id):
                await safe_send_message(session_id, {
                    "type": "summary_trigger",
                    "message": "建议进行阶段性总结"
                })
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
        session_manager.end_session(session_id)


# =============================================================================
# Standalone TTS / ASR / chat endpoints (for testing)
# =============================================================================

class TTSRequest(BaseModel):
    text: str
    voice: str = "male-qn-qingse"


@app.post("/api/v1/tts")
async def text_to_speech(request: TTSRequest):
    minimax = get_minimax_service()
    if not minimax.api_key:
        return {"error": "MINIMAX_API_KEY not configured"}
    try:
        audio_bytes = await minimax.text_to_speech(
            text=request.text, voice=request.voice
        )
        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/mp3",
            headers={"Content-Disposition": "attachment; filename=tts.mp3"}
        )
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/v1/asr")
async def speech_to_text(audio: UploadFile = File(...)):
    minimax = get_minimax_service()
    if not minimax.api_key:
        return {"error": "MINIMAX_API_KEY not configured"}
    try:
        audio_data = await audio.read()
        text = await minimax.speech_to_text(audio_data)
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: str = "M2.7"


@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    minimax = get_minimax_service()
    if not minimax.api_key:
        return {"error": "MINIMAX_API_KEY not configured"}
    try:
        response = await minimax.chat(messages=request.messages, model=request.model)
        return {"response": response}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
