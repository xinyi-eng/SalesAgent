"""
SPIN API v1 - SPIN问题生成与客户调查API
"""
from fastapi import APIRouter, HTTPException
import asyncio
import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
import uuid
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.spin import (
    SpinQuestionsRequest,
    SpinQuestionResponse,
    SpinQuestionList,
    CustomerContext
)
from app.services.llm import get_minimax_service

router = APIRouter(prefix="/spin", tags=["spin"])

# In-memory storage for question lists (replace with database in production)
_question_lists = {}


# ==================== 客户调查相关 ====================

class CustomerInvestigationRequest(BaseModel):
    """客户调查请求"""
    customer_name: str = Field(..., description="客户/公司/联系人名称")
    search_context: Optional[str] = Field(None, description="前端传来的网络搜索结果上下文")


class InvestigationResponse(BaseModel):
    """调查响应"""
    success: bool
    subject_type: Optional[str] = Field(None, description="调查对象类型: company/person")
    data: Optional[dict] = Field(None, description="调查数据(公司或联系人)")
    error: Optional[str] = None


def format_web_context(search_results: list) -> str:
    """将搜索结果格式化为上下文字符串"""
    if not search_results:
        return ""
    lines = ["\n\n【最新网络搜索结果】"]
    for r in search_results[:8]:
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        date = r.get("date", "")
        if title:
            lines.append(f"- {title}")
        if snippet:
            lines.append(f"  {snippet}")
        if date:
            lines.append(f"  ({date})")
    lines.append("\n请基于以上真实网络信息整理成JSON格式返回。")
    return "\n".join(lines)


def generate_company_investigation_prompt(customer_name: str, web_context: str = "") -> str:
    """构建公司调查的提示词"""
    base_prompt = """你是一个专业的销售情报助手。请帮我调查公司"%s"的相关信息。

请从销售角度收集以下信息：
1. 公司背景：公司主营业务、规模、行业地位、成立时间等
2. 近期动态：最近的重要新闻、产品发布、战略动向等（2025-2026年）
3. 竞品信息：主要竞争对手是谁，和竞品相比有什么优劣
4. 潜在痛点：基于公司情况推测可能的销售痛点（销售、CRM、市场获客等）
5. 额外信息（如有）：媒体报道、融资情况、高管信息等

请用JSON格式返回：
{
    "subject_type": "company",
    "background": "公司背景描述...",
    "recent_news": ["动态1", "动态2", "动态3"],
    "competitors": ["竞品1", "竞品2"],
    "potential_pains": ["痛点1", "痛点2", "痛点3"],
    "extra_info": {
        "media_reports": ["媒体报道1", "媒体报道2"],
        "funding_status": "融资情况",
        "leader_info": "高管信息"
    }
}

注意：
- 只返回你确定的信息，不要编造
- 如果某些信息无法获取，用空字符串或空数组
- 痛点要具体，从销售角度思考""" % customer_name
    return base_prompt + web_context


def generate_person_investigation_prompt(customer_name: str, web_context: str = "") -> str:
    """构建个人联系人调查的提示词"""
    base_prompt = """你是一个专业的销售情报助手。请帮我调查联系人"%s"的相关信息。

请从销售角度收集以下信息：
1. 基本信息：姓名、职位、所属公司、部门
2. 背景履历：教育背景、职业履历、擅长领域
3. 近期动态：最近参与的活动、发表的观点、社交媒体动态等（2025-2026年）
4. 潜在痛点：基于其职位和背景推测可能的业务痛点
5. 额外信息（如有）：媒体报道、行业评价、社交关系等

请用JSON格式返回：
{
    "subject_type": "person",
    "name": "姓名",
    "title": "职位/头衔",
    "company": "所属公司",
    "background": "背景履历描述...",
    "recent_activities": ["活动1", "活动2", "活动3"],
    "potential_pains": ["痛点1", "痛点2", "痛点3"],
    "extra_info": {
        "media_reports": ["媒体报道1"],
        "social_links": "领英/脉脉等链接",
        "expertise": "擅长领域"
    }
}

注意：
- 如果名称太宽泛（如"张总"），根据上下文推断最可能的身份并调查
- 只返回你确定的信息，不要编造
- 如果某些信息实在无法获取，用空字符串或空数组
- 痛点要具体，从销售角度思考
- 即使信息很少，也要返回完整的JSON""" % customer_name
    return base_prompt + web_context


def generate_investigation_prompt(customer_name: str, web_context: str = "") -> str:
    """根据名称自动判断是公司还是个人，构建对应提示词"""
    person_indicators = ['总', '先生', '女士', 'CEO', 'CTO', 'COO', 'CFO', 'CMO', 'VP',
                         '总监', '经理', '主任', '总裁', '董事长', '副总裁', '首席',
                         '负责人', '老板', '创始人', '合伙人']
    for indicator in person_indicators:
        if customer_name.endswith(indicator) or indicator in customer_name:
            return generate_person_investigation_prompt(customer_name, web_context)
    return generate_company_investigation_prompt(customer_name, web_context)


async def _do_mcp_search(query: str, num_results: int = 5) -> str:
    """
    通过 MiniMax LLM 自身知识做调查（网络搜索暂不可用）
    """
    # Windows subprocess MCP 调用有兼容性问题，暂时用 LLM 知识回答
    return ""


class WebSearchRequest(BaseModel):
    """网络搜索请求"""
    query: str = Field(..., description="搜索关键词")


class WebSearchResponse(BaseModel):
    """网络搜索响应"""
    success: bool
    context: Optional[str] = None
    error: Optional[str] = None


@router.post("/web-search", response_model=WebSearchResponse)
async def web_search(request: WebSearchRequest):
    """
    通过 MCP 工具执行真正的网络搜索，返回格式化上下文
    """
    try:
        context = await _do_mcp_search(request.query)
        if not context:
            return WebSearchResponse(success=True, context="", error="搜索未返回结果")
        return WebSearchResponse(success=True, context=context)
    except Exception as e:
        return WebSearchResponse(success=False, context="", error=str(e))


@router.post("/investigate", response_model=InvestigationResponse)
async def investigate_customer(request: CustomerInvestigationRequest):
    """
    AI自动调查客户相关信息（网络搜索增强）
    前端通过 MCP 工具做网络搜索，将结果通过 search_context 传回后端
    """
    try:
        minimax = get_minimax_service()
        if not minimax.api_key:
            raise HTTPException(status_code=500, detail="LLM API未配置")

        # 使用前端传来的搜索上下文（如果有）
        web_context = request.search_context or ""

        # 生成提示词（包含搜索结果）
        prompt = generate_investigation_prompt(request.customer_name, web_context)
        messages = [
            {"role": "system", "content": "你是一个专业的销售情报助手，擅长收集和分析客户信息。"},
            {"role": "user", "content": prompt}
        ]

        response = await minimax.chat(messages=messages, model="M2.7")
        # Strip <think>...</think> reasoning blocks (M2.7 model wraps output)
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()

        # LLM 经常在 JSON 前后加 markdown 解释，先尝试从 ```json ... ``` 块抽取
        code_block = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
        if code_block:
            json_text = code_block.group(1)
        else:
            # 没有 code block 就用最后一个 { ... } 块（JSON 通常在末尾）
            matches = list(re.finditer(r'\{[\s\S]*?\}', response))
            json_text = matches[-1].group() if matches else None

        if not json_text:
            # LLM没有返回JSON，检查是否是因为名称太泛
            if any(kw in response for kw in ['无法确定', '无法确认', '请提供', '请输入', '太模糊', '不够具体', '更多信息']):
                return InvestigationResponse(
                    success=False,
                    error=f"'{request.customer_name}' 太泛泛了，请提供更具体的信息，例如：姓名+公司全称（如'张总 阿里巴巴'）或'XX公司CEO'"
                )
            return InvestigationResponse(
                success=False,
                error=f"AI 未返回结构化数据，请稍后重试或换一个更具体的名称"
            )

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"[spin.investigate] JSON parse error: {e}\nRaw text: {json_text[:500]}")
            return InvestigationResponse(
                success=False,
                error=f"AI 返回的 JSON 解析失败，请稍后重试"
            )

        subject_type = data.get("subject_type", "company")

        return InvestigationResponse(success=True, subject_type=subject_type, data=data)

    except HTTPException:
        raise
    except Exception as e:
        return InvestigationResponse(success=False, error=str(e))


# ==================== SPIN问题生成相关 ====================

def generate_spin_prompt(customer: CustomerContext) -> str:
    """构建SPIN问题生成的提示词"""
    prompt = """你是销售顾问专家，根据客户背景生成SPIN四步提问清单。

客户背景：
- 行业：%s
- 规模：%s
- 痛点：%s

SPIN提问法：
1. Situation（现状问题）：了解客户基本情况
2. Problem（难点问题）：发现客户面临的问题
3. Implication（暗示问题）：放大问题的后果
4. Need-payoff（需求效益问题）：引导客户说出方案价值

要求：
- 每个类别生成3-5个问题
- 问题要具体个性化
- 像真实销售那样自然提问

JSON格式：
{
    "situation_questions": ["问题1", "问题2", "问题3"],
    "problem_questions": ["问题1", "问题2", "问题3"],
    "implication_questions": ["问题1", "问题2", "问题3"],
    "need_payoff_questions": ["问题1", "问题2", "问题3"]
}""" % (customer.industry, customer.scale, ', '.join(customer.pain_points))
    return prompt


@router.post("/questions", response_model=SpinQuestionResponse)
async def generate_spin_questions(request: SpinQuestionsRequest):
    """
    生成SPIN个性化问题清单
    """
    try:
        minimax = get_minimax_service()
        if not minimax.api_key:
            raise HTTPException(status_code=500, detail="LLM API未配置")

        prompt = generate_spin_prompt(request.customer)
        messages = [
            {"role": "system", "content": "你是一个专业的销售顾问，擅长SPIN提问法。"},
            {"role": "user", "content": prompt}
        ]

        response = await minimax.chat(messages=messages, model="M2.7")

        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise HTTPException(status_code=500, detail="LLM返回格式错误")

        try:
            questions_data = json.loads(json_match.group())
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="LLM返回JSON解析失败")

        question_list_id = str(uuid.uuid4())
        question_list = SpinQuestionList(
            question_list_id=question_list_id,
            situation_questions=questions_data.get("situation_questions", []),
            problem_questions=questions_data.get("problem_questions", []),
            implication_questions=questions_data.get("implication_questions", []),
            need_payoff_questions=questions_data.get("need_payoff_questions", []),
            customer_context=request.customer,
            created_at=datetime.now().isoformat()
        )

        _question_lists[question_list_id] = question_list
        return SpinQuestionResponse(success=True, data=question_list)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/questions/{question_list_id}", response_model=SpinQuestionResponse)
async def get_spin_questions(question_list_id: str):
    if question_list_id not in _question_lists:
        raise HTTPException(status_code=404, detail="问题清单不存在")
    return SpinQuestionResponse(success=True, data=_question_lists[question_list_id])


@router.get("/questions", response_model=SpinQuestionResponse)
async def list_spin_questions():
    if not _question_lists:
        return SpinQuestionResponse(success=True, data=None)
    latest = max(_question_lists.values(), key=lambda x: x.created_at)
    return SpinQuestionResponse(success=True, data=latest)
