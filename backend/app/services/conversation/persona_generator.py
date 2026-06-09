"""
客户画像生成器
为每个对练会话生成一个具体的、有血有肉的客户人物
"""
import json
import re
from typing import Dict, Any, Optional
from app.services.llm import get_minimax_service


# 12个内置场景对应的客户行业/场景模板
SCENARIO_TEMPLATES = {
    "挖掘客户需求(SPIN)": {
        "industry_pool": ["SaaS软件", "制造业", "教育培训", "医疗健康", "金融服务", "零售连锁", "物流运输", "建筑工程"],
        "company_types": ["中型企业", "成长型创业公司", "传统行业转型公司"],
        "scenes": [
            "销售登门拜访介绍产品",
            "客户被同事推荐接见",
            "客户在做项目选型",
            "客户在参加行业展会后被跟进"
        ]
    },
    "首次拜访客户": {
        "industry_pool": ["B2B服务", "工业设备", "企业管理软件", "咨询培训"],
        "company_types": ["上市公司", "国有企业", "外资企业"],
        "scenes": ["销售登门拜访", "电话陌生拜访", "客户引荐见面"]
    },
    "产品方案呈现": {
        "industry_pool": ["企业服务", "智能制造", "零售连锁", "餐饮品牌"],
        "company_types": ["500强企业", "上市公司", "行业龙头"],
        "scenes": ["客户邀请多家供应商比稿", "客户主动约见产品演示", "续约谈判"]
    },
    "客户拒绝挽回": {
        "industry_pool": ["传统制造", "中小企业服务", "本地生活"],
        "company_types": ["中小企业", "家族企业"],
        "scenes": ["客户已经使用竞品", "客户预算被砍", "客户上次合作不愉快"]
    },
    "处理价格异议": {
        "industry_pool": ["工业耗材", "企业软件", "设备采购", "建材"],
        "company_types": ["成本敏感型企业", "预算有限公司"],
        "scenes": ["客户认为报价过高", "客户在多家比价", "客户预算被砍需要折扣"]
    },
    "处理能力异议": {
        "industry_pool": ["高端制造", "金融科技", "医疗设备", "精密仪器"],
        "company_types": ["大客户", "上市公司"],
        "scenes": ["客户质疑公司规模", "客户担心实施能力", "客户对比竞品资质"]
    },
    "促成成交技巧": {
        "industry_pool": ["B2B软件", "咨询培训", "企业服务", "设备销售"],
        "company_types": ["成长型企业", "上市公司", "国企"],
        "scenes": ["客户已基本认可方案", "客户在走内部流程", "客户希望尽快落地"]
    },
    "大客户开发": {
        "industry_pool": ["金融", "能源", "通信运营商", "大型制造", "政府/事业单位"],
        "company_types": ["世界500强", "国企央企", "上市公司"],
        "scenes": ["跨部门决策链", "招投标项目", "总部-分公司多层关系"]
    },
    "竞品对比应对": {
        "industry_pool": ["企业服务", "工业品", "管理软件"],
        "company_types": ["中型企业"],
        "scenes": ["客户正在用竞争对手产品", "客户提出竞品优势", "客户让销售对比竞品"]
    },
    "防御性销售(异议防范)": {
        "industry_pool": ["企业服务", "B2B产品"],
        "company_types": ["成长型企业"],
        "scenes": ["客户需求尚未明确", "客户可能产生异议", "预防性开发需求"]
    },
    "再次拜访与跟进": {
        "industry_pool": ["B2B服务", "设备销售", "管理软件"],
        "company_types": ["中型企业"],
        "scenes": ["二次拜访深化关系", "处理上次遗留问题", "推进销售进展"]
    },
    "电话销售跟进": {
        "industry_pool": ["B2B服务", "保险金融", "教育培训", "企业SaaS"],
        "company_types": ["中小企业", "个人客户"],
        "scenes": ["陌生电话邀约", "老客户回访", "活动邀约跟进"]
    }
}


async def generate_persona(
    scenario_name: str,
    role_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    根据场景和角色配置，用LLM生成一个具体的客户人物

    Args:
        scenario_name: 场景名（如"挖掘客户需求(SPIN)"）
        role_config: 角色配置 {position_level, personality, decision_style}

    Returns:
        完整客户档案：
        {
            "name": "张志远",
            "title": "采购部经理",
            "company": "盛达电子科技有限公司",
            "industry": "电子制造",
            "company_size": "500人",
            "age": "35-40",
            "gender": "男",
            "background": "从业12年，从工程师做到采购经理...",
            "current_situation": "近期公司新项目选型...",
            "pain_points": ["...", "..."],
            "concerns": ["...", "..."],
            "personality_traits": "务实严谨，重视数据，说话直接...",
            "speaking_style": "常用专业术语，偶尔用'嗯''对'表示在听，不轻易表态...",
            "recent_activities": "上周参加行业展会...",
            "scenario_context": "销售主动登门拜访..."
        }
    """
    template = SCENARIO_TEMPLATES.get(scenario_name, SCENARIO_TEMPLATES.get("挖掘客户需求(SPIN)", {}))

    position = role_config.get("position_level", "middle")
    personality = role_config.get("personality", "rational")
    decision_style = role_config.get("decision_style", "value_oriented")

    position_desc = {
        "junior": "初级客户经理/专员（1-2年经验，预算有限）",
        "middle": "中级采购经理/部门主管（5-10年经验，有一定决策权）",
        "senior": "高级总监/VP（15年+经验，预算充足但决策谨慎）"
    }.get(position, "中级采购经理")

    personality_desc = {
        "rational": "理性分析型：冷静、问数据、不轻易被打动",
        "emotional": "感性沟通型：重视感觉和关系、容易被情绪打动",
        "hesitant": "犹豫不决型：反复比较、迟迟不决定、容易反悔",
        "decisive": "果断决策型：快速决断、但可能冲动"
    }.get(personality, "理性分析型")

    style_desc = {
        "price_oriented": "价格导向：最关心价格，追求性价比，砍价是本能",
        "value_oriented": "价值导向：关注长期价值、ROI、整体方案",
        "relationship_oriented": "关系导向：重视信任、长期合作、口碑",
        "risk_averse": "风险规避：关注潜在风险、决策保守、不愿做第一个"
    }.get(decision_style, "价值导向")

    industry_pool = template.get("industry_pool", ["通用行业"])
    company_types = template.get("company_types", ["一般企业"])
    scenes = template.get("scenes", ["标准销售场景"])

    system_prompt = f"""你是【客户画像设计师】，要为销售对练系统设计一个**真实、立体的客户人物**。

# 场景
{scenario_name}

# 客户基础属性
- 岗位级别：{position_desc}
- 性格类型：{personality_desc}
- 决策风格：{style_desc}

# 行业范围（请从中选1-2个最合适的）
{', '.join(industry_pool)}

# 公司类型范围
{', '.join(company_types)}

# 接触场景（请选1个）
{', '.join(scenes)}

# 设计要求
1. **必须非常具体**：不能是"张总，某科技公司"，要"张志远，盛达电子科技采购部经理"
2. **必须真实可信**：背景、年龄、经历要符合常理
3. **必须当下有具体痛点**：客户最近在忙什么项目？面临什么问题？
4. **必须有个性化语言风格**：他怎么说话？常用什么词？口头禅？专业术语？
5. **必须符合性格特征**：理性的人问数据、果断的人说话短、犹豫的人爱说"我再想想"
6. **绝对不能像机器人**：不要"我作为客户认为..."或"让我考虑一下"这种空话

# 输出格式（严格JSON，不要任何其他内容）
{{
  "name": "中文姓名（2-3字）",
  "gender": "男/女",
  "age_range": "如30-35",
  "title": "职位",
  "company": "公司全称（要有真实感）",
  "industry": "行业",
  "company_size": "如200人/中型企业",
  "background": "从业经历，2-3句话",
  "current_situation": "他/她现在正在忙什么具体的事（1-2句话）",
  "pain_points": ["当前最关心的3个具体痛点"],
  "concerns": ["对供应商的3个具体顾虑"],
  "personality_traits": "性格特点详细描述（3-5句话）",
  "speaking_style": "语言风格详细描述：常用词、口头禅、句式特点、语气词（4-5句话）",
  "scenario_context": "这次销售接触的具体情境（1-2句话）",
  "recent_activities": "近期发生的相关事情（1-2句话）"
}}

只输出JSON，不要任何解释、markdown代码块标记或额外文字。"""

    try:
        svc = get_minimax_service()
        # chat() does not support 'system' kwarg, prepend as system message
        response = await svc.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请生成这个客户的具体人物档案。"}
            ],
            temperature=0.7,
            max_tokens=800
        )

        text = (response or "").strip()

        # Strip <think>...</think> reasoning blocks (M2.7 model wraps output in them)
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

        # Try to extract JSON from response
        # Remove markdown code blocks if any
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
        text = text.strip()

        # Try to find JSON object
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            text = json_match.group(0)

        try:
            persona = json.loads(text)
        except json.JSONDecodeError:
            # The LLM sometimes produces malformed JSON (unescaped quotes inside
            # string values, trailing commas, etc.). Try a tolerant fix:
            # 1) strip control chars; 2) remove trailing commas; 3) try again.
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
            cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
            try:
                persona = json.loads(cleaned)
            except json.JSONDecodeError:
                # Last resort: try to extract key/value pairs with a permissive
                # regex so we keep some useful fields even when JSON is busted.
                persona = _extract_persona_fallback(text, scenario_name, role_config)
                if not persona:
                    raise
        return persona

    except Exception as e:
        print(f"[PersonaGenerator] LLM generation failed: {e}, using fallback")
        # Fallback - build a reasonable persona
        return _fallback_persona(scenario_name, role_config)


def _extract_persona_fallback(text: str, scenario_name: str, role_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Best-effort field extraction when LLM output isn't valid JSON.

    Looks for known persona fields and captures their string values even
    when the surrounding JSON is malformed (unterminated string, etc.).
    Returns None if no recognizable fields were found.
    """
    fields = [
        "name", "gender", "age_range", "title", "company", "industry",
        "company_size", "background", "current_situation", "personality_traits",
        "speaking_style", "scenario_context", "recent_activities",
    ]
    extracted: Dict[str, Any] = {}
    for field in fields:
        # Field is "key": "value" with the value possibly containing
        # unescaped quotes. Greedy match from "key": up to the next
        # unescaped quote followed by , or } or end-of-string.
        m = re.search(
            r'"' + re.escape(field) + r'"\s*:\s*"((?:[^"\\]|\\.)*)(?:"|(?=\s*[,}\n]|$))',
            text,
            flags=re.DOTALL,
        )
        if m:
            extracted[field] = m.group(1).strip()

    # Lists: pain_points, concerns, recent_news (each item is a quoted string)
    for list_field in ("pain_points", "concerns", "recent_news"):
        items = re.findall(r'"([^"\\]{1,300})"', text[text.find(f'"{list_field}"'):] if f'"{list_field}"' in text else "")
        if items:
            extracted[list_field] = [it for it in items if it.strip()][:5]

    if not extracted:
        return None
    # Provide minimal defaults if critical fields missing
    extracted.setdefault("name", "客户")
    extracted.setdefault("title", "客户")
    extracted.setdefault("company", "")
    return extracted


def _fallback_persona(scenario_name: str, role_config: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback persona when LLM fails"""
    position = role_config.get("position_level", "middle")
    personality = role_config.get("personality", "rational")

    if position == "senior":
        return {
            "name": "王建国",
            "gender": "男",
            "age_range": "40-45",
            "title": "采购总监",
            "company": "华信实业集团",
            "industry": "制造业",
            "company_size": "2000人",
            "background": "在制造业采购领域有20年经验，对供应链管理非常熟悉。",
            "current_situation": "公司正在进行年度供应商评估，需要选择新的合作伙伴。",
            "pain_points": ["现有供应商交付不及时", "质量波动大", "成本压力大"],
            "concerns": ["新供应商是否可靠", "切换成本", "服务响应速度"],
            "personality_traits": "经验丰富，决策稳重，不轻易被说服，注重实际数据和案例。",
            "speaking_style": "说话直接简短，常用'嗯''行'回应，喜欢问'具体怎么做的？'。",
            "scenario_context": "销售主动登门拜访，希望介绍新产品。",
            "recent_activities": "上周刚结束一个供应商的审核。"
        }
    elif position == "junior":
        return {
            "name": "李婷",
            "gender": "女",
            "age_range": "25-28",
            "title": "采购专员",
            "company": "新锐科技",
            "industry": "互联网",
            "company_size": "100人",
            "background": "刚入职1年，负责部门日常采购事务。",
            "current_situation": "在整理本周的采购需求，需要采购一批新的办公设备。",
            "pain_points": ["预算有限", "缺乏经验需要学习", "上级审批严格"],
            "concerns": ["产品是否符合公司要求", "价格是否在预算内", "售后是否有保障"],
            "personality_traits": "年轻有活力，学习意愿强，但缺乏决策权，需要向上级汇报。",
            "speaking_style": "语气友好，常用'好的''明白了'，会问很多细节问题。",
            "scenario_context": "销售主动联系，介绍新产品。",
            "recent_activities": "正在准备下周的部门会议汇报。"
        }
    else:
        return {
            "name": "陈志明",
            "gender": "男",
            "age_range": "32-38",
            "title": "采购经理",
            "company": "鼎峰科技股份有限公司",
            "industry": "电子制造",
            "company_size": "800人",
            "background": "在电子制造行业有10年采购经验，从工程师转岗。",
            "current_situation": "新项目即将启动，正在评估几家供应商的方案。",
            "pain_points": ["交付周期紧张", "成本控制压力大", "需要稳定可靠的供应商"],
            "concerns": ["技术方案是否成熟", "价格竞争力", "长期合作可能性"],
            "personality_traits": "理性务实，做决定前会充分调研，喜欢用数据说话。",
            "speaking_style": "语气平稳有条理，常用'我的看法是''具体来说'。",
            "scenario_context": "销售主动登门拜访介绍产品。",
            "recent_activities": "近期参加了几场行业技术交流。"
        }
