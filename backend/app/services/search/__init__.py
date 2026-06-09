"""
Search Service - 网络搜索（通过 MiniMax MCP 工具）
"""
import os
import httpx
import json


# MiniMax MCP search endpoint - 通过 MiniMax API proxy
MINIMAX_MCP_URL = os.getenv("MINIMAX_MCP_URL", "")


async def search_via_mcp(query: str, num_results: int = 5) -> list:
    """
    通过 MiniMax MCP 工具做网络搜索
    返回格式: [{"title": "...", "snippet": "...", "date": "..."}]
    """
    # 如果配置了 MCP URL，通过它代理
    if MINIMAX_MCP_URL:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    MINIMAX_MCP_URL,
                    json={"query": query, "num_results": num_results},
                    headers={"Content-Type": "application/json"}
                )
                if resp.status_code == 200:
                    return resp.json().get("results", [])
        except Exception as e:
            print(f"MCP search error: {e}")

    return []


async def format_search_context(query: str, num_results: int = 5) -> str:
    """
    获取搜索结果并格式化为上下文字符串
    """
    results = await search_via_mcp(query, num_results)
    if not results:
        return ""

    lines = ["\n\n【最新网络搜索结果】"]
    for r in results[:8]:
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
