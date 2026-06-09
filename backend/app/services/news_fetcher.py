"""
News Fetcher Service — 真实新闻源（无需 API key）

多源聚合：
  1. Google News RSS (zh-CN, 任意行业关键词) — 主要源
  2. 36kr / 虎嗅 / IT之家 / 财新 — 中文科技/商业垂类

每条 news item 形如：
    {
      "title": "...",
      "url": "https://...",
      "source": "财新网",          # 来自 RSS <source>
      "source_level": "L2",        # 自动分级
      "published_at": "2026-06-08T09:30:00Z",  # ISO8601
      "raw_excerpt": "..."         # 1-2 句原文摘要
    }

未来可扩展：Tavily API（更高质量，需 key）。
"""
import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx


# 源域名 → L1-L4 分级
# L1 权威官方 / L2 权威媒体 / L3 行业垂直 / L4 社交舆情
SOURCE_LEVEL_MAP: Dict[str, str] = {
    # L1
    "people.com.cn": "L1", "xinhuanet.com": "L1", "gov.cn": "L1",
    # L2 主流权威
    "caixin.com": "L2", "reuters.com": "L2", "bloomberg.com": "L2",
    "ft.com": "L2", "wsj.com": "L2", "bbc.com": "L2",
    "peopleapp.com": "L2", "gmw.cn": "L2",
    # L3 行业垂直
    "36kr.com": "L3", "huxiu.com": "L3", "ithome.com": "L3",
    "leiphone.com": "L3", "pingwest.com": "L3", "donews.com": "L3",
    "csdn.net": "L3", "oschina.net": "L3", "infoq.cn": "L3",
    "cnbeta.com": "L3", "cnbeta.com.tw": "L3",
    "jiemian.com": "L3", "stcn.com": "L3", "yicai.com": "L3",
    "tmtpost.com": "L3", "sspai.com": "L3",
    # L4 社交
    "weibo.com": "L4", "zhihu.com": "L4", "bilibili.com": "L4",
}

# 行业 → 推荐 RSS 源（多源时优先用 Google News 关键词搜索）
INDUSTRY_RSS_HINTS: Dict[str, List[str]] = {
    "制造业": [
        "https://www.chinanews.com/rss/finance.xml",   # 财经/制造业公司新闻
        "https://www.tmtpost.com/rss.xml",              # 钛媒体 商业 / 制造业
        "https://www.leiphone.com/feed",                # 雷锋网 智能制造
        "https://www.36kr.com/feed",                    # 36kr B端 / 制造
    ],
    "科技软件": [
        "https://www.36kr.com/feed",
        "https://www.ithome.com/rss",
        "https://sspai.com/feed",
        "https://www.oschina.net/news/rss",
        "https://www.infoq.cn/feed.xml",
        "https://www.leiphone.com/feed",
    ],
    "金融": [
        "https://www.chinanews.com/rss/finance.xml",    # 中新网财经（30+ 条/天）
        "https://www.chinanews.com/rss/world.xml",      # 国际财经
        "https://www.tmtpost.com/rss.xml",
    ],
    "医疗健康": [
        "https://www.chinanews.com/rss/society.xml",    # 医药/健康常在社会版
        "https://www.tmtpost.com/rss.xml",
    ],
    "教育培训": [
        "https://www.chinanews.com/rss/society.xml",    # 教育常在社会版
        "https://www.36kr.com/feed",
    ],
    "零售电商": [
        "https://www.tmtpost.com/rss.xml",
        "https://www.36kr.com/feed",
        "https://www.chinanews.com/rss/finance.xml",
    ],
    "建筑工程": [
        "https://www.chinanews.com/rss/finance.xml",
        "https://www.chinanews.com/rss/society.xml",
    ],
    "物流运输": [
        "https://www.chinanews.com/rss/finance.xml",
        "https://www.tmtpost.com/rss.xml",
    ],
    "能源化工": [
        "https://www.chinanews.com/rss/finance.xml",
        "https://www.chinanews.com/rss/world.xml",
    ],
    "通用": [
        "https://www.chinanews.com/rss/finance.xml",
        "https://www.chinanews.com/rss/society.xml",
        "https://www.chinanews.com/rss/world.xml",
        "https://www.tmtpost.com/rss.xml",
        "https://www.36kr.com/feed",
    ],
}


def _classify_source(url: str) -> tuple[str, str]:
    """Return (source_name, source_level) from a URL."""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        # 去掉 www.
        host = re.sub(r"^www\.", "", host)
    except Exception:
        return ("未知来源", "L4")

    # 已知域名直接查表
    for domain, level in SOURCE_LEVEL_MAP.items():
        if host.endswith(domain):
            # 取 subdomain 作为来源名
            parts = host.split(".")
            return (parts[0] or host, level)

    # Google News 源 (e.g. news.google.com)
    if "google.com" in host:
        return ("Google News", "L3")

    # fallback: 用 host 第一段
    return (host.split(".")[0], "L3")


def _parse_pub_date(raw: str) -> Optional[str]:
    """Parse various RSS date formats to ISO8601."""
    if not raw:
        return None
    raw = raw.strip()
    # RFC 822 (RSS standard)
    try:
        dt = parsedate_to_datetime(raw)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    # ISO 8601 fallback
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _is_recent(iso_date: Optional[str], hours: int = 48) -> bool:
    """Check if a date is within the last N hours."""
    if not iso_date:
        return False
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt > datetime.now(timezone.utc) - timedelta(hours=hours)
    except Exception:
        return False


def _strip_html(text: str) -> str:
    """Remove HTML tags from RSS descriptions."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]


async def _fetch_rss(client: httpx.AsyncClient, url: str, timeout: int = 10) -> List[Dict[str, Any]]:
    """Fetch and parse a single RSS feed."""
    try:
        resp = await client.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"[news_fetcher] fetch failed: {url} -> {e}")
        return []

    # 跳过 HTML 响应（404 页面、redirect 后的网页）
    ctype = (resp.headers.get("content-type") or "").lower()
    body_head = resp.content[:200].lstrip().lower()
    if "html" in ctype or body_head.startswith(b"<!doctype html") or body_head.startswith(b"<html"):
        print(f"[news_fetcher] skip non-XML response: {url} (ctype={ctype})")
        return []

    try:
        # Google News RSS may have html entities; use bytes
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        print(f"[news_fetcher] parse failed: {url} -> {e}")
        return []

    items: List[Dict[str, Any]] = []
    # RSS 2.0: channel/item
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = (item.findtext("pubDate") or "")
        pub_iso = _parse_pub_date(pub_raw)
        desc = _strip_html(item.findtext("description") or "")

        # source 子元素 <source url="...">xinhua</source>
        source_el = item.find("source")
        source_name = source_el.text.strip() if source_el is not None and source_el.text else ""
        source_url = source_el.get("url", "") if source_el is not None else ""

        # 如果没 source 子元素，从 link 提取域名
        if not source_name and link:
            source_name, _ = _classify_source(link)
        source_level = _classify_source(source_url or link)[1] if (source_url or link) else "L3"

        if not title or not link:
            continue

        items.append({
            "title": title,
            "url": link,
            "source": source_name or "未知",
            "source_level": source_level,
            "published_at": pub_iso,
            "raw_excerpt": desc,
        })
    return items


async def fetch_industry_news(industry: str, keywords: Optional[str] = None,
                              hours: int = 48, max_items: int = 10) -> List[Dict[str, Any]]:
    """
    主入口：按行业 + 关键词从多源抓取近 48 小时新闻。

    1. 查 INDUSTRY_RSS_HINTS 拿推荐 RSS 源
    2. 用户提供的 keywords 暂作"主题过滤"——只保留标题/摘要中含关键词的条目
    3. 并发抓所有源，按 published_at 倒排
    4. 按 URL 去重，取最近 max_items 条
    5. 过滤掉太老的（超过 hours 小时）

    Returns: list of news items 形如：
        {
          "title": str,
          "url": str,
          "source": str,
          "source_level": "L1"|"L2"|"L3"|"L4",
          "published_at": ISO8601 str,
          "raw_excerpt": str (1-2 句)
        }
    """
    # 拿 RSS 源
    feed_urls = list(INDUSTRY_RSS_HINTS.get(industry, INDUSTRY_RSS_HINTS["通用"]))

    # 关键词过滤（如果不传，就不过滤）
    keyword_filter = (keywords or "").strip()
    keyword_filter_tokens = [t for t in keyword_filter.split() if t] if keyword_filter else []

    # 并发抓
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (SalesAgent/1.0) NewsBot"},
        timeout=10.0,
    ) as client:
        results = await asyncio.gather(
            *[_fetch_rss(client, url) for url in feed_urls],
            return_exceptions=True,
        )

    all_items: List[Dict[str, Any]] = []
    for r in results:
        if isinstance(r, Exception):
            continue
        all_items.extend(r)

    # 关键词过滤：用户给的关键词至少匹配一个 token；空则跳过此步
    if keyword_filter_tokens:
        def _match(it: Dict[str, Any]) -> bool:
            hay = (it.get("title", "") + " " + it.get("raw_excerpt", "")).lower()
            return any(tok.lower() in hay for tok in keyword_filter_tokens)
        all_items = [it for it in all_items if _match(it)]

    # 按 URL 去重
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for it in all_items:
        u = it.get("url", "")
        if not u or u in seen:
            continue
        seen.add(u)
        # 时效性过滤
        if not _is_recent(it.get("published_at"), hours=hours):
            continue
        deduped.append(it)

    # 按 published_at 倒排
    deduped.sort(key=lambda x: x.get("published_at") or "", reverse=True)

    return deduped[:max_items]
