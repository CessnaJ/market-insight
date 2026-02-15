"""
Portfolio MCP Server for Claude Desktop Integration

This MCP server provides tools for accessing portfolio data including:
- Portfolio summary and holdings
- Stock prices and history
- Transaction logging
- Portfolio snapshots
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
    get_portfolio_holdings,
    get_latest_stock_price,
    get_or_create_holding,
    update_holding,
    add_transaction,
    get_daily_snapshot,
    get_recent_snapshots,
)
from storage.models import Transaction
from sqlmodel import Session
from storage.db import engine
from datetime import date

# Create MCP server instance
server = Server("portfolio")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available portfolio tools"""
    return [
        Tool(
            name="get_portfolio_summary",
            description="현재 포트폴리오 요약 (총 평가액, 수익률, 종목별 현황)",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_stock_price",
            description="특정 종목의 현재가 및 내 보유 현황",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목코드"}
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_portfolio_history",
            description="포트폴리오 수익률 히스토리",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 30}
                }
            }
        ),
        Tool(
            name="log_transaction",
            description="매수/매도 기록",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "action": {"type": "string", "enum": ["BUY", "SELL"]},
                    "shares": {"type": "number"},
                    "price": {"type": "number"},
                    "reason": {"type": "string"}
                },
                "required": ["ticker", "action", "shares", "price"]
            }
        ),
        Tool(
            name="get_holdings",
            description="보유 종목 목록 조회",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    with Session(engine) as session:
        if name == "get_portfolio_summary":
            return await _get_portfolio_summary(session)
        elif name == "get_stock_price":
            return await _get_stock_price(session, arguments["ticker"])
        elif name == "get_portfolio_history":
            days = arguments.get("days", 30)
            return await _get_portfolio_history(session, days)
        elif name == "log_transaction":
            return await _log_transaction(session, arguments)
        elif name == "get_holdings":
            return await _get_holdings(session)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _get_portfolio_summary(session: Session) -> list[TextContent]:
    """Get portfolio summary"""
    holdings = get_portfolio_holdings(session)

    total_value = 0.0
    total_invested = 0.0
    holdings_list = []

    for holding in holdings:
        latest_price = get_latest_stock_price(session, holding.ticker)
        current_price = latest_price.price if latest_price else holding.avg_price

        current_value = holding.shares * current_price
        invested_value = holding.shares * holding.avg_price
        pnl = current_value - invested_value
        pnl_pct = (pnl / invested_value * 100) if invested_value > 0 else 0.0

        total_value += current_value
        total_invested += invested_value

        holdings_list.append({
            "ticker": holding.ticker,
            "name": holding.name,
            "shares": holding.shares,
            "avg_price": holding.avg_price,
            "current_price": current_price,
            "current_value": current_value,
            "invested_value": invested_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })

    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    summary = {
        "total_value": total_value,
        "total_invested": total_invested,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "holdings": holdings_list,
    }

    return [TextContent(type="text", text=json.dumps(summary, ensure_ascii=False, indent=2))]


async def _get_stock_price(session: Session, ticker: str) -> list[TextContent]:
    """Get stock price and holding info"""
    latest_price = get_latest_stock_price(session, ticker)
    holdings = get_portfolio_holdings(session)

    holding = next((h for h in holdings if h.ticker == ticker), None)

    result = {
        "ticker": ticker,
        "latest_price": latest_price.price if latest_price else None,
        "change_pct": latest_price.change_pct if latest_price else None,
        "volume": latest_price.volume if latest_price else None,
        "high": latest_price.high if latest_price else None,
        "low": latest_price.low if latest_price else None,
        "recorded_at": latest_price.recorded_at.isoformat() if latest_price else None,
        "holding": {
            "shares": holding.shares,
            "avg_price": holding.avg_price,
            "name": holding.name,
        } if holding else None,
    }

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _get_portfolio_history(session: Session, days: int) -> list[TextContent]:
    """Get portfolio history"""
    snapshots = get_recent_snapshots(session, days)

    history = [
        {
            "date": snapshot.date.isoformat(),
            "total_value": snapshot.total_value,
            "total_invested": snapshot.total_invested,
            "total_pnl": snapshot.total_pnl,
            "total_pnl_pct": snapshot.total_pnl_pct,
            "top_gainer": snapshot.top_gainer,
            "top_loser": snapshot.top_loser,
        }
        for snapshot in snapshots
    ]

    return [TextContent(type="text", text=json.dumps(history, ensure_ascii=False, indent=2))]


async def _log_transaction(session: Session, args: dict[str, Any]) -> list[TextContent]:
    """Log a transaction"""
    transaction = Transaction(
        ticker=args["ticker"],
        action=args["action"],
        shares=args["shares"],
        price=args["price"],
        total_amount=args["shares"] * args["price"],
        reason=args.get("reason"),
        date=date.today(),
    )

    add_transaction(session, transaction)

    # Update holding
    holding = get_or_create_holding(
        session,
        args["ticker"],
        args["ticker"],  # Use ticker as name for now
    )

    if args["action"] == "BUY":
        new_shares = holding.shares + args["shares"]
        new_avg = ((holding.shares * holding.avg_price) +
                   (args["shares"] * args["price"])) / new_shares
    else:  # SELL
        new_shares = holding.shares - args["shares"]
        new_avg = holding.avg_price

    update_holding(session, args["ticker"], new_shares, new_avg)

    return [TextContent(
        type="text",
        text=json.dumps({"message": "Transaction logged successfully", "transaction": {
            "ticker": transaction.ticker,
            "action": transaction.action,
            "shares": transaction.shares,
            "price": transaction.price,
            "total_amount": transaction.total_amount,
        }}, ensure_ascii=False, indent=2)
    )]


async def _get_holdings(session: Session) -> list[TextContent]:
    """Get all holdings"""
    holdings = get_portfolio_holdings(session)

    holdings_list = [
        {
            "ticker": h.ticker,
            "name": h.name,
            "shares": h.shares,
            "avg_price": h.avg_price,
            "market": h.market,
            "sector": h.sector,
            "thesis": h.thesis,
            "created_at": h.created_at.isoformat(),
        }
        for h in holdings
    ]

    return [TextContent(type="text", text=json.dumps(holdings_list, ensure_ascii=False, indent=2))]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server
    await server.run(stdio_server())


if __name__ == "__main__":
    asyncio.run(main())
