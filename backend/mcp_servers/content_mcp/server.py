"""
Content MCP Server for Claude Desktop Integration

This MCP server provides tools for managing collected investment content:
- Get recent content from various sources
- Search content by semantic similarity
- Get content related to specific tickers
- Trigger content collection
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server import Server
from mcp.types import Tool, TextContent
from storage.db import (
    get_recent_contents,
)
from storage.vector_store import VectorStore
from sqlmodel import Session
from storage.db import engine

# Create MCP server instance
server = Server("content")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available content tools"""
    return [
        Tool(
            name="get_recent_contents",
            description="최근 수집된 콘텐츠 목록 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10}
                }
            }
        ),
        Tool(
            name="search_content",
            description="의미 기반 콘텐츠 검색",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색할 주제"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_content_stats",
            description="수집된 콘텐츠 통계 (총 개수, 소스별 분포)",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="search_by_source",
            description="특정 소스의 콘텐츠 검색",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_type": {
                        "type": "string",
                        "enum": ["youtube", "naver_blog", "facebook", "ai_chat"],
                        "description": "소스 유형"
                    },
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["source_type"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    with Session(engine) as session:
        if name == "get_recent_contents":
            return await _get_recent_contents(session, arguments)
        elif name == "search_content":
            return await _search_content(arguments)
        elif name == "get_content_stats":
            return await _get_content_stats()
        elif name == "search_by_source":
            return await _search_by_source(session, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _get_recent_contents(session: Session, args: dict[str, Any]) -> list[TextContent]:
    """Get recent contents"""
    limit = args.get("limit", 10)
    contents = get_recent_contents(session, limit)

    recent_contents = [
        {
            "id": c.id,
            "source_type": c.source_type,
            "source_name": c.source_name,
            "title": c.title,
            "url": c.url,
            "content_preview": c.content_preview[:500] + "..." if c.content_preview and len(c.content_preview) > 500 else c.content_preview,
            "summary": c.summary,
            "key_tickers": json.loads(c.key_tickers) if c.key_tickers else [],
            "key_topics": json.loads(c.key_topics) if c.key_topics else [],
            "sentiment": c.sentiment,
            "collected_at": c.collected_at.isoformat(),
            "published_at": c.published_at.isoformat() if c.published_at else None,
        }
        for c in contents
    ]

    return [TextContent(
        type="text",
        text=json.dumps(recent_contents, ensure_ascii=False, indent=2)
    )]


async def _search_content(args: dict[str, Any]) -> list[TextContent]:
    """Search content by semantic similarity"""
    vector_store = VectorStore()
    limit = args.get("limit", 10)

    results = vector_store.search_related_content(
        query=args["query"],
        n=limit
    )

    formatted_results = []
    for result in results:
        formatted_results.append({
            "id": result["id"],
            "content": result["content"],
            "metadata": result["metadata"],
            "relevance": 1 - result["distance"],
        })

    return [TextContent(
        type="text",
        text=json.dumps(formatted_results, ensure_ascii=False, indent=2)
    )]


async def _get_content_stats() -> list[TextContent]:
    """Get content statistics"""
    vector_store = VectorStore()

    stats = {
        "total_content": vector_store.get_content_count(),
        "total_thoughts": vector_store.get_thought_count(),
        "total_ai_chats": vector_store.get_ai_chat_count(),
    }

    return [TextContent(
        type="text",
        text=json.dumps(stats, ensure_ascii=False, indent=2)
    )]


async def _search_by_source(session: Session, args: dict[str, Any]) -> list[TextContent]:
    """Search content by source type"""
    source_type = args["source_type"]
    limit = args.get("limit", 10)

    # Get all contents and filter by source type
    from storage.db import ContentItem
    from sqlmodel import select

    contents = session.exec(
        select(ContentItem)
        .where(ContentItem.source_type == source_type)
        .order_by(ContentItem.collected_at.desc())
        .limit(limit)
    ).all()

    source_contents = [
        {
            "id": c.id,
            "source_type": c.source_type,
            "source_name": c.source_name,
            "title": c.title,
            "url": c.url,
            "content_preview": c.content_preview[:500] + "..." if c.content_preview and len(c.content_preview) > 500 else c.content_preview,
            "summary": c.summary,
            "key_tickers": json.loads(c.key_tickers) if c.key_tickers else [],
            "key_topics": json.loads(c.key_topics) if c.key_topics else [],
            "sentiment": c.sentiment,
            "collected_at": c.collected_at.isoformat(),
            "published_at": c.published_at.isoformat() if c.published_at else None,
        }
        for c in contents
    ]

    return [TextContent(
        type="text",
        text=json.dumps(source_contents, ensure_ascii=False, indent=2)
    )]


async def main():
    """Run MCP server"""
    from mcp.server.stdio import stdio_server
    await server.run(stdio_server())


if __name__ == "__main__":
    asyncio.run(main())
