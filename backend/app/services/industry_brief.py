"""
Industry brief service.

Generates structured industry-news briefs by asking the LLM to roleplay
as a sales intelligence analyst. Output is JSON (per the schema in
`schemas.practice.BriefDetail`) that the API then persists and serves
to the frontend.
"""
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.llm import get_minimax_service


_SYSTEM_PROMPT = """你是一位资深【行业情报分析师】，帮助 B2B 销售团队生成行业简报。

【任务】
根据用户给出的【行业】+【关键词】，生成一份简报（行业概况、近期动态、对销售的启示）。

【要求】
1. 全部用中文输出。
2. 5-10 条结构化 news items。每条必须有：title / source / source_level / summary / date / relevance (0-1)。
3. source_level 取值：L1（权威官方）/L2（权威媒体）/L3（行业垂直媒体）/L4（社交舆情）。
4. date 用 ISO 格式 YYYY-MM-DD；如果不确定，写"近一周"或"近一月"。
5. relevance 是 0-1 浮点，表示与用户给出的【行业+关键词】的相关度。
6. summary 是 2-3 句简洁事实陈述（不要形容词堆砌）。
7. 全部 5-8 条 key_takeaways：给销售可立即采取的行动。
8. summary 是 1-2 段行业概况。
9. title 由你生成（包含行业名 + 日期）。
10. **只输出合法 JSON**，不要任何解释、markdown 代码块标记、额外文字。

【输出 JSON 结构】
{
  "title": "行业名 行业动态 (YYYY-MM-DD)",
  "summary": "1-2 段行业概况...",
  "items": [
    {"title": "...", "source": "...", "source_level": "L2", "summary": "...", "date": "2026-06-01", "relevance": 0.85}
  ],
  "key_takeaways": ["...", "..."]
}"""


def _normalize_items(raw_items: Any) -> List[Dict[str, Any]]:
    """Coerce LLM output items into the documented shape, dropping junk rows."""
    out: List[Dict[str, Any]] = []
    if not isinstance(raw_items, list):
        return out
    for it in raw_items:
        if not isinstance(it, dict):
            continue
        title = (it.get("title") or "").strip()
        if not title:
            continue
        try:
            relevance = float(it.get("relevance") or 0.0)
        except (TypeError, ValueError):
            relevance = 0.0
        relevance = max(0.0, min(1.0, relevance))
        out.append({
            "title": title,
            "source": (it.get("source") or "").strip(),
            "source_level": (it.get("source_level") or "L3").strip().upper(),
            "summary": (it.get("summary") or "").strip(),
            "date": (it.get("date") or "").strip(),
            "relevance": relevance,
        })
    # Keep at most 10 items, sorted by relevance
    out.sort(key=lambda x: x["relevance"], reverse=True)
    return out[:10]


def _parse_json_safely(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON extraction from LLM output that may have wrappers
    (think blocks, markdown fences, trailing commas, etc.).
    """
    if not text:
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Strip code fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()
    json_match = re.search(r"\{[\s\S]*\}", text)
    if not json_match:
        return None
    candidate = json_match.group(0)
    # First try: as-is
    try:
        return json.loads(candidate)
    except Exception:
        pass
    # Second try: remove control chars + trailing commas
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", candidate)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        return None


async def generate_brief(industry: str,
                        keywords: Optional[str] = None,
                        title: Optional[str] = None) -> Dict[str, Any]:
    """Ask the LLM to produce a structured industry brief.

    Returns a dict matching `schemas.practice.BriefDetail`.
    """
    minimax = get_minimax_service()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    user_prompt_parts = [
        f"行业: {industry.strip()}",
        f"关键词: {(keywords or '').strip() or '不限'}",
        f"今日: {today}",
        "请生成简报。",
    ]
    user_prompt = "\n".join(user_prompt_parts)
    response = await minimax.chat(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
        max_tokens=2000,
    )
    data = _parse_json_safely(response or "")
    if not data:
        # Build a minimal fallback so the API still returns a useful object.
        return {
            "title": title or f"{industry} 行业动态 ({today})",
            "industry": industry,
            "keywords": keywords or "",
            "summary": f"关于 {industry} 行业的人工简报生成失败，请稍后重试。",
            "items": [],
            "key_takeaways": [],
        }
    items = _normalize_items(data.get("items"))
    return {
        "title": (title or data.get("title") or f"{industry} 行业动态 ({today})").strip(),
        "industry": industry,
        "keywords": keywords or "",
        "summary": (data.get("summary") or "").strip(),
        "items": items,
        "key_takeaways": [str(x).strip() for x in (data.get("key_takeaways") or []) if str(x).strip()],
    }
