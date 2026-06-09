#!/usr/bin/env python3
"""
MCP search wrapper - calls minimax-coding-plan-mcp via stdio and outputs JSON result.
Usage: python mcp_search.py "search query"
"""
import sys
import json
import asyncio
import os

async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No query provided"}))
        return

    query = sys.argv[1]

    # Load .env
    env = dict(os.environ)
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    k, v = line.split('=', 1)
                    env[k] = v

    from mcp.client.stdio import StdioServerParameters, stdio_client
    from mcp.client.session import ClientSession

    params = StdioServerParameters(
        command="npx",
        args=["-y", "minimax-coding-plan-mcp", "search"],
        env=env
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("web_search", {"query": query})
            text = result.content[0].text if result.content else ""
            # Output raw text (will be captured by parent)
            print(text)

if __name__ == "__main__":
    asyncio.run(main())
