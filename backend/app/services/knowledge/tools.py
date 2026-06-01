"""
知识库工具集 - Agentic RAG 工具定义
用于AI自主调用知识库进行销售对练

销售流程覆盖:
- 访前准备 (Pre-approach)
- 建立联系 (Initial Contact)
- 需求探查 (Needs Discovery) - SPIN
- 方案展示 (Solution Presentation)
- 异议处理 (Objection Handling)
- 缔结成交 (Closing)
- 跟进维护 (Follow-up)
- 客户管理 (Account Management)
"""
import json
import random
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# ============================================================
# 工具定义 (Function Calling Schema)
# ============================================================

KNOWLEDGE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_spin_questions",
            "description": "根据对话阶段和客户情况，获取SPIN四步提问问题。用于AI模拟客户时引导销售学员练习SPIN方法论。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stage": {
                        "type": "string",
                        "enum": ["opening", "situation", "problem", "implication", "need_payoff", "proposal", "closing"],
                        "description": "当前对话阶段"
                    },
                    "customer_type": {
                        "type": "string",
                        "enum": ["assertive", "analytical", "amiable", "expressive", "assertive_analytical", "assertive_expressive", "amiable_expressive", "analytical_amiable"],
                        "description": "客户类型：assertive(主导型-果断直接), analytical(理性型-喜欢数据), amiable(友善型-重视关系), expressive(表达型-热情健谈)，支持组合如assertive_analytical"
                    },
                    "context": {
                        "type": "string",
                        "description": "当前对话情境描述，帮助生成更精准的问题"
                    }
                },
                "required": ["stage", "customer_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_opening_script",
            "description": "获取开场白话术。根据客户类型和行业生成自然的开场对话，不是生硬的自我介绍。",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_type": {
                        "type": "string",
                        "enum": ["assertive", "analytical", "amiable", "expressive", "assertive_analytical", "assertive_expressive", "amiable_expressive", "analytical_amiable"],
                        "description": "客户类型：assertive(主导型-果断直接), analytical(理性型-喜欢数据), amiable(友善型-重视关系), expressive(表达型-热情健谈)，支持组合类型"
                    },
                    "industry": {
                        "type": "string",
                        "description": "客户行业，如：制造业、医疗、教育、零售等"
                    },
                    "situation": {
                        "type": "string",
                        "description": "当前情境描述"
                    }
                },
                "required": ["customer_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_objection",
            "description": "当AI客户提出异议时，获取应对方案和话术。从异议库检索处理方案，AI需要根据语境自然表达。",
            "parameters": {
                "type": "object",
                "properties": {
                    "objection_type": {
                        "type": "string",
                        "enum": ["price", "competitor", "budget", "timing", "authority", "need_more_info", "other"],
                        "description": "异议类型"
                    },
                    "objection_content": {
                        "type": "string",
                        "description": "客户表达的具体异议内容"
                    },
                    "customer_type": {
                        "type": "string",
                        "enum": ["assertive", "analytical", "amiable", "expressive", "assertive_analytical", "assertive_expressive", "amiable_expressive", "analytical_amiable"],
                        "description": "客户类型"
                    }
                },
                "required": ["objection_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_backchannel",
            "description": "获取对话中的回话(Backchannel)确认语，如'嗯'、'好的'、'然后呢'等，表示在倾听但不打断。",
            "parameters": {
                "type": "object",
                "properties": {
                    "backchannel_type": {
                        "type": "string",
                        "enum": ["acknowledgment", "continuation", "question", "emphasis", "transition"],
                        "description": "回话类型：acknowledgment(确认), continuation(继续), question(追问), emphasis(强调), transition(转换话题)"
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative", "impatient"],
                        "description": "客户情绪"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_closing_script",
            "description": "获取缔结话术。根据不同缔结场景（要求承诺、检查关键点、总结利益、提议下一步）生成话术。",
            "parameters": {
                "type": "object",
                "properties": {
                    "closing_type": {
                        "type": "string",
                        "enum": ["commitment", "key_points", "summarize_benefits", "propose_next"],
                        "description": "缔结类型"
                    },
                    "customer_type": {
                        "type": "string",
                        "enum": ["assertive", "analytical", "amiable", "expressive", "assertive_analytical", "assertive_expressive", "amiable_expressive", "analytical_amiable"],
                        "description": "客户类型"
                    },
                    "context": {
                        "type": "string",
                        "description": "对话情境描述"
                    }
                },
                "required": ["closing_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "搜索知识库获取相关知识。支持方法论、话术、案例、异议处理方案的检索。用于AI生成有依据的回答。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或问题"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["framework", "script", "case", "objection", "all"],
                        "description": "知识类别：framework(方法论), script(话术), case(案例), objection(异议处理), all(全部)"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回最相关的结果数量，默认3条",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_spin",
            "description": "对话结束后，基于SPIN方法论对销售学员的对话进行评分和反馈。返回各阶段分数、引用原文、改进建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "conversation_text": {
                        "type": "string",
                        "description": "完整对话记录文本"
                    },
                    "customer_type": {
                        "type": "string",
                        "description": "客户类型"
                    }
                },
                "required": ["conversation_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_proposal_script",
            "description": "获取方案展示话术。当进入方案展示阶段时，生成如何展示产品优势的话术。",
            "parameters": {
                "type": "object",
                "properties": {
                    "proposal_type": {
                        "type": "string",
                        "enum": ["feature", "advantage", "benefit"],
                        "description": "展示类型：feature(特征), advantage(优点), benefit(利益)"
                    },
                    "product_context": {
                        "type": "string",
                        "description": "产品相关上下文"
                    }
                },
                "required": ["proposal_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_profile",
            "description": "根据对话前期内容，识别并返回客户画像信息。包含行业、痛点、决策角色等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "conversation_text": {
                        "type": "string",
                        "description": "对话前期内容"
                    }
                },
                "required": ["conversation_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_discovery_questions",
            "description": "获取探需阶段的问题。根据客户类型和已探明的需求，生成探测更深层需求的问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_type": {
                        "type": "string",
                        "enum": ["assertive", "analytical", "amiable", "expressive", "assertive_analytical", "assertive_expressive", "amiable_expressive", "analytical_amiable"],
                        "description": "客户类型"
                    },
                    "known_issues": {
                        "type": "string",
                        "description": "已探明的客户问题"
                    },
                    "depth_level": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3,
                        "description": "探需深度：1(浅层-背景问题), 2(中层-难点问题), 3(深层-暗示问题)"
                    }
                },
                "required": ["customer_type"]
            }
        }
    },
    # -------- 新增工具：访前准备 --------
    {
        "type": "function",
        "function": {
            "name": "get_pre_approach_plan",
            "description": "获取访前准备计划。在正式拜访客户前，需要了解客户背景、决策链、竞对情况等，制定拜访策略。",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "客户名称/公司名"
                    },
                    "industry": {
                        "type": "string",
                        "description": "客户行业"
                    },
                    "previous_contact": {
                        "type": "string",
                        "description": "之前是否有过接触，接触内容是什么"
                    },
                    "opportunity_context": {
                        "type": "string",
                        "description": "机会背景：这次拜访想达成什么目标"
                    }
                },
                "required": ["customer_name", "industry"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_competition_analysis",
            "description": "获取竞品分析信息。在客户提到竞品或需要对比时，提供竞品优劣分析话术。",
            "parameters": {
                "type": "object",
                "properties": {
                    "competitor_name": {
                        "type": "string",
                        "description": "竞品名称"
                    },
                    "comparison_angle": {
                        "type": "string",
                        "enum": ["price", "feature", "service", "brand", "case"],
                        "description": "对比角度：价格、功能、服务、品牌、案例"
                    },
                    "customer_concern": {
                        "type": "string",
                        "description": "客户关心的具体问题"
                    }
                },
                "required": ["competitor_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_value_summary",
            "description": "生成价值总结/利益综述。当需要总结方案价值、给高层汇报或缔结前回顾时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "value_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "价值点列表（客户已认可的需求）"
                    },
                    "customer_type": {
                        "type": "string",
                        "enum": ["assertive", "analytical", "amiable", "expressive", "assertive_analytical", "assertive_expressive", "amiable_expressive", "analytical_amiable"],
                        "description": "客户类型"
                    },
                    "summary_style": {
                        "type": "string",
                        "enum": ["concise", "detailed", "executive", "emotional"],
                        "description": "总结风格：简洁、详细、高管汇报、情感共鸣"
                    }
                },
                "required": ["value_points"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_decision_maker_strategy",
            "description": "获取面向不同决策角色的沟通策略。分析决策链上不同角色的关注点和应对方法。",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "enum": ["economic_buyer", "technical_buyer", "user_buyer", "champion", "influencer", "blocker"],
                        "description": "决策角色：经济决策者、技术决策者、使用者、Champion、影响者、阻碍者"
                    },
                    "customer_type": {
                        "type": "string",
                        "enum": ["assertive", "analytical", "amiable", "expressive", "assertive_analytical", "assertive_expressive", "amiable_expressive", "analytical_amiable"],
                        "description": "该角色的客户类型"
                    },
                    "situation": {
                        "type": "string",
                        "description": "当前情境描述"
                    }
                },
                "required": ["role"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_social_proof",
            "description": "获取客户见证/成功案例。当客户质疑或有疑虑时，提供相似案例增强信心。",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "客户行业"
                    },
                    "company_size": {
                        "type": "string",
                        "description": "公司规模：中小企业、中大型企业、集团企业"
                    },
                    "pain_point": {
                        "type": "string",
                        "description": "客户的痛点/问题"
                    },
                    "case_type": {
                        "type": "string",
                        "enum": ["success", "transformational", "quick_win", "long_term"],
                        "description": "案例类型：成功案例、转型案例、快速见效、长期合作"
                    }
                },
                "required": ["industry"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_referral_questions",
            "description": "获取转介绍问题。当成功签单后或需要拓展新客户时，询问转介绍获取更多线索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "timing": {
                        "type": "string",
                        "enum": ["after_success", "during_objection", "regular_checkin"],
                        "description": "时机：成功签约后、异议处理中、定期回访时"
                    },
                    "customer_type": {
                        "type": "string",
                        "description": "客户类型"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_follow_up_script",
            "description": "获取跟进话术。在不同跟进场景（催款、维护关系、邀约再次拜访等）使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "follow_up_type": {
                        "type": "string",
                        "enum": ["thank_you", "check_in", "reminder", "reengagement", "upsell"],
                        "description": "跟进类型：感谢、回访检查、提醒、再激活、追加销售"
                    },
                    "days_since_last_contact": {
                        "type": "integer",
                        "description": "距上次联系天数"
                    },
                    "customer_type": {
                        "type": "string",
                        "description": "客户类型"
                    },
                    "context": {
                        "type": "string",
                        "description": "跟进背景"
                    }
                },
                "required": ["follow_up_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_negociation_tactics",
            "description": "获取谈判策略。当进入商务谈判阶段，涉及价格、合同条款等敏感话题时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "negociation_topic": {
                        "type": "string",
                        "enum": ["price", "payment", "timeline", "scope", "warranty", "exclusive"],
                        "description": "谈判话题：价格、付款方式、时间线、范围、保修、独占权"
                    },
                    "customer_leverage": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "客户议价能力：高、中、低"
                    },
                    "our_leverage": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "我方议价能力：高、中、低"
                    },
                    "customer_type": {
                        "type": "string",
                        "description": "客户类型"
                    }
                },
                "required": ["negociation_topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trust_building",
            "description": "获取建立信任的话术。在销售早期，客户还不信任时，需要建立亲和感和信任。",
            "parameters": {
                "type": "object",
                "properties": {
                    "trust_stage": {
                        "type": "string",
                        "enum": ["rapport", "credibility", "rapport_established"],
                        "description": "信任阶段：建立亲和感、建立可信度、亲和感已建立"
                    },
                    "customer_type": {
                        "type": "string",
                        "description": "客户类型"
                    },
                    "context": {
                        "type": "string",
                        "description": "当前情境"
                    }
                },
                "required": ["trust_stage"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_appointment_scheduling",
            "description": "获取预约拜访话术。在约访客户、确认时间、催促回复等场景使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_type": {
                        "type": "string",
                        "enum": ["first_meeting", "demo", "proposal", "negotiation", "follow_up"],
                        "description": "预约类型：首次见面、演示、方案汇报、谈判、跟进"
                    },
                    "proposed_date": {
                        "type": "string",
                        "description": "建议日期"
                    },
                    "meeting_duration": {
                        "type": "integer",
                        "description": "预计时长（分钟）"
                    },
                    "customer_type": {
                        "type": "string",
                        "description": "客户类型"
                    }
                },
                "required": ["appointment_type"]
            }
        }
    }
]


# ============================================================
# 知识库数据 (模拟数据，实际从知识库加载)
# ============================================================

@dataclass
class KnowledgeItem:
    id: str
    text: str
    category: str
    source: str
    tags: List[str] = None


# SPIN方法论数据
SPIN_KNOWLEDGE = {
    "situation": [
        "背景问题用于收集客户基本信息、行业现状。不要问得过多，会让客户不耐烦。",
        "好的背景问题示例：您目前使用的是什么设备？使用多长时间了？团队规模多大？",
        "背景问题的关键是快速建立信任，然后转入难点问题。"
    ],
    "problem": [
        "难点问题用于发现客户当前面临的问题、困难和不满。",
        "难点问题示例：您在使用过程中遇到过什么问题？有哪些让您不太满意的地方？",
        "发现隐含需求是SPIN的关键第一步。"
    ],
    "implication": [
        "暗示问题用于放大问题的后果和影响，让客户感受到问题的严重性。",
        "暗示问题示例：这会对您的生产效率造成什么影响？对客户满意度呢？",
        "暗示问题要让客户自己说出问题的严重性，而不是你直接告诉他。Quincy规则：暗示问题让人感觉悲伤，需求-效益问题让人感觉愉快。"
    ],
    "need_payoff": [
        "需求-效益问题引导客户自己说出解决方案的价值。",
        "需求-效益问题示例：解决这个问题对您有什么价值？如果能提高效率，您觉得会带来什么好处？",
        "最好的销售是让客户告诉你他需要什么，而不是你直接推销。"
    ]
}

# 客户类型画像 - 经典4种买家类型（可组合）
# 同一个客户可能同时具备两种类型特征
CUSTOMER_PROFILES = {
    # 主导型 - 果断、竞争、目标导向
    "assertive": {
        "description": "主导型客户",
        "characteristics": [
            "决策快速果断，不喜欢拖泥带水",
            "关注结果和价值，不关心过程",
            "喜欢直接被告知结论和方案",
            "经常说：'直接告诉我多少钱'、'能还是不能'",
            "有竞争意识，喜欢赢"
        ],
        "recommended_approach": "直接给出结论，准备好数据支持，简洁有力",
        "questions_style": "封闭式问题，给出选项让他选"
    },

    # 理性型 - 喜欢数据、谨慎、注重细节
    "analytical": {
        "description": "理性型客户",
        "characteristics": [
            "喜欢详细数据，需要证据支持",
            "决策谨慎，会反复验证",
            "注重细节和风险分析",
            "经常说：'数据呢'、'让我看看依据'、'有案例吗'",
            "不会轻易表态"
        ],
        "recommended_approach": "准备好完整的数据和案例，按逻辑陈述，不要催促",
        "questions_style": "开放式问题，给他足够信息来自己判断"
    },

    # 友善型 - 友好、热情、重视关系
    "amiable": {
        "description": "友善型客户",
        "characteristics": [
            "友好热情，重视人际关系的建立",
            "不喜欢冲突和压力",
            "需要被认可和鼓励",
            "经常说：'我觉得'、'我们慢慢聊'、'不着急'",
            "容易受情绪影响"
        ],
        "recommended_approach": "先建立关系和信任，给予充分尊重，避免施压",
        "questions_style": "温和的开放式问题，多认可少质疑"
    },

    # 表达型 - 热情、有创造力、重视认同
    "expressive": {
        "description": "表达型客户",
        "characteristics": [
            "热情健谈，喜欢分享想法",
            "有创造力，喜欢新事物",
            "需要被关注和认可",
            "经常说：'我觉得这个想法'、'太好了'、'你知道吗'",
            "容易被说服但也可能变卦"
        ],
        "recommended_approach": "给予充分关注和认可，赞扬他的想法，保持热情互动",
        "questions_style": "让他表达，多问'您觉得呢'，给予认同"
    },

    # 组合类型 - 常见的多重特征客户
    "assertive_analytical": {
        "description": "主导+理性组合（技术决策者）",
        "characteristics": [
            "既有决策权又注重数据",
            "需要完整信息但能快速拍板",
            "看重投资回报率和风险分析",
            "技术出身的领导者偏多"
        ],
        "recommended_approach": "数据+结论并重，给出明确建议和备选方案",
        "questions_style": "先给数据结论，再问他的看法"
    },

    "assertive_expressive": {
        "description": "主导+表达组合（强势说服型）",
        "characteristics": [
            "强势但容易被新颖想法打动",
            "有自己的想法但也愿意听建议",
            "喜欢成为意见领袖",
            "中层管理者偏多"
        ],
        "recommended_approach": "肯定他的想法，引入新视角，引导他自己得出结论",
        "questions_style": "先认同，再引导'如果我们换个角度'..."
    },

    "amiable_expressive": {
        "description": "友善+表达组合（热情支持型）",
        "characteristics": [
            "友好热情但决策依赖他人",
            "需要肯定和支持做决定",
            "重视他人感受和意见",
            "容易受周围人影响"
        ],
        "recommended_approach": "给予充分认可，说服时强调'大家都觉得好'",
        "questions_style": "温和引导，多用'您的团队会怎么想'..."
    },

    "analytical_amiable": {
        "description": "理性+友善组合（谨慎温和型）",
        "characteristics": [
            "需要数据但性格友好不强势",
            "决策时间长但不拒绝沟通",
            "重视风险也重视关系维护",
            "财务或行政背景偏多"
        ],
        "recommended_approach": "提供数据的同时建立信任，给足时间做决定",
        "questions_style": "耐心回答问题，不要逼太紧"
    }
}

# 快速匹配函数 - 根据对话内容推断客户类型
def infer_customer_types(conversation_text: str) -> List[str]:
    """
    根据对话内容推断客户可能具备的类型组合
    返回多个可能的类型，按匹配度排序
    """
    text_lower = conversation_text.lower()
    types_scores = []

    # 主导型特征
    assertive_keywords = ["能还是不能", "多少钱", "直接说", "快点决定", "我没时间", "结论是什么", "到底行不行"]
    assertive_score = sum(1 for k in assertive_keywords if k in text_lower)

    # 理性型特征
    analytical_keywords = ["数据", "依据", "案例", "分析", "风险", "细节", "让我看看", "有什么证据", "具体是多少", " ROI ", "投资回报"]
    analytical_score = sum(1 for k in analytical_keywords if k in text_lower)

    # 友善型特征
    amiable_keywords = ["慢慢聊", "不着急", "我觉得", "我们可以", "大家商量", "关系", "朋友", "信任"]
    amiable_score = sum(1 for k in amiable_keywords if k in text_lower)

    # 表达型特征
    expressive_keywords = ["我觉得", "太好了", "你知道吗", "有个想法", "有意思", "太棒了", "我们来讨论"]
    expressive_score = sum(1 for k in expressive_keywords if k in text_lower)

    # 组合判断
    results = []

    if assertive_score >= 2:
        results.append(("assertive", assertive_score))
    if analytical_score >= 2:
        results.append(("analytical", analytical_score))
    if amiable_score >= 2:
        results.append(("amiable", amiable_score))
    if expressive_score >= 2:
        results.append(("expressive", expressive_score))

    # 如果没有明显特征，返回默认组合
    if not results:
        return ["assertive_analytical"]  # 默认：技术决策者型

    # 按得分排序，返回top 2
    results.sort(key=lambda x: x[1], reverse=True)
    inferred = [t[0] for t in results[:2]]

    # 如果有多种类型，返回组合类型
    if len(inferred) == 2:
        combo = f"{inferred[0]}_{inferred[1]}"
        if combo in CUSTOMER_PROFILES:
            return [combo]
        # 如果没有精确组合，返回两个单独的
        return inferred

    return inferred

# 异议处理方案
OBJECTION_HANDLING = {
    "price": [
        {
            "template": "理解您对价格的关注。让我们一起看看这个投资能带来什么回报。您最关心的是初期投入还是长期成本？",
            "principle": "将价格问题转化为价值问题"
        },
        {
            "template": "很多客户一开始也觉得价格高，但他们算了算，发现一年就能收回成本。您有兴趣听听他们是怎么算的吗？",
            "principle": "用投资回报率说话"
        }
    ],
    "competitor": [
        {
            "template": "您提到XX确实不错。我们和他们的主要区别是...您最关心哪个方面？",
            "principle": "承认竞品但不贬低，差异化竞争"
        },
        {
            "template": "我们的客户中有不少之前用XX的，他们选择我们是因为...您觉得这个对您重要吗？",
            "principle": "用客户证言说话"
        }
    ],
    "budget": [
        {
            "template": "预算确实是需要考虑的因素。您能告诉我您的预算范围吗？我帮您看看怎么配置最合适。",
            "principle": "了解预算边界，提供合适方案"
        },
        {
            "template": "其实很多公司一开始也担心预算问题，后来发现我们的方案其实比他们想象的要省钱。您想听听他们是怎么省钱的吗？",
            "principle": "重新定义成本概念"
        }
    ],
    "timing": [
        {
            "template": "理解您想再等等。请问您是在等什么特定的时机吗？也许我可以帮您分析一下最佳时机。",
            "principle": "了解真正障碍"
        },
        {
            "template": "其实越早开始，越早受益。很多客户算了一下，早用一个月其实省了不少钱。您觉得呢？",
            "principle": "强调时间成本"
        }
    ],
    "authority": [
        {
            "template": "完全理解，这种决定需要多方同意。您觉得还缺谁的意见？我可以提供一些补充材料。",
            "principle": "支持决策过程"
        },
        {
            "template": "如果您需要和同事或上级讨论，我这边可以准备一份简明的对比报告，您看怎么样？",
            "principle": "提供决策支持材料"
        }
    ],
    "need_more_info": [
        {
            "template": "您说得对，做决定前需要充分了解。您最想了解哪方面？我给您详细说说。",
            "principle": "积极提供信息"
        },
        {
            "template": "我很乐意为您提供更多细节。您最关心的是功能、价格还是实施方面？",
            "principle": "聚焦客户关注点"
        }
    ]
}

# 回话(Backchannel)数据
BACKCHANNEL_RESPONSES = {
    "acknowledgment": {
        "positive": ["嗯，好的", "明白了", "有道理", "确实是这样"],
        "neutral": ["嗯", "哦", "这样啊", "我听到了"],
        "negative": ["但是...", "其实...", "也不完全是..."],
        "impatient": ["然后呢？", "继续说吧", "我听着"]
    },
    "continuation": {
        "positive": ["还有呢？", "然后呢？", "继续说", "我想听更多"],
        "neutral": ["哦，是吗", "这样啊", "后来呢", "嗯嗯"],
        "negative": ["但是...", "等等", "等一下"],
        "impatient": ["说重点", "然后？"]
    },
    "question": {
        "positive": ["您能举个例子吗？", "具体是什么情况？", "能详细说说吗？"],
        "neutral": ["怎么讲？", "您的意思是？", "能解释一下吗？"],
        "negative": ["等等，这个我不明白", "您的意思是..."],
        "impatient": ["能不能说具体点", "简单点说"]
    },
    "emphasis": {
        "positive": ["对！没错！", "就是这个意思！", "您说得太对了！"],
        "neutral": ["最重要的是...", "关键是这样...", "您说对不对？"],
        "negative": ["但问题是...", "不过有一点...", "然而..."],
        "impatient": ["说重点！", "所以到底怎么样？"]
    },
    "transition": {
        "positive": ["那我们来聊聊...", "说起来...", "对了，还有一个事...", "既然这样..."],
        "neutral": ["那我们换个话题...", "顺便说一下...", "对了..."],
        "negative": ["不过...", "但我们还是得...", "话说回来..."],
        "impatient": ["行了，说下一个", "换个话题吧"]
    }
}

# 缔结话术
CLOSING_SCRIPTS = {
    "commitment": [
        "那么，我们可以先从...开始，您看下周有时间吗？",
        "如果您觉得合适，我们可以先做一个试点，您觉得怎么样？",
        "您看我们是先签合同还是先做演示？"
    ],
    "key_points": [
        "在我们继续之前，我想确认一下还有什么问题需要我解释吗？",
        "关于刚才讨论的方案，您还有什么需要更清楚的吗？",
        "我想确认一下，我们已经涵盖了您关心的所有问题，您看对吗？"
    ],
    "summarize_benefits": [
        "总结一下，我们刚才讨论的方案可以帮您解决...，带来...的价值。",
        "您看这套方案的核心价值是...，这正是您最关心的，对吗？",
        "我们来回顾一下主要的好处：第一...第二...第三..."
    ],
    "propose_next": [
        "那么下一步，建议我们先做一个小范围试点，您觉得呢？",
        "接下来我可以安排我们的技术人员先给您做一个评估，您什么时候方便？",
        "如果您觉得方案合适，我们是不是可以先签一个意向书？"
    ]
}

# 开场白话术 - 按客户类型分组
OPENING_SCRIPTS = {
    # 主导型 - 直接简洁
    "assertive": [
        "您好，我是...，直接说重点：我们有个方案能帮您解决...问题，您有兴趣了解吗？",
        "您好，我这边有个能帮您提高效率的方案，现在方便听几分钟吗？",
        "您好，我是...的...，我们发现一个能帮您降低成本的方法。"
    ],
    # 理性型 - 数据导向
    "analytical": [
        "您好，我是...，想和您探讨一下...方面的话题，有数据表明...。",
        "您好，我这边有个方案想请您评估一下，包含详细的ROI分析。",
        "您好，我是...，做了一个关于...的分析，想和您讨论一下。"
    ],
    # 友善型 - 友好轻松
    "amiable": [
        "您好，请问您是...先生/女士吗？我这边有个事情想和您聊聊，不会耽误太久。",
        "您好，我是...，您现在方便说话吗？有个事情想和您请教一下。",
        "您好，打扰您几分钟，我这边有个方案觉得可能对您有用，想和您简单介绍一下。"
    ],
    # 表达型 - 热情有创意
    "expressive": [
        "您好！我是...，有个超棒的想法想和您分享！",
        "您好，我这边有个超有意思的方案，您一定会感兴趣！",
        "您好！不知道您有没有听说过...，我这边有个新思路..."
    ],
    # 组合类型 - 主导+理性（技术决策者）
    "assertive_analytical": [
        "您好，我是...，直接说：我们有个方案能帮您解决...问题，有数据支持。",
        "您好，我这边有个高效方案，附详细的ROI分析，您看方便了解吗？"
    ],
    # 组合类型 - 友善+表达（热情支持型）
    "amiable_expressive": [
        "您好！很高兴有机会和您聊聊！我这边有个很好的方案...",
        "您好！不知道您有没有五分钟？我这边有个超棒的想法想和您分享！"
    ],
    # 组合类型 - 理性+友善（谨慎温和型）
    "analytical_amiable": [
        "您好，我是...，想和您探讨一下...方面的话题，不着急，我们慢慢聊。",
        "您好，我这边有个方案想请您帮忙评估一下，您看什么时候方便？"
    ],
    # 组合类型 - 主导+表达（强势说服型）
    "assertive_expressive": [
        "您好！我是...，有个重要的事情想和您快速确认一下！",
        "您好，我这边有个想法保证您会感兴趣！让我简单说一下..."
    ]
}

# 方案展示话术
PROPOSAL_SCRIPTS = {
    "feature": [
        "这个系统有...功能，可以...。",
        "我们的产品特点是...，这意味着...。",
        "另一个功能是...，能够帮助您...。"
    ],
    "advantage": [
        "这个功能可以帮助您解决...问题，这就是我们的优势所在。",
        "和市场上其他产品相比，我们的优势是...，这意味着您可以...。",
        "我们之所以有这个优势，是因为...，这对于您意味着...。"
    ],
    "benefit": [
        "正是您刚才提到的...需求，我们正好可以帮您解决。",
        "根据您说的情况，我建议您选择...方案，因为它可以给您带来...的价值。",
        "如果您选择我们的方案，您将获得...，这对您的意义是...。"
    ]
}

# SPIN问题示例 - 按客户类型分组
SPIN_QUESTIONS = {
    "opening": [
        "您好，请问您是王总吗？我这边有个销售培训的事情想和您聊聊。",
        "王总您好，我是AI销售教练，这次想帮您练习一下和客户沟通的技巧，您看方便吗？"
    ],
    "situation": {
        # 主导型 - 直接快速
        "assertive": [
            "您的销售团队规模多大？",
            "目前主要的销售渠道是什么？",
            "销售周期大概多长？"
        ],
        # 理性型 - 数据导向
        "analytical": [
            "您能给我介绍一下目前的销售流程吗？有数据最好。",
            "您们用哪些指标来评估销售效果？",
            "您们目前的客户转化率是多少？"
        ],
        # 友善型 - 友好轻松
        "amiable": [
            "您现在团队有多少人？",
            "您公司做销售多久了？",
            "目前使用什么方式做销售？"
        ],
        # 表达型 - 热情分享
        "expressive": [
            "跟您分享一下，我们发现销售团队有个共性问题...您那边情况怎么样？",
            "我很好奇，您们团队现在是怎么运作的？",
            "能跟我说说您们目前的销售方式吗？"
        ],
        # 组合类型
        "assertive_analytical": [
            "直接说，我们想了解您的销售数据：转化率、周期、团队规模？",
            "您能给我一个销售漏斗的概况吗？"
        ],
        "amiable_expressive": [
            "跟您聊聊天，您现在团队情况怎么样？",
            "我很好奇您们是怎么做销售的，能分享下吗？"
        ],
        "analytical_amiable": [
            "不着急，慢慢说，您能先介绍一下目前的销售情况吗？",
            "您们有用什么系统跟踪销售数据吗？"
        ],
        "assertive_expressive": [
            "快速确认一下，您们现在的销售模式是怎样的？",
            "有个问题想直接问您，您们现在的销售效率怎么样？"
        ]
    },
    "problem": {
        # 主导型 - 关注结果
        "assertive": [
            "您最希望解决哪个销售问题？",
            "现在最大的痛点是什么？",
            "目前销售转化率大概是多少？"
        ],
        # 理性型 - 深入分析
        "analytical": [
            "您觉得问题出在哪个环节？有没有数据支撑？",
            "您分析过客户流失的原因吗？",
            "您觉得现有流程中最大的瓶颈在哪里？"
        ],
        # 友善型 - 温和探索
        "amiable": [
            "在销售过程中，遇到比较多的问题是什么？",
            "有没有感觉有时候不知道该怎么和客户开口？",
            "哪些环节觉得比较吃力？"
        ],
        # 表达型 - 启发式
        "expressive": [
            "我跟您说个有意思的现象，很多销售都会遇到...您有这种感觉吗？",
            "不知道您有没有发现，有时候事情不像预期那样顺利？",
            "我跟您请教一下，您觉得销售中最难的部分是什么？"
        ],
        # 组合类型
        "assertive_analytical": [
            "我想直接问您，最影响业绩的是哪个问题？有数据吗？",
            "您觉得要用数据说话的话，问题出在哪？"
        ],
        "amiable_expressive": [
            "我跟您聊聊，您觉得在销售中最大的挑战是什么？",
            "不知道您有没有这种感觉，销售中有时候会卡在某个地方？"
        ],
        "analytical_amiable": [
            "您能不能说说，最近在销售中让您头疼的事情是什么？",
            "我很好奇您觉得最难搞定的是什么？"
        ],
        "assertive_expressive": [
            "有个问题想问您，您觉得销售中最头疼的是什么？",
            "我跟您快速确认下，您现在最大的销售难题是什么？"
        ]
    },
    "implication": {
        # 主导型 - 影响目标
        "assertive": [
            "这对您的业绩目标有什么影响？",
            "如果转化率提不上去，会怎样？",
            "这个问题不解决，年底能完成目标吗？"
        ],
        # 理性型 - 放大后果
        "analytical": [
            "您算过这个问题每年给您造成多少损失吗？",
            "如果继续这样下去，对您的业务有什么具体影响？",
            "这个问题会传导到其他部门吗？"
        ],
        # 友善型 - 温和引导
        "amiable": [
            "如果这个问题不解决，会影响什么？",
            "这种情况持续下去会怎样？",
            "您有没有算过这给您带来的损失有多大？"
        ],
        # 表达型 - 戏剧化
        "expressive": [
            "我跟您说个有意思的现象，这个问题不解决会像滚雪球一样越来越大...",
            "您有没有想过，如果这个问题持续下去，会发生什么？",
            "我跟您分析一下，如果这个问题不解决，后果可能会很严重..."
        ],
        # 组合类型
        "assertive_analytical": [
            "我们来算笔账，这个问题不解决会损失多少？",
            "您觉得从数据来看，这个问题的影响有多大？"
        ],
        "amiable_expressive": [
            "我跟您举个例子，这种问题如果不解决会越来越严重...",
            "您有没有发现，这个问题其实在慢慢变大？"
        ],
        "analytical_amiable": [
            "我想帮您分析一下，如果这个问题不解决会带来什么影响？",
            "您觉得长远来看，这个问题会造成什么后果？"
        ],
        "assertive_expressive": [
            "我跟您直说，这个问题不解决会影响您的竞争力...",
            "您想想，这个问题如果不解决会不会很危险？"
        ]
    },
    "need_payoff": {
        # 主导型 - 关注价值
        "assertive": [
            "您希望达到什么样的效果？",
            "如果转化率能提高50%，您觉得怎么样？",
            "对您来说，最理想的解决方案是什么样的？"
        ],
        # 理性型 - ROI导向
        "analytical": [
            "如果有个方案能帮您提高30%的效率，您觉得值得投资吗？",
            "您觉得什么样的投资回报率才值得您做这个决定？",
            "如果帮您算了一下，半年就能回本，您考虑吗？"
        ],
        # 友善型 - 愿景式
        "amiable": [
            "如果有个方法能帮您提高销量，您觉得怎么样？",
            "您觉得如果能解决这个问题，对您有多大的帮助？",
            "有没有想过如果销售能力提升了，您会怎么安排？"
        ],
        # 表达型 - 启发愿景
        "expressive": [
            "我跟您分享个好消息，很多企业用了我们的方案后效果超棒...",
            "您想过没有，如果销售变得很轻松是什么感觉？",
            "如果我告诉您有个方案能让您的业绩翻倍，您有兴趣吗？"
        ],
        # 组合类型
        "assertive_analytical": [
            "直接说重点，这个方案能给您带来多大的投资回报？",
            "您最关心的ROI数字是多少？"
        ],
        "amiable_expressive": [
            "我跟您描绘一个美好愿景，如果这个方案成功的话...",
            "您想象一下，如果您的销售团队效率提高一倍会怎样？"
        ],
        "analytical_amiable": [
            "我跟您算算，如果用这个方案，一年后您会省下多少成本？",
            "您觉得什么样的结果才值得您投入？"
        ],
        "assertive_expressive": [
            "我跟您保证，用了这个方案您会满意的！",
            "您想想，用了我们的方案后，您的业绩肯定会大幅提升！"
        ]
    }
}


# ============================================================
# 工具执行函数
# ============================================================

def execute_get_spin_questions(stage: str, customer_type: str = "assertive", context: str = "") -> str:
    """执行SPIN问题获取"""
    if stage == "opening":
        questions = SPIN_QUESTIONS["opening"]
        return json.dumps({
            "stage": stage,
            "questions": questions,
            "tip": "开场阶段先用轻松的方式建立联系，不要直接进入SPIN提问"
        }, ensure_ascii=False)

    stage_key = stage.replace("-", "_")
    if stage_key in ["situation", "problem", "implication", "need_payoff"]:
        stage_questions = SPIN_QUESTIONS.get(stage_key, {})
        questions = stage_questions.get(customer_type, ["这个问题您能详细说说吗？"])
        spin_knowledge = SPIN_KNOWLEDGE.get(stage_key, [])

        return json.dumps({
            "stage": stage,
            "customer_type": customer_type,
            "questions": questions,
            "knowledge_reference": spin_knowledge,
            "tip": f"这是{stage_key}阶段的问题，注意SPIN的顺序是：背景→难点→暗示→需求-效益"
        }, ensure_ascii=False)

    return json.dumps({
        "stage": stage,
        "questions": ["我们聊聊其他方面吧？"],
        "tip": "未知阶段，使用通用过渡问题"
    }, ensure_ascii=False)


def execute_get_opening_script(customer_type: str, industry: str = "", situation: str = "") -> str:
    """执行开场白获取"""
    scripts = OPENING_SCRIPTS.get(customer_type, OPENING_SCRIPTS["assertive"])
    profile = CUSTOMER_PROFILES.get(customer_type, {})

    return json.dumps({
        "customer_type": customer_type,
        "scripts": scripts,
        "approach": profile.get("recommended_approach", ""),
        "industry": industry or "通用",
        "tip": "开场要自然，不要太生硬。先建立亲和感，再转入正题。"
    }, ensure_ascii=False)


def execute_handle_objection(objection_type: str, objection_content: str = "", customer_type: str = "assertive") -> str:
    """执行异议处理"""
    handling_options = OBJECTION_HANDLING.get(objection_type, [
        {
            "template": "理解您的顾虑。能详细说说您的担心吗？我想确保给您提供最合适的方案。",
            "principle": "倾听并理解，真诚回应"
        }
    ])

    return json.dumps({
        "objection_type": objection_type,
        "objection_content": objection_content,
        "customer_type": customer_type,
        "handling_options": handling_options,
        "tip": "处理异议的原则：先认同，再理解，最后提供解决方案。不要直接反驳客户。"
    }, ensure_ascii=False)


def execute_get_backchannel(backchannel_type: str = "acknowledgment", sentiment: str = "neutral") -> str:
    """执行回话获取"""
    responses = BACKCHANNEL_RESPONSES.get(backchannel_type, BACKCHANNEL_RESPONSES["acknowledgment"])
    options = responses.get(sentiment, responses["neutral"])

    return json.dumps({
        "backchannel_type": backchannel_type,
        "sentiment": sentiment,
        "options": options,
        "tip": "回话要自然，不要机械重复。根据语境选择合适的回话类型。"
    }, ensure_ascii=False)


def execute_get_closing_script(closing_type: str, customer_type: str = "assertive", context: str = "") -> str:
    """执行缔结话术获取"""
    scripts = CLOSING_SCRIPTS.get(closing_type, CLOSING_SCRIPTS["summarize_benefits"])
    profile = CUSTOMER_PROFILES.get(customer_type, {})

    return json.dumps({
        "closing_type": closing_type,
        "customer_type": customer_type,
        "scripts": scripts,
        "approach": profile.get("recommended_approach", ""),
        "context": context,
        "tip": "缔结阶段要注意：1)确认关键点都覆盖了 2)总结利益 3)提议下一步行动 4不要太强迫"
    }, ensure_ascii=False)


def execute_search_knowledge(query: str, category: str = "all", top_k: int = 3) -> str:
    """执行知识库检索 - 带5分钟缓存(FR-6)"""
    # FR-6: 先检查缓存
    from app.services.knowledge.cache import knowledge_cache
    cached = knowledge_cache.get(query, category, top_k)
    if cached:
        print(f"[CACHE] Knowledge hit for query: {query[:30]}...")
        return cached

    # 缓存未命中，执行检索
    result = _do_search_knowledge(query, category, top_k)

    # 存入缓存
    knowledge_cache.set(query, category, top_k, result)

    return result


def _do_search_knowledge(query: str, category: str, top_k: int) -> str:
    """实际执行知识库检索（原有逻辑）"""
    try:
        from app.services.knowledge.vector_store import get_vector_store
        from app.services.knowledge.knowledge_loader import KnowledgeLoader

        # 使用真实的向量知识库检索
        loader = KnowledgeLoader()
        chunks = loader.search_knowledge(query, category=category if category != "all" else None, top_k=top_k)

        results = []
        for chunk in chunks:
            results.append({
                "category": chunk.category,
                "source": chunk.source,
                "content": [chunk.text[:500]] if len(chunk.text) > 500 else [chunk.text],
                "chapter": chunk.chapter,
                "section": chunk.section,
                "relevance": 0.8  # 向量搜索返回的是相似度，这里简化处理
            })

        if results:
            return json.dumps({
                "query": query,
                "category": category,
                "results": results,
                "total": len(results),
                "tip": "检索到的知识应该作为LLM生成回复的参考，不要直接朗读，要自然融入对话。"
            }, ensure_ascii=False)

    except Exception as e:
        print(f"Vector search failed: {e}, using keyword fallback")

    # 回退到内置关键词搜索
    results = []

    if category in ["framework", "all"]:
        for stage, texts in SPIN_KNOWLEDGE.items():
            if query.lower() in " ".join(texts).lower() or stage in query.lower():
                results.append({
                    "category": "framework",
                    "source": "SPIN销售巨人",
                    "content": texts[:2],
                    "relevance": 0.9
                })

    if category in ["objection", "all"]:
        for obj_type, handlers in OBJECTION_HANDLING.items():
            if obj_type in query.lower():
                results.append({
                    "category": "objection",
                    "source": "异议处理库",
                    "content": [h["template"] for h in handlers],
                    "relevance": 0.9
                })

    if category in ["script", "all"]:
        if "开场" in query or "opening" in query.lower():
            results.append({
                "category": "script",
                "source": "话术库",
                "content": OPENING_SCRIPTS,
                "relevance": 0.8
            })
        if "缔结" in query or "closing" in query.lower():
            results.append({
                "category": "script",
                "source": "话术库",
                "content": CLOSING_SCRIPTS,
                "relevance": 0.8
            })

    if not results:
        results.append({
            "category": "general",
            "source": "知识库",
            "content": ["当前知识库中没有找到精确匹配的内容，请尝试其他关键词。"],
            "relevance": 0.3
        })

    return json.dumps({
        "query": query,
        "category": category,
        "results": results[:top_k],
        "total": len(results),
        "tip": "检索到的知识应该作为LLM生成回复的参考，不要直接朗读，要自然融入对话。"
    }, ensure_ascii=False)


def execute_evaluate_spin(conversation_text: str, customer_type: str = "assertive") -> str:
    """执行SPIN评价"""
    # 简化的评价逻辑
    return json.dumps({
        "conversation": conversation_text[:500],
        "customer_type": customer_type,
        "evaluation": {
            "situation": {
                "score": 6,
                "max": 10,
                "quote": "您现在使用什么设备？",
                "issue": "背景问题过多，但没有快速转入难点问题",
                "suggestion": "减少背景问题，快速探查客户痛点"
            },
            "problem": {
                "score": 5,
                "max": 10,
                "quote": "有没有遇到过什么问题？",
                "issue": "难点问题不够深入，没有追问具体影响",
                "suggestion": "用暗示问题放大问题后果，如：这会怎么影响您的生意？"
            },
            "implication": {
                "score": 4,
                "max": 10,
                "quote": "问题确实存在",
                "issue": "几乎没有使用暗示问题，没有放大客户痛点",
                "suggestion": "追问问题不解决的后果，让客户自己感受到紧迫性"
            },
            "need_payoff": {
                "score": 5,
                "max": 10,
                "quote": "那您看怎么解决呢？",
                "issue": "直接给方案而不是引导客户自己说出价值",
                "suggestion": "问：如果能解决这个问题，对您有什么价值？引导客户自己说"
            }
        },
        "total_score": 20,
        "max_total": 40,
        "overall": {
            "strength": "态度亲切，有亲和力",
            "weakness": "SPIN顺序不完整，暗示问题缺失，需要加强探需深度",
            "improvement": [
                "练习在30秒内快速建立背景后转入难点问题",
                "多使用'这对您的...有什么影响'类问题",
                "让客户自己说出方案价值，而不是直接推销"
            ]
        },
        "tip": "评价要具体指出问题在哪句话，不是泛泛而谈"
    }, ensure_ascii=False)


def execute_get_proposal_script(proposal_type: str, product_context: str = "") -> str:
    """执行方案展示话术获取"""
    scripts = PROPOSAL_SCRIPTS.get(proposal_type, PROPOSAL_SCRIPTS["feature"])

    return json.dumps({
        "proposal_type": proposal_type,
        "scripts": scripts,
        "context": product_context,
        "tip": "方案展示原则：先建立需求，再展示解决方案。不要在客户还没表达需求时就介绍产品特征。"
    }, ensure_ascii=False)


def execute_get_customer_profile(conversation_text: str) -> str:
    """执行客户画像识别"""
    # 简化的画像识别逻辑
    profile = {
        "industry": "未知",
        "role": "未知",
        "pain_points": [],
        "customer_type_hint": "需要更多对话才能判断"
    }

    # 简单的关键词识别
    keywords = {
        "制造业": ["工厂", "设备", "生产线", "产能", "制造业"],
        "医疗": ["医院", "医生", "患者", "医疗", "药品"],
        "教育": ["学校", "学生", "老师", "教育", "培训"],
        "零售": ["门店", "客流", "销量", "零售", "客户"]
    }

    for industry, words in keywords.items():
        if any(w in conversation_text for w in words):
            profile["industry"] = industry
            break

    return json.dumps({
        "conversation": conversation_text[:300],
        "profile": profile,
        "tip": "客户画像从对话中实时识别，不需要预设场景"
    }, ensure_ascii=False)


def execute_get_discovery_questions(customer_type: str = "assertive", known_issues: str = "", depth_level: int = 2) -> str:
    """执行探需问题获取"""
    stage_map = {1: "situation", 2: "problem", 3: "implication"}
    stage = stage_map.get(depth_level, "problem")

    questions = SPIN_QUESTIONS.get(stage, {}).get(customer_type, ["您能详细说说吗？"])

    return json.dumps({
        "customer_type": customer_type,
        "stage": stage,
        "depth_level": depth_level,
        "known_issues": known_issues,
        "questions": questions,
        "tip": f"探需深度{depth_level}意味着{'浅层背景' if depth_level==1 else '中层难点' if depth_level==2 else '深层暗示'}问题"
    }, ensure_ascii=False)


# ============================================================
# 新增工具执行函数
# ============================================================

def execute_get_pre_approach_plan(customer_name: str, industry: str, previous_contact: str = "", opportunity_context: str = "") -> str:
    """执行访前准备计划获取"""
    plan = {
        "customer_name": customer_name,
        "industry": industry,
        "previous_contact": previous_contact,
        "opportunity_context": opportunity_context,
        "research_areas": [
            "客户公司背景和最新动态",
            "客户组织架构和决策链",
            "竞品使用情况和满意度",
            "行业趋势和痛点",
            "客户最近的新闻或事件"
        ],
        "questions_to_prepare": [
            f"您是如何了解我们公司的？",
            "您对目前供应商满意吗？哪里不满意？",
            "您这次采购的核心目标是什么？",
            "决策流程是怎样的？有哪些人参与？"
        ],
        "strategy_suggestions": [
            "开场不要直接谈产品，先了解客户现状",
            "注意识别决策链上的关键人物",
            "准备好竞品对比的证据和数据"
        ],
        "tip": "访前准备越充分，拜访成功率越高。建议至少提前30分钟准备。"
    }
    return json.dumps(plan, ensure_ascii=False)


def execute_get_competition_analysis(competitor_name: str, comparison_angle: str = "feature", customer_concern: str = "") -> str:
    """执行竞品分析获取"""
    competitor_data = {
        "huawei": {
            "strengths": ["品牌影响力大", "技术实力强", "本土化服务好"],
            "weaknesses": ["价格较高", "有些产品线较老", "服务响应慢"],
            "price_range": "中高价位",
            "typical_customer": "大型企业、政府客户"
        },
        "xingchen": {
            "strengths": ["价格有竞争力", "灵活定制", "本地化支持快"],
            "weaknesses": ["品牌知名度低", "研发投入有限", "国际案例少"],
            "price_range": "中低价位",
            "typical_customer": "中小企业"
        },
        "default": {
            "strengths": ["市场知名度高", "客户基础大"],
            "weaknesses": ["可能价格较高", "服务未必跟得上"],
            "price_range": "中等价位",
            "typical_customer": "各类型客户"
        }
    }

    data = competitor_data.get(competitor_name.lower(), competitor_data["default"])

    analysis_map = {
        "price": {
            "our_advantage": "我们提供更具竞争力的性价比，相同配置价格更优",
            "script": f"您说得对，{competitor_name}的价格确实有优势。不过您看的是入门配置，如果算上我们包含的高级功能，其实总体投入差不多，但价值完全不一样。您有兴趣详细对比一下吗？"
        },
        "feature": {
            "our_advantage": "我们在核心功能上有差异化优势",
            "script": f"{competitor_name}的产品我了解过，他们确实在某些功能上做得不错。不过我们更专注于解决您提到的{customer_concern or '核心痛点'}问题，这方面的深度和效果是完全不同的。"
        },
        "service": {
            "our_advantage": "我们提供7x24本地化服务响应",
            "script": "服务确实很重要。我们见过很多客户选择了大品牌，但出了问题找不到人支持，耽误了业务。我们这边服务响应速度在行业里是有口碑的。"
        }
    }

    result = analysis_map.get(comparison_angle, analysis_map["feature"])

    return json.dumps({
        "competitor": competitor_name,
        "comparison_angle": comparison_angle,
        "competitor_data": data,
        "our_advantage": result["our_advantage"],
        "recommended_script": result["script"],
        "tip": "谈论竞品时不要贬低，保持专业和客观。强调我们的差异化优势就好。"
    }, ensure_ascii=False)


def execute_get_value_summary(value_points: List[str], customer_type: str = "assertive", summary_style: str = "concise") -> str:
    """执行价值总结获取"""
    styles = {
        "concise": "简洁明了，重点突出",
        "detailed": "全面覆盖，数据支撑",
        "executive": "高管视角，ROI导向",
        "emotional": "情感共鸣，建立连接"
    }

    profile = CUSTOMER_PROFILES.get(customer_type, CUSTOMER_PROFILES["assertive"])
    approach = profile.get("recommended_approach", "")

    return json.dumps({
        "value_points": value_points,
        "customer_type": customer_type,
        "summary_style": styles.get(summary_style, "简洁明了"),
        "approach": approach,
        "script_templates": [
            "根据我们今天的讨论，这套方案能帮您解决三个核心问题：第一...第二...第三...",
            "简单总结一下，这套方案对您的核心价值是...，这正好是您最关心的，对吗？",
            "我想帮您梳理一下，今天我们讨论的方案能为您带来这些价值..."
        ],
        "tip": f"价值总结要根据客户类型调整风格：{approach}"
    }, ensure_ascii=False)


def execute_get_decision_maker_strategy(role: str, customer_type: str = "assertive", situation: str = "") -> str:
    """执行决策角色策略获取"""
    strategies = {
        "economic_buyer": {
            "concerns": ["投资回报率", "成本控制", "风险规避", "业务目标达成"],
            "approach": "直接给出数据化的价值证明，用ROI和成本节约说服",
            "questions": ["您今年的预算目标是什么？", "您更关注初期投入还是长期成本？", "您如何评估一个项目的成功？"],
            "script": "我直接和您汇报一下这个方案的投资回报率。根据我们的测算，第一年就能收回成本，之后每年能节省..."
        },
        "technical_buyer": {
            "concerns": ["技术可行性", "系统兼容性", "安全合规", "性能指标"],
            "approach": "提供详细的技术文档、白皮书、数据表，用技术深度建立信任",
            "questions": ["您对技术架构有什么要求？", "有哪些合规要求需要满足？", "现有系统的集成方案是什么？"],
            "script": "关于技术层面，我可以给您详细介绍一下我们的架构设计、兼容性和安全认证..."
        },
        "user_buyer": {
            "concerns": ["易用性", "学习成本", "工作效率提升", "日常工作影响"],
            "approach": "强调易用性和工作效率提升，提供试用让用户亲身感受",
            "questions": ["您每天在哪些场景下使用这个系统？", "现在用什么方式完成这些工作？", "有哪些具体的不方便？"],
            "script": "我理解您更关心实际使用体验。让我给您演示一下我们产品在实际工作中是怎么用的..."
        },
        "champion": {
            "concerns": ["如何说服其他决策者", "项目成功指标", "个人职业发展"],
            "approach": "提供内部推广的材料和支持，帮Champion在内部推进",
            "questions": ["您觉得其他决策者最关心什么？", "有什么担心或反对意见需要提前准备？", "项目的成功标准是什么？"],
            "script": "您是这个项目的推动者，我很愿意支持您。我可以给您准备一份内部汇报材料，帮您向其他决策者说明..."
        },
        "influencer": {
            "concerns": ["专业意见被采纳", "部门利益", "工作负荷影响"],
            "approach": "尊重其专业意见，提供有价值的信息，建立合作关系",
            "questions": ["您觉得这个方案在技术层面有什么需要改进的？", "实施过程中您最担心什么？", "对其他部门的协作有什么建议？"],
            "script": "您的意见很重要。我想听听您对这个方案的专业看法，特别是从实施角度..."
        },
        "blocker": {
            "concerns": ["风险规避", "责任归属", "预算消耗"],
            "approach": "理解其担忧，提供风险保障，用案例证明可行性",
            "questions": ["能了解一下您主要的顾虑是什么吗？", "之前有没有遇到过类似的问题？", "我们可以做什么来消除您的担忧？"],
            "script": "我理解您的顾虑。其实很多客户一开始也有同样的担心，后来我们通过这种方式解决了..."
        }
    }

    strategy = strategies.get(role, strategies["economic_buyer"])
    profile = CUSTOMER_PROFILES.get(customer_type, CUSTOMER_PROFILES["assertive"])

    return json.dumps({
        "role": role,
        "customer_type": customer_type,
        "situation": situation,
        "concerns": strategy["concerns"],
        "approach": strategy["approach"],
        "questions": strategy["questions"],
        "recommended_script": strategy["script"],
        "tip": f"针对{role}类型的客户，关键在于：{strategy['approach']}"
    }, ensure_ascii=False)


def execute_get_social_proof(industry: str, company_size: str = "中小企业", pain_point: str = "", case_type: str = "success") -> str:
    """执行客户见证获取"""
    # 模拟案例库
    cases = [
        {
            "industry": "制造业",
            "company_size": "中大型企业",
            "case": "某大型制造企业引入我们的方案后，年度节省成本200万，效率提升40%",
            "metrics": {"cost_saving": "200万", "efficiency_improvement": "40%", "timeline": "6个月"},
            "pain_point": "生产线效率低，成本居高不下",
            "type": "transformational"
        },
        {
            "industry": "医疗",
            "company_size": "中小企业",
            "case": "某医院使用我们的系统后，患者满意度从70%提升到92%",
            "metrics": {"satisfaction_improvement": "22%", "patient_processing_time": "减少30%"},
            "pain_point": "患者等待时间长，服务质量难提升",
            "type": "quick_win"
        },
        {
            "industry": "教育",
            "company_size": "集团企业",
            "case": "某教育集团通过我们的方案实现了业务在线化，年营收增长50%",
            "metrics": {"revenue_growth": "50%", "online_conversion": "80%"},
            "pain_point": "传统模式增长乏力，数字化转型需求迫切",
            "type": "long_term"
        }
    ]

    # 过滤相似案例
    relevant_cases = [c for c in cases if industry in c["industry"]]
    if not relevant_cases:
        relevant_cases = cases[:1]

    case = random.choice(relevant_cases) if relevant_cases else cases[0]

    return json.dumps({
        "industry": industry,
        "company_size": company_size,
        "pain_point": pain_point or case["pain_point"],
        "case_type": case_type,
        "case": {
            "story": case["case"],
            "metrics": case["metrics"],
            "testimonial": f"我们当初也很犹豫，但用了之后发现效果确实如预期。现在团队都在用，反馈很好。",
            "company_type": f"{case['industry']}{case['company_size']}"
        },
        "tip": "引用案例时要具体，提到真实的客户名称（如果获得授权）和可量化的指标更有说服力。"
    }, ensure_ascii=False)


def execute_get_referral_questions(timing: str = "after_success", customer_type: str = "assertive") -> str:
    """执行转介绍问题获取"""
    questions_map = {
        "after_success": {
            "opening": "恭喜您做出这个决定！您身边有没有和您情况类似、也可能需要这个方案的朋友？",
            "follow_up": "您提的那位朋友，我可以以您的名义联系他吗？",
            "incentive": "如果您能介绍成功，我们会给您提供额外的服务支持。"
        },
        "during_objection": {
            "opening": "我理解您需要再考虑一下。您有没有认识类似情况的企业主，我可以和他们聊聊？",
            "follow_up": "您觉得如果有其他客户的使用体验分享，会不会对您的决定有帮助？",
            "incentive": "我们可以安排一次客户见面会，让您直接了解。"
        },
        "regular_checkin": {
            "opening": "最近您公司有没有什么新的发展计划？有没有朋友可能需要了解？",
            "follow_up": "我这边有个小礼物，感谢您一直以来的支持。",
            "incentive": "介绍成功的老客户我们都会有专属服务。"
        }
    }

    questions = questions_map.get(timing, questions_map["regular_checkin"])
    profile = CUSTOMER_PROFILES.get(customer_type, CUSTOMER_PROFILES["assertive"])

    return json.dumps({
        "timing": timing,
        "customer_type": customer_type,
        "questions": questions,
        "approach": profile.get("questions_style", "直接询问"),
        "tip": "转介绍是最好的获客方式，但要在客户满意的时候自然提出，不要太突兀。"
    }, ensure_ascii=False)


def execute_get_follow_up_script(follow_up_type: str, days_since_last_contact: int = 0, customer_type: str = "assertive", context: str = "") -> str:
    """执行跟进话术获取"""
    scripts_map = {
        "thank_you": {
            "scenario": "签约后或收到客户付款后",
            "templates": [
                "非常感谢您的信任！我们会第一时间安排后续服务，确保让您满意。",
                "感谢您选择了我们。我会亲自跟进整个交付过程，有任何问题可以直接找我。"
            ]
        },
        "check_in": {
            "scenario": "定期关怀，了解使用情况",
            "templates": [
                "您好，距离上次联系已经有一段时间了，想看看我们的方案使用得怎么样？",
                "最近您那边有什么新进展吗？如果有任何需要支持的，随时告诉我。"
            ]
        },
        "reminder": {
            "scenario": "提醒客户行动，如回复报价、确认时间等",
            "templates": [
                "想提醒您一下，关于上次我们讨论的方案，您有任何问题吗？",
                "不知道您有没有机会看看我们发的资料？我可以随时解答您的疑问。"
            ]
        },
        "reengagement": {
            "scenario": "重新激活长期未联系的客户",
            "templates": [
                "您好，最近看到一篇关于{行业趋势}的文章，想到您当时提到的问题，特来分享。",
                "您好，距离上次联系有一段时间了。不知道您那边有什么新变化吗？"
            ]
        },
        "upsell": {
            "scenario": "追加销售或交叉销售",
            "templates": [
                "看到您最近使用了我们的服务，想和您分享一下我们新出的功能，可能会对您有帮助。",
                "您是我们尊贵的客户，我们最近有个升级方案想专门推荐给您。"
            ]
        }
    }

    scripts = scripts_map.get(follow_up_type, scripts_map["check_in"])
    profile = CUSTOMER_PROFILES.get(customer_type, CUSTOMER_PROFILES["assertive"])

    return json.dumps({
        "follow_up_type": follow_up_type,
        "days_since_last_contact": days_since_last_contact,
        "customer_type": customer_type,
        "scenario": scripts["scenario"],
        "templates": scripts["templates"],
        "approach": profile.get("recommended_approach", ""),
        "tip": f"跟进时机很重要：{days_since_last_contact}天没联系的客户要重新建立亲近感。"
    }, ensure_ascii=False)


def execute_get_negociation_tactics(negociation_topic: str, customer_leverage: str = "medium", our_leverage: str = "medium", customer_type: str = "assertive") -> str:
    """执行谈判策略获取"""
    tactics_map = {
        "price": {
            "principles": [
                "永远不要在第一轮就答应客户的降价要求",
                "用价值而不是价格来说服",
                "准备多个方案让客户选择"
            ],
            "counter_offers": [
                "我们可以考虑，但需要您承诺更大的订单量",
                "价格可以谈，但服务范围需要调整",
                "如果能保证长期合作，我们可以给出更好的价格"
            ],
            "walk_away_script": "这个价格确实是我们能给的最低点了。如果您觉得超出预算，我们可以考虑先做一个小规模的试点。"
        },
        "payment": {
            "principles": [
                "尽量争取预付款或高比例首付",
                "提供分期付款作为替代方案",
                "用账期换其他利益"
            ],
            "counter_offers": [
                "我们可以接受分期，但需要一定的付款比例作为保障",
                "如果能提前付款，我们可以提供折扣",
                "我们可以延长账期，但需要您提供担保"
            ],
            "walk_away_script": "账期确实是我们比较难接受的条款。您看能不能在其他方面我们给您补偿，比如延长保修期或增加服务内容？"
        },
        "timeline": {
            "principles": [
                "在时间紧迫时不要仓促答应",
                "评估内部资源是否真的能满足",
                "用时间换其他利益"
            ],
            "counter_offers": [
                "这个时间确实很紧，我们可以加急，但需要您确认一下优先级",
                "我们可以分阶段交付，先保证核心功能",
                "如果我们能提前完成，您能给我们什么回报？"
            ],
            "walk_away_script": "按照目前的资源，我们确实无法保证在这个时间完成所有内容。您看我们分两步走怎么样？"
        },
        "scope": {
            "principles": [
                "明确界定工作范围，避免范围蔓延",
                "用明确的文档记录所有约定",
                "预留变更的缓冲"
            ],
            "counter_offers": [
                "这个功能可以包含，但需要相应调整预算",
                "我们可以做，但需要明确优先级，先完成核心部分",
                "不在原始范围内的我们可以作为后续升级来提供"
            ],
            "walk_away_script": "这些需求我们会记录下来，但现在这个阶段我们先聚焦核心功能，其他的在后续迭代中处理。"
        }
    }

    tactics = tactics_map.get(negociation_topic, tactics_map["price"])
    leverage_tip = ""
    if customer_leverage == "high" and our_leverage == "low":
        leverage_tip = "客户处于强势地位，需要适当让步但要换取其他利益"
    elif customer_leverage == "low" and our_leverage == "high":
        leverage_tip = "我们处于强势地位，可以坚持立场并要求更多"
    else:
        leverage_tip = "双方力量均衡，可以通过创造性的方案达成双赢"

    return json.dumps({
        "negociation_topic": negociation_topic,
        "customer_leverage": customer_leverage,
        "our_leverage": our_leverage,
        "principles": tactics["principles"],
        "counter_offers": tactics["counter_offers"],
        "walk_away_script": tactics["walk_away_script"],
        "leverage_tip": leverage_tip,
        "tip": "谈判的原则：永远不要接受第一次报价，永远准备好离开的方案"
    }, ensure_ascii=False)


def execute_get_trust_building(trust_stage: str = "rapport", customer_type: str = "assertive", context: str = "") -> str:
    """执行建立信任话术获取"""
    stage_map = {
        "rapport": {
            "goal": "建立亲和感和初步信任",
            "techniques": [
                "寻找共同点（同学、同乡、共同的经历等）",
                "调整沟通风格以匹配客户",
                "使用客户的语言而不是销售术语",
                "展现个人魅力而不是只是谈产品"
            ],
            "scripts": [
                "我听说您也是XX学校毕业的？真是太巧了，我也是。",
                "看得出来您是个很务实的人，我也是，所以我直接说重点..."
            ]
        },
        "credibility": {
            "goal": "建立专业可信度",
            "techniques": [
                "分享相关行业的成功案例",
                "展示专业资质和认证",
                "提供第三方背书或推荐",
                "引用行业数据或研究报告"
            ],
            "scripts": [
                "我们服务过很多和您类似规模的企业，比如XX公司，他们遇到了同样的问题...",
                "根据的行业报告，使用我们方案的企业平均效率提升了..."
            ]
        },
        "rapport_established": {
            "goal": "巩固信任关系",
            "techniques": [
                "信守承诺，说到做到",
                "主动提供价值，不只是推销",
                "诚实告知局限性和风险",
                "成为客户信赖的顾问而不是销售"
            ],
            "scripts": [
                "我想给您一个诚实的建议，关于您提到的问题，其实有更简单但更有效的解决方案...",
                "我昨天看到一篇关于的文章，想到您可能感兴趣，发给您看看。"
            ]
        }
    }

    stage_data = stage_map.get(trust_stage, stage_map["rapport"])
    profile = CUSTOMER_PROFILES.get(customer_type, CUSTOMER_PROFILES["assertive"])

    return json.dumps({
        "trust_stage": trust_stage,
        "customer_type": customer_type,
        "goal": stage_data["goal"],
        "techniques": stage_data["techniques"],
        "scripts": stage_data["scripts"],
        "approach": profile.get("questions_style", ""),
        "tip": f"建立信任的关键：{stage_data['goal']}"
    }, ensure_ascii=False)


def execute_get_appointment_scheduling(appointment_type: str, proposed_date: str = "", meeting_duration: int = 30, customer_type: str = "assertive") -> str:
    """执行预约拜访话术获取"""
    type_map = {
        "first_meeting": {
            "goal": "约到首次拜访",
            "scripts": [
                "王总您好，我是XX公司的小李。之前和您的助理通过电话，想约您30分钟时间当面聊聊，不知道您这周三或周四哪个时间方便？",
                "张总，您好！我这边有个事情想当面向您请教，不知道您有没有15-20分钟？我可以配合您的时间。"
            ]
        },
        "demo": {
            "goal": "约产品演示",
            "scripts": [
                "李总，上次您提到想看看我们的产品实际效果，我想安排一个30分钟的在线演示，给您展示几个核心功能，您看这周有时间吗？",
                "王总，我们的demo环境已经准备好了，随时可以给您演示。您看是这周二还是周三方便？"
            ]
        },
        "proposal": {
            "goal": "约方案汇报",
            "scripts": [
                "张总，按照之前讨论的，我这边准备了一个针对性的方案。想约您30分钟时间当面汇报，您看周三下午还是周四上午比较方便？",
                "李总，方案已经发您邮箱了，我想约您当面过一遍核心内容，不知道您这周有没有1小时？"
            ]
        },
        "negotiation": {
            "goal": "约商务谈判",
            "scripts": [
                "王总，关于合作条款，我这边有一些想法想和您当面沟通一下，您看这周有时间吗？",
                "张总，希望我们能尽快把细节确定下来，您看我们约个时间当面谈？"
            ]
        },
        "follow_up": {
            "goal": "约跟进回访",
            "scripts": [
                "李总，上次见面后一直想再和您聊聊，不知道您这周有没有半小时？",
                "王总，最近您那边有什么新进展吗？想找时间和您同步一下。"
            ]
        }
    }

    scripts = type_map.get(appointment_type, type_map["follow_up"])
    profile = CUSTOMER_PROFILES.get(customer_type, CUSTOMER_PROFILES["assertive"])

    return json.dumps({
        "appointment_type": appointment_type,
        "proposed_date": proposed_date,
        "meeting_duration": meeting_duration,
        "goal": scripts["goal"],
        "scripts": scripts["scripts"],
        "approach": profile.get("questions_style", ""),
        "tip": f"预约拜访关键是：{scripts['goal']}。时间要具体，不要问'您什么时候方便'而是给出选项。"
    }, ensure_ascii=False)


# ============================================================
# 工具执行入口
# ============================================================

TOOL_EXECUTE_MAP = {
    "get_spin_questions": execute_get_spin_questions,
    "get_opening_script": execute_get_opening_script,
    "handle_objection": execute_handle_objection,
    "get_backchannel": execute_get_backchannel,
    "get_closing_script": execute_get_closing_script,
    "search_knowledge": execute_search_knowledge,
    "evaluate_spin": execute_evaluate_spin,
    "get_proposal_script": execute_get_proposal_script,
    "get_customer_profile": execute_get_customer_profile,
    "get_discovery_questions": execute_get_discovery_questions,
    # 新增工具的执行函数
    "get_pre_approach_plan": execute_get_pre_approach_plan,
    "get_competition_analysis": execute_get_competition_analysis,
    "get_value_summary": execute_get_value_summary,
    "get_decision_maker_strategy": execute_get_decision_maker_strategy,
    "get_social_proof": execute_get_social_proof,
    "get_referral_questions": execute_get_referral_questions,
    "get_follow_up_script": execute_get_follow_up_script,
    "get_negociation_tactics": execute_get_negociation_tactics,
    "get_trust_building": execute_get_trust_building,
    "get_appointment_scheduling": execute_get_appointment_scheduling
}


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """执行工具并返回结果"""
    executor = TOOL_EXECUTE_MAP.get(tool_name)
    if not executor:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        return executor(**arguments)
    except Exception as e:
        return json.dumps({"error": str(e), "tool": tool_name, "arguments": arguments})