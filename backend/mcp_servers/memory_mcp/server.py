"""
Memory MCP Server for Claude Desktop Integration

This MCP server provides tools for managing investment thoughts and memories:
- Log thoughts with classification
- Search past thoughts by semantic similarity
- Get thought timeline for specific topics
- Review past predictions and outcomes
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server import Server
from mcp.types import Tool, TextContent
from storage.db import (
    add_thought,
    get_recent_thoughts,
    get_thoughts_by_ticker,
)
from storage.vector_store import VectorStore
from storage.models import Thought
from sqlmodel import Session
from storage.db import engine
import uuid

# Create MCP server instance
server = Server("memory")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available memory tools"""
    return [
        Tool(
            name="log_thought",
            description="투자 관련 생각/인사이트 기록",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "생각 내용"},
                    "type": {
                        "type": "string",
                        "enum": ["market_view", "stock_idea", "risk_concern",
                                "ai_insight", "content_note", "general"]
                    },
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "관련 종목코드"
                    },
                    "confidence": {
                        "type": "integer",
                        "description": "확신도 1-10"
                    }
                },
                "required": ["content", "type"]
            }
        ),
        Tool(
            name="recall_thoughts",
            description="과거에 특정 주제에 대해 어떤 생각을 했는지 검색",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색할 주제"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_thought_timeline",
            description="특정 종목/주제에 대한 내 생각의 변화 타임라인",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목코드"},
                    "days": {"type": "integer", "default": 30}
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_recent_thoughts",
            description="최근 기록한 생각 목록 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10}
                }
            }
        ),
        Tool(
            name="search_by_ticker",
            description="특정 종목에 관련된 모든 생각 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목코드"}
                },
                "required": ["ticker"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    with Session(engine) as session:
        if name == "log_thought":
            return await _log_thought(session, arguments)
        elif name == "recall_thoughts":
            return await _recall_thoughts(arguments)
        elif name == "get_thought_timeline":
            return await _get_thought_timeline(session, arguments)
        elif name == "get_recent_thoughts":
            return await _get_recent_thoughts(session, arguments)
        elif name == "search_by_ticker":
            return await _search_by_ticker(session, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _log_thought(session: Session, args: dict[str, Any]) -> list[TextContent]:
    """Log a new thought"""
    thought_id = str(uuid.uuid4())

    thought = Thought(
        id=thought_id,
        content=args["content"],
        thought_type=args["type"],
        tags=json.dumps(args.get("tags", [])),
        related_tickers=json.dumps(args.get("tickers", [])),
        confidence=args.get("confidence"),
        outcome=None,
    )

    add_thought(session, thought)

    # Add to vector store for semantic search
    vector_store = VectorStore()
    vector_store.add_thought(
        thought_id=thought_id,
        content=args["content"],
        metadata={
            "type": args["type"],
            "tickers": args.get("tickers", []),
            "tags": args.get("tags", []),
            "created_at": datetime.now().isoformat(),
        }
    )

    return [TextContent(
        type="text",
        text=json.dumps({
            "message": "Thought logged successfully",
            "thought_id": thought_id,
            "content": args["content"],
            "type": args["type"],
        }, ensure_ascii=False, indent=2)
    )]


async def _recall_thoughts(args: dict[str, Any]) -> list[TextContent]:
    """Search past thoughts by semantic similarity"""
    vector_store = VectorStore()
    limit = args.get("limit", 5)

    results = vector_store.search_similar_thoughts(
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


async def _get_thought_timeline(session: Session, args: dict[str, Any]) -> list[TextContent]:
    """Get thought timeline for a specific ticker"""
    ticker = args["ticker"]
    days = args.get("days", 30)

    thoughts = get_thoughts_by_ticker(session, ticker)

    # Filter by date
    cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

    timeline = [
        {
            "id": t.id,
            "content": t.content,
            "type": t.thought_type,
            "tags": json.loads(t.tags) if t.tags else [],
            "related_tickers": json.loads(t.related_tickers) if t.related_tickers else [],
            "confidence": t.confidence,
            "outcome": t.outcome,
            "created_at": t.created_at.isoformat(),
        }
        for t in thoughts
        if t.created_at >= cutoff_date
    ]

    # Sort by creation date
    timeline.sort(key=lambda x: x["created_at"])

    return [TextContent(
        type="text",
        text=json.dumps(timeline, ensure_ascii=False, indent=2)
    )]


async def _get_recent_thoughts(session: Session, args: dict[str, Any]) -> list[TextContent]:
    """Get recent thoughts"""
    limit = args.get("limit", 10)
    thoughts = get_recent_thoughts(session, limit)

    recent_thoughts = [
        {
            "id": t.id,
            "content": t.content,
            "type": t.thought_type,
            "tags": json.loads(t.tags) if t.tags else [],
            "related_tickers": json.loads(t.related_tickers) if t.related_tickers else [],
            "confidence": t.confidence,
            "outcome": t.outcome,
            "created_at": t.created_at.isoformat(),
        }
        for t in thoughts
    ]

    return [TextContent(
        type="text",
        text=json.dumps(recent_thoughts, ensure_ascii=False, indent=2)
    )]


async def _search_by_ticker(session: Session, args: dict[str, Any]) -> list[TextContent]:
    """Search thoughts by ticker"""
    ticker = args["ticker"]
    thoughts = get_thoughts_by_ticker(session, ticker)

    ticker_thoughts = [
        {
            "id": t.id,
            "content": t.content,
            "type": t.thought_type,
            "tags": json.loads(t.tags) if t.tags else [],
            "related_tickers": json.loads(t.related_tickers) if t.related_tickers else [],
            "confidence": t.confidence,
            "outcome": t.outcome,
            "created_at": t.created_at.isoformat(),
        }
        for t in thoughts
    ]

    return [TextContent(
        type="text",
        text=json.dumps(ticker_thoughts, ensure_ascii=False, indent=2)
    )]


async def main():
    """Run MCP server"""
    from mcp.server.stdio import stdio_server
    await server.run(stdio_server())


if __name__ == "__main__":
    asyncio.run(main())
