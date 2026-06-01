"""
SPIN API v1 - SPIN问题生成API
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
import json
import re
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


def generate_spin_questions_prompt(customer: CustomerContext) -> str:
    """构建SPIN问题生成的提示词"""
    return f"""你是销售顾问专家，根据以下客户背景信息，生成个性化的SPIN四步提问清单。

【客户背景】
- 行业：{customer.industry}
- 规模：{customer.scale}
- 痛点：{', '.join(customer.pain_points)}

【SPIN提问法说明】
1. Situation（现状问题）：了解客户的基本情况的背景
2. Problem（难点问题）：发现客户当前面临的问题和困难
3. Implication（暗示问题）：放大问题的后果和影响，让客户感受到紧迫性
4. Need-payoff（需求效益问题）：引导客户自己说出解决方案的价值

【要求】
- 每个类别生成3-5个问题
- 问题要具体、个性化，符合客户的行业和痛点
- 问题要像真实销售会问的那样自然
- 不要生硬地直接问，要符合顾问式销售的风格

请以JSON格式返回：
{{
    "situation_questions": ["问题1", "问题2", "问题3"],
    "problem_questions": ["问题1", "问题2", "问题3"],
    "implication_questions": ["问题1", "问题2", "问题3"],
    "need_payoff_questions": ["问题1", "问题2", "问题3"]
}}
"""


@router.post("/questions", response_model=SpinQuestionResponse)
async def generate_spin_questions(request: SpinQuestionsRequest):
    """
    根据客户背景生成SPIN个性化问题清单

    Args:
        request: 包含客户行业、规模、痛点的请求

    Returns:
        SPIN问题清单（按S/P/I/N分类）
    """
    try:
        minimax = get_minimax_service()

        if not minimax.api_key:
            raise HTTPException(status_code=500, detail="LLM API未配置")

        # 构建提示词
        prompt = generate_spin_questions_prompt(request.customer)

        # 调用LLM生成问题
        messages = [
            {"role": "system", "content": "你是一个专业的销售顾问，擅长SPIN提问法。"},
            {"role": "user", "content": prompt}
        ]

        response = await minimax.chat(messages=messages, model="M2.7")

        # 解析LLM返回的JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise HTTPException(status_code=500, detail="LLM返回格式错误")

        try:
            questions_data = json.loads(json_match.group())
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="LLM返回JSON解析失败")

        # 生成问题清单ID
        question_list_id = str(uuid.uuid4())

        # 构建响应
        question_list = SpinQuestionList(
            question_list_id=question_list_id,
            situation_questions=questions_data.get("situation_questions", []),
            problem_questions=questions_data.get("problem_questions", []),
            implication_questions=questions_data.get("implication_questions", []),
            need_payoff_questions=questions_data.get("need_payoff_questions", []),
            customer_context=request.customer,
            created_at=datetime.now().isoformat()
        )

        # 存储到内存
        _question_lists[question_list_id] = question_list

        return SpinQuestionResponse(
            success=True,
            data=question_list
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/questions/{question_list_id}", response_model=SpinQuestionResponse)
async def get_spin_questions(question_list_id: str):
    """
    获取已生成的问题清单

    Args:
        question_list_id: 问题清单ID

    Returns:
        问题清单
    """
    if question_list_id not in _question_lists:
        raise HTTPException(status_code=404, detail="问题清单不存在")

    return SpinQuestionResponse(
        success=True,
        data=_question_lists[question_list_id]
    )


@router.get("/questions", response_model=SpinQuestionResponse)
async def list_spin_questions():
    """
    获取所有问题清单（测试用）

    Returns:
        所有问题清单
    """
    if not _question_lists:
        return SpinQuestionResponse(
            success=True,
            data=None
        )

    # 返回最新的一个
    latest = max(_question_lists.values(), key=lambda x: x.created_at)
    return SpinQuestionResponse(
        success=True,
        data=latest
    )
