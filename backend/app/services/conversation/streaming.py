"""
Streaming Pipeline — 把 LLM + TTS 改成流式，句子级切片，逐句推送

目标：用户说完 → 1.5-2s 听到 AI 第一句

设计：
  1. ASR final transcript 已就绪
  2. 并行 4 任务装配 context（user_ctx / history / RAG / persona）
  3. LLM stream=True → 累积 token
  4. 每凑齐 1 个完整句子（中英文标点边界）→ 立刻送 TTS → 推 audio_chunk
  5. 整段生成完 → 推 ai_streaming_end（带 audio_data 给回放用）

兼容性：保留原 handle_message() 给非 WS 路径用。
"""
import asyncio
import json
import re
import time
import base64
from typing import AsyncIterator, List, Optional, Dict, Any, Callable, Awaitable

# 句子边界正则：中英文标点 + 问号 + 感叹号 + 句号 + 换行
# 注意：保留 lookbehind 的标点，但不切分括号 / 引号 / 数字后的小数点
_SENTENCE_BOUNDARY = re.compile(
    r'(?<=[。！？!?；;])\s*'           # 中英文主标点
    r'|(?<=[.!?])\s+(?=[A-Z一-鿿])'   # 英文 . ! ? 后接大写或中文（口语）
    r'|\n+'                              # 换行也算
)


def split_sentences(buffer_text: str) -> List[str]:
    """
    给定累积的 LLM 输出，找出已完整的句子。

    Args:
        buffer_text: LLM 累积到现在的所有 token 拼起来

    Returns:
        list of 完整句子（不含标点后的残留 buffer）

    Note: 不会返回最后那个可能还在累积的尾巴。
    """
    if not buffer_text:
        return []

    # 找所有句子边界位置
    sentences = []
    pos = 0
    for m in _SENTENCE_BOUNDARY.finditer(buffer_text):
        end = m.end()
        s = buffer_text[pos:end].strip()
        if s:
            sentences.append(s)
        pos = end
    return sentences


def remaining(buffer_text: str) -> str:
    """取 buffer 中最后未完成的尾巴"""
    if not buffer_text:
        return ""
    last_boundary = None
    for m in _SENTENCE_BOUNDARY.finditer(buffer_text):
        last_boundary = m.end()
    if last_boundary is None:
        return buffer_text
    return buffer_text[last_boundary:]


def strip_think_blocks(text: str) -> str:
    """去除 M2.7 模型输出的 <think>...</think> 思考块"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def looks_like_reasoning_dump(text: str) -> bool:
    """
    M2.7 有时会把 chain-of-thought 直接 dump 在 <think> 块之外。
    启发式：检测典型 reasoning 标记，如果匹配，跳过整段。
    """
    if not text:
        return False
    markers = (
        '语音转文字', '我应该', '特点：', '我的任务',
        '作为', '你需要', '客户：', '李明辉的',
    )
    head = text[:200]
    return any(m in head for m in markers)


def clean_reasoning_dump(text: str) -> str:
    """
    提取真正 in-character 的回复：跳过 reasoning 标记开头的行。
    """
    if not text:
        return text
    lines = [l for l in text.split('\n') if l.strip()]
    skip = ('语音转文字', '我应该', '特点：', '我的任务', '作为', '你需要', '客户：', '李明辉的', '好的我', '好的您')
    for line in lines:
        if not any(line.strip().startswith(m) for m in skip):
            return line.strip()
    return text


def _build_simple_system_prompt(persona, scenario: str, user_context) -> str:
    """
    给 MiniMax-Text-01 用的极简 system prompt。
    故意短、目标明确、避免触发长 reasoning。
    """
    # 提取 persona 关键信息
    name = ""
    title = ""
    company = ""
    industry = ""
    background = ""
    if persona:
        name = persona.get("name", "")
        title = persona.get("title", "")
        company = persona.get("company", "")
        industry = persona.get("industry", "")
        bg = persona.get("background", "")
        if bg:
            background = bg[:150]

    # 销售员背景
    sales_info = ""
    if user_context:
        sc_name = user_context.get("name", "")
        sc_product = user_context.get("product", "")
        if sc_name: sales_info += f"销售员 {sc_name} "
        if sc_product: sales_info += f"卖{sc_product}"

    return f"""你扮演客户，{name or '某客户'}，{title}@{company}，{industry}行业。
{('背景：' + background) if background else ''}

场景：{scenario or '销售拜访'}

{sales_info + '正找你谈。' if sales_info else '有销售来找你谈。'}

回复要求（必须遵守）：
- 直接回答，不要任何思考或解释
- 短句，1-3 句，像真人说话
- 口语化，可以用 (breath) (sighs) 等 TTS 标签
- 绝不扮演销售、绝不提产品优势
- 绝不输出"<think>"等内部思考标记
"""


class SentenceBuffer:
    """
    累积 LLM 流式 token，按句子边界切分并产出。
    解决：英文省略号、数字小数点、连续标点等"假边界"问题。
    实时剥掉 <think>...</think> 块（M2.7 reasoning model）。
    """

    def __init__(self):
        self._buf = ""
        self._in_think = False  # 是否在 <think> 块内
        self._think_buf = ""    # 累积 think 内容用于检测结束

    def push(self, token: str) -> List[str]:
        """
        追加新 token，返回本次新增的完整句子列表。
        残留的部分（不完整句子）保留在内部 buffer。
        """
        if not token:
            return []
        # 流式剥 think 块：检测 <think> 和 </think>
        clean = self._strip_think(token)
        if not clean:
            return []
        self._buf += clean
        sentences = split_sentences(self._buf)
        if sentences:
            # 把已完成句子切走，保留尾巴
            cut_pos = 0
            for s in sentences:
                idx = self._buf.find(s, cut_pos)
                if idx >= 0:
                    cut_pos = idx + len(s)
            self._buf = self._buf[cut_pos:]
        return sentences

    def _strip_think(self, token: str) -> str:
        """实时剥 <think>...</think> 块，处理跨 token 的边界"""
        out = ""
        i = 0
        while i < len(token):
            if self._in_think:
                # 找 </think>
                end_idx = token.find("</think>", i)
                if end_idx >= 0:
                    self._in_think = False
                    i = end_idx + len("</think>")
                else:
                    break  # 还在 think 块里，整个 token 都丢掉
            else:
                # 找 <think>
                start_idx = token.find("<think>", i)
                if start_idx >= 0:
                    out += token[i:start_idx]
                    self._in_think = True
                    i = start_idx + len("<think>")
                else:
                    out += token[i:]
                    break
        return out

    def flush(self) -> str:
        """
        强制取出 buffer 中剩余内容（生成结束时调用）。
        可能包含未完成句子（兜底）。
        """
        rest = self._buf
        self._buf = ""
        return rest.strip()

    def reset(self):
        self._buf = ""
        self._in_think = False
        self._think_buf = ""


async def sentence_to_audio(
    sentence: str,
    minimax,
    emotion: str = "neutral",
    voice_modify: Optional[Dict] = None,
    voice: str = "male-qn-qingse",
) -> bytes:
    """
    把一个句子转成 mp3 bytes。
    短句（约 60-100 字）合成时间 400-700ms。
    """
    try:
        return await minimax.text_to_speech(
            text=sentence,
            model="speech-2.8-hd",
            voice=voice,
            speed=1.0,
            format="mp3",
            emotion=emotion if emotion else "neutral",
            voice_modify=voice_modify or {},
        )
    except Exception as e:
        print(f"[TTS] sentence failed: {e}")
        return b""


async def parallel_context_assembly(
    session_id: str,
    user_text: str,
    session_info: Dict,
    handler,
) -> Dict[str, Any]:
    """
    4 源并行装配 context（user_ctx / history / RAG / persona），
    总耗时 ≈ max(t1..t4) 而不是 4*t。

    Returns dict with: messages, emotion, voice_modify, knowledge_refs
    """
    from app.services.knowledge.tools import (
        execute_search_knowledge,
        execute_get_spin_questions,
    )

    role_config = session_info.get("role_config", {})
    customer_type_map = {
        "rational": "analytical", "emotional": "expressive",
        "hesitant": "amiable", "decisive": "assertive",
    }
    customer_type = customer_type_map.get(
        role_config.get("personality", "decisive"), "assertive"
    )
    scenario = session_info.get("scenario_id", "general")
    persona = session_info.get("persona")
    user_context = session_info.get("user_context")

    # 从 session_manager 拉历史（最新 10 轮）
    from app.websocket.manager import session_manager
    ctx = session_manager.get_context(session_id)
    if not ctx:
        # 退化：从 DB 拉
        from app.database import SessionLocal
        from app.models.practice import PracticeMessage
        db = SessionLocal()
        try:
            msgs = db.query(PracticeMessage).filter(
                PracticeMessage.session_id == session_id
            ).order_by(PracticeMessage.created_at).all()
            ctx = [{"role": m.role, "content": m.content} for m in msgs]
        finally:
            db.close()
    history = ctx[-10:]
    for msg in history:
        if msg.get("role") == "ai":
            msg["role"] = "assistant"

    # 并行装配 — 完整保留所有功能
    async def build_msgs():
        return handler._build_messages(
            user_text, history, customer_type, scenario,
            None, None, persona, user_context,
        )

    async def detect_emot():
        from app.services.conversation.handler import detect_emotion
        return detect_emotion(user_text, customer_type, history)

    async def rag():
        """RAG 检索知识库（保留功能）"""
        try:
            refs = handler._retrieve_knowledge_references(
                user_message=user_text,
                conversation_history=history,
                scenario=scenario,
            )
            return refs or []
        except Exception as e:
            print(f"[RAG] failed (non-fatal): {e}")
            return []

    msgs, emotion_data, knowledge_refs = await asyncio.gather(
        build_msgs(), detect_emot(), rag()
    )

    # 把 knowledge_refs 注入到 system message
    if knowledge_refs and msgs and msgs[0].get("role") == "system":
        ref_text = "\n\n【知识库参考】\n" + "\n".join(
            f"- [{r.get('source', '?')}] {r.get('excerpt', '')[:120]}"
            for r in knowledge_refs[:3]
        )
        msgs[0]["content"] = msgs[0]["content"] + ref_text

    return {
        "messages": msgs,
        "emotion": emotion_data.get("emotion", "neutral"),
        "voice_modify": emotion_data.get("voice_modify", {}),
        "breath_tag": emotion_data.get("breath_tag", ""),
        "knowledge_refs": knowledge_refs,
    }


async def stream_pipeline(
    websocket_send,
    websocket_send_binary,
    session_id: str,
    user_text: str,
    user_audio_data: Optional[str],
    user_audio_mime: Optional[str],
    client_id: Optional[str],
    minimax,
    handler,
    persona: Optional[Dict] = None,
    user_context: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    主入口：执行一次完整的"用户消息 → 流式 AI 回复"流程。

    Args:
        websocket_send: async callable(json_dict) -> awaitable
        session_id: session uuid
        user_text: ASR 转写后的文本（或用户输入）
        minimax: MiniMax service
        handler: ConversationHandler 实例
        persona, user_context: 来自 session_info

    Returns:
        dict with: full_response, sentences (list[str]), audio_chunks (list[bytes]),
                   emotion, voice_modify, knowledge_refs
    """
    from app.websocket.manager import session_manager
    from app.services.conversation.handler import add_breath_tags_to_response

    session_info = session_manager.get_session_info(session_id) or {}
    role_config = session_info.get("role_config", {})
    customer_type_map = {
        "rational": "analytical", "emotional": "expressive",
        "hesitant": "amiable", "decisive": "assertive",
    }
    customer_type = customer_type_map.get(
        role_config.get("personality", "decisive"), "assertive"
    )
    scenario = session_info.get("scenario_id", "general")
    if persona is None:
        persona = session_info.get("persona")
    if user_context is None:
        user_context = session_info.get("user_context")

    t0 = time.time()
    # 1. 并行装配 context
    print(f"[STREAM] assembling context for {user_text[:30]}...")
    assembled = await parallel_context_assembly(
        session_id, user_text, session_info, handler
    )
    messages = assembled["messages"]
    emotion = assembled["emotion"]
    voice_modify = assembled["voice_modify"]
    breath_tag = assembled["breath_tag"]
    knowledge_refs = assembled["knowledge_refs"]
    print(f"[STREAM] context assembly took {(time.time()-t0)*1000:.0f}ms, msgs={len(messages)}, refs={len(knowledge_refs)}")

    # 2. 发 ai_streaming_start
    msg_id = f"msg-{session_id}-ai-{int(time.time()*1000)}"
    await websocket_send({
        "type": "ai_streaming_start",
        "id": msg_id,
        "content": "",
        "timestamp": time.time(),
    })

    # 3. 流式 LLM + 句子切分
    buf = SentenceBuffer()
    full_text = ""
    sentences_emitted: List[str] = []
    audio_chunks_emitted: List[bytes] = []
    tts_tasks: List[Awaitable] = []
    t0 = time.time()
    try:
        token_count = 0
        # 关键优化：边收 LLM token 边推送 TTS 完成的 audio chunk
        # 用 asyncio.wait 监控"任何 TTS 任务完成就立刻推"，不等 gather
        async def monitor_tts():
            """在 LLM 还在生成时，实时把已完成的 TTS 推给前端"""
            while True:
                if not tts_tasks:
                    await asyncio.sleep(0.05)
                    continue
                # 等任何一个 TTS 任务完成（不阻塞 LLM 流）
                done, pending = await asyncio.wait(
                    tts_tasks, return_when=asyncio.FIRST_COMPLETED, timeout=0.1
                )
                for d in done:
                    tts_tasks.remove(d)
                    try:
                        r = d.result()
                        if r and isinstance(r, (bytes, bytearray)) and len(r) > 0:
                            audio_chunks_emitted.append(bytes(r))
                            if websocket_send_binary:
                                try:
                                    await websocket_send_binary(bytes(r))
                                    print(f"[STREAM] pushed audio chunk ({len(r)} bytes) at {(time.time()-t0)*1000:.0f}ms")
                                except Exception as e:
                                    print(f"[STREAM] send_binary error: {e}")
                    except Exception as e:
                        print(f"[STREAM] TTS task error: {e}")
                if not tts_tasks and not llm_streaming:
                    break

        # 起 monitor（和 LLM 流并行）
        monitor_task = asyncio.create_task(monitor_tts())

        # 用 M2.7-highspeed（保持全部功能：persona/user_context/history/RAG/emotion 全在）
        llm_streaming = True
        async for token in minimax.chat_stream(messages, model="MiniMax-M2.7-highspeed"):
            token_count += 1
            if token_count <= 3:
                print(f"[STREAM] first tokens: {token[:30]!r}")
            # 后处理 token
            full_text += token
            # 切句
            for s in buf.push(token):
                # 把 breath_tag 插入第一句开头
                if not sentences_emitted and breath_tag:
                    tag = " ".join(breath_tag) if isinstance(breath_tag, list) else str(breath_tag)
                    s = f"{tag} {s}"
                sentences_emitted.append(s)
                print(f"[STREAM] sentence #{len(sentences_emitted)}: {s[:50]}...")
                # 并发送 TTS（不等它返回）
                tts_tasks.append(asyncio.create_task(
                    sentence_to_audio(s, minimax, emotion, voice_modify)
                ))
                # 推 streaming update
                await websocket_send({
                    "type": "ai_streaming_update",
                    "id": msg_id,
                    "content": "".join(sentences_emitted),
                    "timestamp": time.time(),
                })
        llm_streaming = False
        print(f"[STREAM] LLM done, total {token_count} tokens")
        # 4. 收尾：把残留 buffer 拼出来
        tail = buf.flush()
        if tail:
            tail = clean_reasoning_dump(tail)
            if tail and not looks_like_reasoning_dump(tail):
                if not sentences_emitted and breath_tag:
                    tag = " ".join(breath_tag) if isinstance(breath_tag, list) else str(breath_tag)
                    tail = f"{tag} {tail}"
                sentences_emitted.append(tail)
                tts_tasks.append(asyncio.create_task(
                    sentence_to_audio(tail, minimax, emotion, voice_modify)
                ))
        # 等 monitor 把所有剩余 TTS 推完
        if tts_tasks:
            await asyncio.gather(*tts_tasks, return_exceptions=True)
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    except Exception as e:
        print(f"[STREAM] LLM error: {e}")
        import traceback
        traceback.print_exc()
        await websocket_send({
            "type": "ai_streaming_end",
            "id": msg_id,
            "content": "抱歉，我现在无法回答。",
            "audio_data": "",
            "timestamp": time.time(),
        })
        return {
            "full_response": "",
            "sentences": [],
            "audio_chunks": [],
            "emotion": emotion,
            "voice_modify": voice_modify,
            "knowledge_refs": knowledge_refs,
        }

    elapsed_ms = (time.time() - t0) * 1000
    print(f"[STREAM] LLM+sentences in {elapsed_ms:.0f}ms, "
          f"{len(sentences_emitted)} sentences, {len(audio_chunks_emitted)} audio chunks")

    # 5. 清理 full_text
    clean = strip_think_blocks(full_text)
    clean = clean_reasoning_dump(clean) if looks_like_reasoning_dump(clean) else clean
    if not clean:
        clean = "".join(sentences_emitted)

    # 6. 为整段合成一个 mp3（给回放用）
    full_audio_b64 = ""
    if clean:
        try:
            full_audio = await minimax.text_to_speech(
                text=clean,
                model="speech-2.8-hd",
                voice="male-qn-qingse",
                speed=1.0,
                format="mp3",
                emotion=emotion,
                voice_modify=voice_modify or {},
            )
            full_audio_b64 = base64.b64encode(full_audio).decode()
        except Exception as e:
            print(f"[STREAM] full TTS failed: {e}")

    # 7. 推 ai_streaming_end
    await websocket_send({
        "type": "ai_streaming_end",
        "id": msg_id,
        "content": clean,
        "audio_data": full_audio_b64,
        "knowledge_refs": knowledge_refs,
        "timestamp": time.time(),
    })

    return {
        "full_response": clean,
        "sentences": sentences_emitted,
        "audio_chunks": audio_chunks_emitted,
        "emotion": emotion,
        "voice_modify": voice_modify,
        "knowledge_refs": knowledge_refs,
    }
