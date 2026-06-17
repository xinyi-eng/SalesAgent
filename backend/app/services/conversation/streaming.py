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
import sys
import time
import base64
from typing import AsyncIterator, List, Optional, Dict, Any, Callable, Awaitable

# Windows CMD 默认 GBK 编码，遇到 emoji / 中日韩生僻字会 UnicodeEncodeError
# 强制让 print 用 utf-8，把 token / 句子原样打出来（不再 gbk 'illegal multibyte'）
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 句子边界正则：中英文标点 + 问号 + 感叹号 + 句号
# 注意：保留 lookbehind 的标点，但不切分括号 / 引号 / 数字后的小数点
# 不在 \n 切（MiniMax LLM 输出含 \n\n 分段，但切 3 段会让 TTS 并发到 3 个、限流变慢）
_SENTENCE_BOUNDARY = re.compile(
    r'(?<=[。！？!?；;])\s*'           # 中英文主标点
    r'|(?<=[.!?])\s+(?=[A-Z一-鿿])'   # 英文 . ! ? 后接大写或中文（口语）
)

# P1: 流式 TTS 提前触发阈值 — buffer 累积到 ~25 字时，如果当前 token 末尾不是数字/字母，
# 也允许切出。避免 LLM 一口气 yield 整个句子（"嗯，精度多少？价格呢？"）时 TTS
# 一直在等完整句号。让 TTS 真正和 LLM 并行。
# 阈值 25 字：避免切出 (breath) 这种 8 字短句（MiniMax TTS 短句会因限流/冷启动变慢）
_PARTIAL_BOUNDARY = re.compile(
    r'(?<=[，,、：:。；;])\s*'         # 短停顿标点（次级边界）
    r'|\s+'                              # 空格也算可切
)
_PARTIAL_MIN_CHARS = 25


def split_sentences(buffer_text: str, allow_partial: bool = True) -> List[str]:
    """
    给定累积的 LLM 输出，找出已完整的句子。

    Args:
        buffer_text: LLM 累积到现在的所有 token 拼起来
        allow_partial: True 时允许用次级边界（逗号/分号/空格）切短句，
                       让 TTS 在 LLM 还在推后续 token 时就能 fire。
                       要求累积 >= _PARTIAL_MIN_CHARS 才切。

    Returns:
        list of 完整句子（不含标点后的残留 buffer）

    Note: 不会返回最后那个可能还在累积的尾巴。
    """
    if not buffer_text:
        return []

    # 先找主边界（句号问号感叹号）
    sentences = []
    pos = 0
    last_main_end = 0
    for m in _SENTENCE_BOUNDARY.finditer(buffer_text):
        end = m.end()
        s = buffer_text[pos:end].strip()
        if s:
            sentences.append(s)
        pos = end
        last_main_end = end
    # 如果有主边界句子，先返回（让完整句号能切出）
    if sentences:
        return sentences
    # 没主边界，且允许次级切句（流式 TTS 提前触发）— 找次级边界
    if not allow_partial or len(buffer_text) < _PARTIAL_MIN_CHARS:
        return []
    # 找次级边界（逗号/分号/空格）后位置
    candidates = []
    for m in _PARTIAL_BOUNDARY.finditer(buffer_text):
        candidates.append(m.end())
    if not candidates:
        return []
    # 选最后一个让 >= _PARTIAL_MIN_CHARS 的位置
    chosen = None
    for c in candidates:
        if c >= _PARTIAL_MIN_CHARS:
            chosen = c  # 取最后一个满足的
    if chosen is None:
        return []
    s = buffer_text[:chosen].strip()
    if not s:
        return []
    return [s]


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
    """保留为防御性兜底 — 当前 chat_stream 默认 reasoning_split=True，
    内容里不应再含 <think> 块。万一上游退化，这里做最后一道保险。"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def looks_like_reasoning_dump(text: str) -> bool:
    """保留为防御性兜底（默认 False，因 reasoning_split=True 已把 think 拆出去）。"""
    return False


def clean_reasoning_dump(text: str) -> str:
    """保留为防御性兜底：当前 chat_stream 已 reasoning_split=True，原始内容就是 in-character。"""
    return text.strip() if text else text


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

        P1 优化：默认 allow_partial=True，让 split_sentences 在没主边界（句号问号）
        时也能用次级边界（逗号/分号/空格）切短句，让 TTS 在 LLM 还在推后续 token 时
        就能 fire，真正实现 TTS 与 LLM 并行。
        """
        if not token:
            return []
        # 流式剥 think 块：检测 <think> 和 </think>
        clean = self._strip_think(token)
        if not clean:
            return []
        self._buf += clean
        # 实测 partial split 反而触发 MiniMax TTS 并发限流：
        # 1 句完整 TTS 用 turbo 5.2s，但 3-4 个并发 TTS 每个 12-14s。
        # 当前 LLM 一口气 yield 整个句子，partial 切短句没收益。
        # 等将来 LLM 真正流式推 token（1 token / chunk）时再开。
        sentences = split_sentences(self._buf, allow_partial=False)
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
    t_tts = time.time()
    try:
        out = await minimax.text_to_speech(
            text=sentence,
            model="speech-2.8-turbo",
            voice=voice,
            speed=1.0,
            format="mp3",
            emotion=emotion if emotion else "neutral",
            voice_modify=voice_modify or {},
        )
        print(f"[TTS][{int((time.time()-t_tts)*1000):>4}ms] {len(sentence)} chars → {len(out)} bytes")
        return out
    except Exception as e:
        print(f"[TTS] sentence failed ({int((time.time()-t_tts)*1000)}ms): {e}")
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
    print(f"[STREAM][T=    0ms] assembling context for {user_text[:30]!r}...")
    assembled = await parallel_context_assembly(
        session_id, user_text, session_info, handler
    )
    t_ctx = int((time.time() - t0) * 1000)
    messages = assembled["messages"]
    emotion = assembled["emotion"]
    voice_modify = assembled["voice_modify"]
    breath_tag = assembled["breath_tag"]
    knowledge_refs = assembled["knowledge_refs"]
    print(f"[STREAM][T={t_ctx:>5}ms] ← context assembly done in {t_ctx}ms, msgs={len(messages)}, refs={len(knowledge_refs)}, emotion={emotion}")

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
    tts_tasks: List[asyncio.Task] = []
    t0 = time.time()
    stop_event = asyncio.Event()  # 通知 monitor 退出
    try:
        token_count = 0
        first_token_at = None
        # 关键优化：边收 LLM token 边推送 TTS 完成的 audio chunk
        async def monitor_tts():
            """在 LLM 还在生成时，实时把已完成的 TTS 推给前端"""
            while not stop_event.is_set():
                if not tts_tasks:
                    # 没任务了，等 LLM 完或 stop
                    if not llm_streaming:
                        break
                    await asyncio.sleep(0.05)
                    continue
                # 等任何一个 TTS 任务完成
                done, pending = await asyncio.wait(
                    tts_tasks, return_when=asyncio.FIRST_COMPLETED, timeout=0.1
                )
                for d in done:
                    # 防御性：d 可能已被 main task remove（比如 gather 完成时），
                    # 用 if 保护避免 ValueError
                    if d in tts_tasks:
                        tts_tasks.remove(d)
                    try:
                        r = d.result()
                        if r and isinstance(r, (bytes, bytearray)) and len(r) > 0:
                            audio_chunks_emitted.append(bytes(r))
                            if websocket_send_binary:
                                try:
                                    await websocket_send_binary(bytes(r))
                                    print(f"[STREAM][T={int((time.time()-t0)*1000):>5}ms] pushed audio chunk ({len(r)} bytes)")
                                except Exception as e:
                                    print(f"[STREAM] send_binary error: {e}")
                    except Exception as e:
                        print(f"[STREAM] TTS task error: {e}")
            print(f"[STREAM][T={int((time.time()-t0)*1000):>5}ms] monitor exit, total audio chunks pushed: {len(audio_chunks_emitted)}")

        # 起 monitor（和 LLM 流并行）
        monitor_task = asyncio.create_task(monitor_tts())

        # 用 M2.7-highspeed（保持全部功能：persona/user_context/history/RAG/emotion 全在）
        llm_streaming = True
        print(f"[STREAM][T={int((time.time()-t0)*1000):>5}ms] → calling chat_stream (model=M2.7-highspeed, reasoning_split=True)")
        # 实测结论：MiniMax M2.7-highspeed 一次 yield 整个句子（不是真 1 token / chunk）。
        # 流式切句（每 token 切）反而切出 2-4 个短句，TTS 并发触发限流，每句 12-15s。
        # 改成：等 LLM stream 结束再统一切 + 1 句完整 TTS。Turbo 5.2s 即可。
        # 用户感知：先推 streaming_update 看到 AI 在想（T=8s 时就显示），再 TTS 5s 后听到。
        async for token in minimax.chat_stream(messages, model="MiniMax-M2.7-highspeed"):
            now_ms = int((time.time() - t0) * 1000)
            token_count += 1
            if first_token_at is None:
                first_token_at = now_ms
                print(f"[STREAM][T={now_ms:>5}ms] ← FIRST token from LLM (TTFT)")
            if token_count <= 3:
                print(f"[STREAM][T={now_ms:>5}ms] token #{token_count}: {token[:30]!r}")
            # 后处理 token
            full_text += token
            # 累积到 buf（不切句，等 LLM 完再切）
            buf.push(token)
            # 实时推 streaming update（让前端看到 AI 正在"打字"）
            # 用 strip 后的 full_text 作为可见内容
            visible = strip_think_blocks(full_text) if False else full_text
            if visible.strip() and (not sentences_emitted or sentences_emitted[-1] != visible):
                # 第一句还没 fire 时不发 update（等真正 TTS 时一起发）
                pass
            # 实时把 visible text 推给前端（但 ai_streaming_update content 留空给 LLM 完才发）
        llm_streaming = False
        end_ms = int((time.time() - t0) * 1000)
        print(f"[STREAM][T={end_ms:>5}ms] ← LLM stream ended, total {token_count} tokens, first_token_at={first_token_at}ms, last_token_at={end_ms}ms")
        # 4. LLM 结束：flush buf 拿到完整内容（不切句，1 句完整 TTS）
        tail = buf.flush()
        full_sentence = tail.strip() if tail else ""
        if full_sentence:
            full_sentence = clean_reasoning_dump(full_sentence)
        if full_sentence and not looks_like_reasoning_dump(full_sentence):
            # 把 breath_tag 插到开头
            if breath_tag:
                tag = " ".join(breath_tag) if isinstance(breath_tag, list) else str(breath_tag)
                full_sentence = f"{tag} {full_sentence}"
            sentences_emitted.append(full_sentence)
            print(f"[STREAM][T={int((time.time()-t0)*1000):>5}ms] ✂ final sentence: {full_sentence[:60]!r} → fire TTS")
            # 推 streaming update（一次性推完整文本给前端）
            await websocket_send({
                "type": "ai_streaming_update",
                "id": msg_id,
                "content": full_sentence,
                "timestamp": time.time(),
            })
            tts_tasks.append(asyncio.create_task(
                sentence_to_audio(full_sentence, minimax, emotion, voice_modify)
            ))
        else:
            print(f"[STREAM][T={int((time.time()-t0)*1000):>5}ms] final sentence empty or reasoning-dump, skip")
        # 关键：让 monitor 自己跑完所有 TTS 后再退出，main 等待 monitor 完成
        # 而不是 cancel monitor —— 否则 monitor 还在 await send_binary 时被中断
        # 导致 audio chunk 丢失。
        if tts_tasks:
            print(f"[STREAM][T={int((time.time()-t0)*1000):>5}ms] waiting for {len(tts_tasks)} TTS tasks to finish")
            await asyncio.gather(*tts_tasks, return_exceptions=True)
            print(f"[STREAM][T={int((time.time()-t0)*1000):>5}ms] all TTS task objects done")
        # 通知 monitor 退出（不 cancel），等它自己跑完
        stop_event.set()
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
