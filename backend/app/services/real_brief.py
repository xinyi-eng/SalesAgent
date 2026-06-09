"""
Real Brief Service — 简报生成 v2（基于真实新闻源，LLM 只写摘要）

数据流：
  1. news_fetcher.fetch_industry_news(industry, keywords)
     → 从 Google News RSS + 36kr/虎嗅/IT之家/财新 等公共 RSS 抓真实新闻
     → 返回 list[{title, url, source, source_level, published_at, raw_excerpt}]
  2. （可选）调 LLM 给每条新闻写 1-2 句事实摘要（限 token，绝不编造）
  3. 聚合 + 存 DB

与旧的 industry_brief.py 区别：
  - 旧版 LLM 完全幻觉，没有 URL
  - 新版 100% 真实 URL，LLM 仅做摘要润色
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.news_fetcher import fetch_industry_news
from app.services.llm import get_minimax_service


# 极简摘要 prompt — 只让 LLM 改写/压缩原文 excerpt，绝不编
_SUMMARY_PROMPT = """你是新闻摘要助手。任务：把下面这条新闻的 excerpt 压缩到 1-2 句中文事实陈述（30-60 字）。

**严格要求**：
- 只基于提供的 excerpt 改写，不许引入新信息
- 保留数字、人名、公司名等关键事实
- 1-2 句，不要超过 60 字
- 不许加"据悉""近日"等空话
- 输出纯文本，不要 markdown

新闻标题：{TITLE}
新闻原文摘要：{RAW}
"""


async def _summarize_one(title: str, raw_excerpt: str) -> str:
    """调 LLM 把 raw_excerpt 改写成 1-2 句事实摘要。失败时 fallback 到原文截取。"""
    if not raw_excerpt or len(raw_excerpt) < 20:
        return raw_excerpt or title

    try:
        minimax = get_minimax_service()
        prompt = _SUMMARY_PROMPT.format(TITLE=title, RAW=raw_excerpt[:500])
        result = await minimax.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=120,
        )
        # 简单清理
        result = result.strip().strip("「」""").strip()
        if 5 < len(result) < 200:
            return result
        return raw_excerpt[:120]
    except Exception as e:
        print(f"[real_brief] summarize failed: {e}")
        return raw_excerpt[:120]


async def generate_real_brief(
    industry: str,
    keywords: Optional[str] = None,
    max_news: int = 8,
    hours: int = 48,
) -> Dict[str, Any]:
    """
    主入口：从真实 RSS 抓新闻 → LLM 摘要润色 → 返回 dict（待存 DB）

    Returns:
        {
            "title": "...",
            "industry": "...",
            "keywords": "...",
            "summary": "..." (从 items 自动生成),
            "items": [{title, url, source, source_level, published_at, summary, raw_excerpt}],
            "key_takeaways": [...],  # 从 items 自动抽取
            "news_count": int,
            "brief_date": ISO str,
        }
    """
    print(f"[real_brief] fetching {industry} (keywords={keywords!r}, max={max_news}, hours={hours}h)")
    raw_items = await fetch_industry_news(
        industry=industry,
        keywords=keywords,
        hours=hours,
        max_items=max_news,
    )
    print(f"[real_brief] got {len(raw_items)} real news items from RSS")

    if not raw_items:
        return {
            "title": f"{industry} 行业动态（{_today_str()}）",
            "industry": industry,
            "keywords": keywords or "",
            "summary": f"近 {hours} 小时内未抓到 {industry} 行业新闻，请稍后重试或换个关键词。",
            "items": [],
            "key_takeaways": [],
            "news_count": 0,
            "brief_date": _today_str(),
        }

    # 并发 LLM 摘要（每条）
    summaries = await asyncio.gather(
        *[_summarize_one(it["title"], it.get("raw_excerpt", "")) for it in raw_items],
        return_exceptions=True,
    )
    items: List[Dict[str, Any]] = []
    for it, sm in zip(raw_items, summaries):
        summary_text = sm if isinstance(sm, str) and sm else (it.get("raw_excerpt", "")[:120] or it["title"])
        items.append({
            "title": it["title"],
            "url": it["url"],
            "source": it["source"],
            "source_level": it["source_level"],
            "published_at": it.get("published_at"),
            "summary": summary_text,
            "raw_excerpt": it.get("raw_excerpt", ""),
        })

    # 自动从 items 生成 key_takeaways（每条新闻一个"销售行动点"）
    key_takeaways = [
        f"📰 {it['source']} · {it['title'][:30]}{'…' if len(it['title'])>30 else ''} — 看看跟你客户有没有关系"
        for it in items[:3]
    ]

    return {
        "title": f"{industry} 行业动态（{_today_str()}）",
        "industry": industry,
        "keywords": keywords or "",
        "summary": _build_summary_text(items),
        "items": items,
        "key_takeaways": key_takeaways,
        "news_count": len(items),
        "brief_date": _today_str(),
    }


def _build_summary_text(items: List[Dict[str, Any]]) -> str:
    """从 items 生成 1-2 段行业概况（不调 LLM，纯模板）。"""
    if not items:
        return ""
    sources = sorted({it["source_level"] for it in items})
    src_str = "/".join(sources)
    return (
        f"共 {len(items)} 条近 48 小时内的 {items[0].get('industry', '')} 新闻，"
        f"来源层级：{src_str}。"
        f"点击每条新闻卡片可跳转原文核实。"
    )


def _today_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")
