"""
对话处理器 - 集成知识服务的Agentic RAG对话处理
"""
import json
from typing import Optional, List, Dict, Any
from app.services.llm.minimax import get_minimax_service
from app.services.knowledge.service import get_knowledge_service
from app.services.knowledge.tools import CUSTOMER_PROFILES
from app.websocket.manager import session_manager


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

    def get_system_prompt(self, customer_type: str = "assertive", scenario: str = "general") -> str:
        """
        获取系统提示词，包含客户画像和工具说明

        客户类型（8种）：
        - assertive: 主导型 - 果断直接，竞争意识强
        - analytical: 理性型 - 喜欢数据，谨慎决策
        - amiable: 友善型 - 重视关系，需要信任
        - expressive: 表达型 - 热情健谈，需要认可
        - assertive_analytical: 主导+理性（技术决策者）
        - assertive_expressive: 主导+表达（强势说服型）
        - amiable_expressive: 友善+表达（热情支持型）
        - analytical_amiable: 理性+友善（谨慎温和型）
        """
        # 从知识库获取客户画像，而不是硬编码
        profile = CUSTOMER_PROFILES.get(customer_type, CUSTOMER_PROFILES["assertive"])
        characteristics = profile.get("characteristics", [])
        approach = profile.get("recommended_approach", "")

        chars_text = "\n".join([f"- {c}" for c in characteristics[:5]])

        return f"""你是客户，不是教练！

【你的身份】
你就是一个客户（买方），接到了销售人员的电话。
你的唯一任务是对销售人员的开场白做出反应。

【绝对禁止】
- 不要扮演销售教练
- 不要给销售员提供建议
- 不要分析销售员的表现
- 不要提及SPIN或任何销售方法论
- 不要说"作为AI客户..."或类似的话
- 如果销售说得不好，你只需要冷淡或质疑即可

【回应方式】
当销售说"您好，请问是王总吗？我是做企业软件销售的，想和您聊聊。"
你只需要简单地回应，像真实客户一样，例如：
- "嗯，谁呀？"（冷淡）
- "王总不在，你有什么事？"（警惕）
- "企业软件？哪家的？"（有点兴趣）

保持简短、自然，符合你的性格特点。
不要长篇大论！不要分析！只要回应！

【客户画像】
类型：{profile.get('description', customer_type)}
特征：
{chars_text}

你是客户，对话要自然简短。"""

    async def handle_message(
        self,
        user_message: str,
        conversation_history: List[Dict],
        customer_type: str = "assertive",
        scenario: str = "general"
    ) -> Dict[str, Any]:
        """
        处理用户消息，返回AI回复

        Args:
            user_message: 用户发言
            conversation_history: 对话历史
            customer_type: 客户类型
            scenario: 场景配置

        Returns:
            {
                "response": str,  # AI回复文本
                "tool_calls": List[Dict],  # 触发的工具调用
                "knowledge_used": List[str],  # 使用了的知识
            }
        """
        # 1. 构建消息列表
        messages = self._build_messages(user_message, conversation_history, customer_type, scenario)

        # 2. 获取工具定义
        tools = self.knowledge.get_tool_definitions()

        # 3. 调用LLM（包含工具）
        response_text = await self.llm.chat(
            messages=messages,
            tools=tools
        )

        # 4. 检查是否触发了function calling
        tool_calls_result = None
        knowledge_used = []

        try:
            response_data = json.loads(response_text)
            if response_data.get("type") == "function_call":
                tool_calls = response_data.get("tool_calls", [])

                # 5. 执行工具调用
                tool_results = self.knowledge.process_tool_calls(tool_calls)

                # 6. 收集知识使用情况
                for tr in tool_results:
                    if tr["success"]:
                        knowledge_used.append(tr["tool_name"])
                        # 将工具结果追加到对话历史
                        messages.append({
                            "role": "user",
                            "content": f"[TOOL RESULT: {tr['tool_name']}]\n{tr['formatted_result']}"
                        })

                # 7. 用工具结果再次调用LLM生成最终回复
                if tool_results:
                    final_response = await self.llm.chat(messages=messages, tools=tools)
                    return {
                        "response": final_response,
                        "tool_calls": tool_results,
                        "knowledge_used": knowledge_used
                    }

        except json.JSONDecodeError:
            # 普通回复，没有触发function calling
            pass

        return {
            "response": response_text,
            "tool_calls": tool_calls_result or [],
            "knowledge_used": knowledge_used
        }

    def _build_messages(
        self,
        user_message: str,
        conversation_history: List[Dict],
        customer_type: str,
        scenario: str
    ) -> List[Dict]:
        """构建消息列表"""
        messages = []

        # 系统提示
        messages.append({
            "role": "system",
            "content": self.get_system_prompt(customer_type, scenario)
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
        evaluation_prompt = f"""你是销售对练系统的AI教练，负责对销售学员的对话进行SPIN标准评价。

【知识库 - SPIN方法论参考】
{spin_framework}

【知识库 - SPIN各阶段问题建议】
{spin_questions}

【待评价对话】
{conversation_text}

客户类型：{customer_type}

请按照以下JSON格式输出评价（必须包含knowledge_reference字段，引用上面知识库中的具体内容）：

{{
    "situation_score": 分数(0-10),
    "situation_analysis": "分析为什么得这个分数",
    "situation_quote": "引用的对话中原销售说的话",
    "situation_reference": "引用知识库的具体内容作为评分依据",
    "situation_suggestion": "改进建议",

    "problem_score": 分数(0-10),
    "problem_analysis": "分析",
    "problem_quote": "引用的对话原文",
    "problem_reference": "引用知识库的具体内容",
    "problem_suggestion": "改进建议",

    "implication_score": 分数(0-10),
    "implication_analysis": "分析",
    "implication_quote": "引用的对话原文",
    "implication_reference": "引用知识库的具体内容（如：方法论说应该追问问题后果）",
    "implication_suggestion": "改进建议",

    "need_payoff_score": 分数(0-10),
    "need_payoff_analysis": "分析",
    "need_payoff_quote": "引用的对话原文",
    "need_payoff_reference": "引用知识库的具体内容",
    "need_payoff_suggestion": "改进建议",

    "overall_score": 总分(0-40),
    "key_strengths": ["优点1", "优点2"],
    "areas_for_improvement": ["改进点1", "改进点2"],
    "next_practice_focus": "下次练习重点建议"
}}"""

        # 构建消息
        messages = [
            {
                "role": "system",
                "content": "你是销售对练系统的AI教练，负责对销售学员的对话进行SPIN标准评价。评价要具体引用知识库内容作为依据。"
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