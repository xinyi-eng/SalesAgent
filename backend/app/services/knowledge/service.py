"""
知识服务 - Agentic RAG 核心服务
管理知识库工具的执行和对话集成
"""
import json
import re
from typing import Optional, List, Dict, Any
from app.services.knowledge.tools import (
    KNOWLEDGE_TOOLS,
    TOOL_EXECUTE_MAP,
    execute_tool,
    execute_search_knowledge
)


class KnowledgeService:
    """知识服务 - 管理Agentic RAG"""

    def __init__(self):
        self.tools = KNOWLEDGE_TOOLS
        # 支持新旧两种格式
        self.tool_map = {}
        for t in self.tools:
            if "function" in t:
                self.tool_map[t["function"]["name"]] = t
            elif "name" in t:
                self.tool_map[t["name"]] = t

    def get_tools_schema(self) -> List[Dict]:
        """获取工具定义Schema，用于LLM Function Calling"""
        return self.tools

    def get_tool_definitions(self) -> List[Dict]:
        """获取工具定义列表（供MiniMax API使用）"""
        return self.tools

    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """执行工具调用"""
        return execute_tool(tool_name, arguments)

    def should_retrieve_knowledge(self, user_message: str, conversation_history: List[Dict]) -> bool:
        """
        判断是否需要检索知识库
        基于对话上下文和用户消息内容
        """
        user_lower = user_message.lower()

        # 触发知识检索的关键词
        knowledge_keywords = [
            "spin's", "spin", "背景问题", "难点问题", "暗示问题", "需求-效益",
            "话术", "怎么问", "如何说", "开场白", "缔结",
            "客户说", "他觉得", "异议", "太贵了", "不需要", "再想想",
            "竞品", "对比", "其他家",
            "评价", "打几分", "给点建议"
        ]

        for keyword in knowledge_keywords:
            if keyword.lower() in user_lower:
                return True

        # 检查对话历史，如果连续3轮没有调用知识工具，触发一次
        tool_call_count = sum(
            1 for msg in conversation_history[-5:]
            if msg.get("role") == "assistant" and "tool_calls" in str(msg)
        )

        if tool_call_count == 0 and len(conversation_history) > 3:
            return True

        return False

    def extract_conversation_text(self, messages: List[Dict]) -> str:
        """从消息列表中提取对话文本"""
        texts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ["user", "assistant"]:
                prefix = "用户" if role == "user" else "AI"
                texts.append(f"{prefix}：{content}")
        return "\n".join(texts)

    def get_context_for_llm(self, tool_result: str, original_query: str) -> str:
        """
        将工具执行结果格式化为LLM上下文
        确保知识以自然的方式融入对话
        """
        try:
            data = json.loads(tool_result)
            if "error" in data:
                return f"知识检索出错：{data['error']}"

            # 根据不同工具类型格式化结果
            if "questions" in data:
                # SPIN问题类
                questions = data.get("questions", [])
                tip = data.get("tip", "")
                result = f"【相关问题建议】{', '.join(questions)}"
                if tip:
                    result += f"\n{tip}"
                return result

            elif "scripts" in data:
                # 话术类
                scripts = data.get("scripts", [])
                tip = data.get("tip", "")
                result = f"【话术建议】{', '.join(scripts[:2])}"
                if tip:
                    result += f"\n{tip}"
                return result

            elif "handling_options" in data:
                # 异议处理类
                options = data.get("handling_options", [])
                tip = data.get("tip", "")
                result = f"【异议处理】{' '.join([o['template'] for o in options[:1]])}"
                if tip:
                    result += f"\n{tip}"
                return result

            elif "results" in data:
                # 知识检索类
                results = data.get("results", [])
                tip = data.get("tip", "")
                content_items = []
                for r in results[:2]:
                    content = r.get("content", [])
                    if isinstance(content, list):
                        content_items.extend(content[:2])
                    else:
                        content_items.append(str(content))
                result = f"【知识参考】{' '.join(content_items[:3])}"
                if tip:
                    result += f"\n{tip}"
                return result

            elif "evaluation" in data:
                # 评价类 - 直接返回完整评价
                return f"【SPIN评价报告】\n{json.dumps(data, ensure_ascii=False, indent=2)}"

            else:
                return f"【知识】{tool_result}"

        except json.JSONDecodeError:
            return f"【知识】{tool_result}"

    def process_tool_calls(self, tool_calls: List[Dict]) -> List[Dict[str, Any]]:
        """
        处理LLM返回的tool_calls
        返回格式化的工具执行结果列表
        """
        results = []
        for call in tool_calls:
            tool_name = call.get("function", {}).get("name", "")
            arguments_str = call.get("function", {}).get("arguments", "{}")

            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except:
                arguments = {"raw": arguments_str}

            # 执行工具
            tool_result = self.execute_tool_call(tool_name, arguments)

            # 格式化结果
            formatted_result = self.get_context_for_llm(tool_result, arguments.get("query", ""))

            results.append({
                "tool_name": tool_name,
                "arguments": arguments,
                "result": tool_result,
                "formatted_result": formatted_result,
                "success": "error" not in tool_result
            })

        return results


# 单例
_knowledge_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    """获取知识服务单例"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service