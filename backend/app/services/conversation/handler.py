"""
对话处理器 - 集成知识服务的Agentic RAG对话处理
"""
import json
import re
import random
from typing import Optional, List, Dict, Any
from app.services.llm.minimax import get_minimax_service
from app.services.knowledge.service import get_knowledge_service
from app.services.knowledge.tools import CUSTOMER_PROFILES
from app.websocket.manager import session_manager


# 情感定义 - 对应MiniMax TTS的emotion参数
EMOTIONS = ["neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"]

# 情感触发关键词
EMOTION_TRIGGERS = {
    "happy": [
        "太好了", "很棒", "不错", "挺好的", "满意", "谢谢", "好的", "行", "没问题",
        "有意思", "有趣", "惊讶", "真的吗", "厉害", "佩服", "点赞"
    ],
    "sad": [
        "可惜", "遗憾", "无奈", "难过", "失望", "沮丧", "郁闷", "烦恼", "忧愁"
    ],
    "angry": [
        "太贵", "不合理", "骗子", "垃圾", "很差", "不满", "投诉", "怎么这样",
        "不负责任", "敷衍", "失望透顶", "气愤", "愤怒"
    ],
    "fearful": [
        "担心", "害怕", "顾虑", "忧虑", "不安", "风险", "危险", "怕出问题", "万一"
    ],
    "disgusted": [
        "恶心", "讨厌", "反感", "厌恶", "鄙视", "不屑", "看不上", "low", "差劲"
    ],
    "surprised": [
        "没想到", "居然", "竟然", "惊讶", "吃惊", "震惊", "什么", "怎么", "为什么",
        "这也太", "不会吧", "真的假的", "简直"
    ]
}

# 语气词标签（MiniMax TTS speech-2.8-hd / turbo 支持 19 种）
# 现在交给 LLM 自主决定是否插入、插哪里；这里只保留作为
# 兜底（长回复 0 标签时插 1 个）和校验（剥离非法字符）
BREATH_TAGS = {
    "neutral":   ["(breath)",  "(exhale)",  "(clear-throat)"],
    "happy":     ["(laughs)",  "(chuckle)", "(humming)"],
    "sad":       ["(sighs)",   "(sniffs)",  "(breath)"],
    "angry":     ["(groans)",  "(snorts)",  "(hissing)"],
    "fearful":   ["(inhale)",  "(gasps)",   "(pant)"],
    "disgusted": ["(snorts)",  "(lip-smacking)", "(hissing)"],
    "surprised": ["(gasps)",   "(exhale)",  "(emm)"],
}

# 注入到 system prompt 的标签指南 — 让 LLM 自主决定调用哪个
TTS_TAGS_GUIDE = """
【TTS 语气词标签 — 重要】
你的回复会通过 MiniMax speech-2.8-hd 合成语音。这个模型支持以下 19 个英文语气词标签，
让你听起来更自然、更有情绪：

  呼吸类： (breath) (inhale) (exhale) (pant) (clear-throat)
  笑声类： (laughs) (chuckle) (humming)
  情绪类： (sighs) (sniffs) (groans) (snorts) (gasps) (hissing) (lip-smacking)
  拟声类： (coughs) (burps) (sneezes) (emm)

**你可以根据当下情绪和场景自主决定是否调用、调用哪个。**
- 短句（< 15 字）：可不加
- 平静陈述：可在句中加 1 个 (breath)
- 表达惊讶/恍然大悟：(gasps) (exhale) (emm)
- 苦笑/自嘲：(chuckle) (snorts)
- 真的被逗笑：(laughs) (humming)
- 失望/无奈：(sighs) (sniffs)
- 愤怒/不满：(groans) (snorts) (hissing)
- 接电话被吓到/突然想起什么：(inhale) (pant) (gasps)
- 喉咙不舒服/掩饰尴尬：(clear-throat) (coughs)
- 想说什么但犹豫：(emm) (lip-smacking)

**插入规则（必须遵守）**：
1. 标签格式必须严格用半角圆括号包裹，例如 `(laughs)`，不要用全角 `(laughs)`
2. **同一个标签在一条回复里最多出现 1 次**（避免机械重复）
3. **建议 1 条回复里用 0-2 个**，不要超过 3 个
4. 标签应放在**情绪变化最明显的那个词前面或自然换气处**
   - ✓ "(laughs) 真的？那挺有意思的。"
   - ✓ "行，(sighs) 回头再聊吧。"
   - ✗ "(breath) 嗯 (breath) 你好 (breath)" — 太多
5. **不要插在数字、电话、邮箱、产品名等专有名词中间**

调用示例（合理）：
- "(laughs) 行，那就这么定。"
- "(sighs) 算了吧，我再考虑考虑。"
- "(gasps) 等等，你说什么？"
- "嗯，(clear-throat) 我先说三点。"
"""

# 同一族标签：插了一个就不用再插（避免重复）
# MiniMax TTS speech-2.8-hd / turbo 官方支持的 19 个语气词标签
BREATH_TAG_FAMILY = {
    # 呼吸类
    "breath":        "(breath)",
    "inhale":        "(inhale)",
    "exhale":        "(exhale)",
    "pant":          "(pant)",
    # 情绪类
    "laughs":        "(laughs)",
    "chuckle":       "(chuckle)",
    "sighs":         "(sighs)",
    "groans":        "(groans)",
    "gasps":         "(gasps)",
    "snorts":        "(snorts)",
    "sniffs":        "(sniffs)",
    "coughs":        "(coughs)",
    "clear-throat":  "(clear-throat)",   # 注意官方是连字符 (clear-throat)
    # 拟声/杂项
    "burps":         "(burps)",
    "lip-smacking":  "(lip-smacking)",
    "humming":       "(humming)",
    "hissing":       "(hissing)",
    "emm":           "(emm)",
    "sneezes":       "(sneezes)",
}

# 把 19 个标签打包成一个集合，方便跟文本对比（防重复插）
ALL_TTS_BREATH_TAGS = set(BREATH_TAG_FAMILY.values())

# 根据客户类型调整voice_modify
VOICE_MODIFY_MAP = {
    "assertive": {"pitch": 20, "intensity": 30, "timbre": 10},      # 主导型：偏冷、坚定
    "analytical": {"pitch": 0, "intensity": 0, "timbre": 0},     # 理性型：中性
    "amiable": {"pitch": -20, "intensity": -30, "timbre": 40},     # 友善型：温暖柔和
    "expressive": {"pitch": -30, "intensity": 40, "timbre": 30}, # 表达型：热情有感染力
    # 混合类型
    "assertive_analytical": {"pitch": 15, "intensity": 15, "timbre": 5},
    "assertive_expressive": {"pitch": -10, "intensity": 25, "timbre": 20},
    "amiable_expressive": {"pitch": -25, "intensity": -20, "timbre": 35},
    "analytical_amiable": {"pitch": -10, "intensity": -15, "timbre": 25},
}


# 4 种客户性格的具体说话风格 —— 注入到 system prompt 让 LLM 知道怎么"演"
SPEAKING_STYLE_BY_TYPE = {
    "assertive": """你是【果断型】客户：
- 说话非常直接，常用"行"、"那就"、"可以"、"别绕弯子"
- 拒绝时不会留情面（"算了"、"不行"、"我不要"）
- 不喜欢被推销员牵着走，会主动打断（"等下，你先说重点"）
- 决策快，常用反问逼对方亮底牌（"多少钱？""具体效果？""多久见效？"）
- 容易不耐烦（"你说快点，我还有会"）""",
    "analytical": """你是【理性型】客户：
- 注重数据、证据、案例——会问"有数据吗？""怎么证明？""客户案例？"
- 说话有逻辑，常用"因为...所以..."、"第一...第二..."
- 决策慢，会反复比较，但不会直说
- 不喜欢情绪化表达，但你给他数字他反而会放松
- 经常反问要求对方自证（"你这么说有什么依据？"）""",
    "amiable": """你是【犹豫型 / 友善型】客户：
- 说话柔和、配合度高，常用"嗯嗯"、"好的"、"那行吧"
- 经常表达顾虑但不会直接拒绝（"我再考虑考虑"、"跟领导说说"）
- 容易被销售员的热情打动，但也最容易被拖死
- 常用拖延词（"这个...那个..."、"回头再说"）
- 真的拒绝时反而很委婉（"我最近确实没空"而不是"不行"）""",
    "expressive": """你是【感性型 / 表达型】客户：
- 说话热情、有感染力，常用感叹号情绪（"真的？""那太棒了！""哎呀"）
- 喜欢讲自己的故事（"我之前..."、"我们公司..."）
- 容易被产品愿景打动，不那么在意细节数据
- 决策看心情，看销售员顺不顺眼
- 经常接话（"对对对"、"可不是嘛"、"说到这个我也..."）""",
}


def get_speaking_style(customer_type: str) -> str:
    """从 customer_type 查表得到具体说话风格 prompt 片段"""
    if not customer_type:
        return ""
    return SPEAKING_STYLE_BY_TYPE.get(
        customer_type.lower(),
        SPEAKING_STYLE_BY_TYPE["assertive"]
    )


def detect_emotion(user_message: str, customer_type: str = "assertive", conversation_context: list = None) -> Dict[str, Any]:
    """
    根据用户消息内容和客户类型检测AI客户应有的情感和voice_modify

    Args:
        user_message: 用户（销售）的最新消息
        customer_type: 客户画像类型
        conversation_context: 对话历史上下文（用于检测语气变化）

    Returns:
        Dict with emotion, voice_modify, and breath_tag
    """
    if not user_message:
        return {"emotion": "neutral", "voice_modify": {}, "breath_tag": "(breath)"}

    msg_lower = user_message.lower()

    # 统计各情感关键词匹配数量
    emotion_scores = {e: 0 for e in EMOTIONS if e != "neutral"}

    for emotion, keywords in EMOTION_TRIGGERS.items():
        for keyword in keywords:
            if keyword in msg_lower:
                emotion_scores[emotion] += 1

    # 客户类型影响基础情感倾向
    type_bonus = {
        "assertive": {"angry": 1, "surprised": 1},
        "analytical": {"neutral": 1},
        "amiable": {"happy": 1, "sad": 1},
        "expressive": {"surprised": 2, "happy": 1},
    }

    for t, bonuses in type_bonus.items():
        if t in customer_type.lower():
            for e, bonus in bonuses.items():
                if e in emotion_scores:
                    emotion_scores[e] += bonus

    # 如果有对话历史，检测语气变化趋势
    if conversation_context and len(conversation_context) >= 3:
        # 检测用户语气是否越来越不耐烦
        recent_messages = conversation_context[-3:]
        short_count = sum(1 for m in recent_messages if len(m.get("content", "")) < 20)
        if short_count >= 2:
            emotion_scores["angry"] += 1

    # 找出得分最高的情感
    max_score = max(emotion_scores.values())
    if max_score == 0:
        emotion = "neutral"
    else:
        for e, score in emotion_scores.items():
            if score == max_score:
                emotion = e
                break

    # 获取voice_modify
    base_type = customer_type.split("_")[0]  # 取第一部分作为基础类型
    voice_modify = VOICE_MODIFY_MAP.get(base_type, VOICE_MODIFY_MAP.get("analytical", {}))

    # 根据emotion微调voice_modify
    if emotion == "angry":
        voice_modify["pitch"] = min(voice_modify.get("pitch", 0) + 10, 100)
        voice_modify["intensity"] = min(voice_modify.get("intensity", 0) + 20, 100)
    elif emotion == "sad":
        voice_modify["pitch"] = max(voice_modify.get("pitch", 0) - 15, -100)
        voice_modify["intensity"] = max(voice_modify.get("intensity", 0) - 20, -100)
    elif emotion == "happy":
        voice_modify["pitch"] = max(voice_modify.get("pitch", 0) - 10, -100)

    # 获取语气词标签
    breath_tag = BREATH_TAGS.get(emotion, "(breath)")

    return {
        "emotion": emotion,
        "voice_modify": voice_modify,
        "breath_tag": breath_tag
    }


def add_breath_tags_to_response(response: str, emotion: str) -> str:
    """
    校验 + 兜底：让 LLM 自主决定标签，本函数只做
    1) 剥离不在白名单的"假"标签
    2) 长回复 LLM 一无所插时，兜底插 1 个 (breath)

    不再做随机机械插入 —— 标签位置和种类由 LLM 决定。
    """
    if not response:
        return response

    # 1) 校验：剥离不在白名单的标签，避免 LLM 幻觉出无效标签污染 TTS
    response = _sanitize_breath_tags(response)

    # 2) 兜底：长回复（>= 30 字）如果 LLM 一次都没插任何标签，
    #    在句尾插 1 个 emotion 对应的标签，避免整段干读
    if len(response) >= 30 and not _existing_tag_kind(response):
        tag = random.choice(BREATH_TAGS.get(emotion, BREATH_TAGS["neutral"]))
        response = _insert_tag_at_end(response, tag, emotion)

    return response


def _sanitize_breath_tags(text: str) -> str:
    """
    校验 LLM 输出中的 TTS 标签，只保留白名单里的 19 个。
    防止 LLM 编出 (smile) (angry-voice) 之类的假标签。
    """
    # 匹配 (word) 或 (word-with-dash) 模式
    pattern = re.compile(r"\(([a-zA-Z\-]+)\)")
    valid_set = ALL_TTS_BREATH_TAGS

    def _replace(m):
        tag = m.group(0)
        return tag if tag in valid_set else ""

    return pattern.sub(_replace, text)


def _existing_tag_kind(response: str) -> set:
    """扫描已有标签，按 'family' 收集（去重避免同族重复）"""
    found = set()
    for kind in BREATH_TAG_FAMILY:
        if BREATH_TAG_FAMILY[kind] in response:
            found.add(kind)
    return found


def _insert_tag_at_end(response: str, tag: str, emotion: str) -> str:
    """在最后一个句末标点前插入标签（同族已存在则跳过）"""
    existing = _existing_tag_kind(response)
    tag_kind = _tag_kind(tag)
    if tag_kind in existing:
        return response
    # 找最后一个句末标点
    last_punct = -1
    for i, ch in enumerate(response):
        if ch in "。？！\n":
            last_punct = i
    if last_punct <= 0:
        return response
    return response[:last_punct] + tag + response[last_punct:]


def _insert_tags_at_intervals(response: str, tag_candidates, interval: int, emotion: str) -> str:
    """按 interval 字数在中段停顿处插入多个标签，最多 3 个；不同位置用不同标签；同族去重"""
    if isinstance(tag_candidates, str):
        tag_candidates = [tag_candidates]
    existing = _existing_tag_kind(response)
    # 如果候选里的所有标签 family 都已存在，则不再插
    candidate_kinds = {_tag_kind(t) for t in tag_candidates}
    if candidate_kinds & existing:
        # 还有至少一个 family 没出现过，可以插
        candidate_kinds = candidate_kinds - existing
    if not candidate_kinds:
        return response

    # 找候选插入点：停顿标点 (， 。 ？ ！ \n) 且位置在 [interval-10, interval+10] 区间内
    candidates = []
    for i, ch in enumerate(response):
        if ch in "， 。？！\n":
            candidates.append(i)
    if not candidates:
        return response

    # 选最接近目标位置 interval, 2*interval, ... 的标点
    target_positions = [interval * k for k in range(1, 4)]  # 30, 60, 90 字
    insertions: List[tuple] = []  # (pos, tag_str)
    last_insert_pos = 0

    for target in target_positions:
        if target <= last_insert_pos:
            continue
        if target > len(response) - 3:
            target = len(response) - 1
        # 找 [target-15, target+15] 范围内最近且 > last_insert_pos 的标点
        best = None
        for pos in candidates:
            if pos <= last_insert_pos:
                continue
            if abs(pos - target) <= 15:
                if best is None or abs(pos - target) < abs(best - target):
                    best = pos
        if best is not None:
            # 每次随机抽一个候选 tag（不重复同族）
            available = [
                t for t in tag_candidates
                if _tag_kind(t) in candidate_kinds
            ]
            if not available:
                break
            chosen = random.choice(available)
            # 用完一种 kind 后从候选里移除，避免下一位置再抽到
            candidate_kinds.discard(_tag_kind(chosen))
            insertions.append((best, chosen))
            last_insert_pos = best + len(chosen) + 1

    if not insertions:
        return response

    # 从后往前插入以保索引有效
    result = response
    for pos, tag_str in reversed(insertions):
        result = result[:pos] + tag_str + result[pos:]

    return result


def _tag_kind(tag: str) -> str:
    """把 '(laughs)' 这种字符串归类到 family key"""
    for kind, t in BREATH_TAG_FAMILY.items():
        if t == tag:
            return kind
    return tag


class ConversationHandler:
    """
    处理对话的核心逻辑，集成知识检索和LLM调用

    对话流程：
    1. 用户消息进入
    2. 判断是否需要知识检索
    3. 如果需要，LLM先调用知识工具
    4. 收集工具执行结果
    5. LLM生成最终回复
    6. 返回给用户
    """

    def __init__(self):
        self.llm = get_minimax_service()
        self.knowledge = get_knowledge_service()

    def get_system_prompt(
        self,
        customer_type: str = "assertive",
        scenario: str = "general",
        customer_context: dict = None,
        investigation_result: dict = None,
        persona: dict = None,
        user_context: dict = None,
    ) -> str:
        """
        获取系统提示词，包含具体客户人物档案

        优先使用 persona（动态生成的具体人物），其次用 investigation_result，
        最后才用抽象的性格描述
        """
        # 1. 优先使用动态生成的具体人物档案
        if persona and persona.get("name"):
            return self._build_persona_prompt(
                persona, scenario,
                customer_type=customer_type,
                user_context=user_context,
            )

        # 2. 兼容旧的逻辑
        # 从知识库获取客户画像
        profile = CUSTOMER_PROFILES.get(customer_type, CUSTOMER_PROFILES["assertive"])
        characteristics = profile.get("characteristics", [])

        chars_text = "\n".join([f"- {c}" for c in characteristics[:5]])

        # 构建客户背景信息
        context_text = ""
        customer_name = ""
        customer_title = ""
        customer_company = ""

        if customer_context:
            industry = customer_context.get("industry", "")
            scale = customer_context.get("scale", "")
            pain_points = customer_context.get("pain_points", [])
            customer_name = customer_context.get("name", "")
            customer_title = customer_context.get("title", "")
            customer_company = customer_context.get("company", "")
            if industry:
                context_text += f"\n行业：{industry}"
            if scale:
                context_text += f"\n公司规模：{scale}"
            if pain_points:
                context_text += f"\n关注的痛点：{'；'.join(pain_points[:5])}"

        if investigation_result:
            name = investigation_result.get("name", "")
            title = investigation_result.get("title", "")
            company = investigation_result.get("company", "")
            background = investigation_result.get("background", "")
            recent_activities = investigation_result.get("recent_activities", [])
            potential_pains = investigation_result.get("potential_pains", [])

            customer_name = customer_name or name
            customer_title = customer_title or title
            customer_company = customer_company or company

            if name:
                context_text += f"\n姓名：{name}"
            if title or company:
                context_text += f"\n职位/公司：{title}@{company}" if title else f"\n公司：{company}"
            if background:
                context_text += f"\n背景：{background[:200]}..."
            if recent_activities:
                context_text += f"\n近期动态：{'；'.join(recent_activities[:3])}"
            if potential_pains:
                context_text += f"\n推测痛点：{'；'.join(potential_pains[:3])}"

        # 角色代入式提示词
        role_intro = f"你是{customer_name or '客户'}" if customer_name else "你是一个客户"
        if customer_title:
            role_intro += f"，{customer_title}"
        if customer_company:
            role_intro += f"，在{customer_company}工作"

        return f"""【角色代入】{role_intro}

【你的性格特点】
{chars_text}

【当前场景背景】
{context_text if context_text else '标准销售场景'}

【你现在接到了一个销售人员的电话】
- 你完全不知道对方要卖什么产品
- 你正在做自己的工作，可能在忙别的事情
- 对陌生推销电话你有戒备心
- 如果发现没用你会直接挂电话或说忙

【你的说话方式】
- 短句为主，像真正打电话那样简洁
- 可以用 TTS 语气词标签（如 `(laughs)` `(sighs)` `(breath)` `(chuckle)` 等）增加真实感
- 根据性格不同，语速和态度也不同：
  * 主导型：直接、不耐烦、决策快
  * 理性型：冷静、问数据、谨慎
  * 友善型：客气、有耐心、友好
  * 表达型：健谈、情绪化、爱发表意见

【绝对禁止】
- 不要主动介绍任何产品或服务
- 不要说"我们产品..."或"我们的优势..."
- 不要扮演销售角色
- 不要主动给销售人员建议或反馈
- 不要提及SPIN销售方法论
- 不要说"作为AI客户..."或"作为客户我认为..."

【回复格式要求】
你的回复会被转成语音，所以：
- 句子要短（每句不超过20字）
- 适当停顿（用逗号、句号、自然换行）
- **可以自主决定是否插入 TTS 语气词标签**（详见下方标签指南）

{TTS_TAGS_GUIDE}

保持自然，像真正在接电话一样！"""

    def _build_persona_prompt(
        self,
        persona: dict,
        scenario: str,
        customer_type: str = "",
        user_context: dict = None,
    ) -> str:
        """根据具体人物档案构建system prompt"""
        name = persona.get("name", "客户")
        gender = persona.get("gender", "")
        age_range = persona.get("age_range", "")
        title = persona.get("title", "")
        company = persona.get("company", "")
        industry = persona.get("industry", "")
        company_size = persona.get("company_size", "")
        background = persona.get("background", "")
        current_situation = persona.get("current_situation", "")
        pain_points = persona.get("pain_points", [])
        concerns = persona.get("concerns", [])
        personality_traits = persona.get("personality_traits", "")
        speaking_style = persona.get("speaking_style", "")
        scenario_context = persona.get("scenario_context", "")
        recent_activities = persona.get("recent_activities", "")

        pain_text = "\n".join([f"  - {p}" for p in pain_points]) if pain_points else "  - (无具体痛点)"
        concerns_text = "\n".join([f"  - {c}" for c in concerns]) if concerns else "  - (无具体顾虑)"

        # 从 customer_type 拿到具体说话风格 prompt 片段
        customer_type_speaking_style = get_speaking_style(customer_type)

        # 销售员档案（用户自填）— 让 AI 客户"心里知道"对方是谁
        user_context_str = ""
        if user_context:
            sales_name = user_context.get("sales_name") or "销售员"
            sales_level = {
                "junior": "初级销售",
                "mid": "中级销售",
                "senior": "高级销售",
                "manager": "销售经理",
            }.get(user_context.get("sales_level", ""), "销售员")
            years = user_context.get("years_experience", 0)
            goals = user_context.get("practice_goals") or []
            goal_labels = {
                "opening": "开场破冰", "discovery": "需求挖掘",
                "presentation": "产品呈现", "objection": "异议处理",
                "closing": "促成成交", "rapport": "关系建立",
            }
            goals_text = "、".join(goal_labels.get(g, g) for g in goals) or "未指定"
            difficulty_map = {
                "easy": "愿意配合，回答直接，不太刁难",
                "medium": "真实客户，会质疑，会提问题",
                "hard": "刁钻、追问、提不合理要求",
            }
            difficulty = difficulty_map.get(user_context.get("difficulty", "medium"), "真实客户")
            notes = user_context.get("notes") or ""

            user_context_str = f"""
【你"心里知道"的销售对手】
- 称呼: {sales_name}
- 职级: {sales_level}（{years} 年经验）
- 销售员声称的本次重点: {goals_text}
- 销售员要求你配合的难度: {difficulty}
"""
            if notes:
                user_context_str += f"- 销售员的特殊要求: {notes}\n"
            user_context_str += (
                "\n**注意：你知道这些，但不要在对话里主动复述它——"
                "让对话自然发生就好。如果销售员表现得像新手（思路混乱、没问到痛点就报方案），"
                "你可以稍稍温和一些、提示一下；表现得像老手（直奔主题、要数据），你也可以更直接、要求更严。**\n"
            )

        return f"""【你是谁】
你是【{name}】，{gender}，{age_range}岁
职位：{title}
公司：{company}（{industry}行业，{company_size}）

【你的经历】
{background}

【你最近在忙什么】
{current_situation}

【你最近的动态】
{recent_activities}

【你当前最关心的痛点】
{pain_text}

【你对供应商的顾虑】
{concerns_text}

【你的性格特点】
{personality_traits}

【你的说话风格（这一点极其重要）】
{speaking_style}

{user_context_str}
【当前接触场景】
{scenario_context}
（场景类型：{scenario}）

【行为准则】
1. **你就是这个具体的人**：你不是"AI客户"，不是"模拟客户"，你是【{name}】
2. **用你自己的话说话**：根据上面的"说话风格"特征来表达
3. **保持场景一致性**：{scenario_context}
4. **不要主动提供产品信息**：等销售来问你来答
5. **不要装销售**：你不帮销售总结，不给销售建议
6. **不提及任何销售方法论**（如SPIN、痛点挖掘、需求分析等）
7. **像真人一样有生活感**：提到你公司、你的同事、你最近遇到的具体事
8. **如果销售让你没兴趣**：礼貌但不热情地说忙或婉拒
9. **如果销售让你有兴趣**：会追问具体细节

【回复格式要求】
你的回复会被转成语音播给销售听，所以要**像真人接电话那样自然**：
- 短的时候 5-15 字（"嗯"、"行"、"什么？"、"你继续"）
- 被问实质问题时 30-80 字（透露背景、痛点、具体例子、真实数据）
- 偶尔 80+ 字也很正常——如果你正在详细解释自己的情况
- 不要写小作文（除非客户正在主动讲自己的事）
- 如果销售问得太泛（"你们能提供什么"），用反问让他具体（"你说的哪个方面？定价还是功能？"）
- **可以自主决定是否插入 TTS 语气词标签**（详见下方标签指南）
- 不要写 `<think>` 等思考过程
- 不要写 markdown、列表、代码
- **不要在回复里复述你的行业、公司全称等元数据**——你"心里知道"，但真人不会每次把公司全称说一遍

【按你性格的说话风格】
{customer_type_speaking_style}

{TTS_TAGS_GUIDE}

记住：你就是【{name}】，{title}@{company}。你正在做你的工作，对面是个陌生销售打来的电话。"""


    def _retrieve_knowledge_references(
        self,
        user_message: str,
        conversation_history: List[Dict],
        scenario: str = "general"
    ) -> List[Dict[str, Any]]:
        """Proactively retrieve knowledge references for the LLM and frontend.

        The goal is to (a) inject relevant sales methodology/scripts/objection
        handling into the LLM context, and (b) return structured references so
        the chat UI and the report page can show "AI 客户的话术依据".
        """
        from app.services.knowledge.tools import execute_search_knowledge

        # Normalize user_message in case it was passed as a list (multimodal)
        if not isinstance(user_message, str):
            user_message = str(user_message) if user_message else ""

        # Build a richer query: latest user message + tail of conversation
        history_tail = []
        for msg in (conversation_history or [])[-4:]:
            role = msg.get("role", "user")
            content = msg.get("content") or ""
            # `content` may be a string (most messages) or a list of
            # content-part dicts (multimodal messages with audio/image).
            if isinstance(content, list):
                # Concatenate any text parts and drop empty fragments.
                content = "".join(
                    p.get("text", "") if isinstance(p, dict) else str(p)
                    for p in content
                )
            if not isinstance(content, str):
                content = str(content)
            content = content.strip()
            if content:
                prefix = "客户" if role in ("user", "human") else "我"
                history_tail.append(f"{prefix}:{content[:80]}")
        convo_snippet = "; ".join(history_tail)
        query = f"{user_message} {(' 上下文: ' + convo_snippet) if convo_snippet else ''}".strip()

        # Choose category hint from scenario
        scenario_to_category = {
            "挖掘客户需求(SPIN)": "framework",
            "处理价格异议": "objection",
            "处理能力异议": "objection",
            "竞品对比应对": "objection",
            "促成成交技巧": "script",
            "首次拜访客户": "script",
            "电话销售跟进": "script",
            "产品方案呈现": "script",
            "客户拒绝挽回": "objection",
            "防御性销售(异议防范)": "framework",
            "再次拜访与跟进": "script",
            "大客户开发": "framework",
        }
        category = scenario_to_category.get(scenario, "all")

        try:
            raw = execute_search_knowledge(query, category=category, top_k=3)
            data = json.loads(raw)
        except Exception as e:
            print(f"[RAG] search failed: {e}")
            return []

        refs = []
        for item in data.get("results", []) or []:
            content_list = item.get("content") or []
            excerpt = (content_list[0] if content_list else "") or ""
            refs.append({
                "category": item.get("category", "general"),
                "source": item.get("source", "知识库"),
                "chapter": item.get("chapter", ""),
                "section": item.get("section", ""),
                "excerpt": excerpt[:300],
                "relevance": item.get("relevance", 0.5),
            })
        return refs

    def _format_refs_for_llm(self, refs: List[Dict[str, Any]]) -> str:
        """Format references into a compact block the LLM sees as background context."""
        if not refs:
            return ""
        lines = [
            "\n\n【销售知识库参考（请把下面的要点融进你的自然对话里，"
            "不要直接引用原句；表/人名附录这类噪声忽略）】"
        ]
        for i, r in enumerate(refs, 1):
            src = r.get("source", "")
            chapter = r.get("chapter", "")
            section = r.get("section", "")
            excerpt = (r.get("excerpt") or "").strip()
            category = r.get("category", "")
            header = f"[{i}] {src}"
            if chapter:
                header += f" / {chapter}"
            if section:
                header += f" / {section}"
            if category:
                header += f" ({category})"
            lines.append(header)
            # Heuristic: skip "appendix / names list" type content that is
            # obviously noise — it's a list of people, not actionable advice.
            noisy_chapter_markers = ("人名", "公司名", "目录", "index", "appendix")
            if any(m in (chapter + section).lower() for m in noisy_chapter_markers):
                lines.append("    (内容是人名/目录附录，非话术知识，跳过)")
                continue
            # Skip if excerpt is suspiciously long and looks like a list of
            # comma-separated names (typical appendix noise).
            if excerpt and (len(excerpt) > 200 and excerpt.count("·") >= 5):
                lines.append("    (内容是大量并列名词列表，疑似附录，跳过)")
                continue
            if excerpt:
                lines.append(f"    提示: {excerpt[:200]}")
        return "\n".join(lines)



    async def handle_message(
        self,
        user_message: str,
        conversation_history: List[Dict],
        customer_type: str = "assertive",
        scenario: str = "general",
        customer_context: dict = None,
        investigation_result: dict = None,
        persona: dict = None,
        user_context: dict = None,
    ) -> Dict[str, Any]:
        """
        处理用户消息，返回AI回复
        """
        # 1. 构建消息列表
        messages = self._build_messages(
            user_message, conversation_history, customer_type, scenario,
            customer_context, investigation_result, persona, user_context,
        )

        # 2. 检测用户情感和voice_modify（基于销售说的话和对话上下文）
        emotion_data = detect_emotion(user_message, customer_type, conversation_history)
        emotion = emotion_data["emotion"]
        voice_modify = emotion_data["voice_modify"]
        breath_tag = emotion_data["breath_tag"]

        # 2.5 主动知识库检索 (RAG)：把相关方法论/话术/异议处理注入 system prompt
        knowledge_refs = self._retrieve_knowledge_references(
            user_message=user_message,
            conversation_history=conversation_history,
            scenario=scenario,
        )
        if knowledge_refs:
            # 把参考材料追加到 system message
            if messages and messages[0].get("role") == "system":
                messages[0]["content"] += self._format_refs_for_llm(knowledge_refs)

        # 3. 获取工具定义
        tools = self.knowledge.get_tool_definitions()

        # 4. 调用LLM（包含工具）
        response_text = await self.llm.chat(
            messages=messages,
            tools=tools
        )
        # Strip <think>...</think> reasoning blocks (M2.7 model wraps output)
        if response_text:
            response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()

        # 5. 检查是否触发了function calling
        tool_calls_result = None
        knowledge_used = []

        try:
            response_data = json.loads(response_text)
            if response_data.get("type") == "function_call":
                tool_calls = response_data.get("tool_calls", [])

                # 6. 执行工具调用
                tool_results = self.knowledge.process_tool_calls(tool_calls)

                # 7. 收集知识使用情况
                for tr in tool_results:
                    if tr["success"]:
                        knowledge_used.append(tr["tool_name"])
                        # 将工具结果追加到对话历史
                        messages.append({
                            "role": "user",
                            "content": f"[TOOL RESULT: {tr['tool_name']}]\n{tr['formatted_result']}"
                        })

                # 8. 用工具结果再次调用LLM生成最终回复
                if tool_results:
                    final_response = await self.llm.chat(messages=messages, tools=tools)
                    # 9. 在回复中适当位置添加语气词标签
                    final_response = add_breath_tags_to_response(final_response, emotion)
                    return {
                        "response": final_response,
                        "tool_calls": tool_results,
                        "knowledge_used": knowledge_used,
                        "knowledge_refs": knowledge_refs,
                        "emotion": emotion,
                        "voice_modify": voice_modify,
                        "breath_tag": breath_tag
                    }

        except json.JSONDecodeError:
            # 普通回复，没有触发function calling
            pass

        # 10. 在回复中适当位置添加语气词标签
        response_text_with_tags = add_breath_tags_to_response(response_text, emotion)

        return {
            "response": response_text_with_tags,
            "tool_calls": tool_calls_result or [],
            "knowledge_used": knowledge_used,
            "knowledge_refs": knowledge_refs,
            "emotion": emotion,
            "voice_modify": voice_modify,
            "breath_tag": breath_tag
        }

    def _build_messages(
        self,
        user_message: str,
        conversation_history: List[Dict],
        customer_type: str,
        scenario: str,
        customer_context: dict = None,
        investigation_result: dict = None,
        persona: dict = None,
        user_context: dict = None,
    ) -> List[Dict]:
        """构建消息列表"""
        messages = []

        # 系统提示
        messages.append({
            "role": "system",
            "content": self.get_system_prompt(
                customer_type, scenario,
                customer_context, investigation_result,
                persona, user_context,
            )
        })

        # 对话历史
        for msg in conversation_history:
            role = msg.get("role", "user")
            # Map "ai" role to "assistant" for MiniMax API compatibility
            if role == "ai":
                role = "assistant"
            messages.append({
                "role": role,
                "content": msg.get("content", "")
            })

        # 用户最新消息
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    async def evaluate_conversation(
        self,
        conversation_history: List[Dict],
        customer_type: str = "assertive"
    ) -> str:
        """
        对话结束后，生成SPIN评价报告（FR-9: 引用知识库内容）

        Args:
            conversation_history: 完整对话历史
            customer_type: 客户类型

        Returns:
            评价报告JSON字符串（带知识引用）
        """
        # FR-9: 先检索相关知识作为评价依据
        from app.services.knowledge.tools import execute_search_knowledge, execute_get_spin_questions

        # 检索SPIN方法论
        spin_framework = execute_search_knowledge(
            query="SPIN方法论 Situation Problem Implication Need-payoff 销售",
            category="framework",
            top_k=3
        )

        # 检索SPIN各阶段问题示例
        spin_questions = execute_get_spin_questions(
            stage="all",
            customer_type=customer_type
        )

        # 提取对话文本
        conversation_text = self.knowledge.extract_conversation_text(conversation_history)

        # FR-9: 构建带知识的评价prompt
        # 注意：JSON 模板里的 { } 必须用 {{ }} 转义，否则 f-string 会把它们当 format spec
        evaluation_prompt = f"""你是销售对练系统的AI教练，负责对销售学员的对话进行SPIN标准评价。

【知识库 - SPIN方法论参考】
{spin_framework}

【知识库 - SPIN各阶段问题建议】
{spin_questions}

【待评价对话】
{conversation_text}

客户类型：{customer_type}

请**严格只输出一个 JSON 对象**（不要任何解释、不要 ```json ``` 包裹），格式：

{{
    "situation_score": 0-10 的整数,
    "situation_analysis": "分析为什么得这个分数（30-80 字）",
    "situation_quote": "引用的对话中原销售说的话",
    "situation_reference": "引用知识库的具体内容作为评分依据（10-40 字）",
    "situation_suggestion": "具体改进建议（10-40 字）",

    "problem_score": 0-10 的整数,
    "problem_analysis": "分析",
    "problem_quote": "引用的对话原文",
    "problem_reference": "引用知识库的具体内容",
    "problem_suggestion": "改进建议",

    "implication_score": 0-10 的整数,
    "implication_analysis": "分析",
    "implication_quote": "引用的对话原文",
    "implication_reference": "引用知识库的具体内容",
    "implication_suggestion": "改进建议",

    "need_payoff_score": 0-10 的整数,
    "need_payoff_analysis": "分析",
    "need_payoff_quote": "引用的对话原文",
    "need_payoff_reference": "引用知识库的具体内容",
    "need_payoff_suggestion": "改进建议",

    "overall_score": 0-40 的整数（situation+problem+implication+need_payoff 之和）,
    "key_strengths": ["优点1（10-30字）", "优点2（10-30字）"],
    "areas_for_improvement": ["改进点1（10-30字）", "改进点2（10-30字）"],
    "next_practice_focus": "下次练习重点建议（20-50字）"
}}

只输出这一个 JSON 对象，**不要任何其它文字**。"""

        # 构建消息
        messages = [
            {
                "role": "system",
                "content": "你是销售对练系统的AI教练，负责对销售学员的对话进行SPIN标准评价。"
                           "评价要具体引用知识库内容作为依据。输出必须是严格合法的 JSON 对象。"
            },
            {
                "role": "user",
                "content": evaluation_prompt
            }
        ]

        # 调用LLM生成评价
        response = await self.llm.chat(messages=messages)
        return response


# 单例
_conversation_handler: Optional[ConversationHandler] = None


def get_conversation_handler() -> ConversationHandler:
    """获取对话处理器单例"""
    global _conversation_handler
    if _conversation_handler is None:
        _conversation_handler = ConversationHandler()
    return _conversation_handler