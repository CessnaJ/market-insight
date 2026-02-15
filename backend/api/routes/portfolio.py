"""Portfolio API Routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
from datetime import date

from storage.models import StockPrice, PortfolioHolding, Transaction, DailySnapshot
from storage.db import get_session, get_portfolio_holdings, get_latest_stock_price, add_transaction
from collector.stock_tracker import fetch_all_prices


router = APIRouter()


# ──── Portfolio Summary ────
@router.get("/summary")
async def get_portfolio_summary(session: Session = Depends(get_session)):
    """
    포트폴리오 요약 조회

    Returns:
        총 평가액, 총 수익률, 종목별 현황 등
    """
    holdings = get_portfolio_holdings(session)

    total_value = 0.0
    total_invested = 0.0
    holdings_data = []

    for holding in holdings:
        # 최신 가격 조회
        latest_price = get_latest_stock_price(session, holding.ticker)

        current_price = latest_price.price if latest_price else holding.avg_price
        current_value = current_price * holding.shares
        invested_value = holding.avg_price * holding.shares

        total_value += current_value
        total_invested += invested_value

        pnl = current_value - invested_value
        pnl_pct = (pnl / invested_value * 100) if invested_value > 0 else 0

        holdings_data.append({
            "ticker": holding.ticker,
            "name": holding.name,
            "shares": holding.shares,
            "avg_price": holding.avg_price,
            "current_price": current_price,
            "current_value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "market": holding.market,
            "sector": holding.sector
        })

    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    return {
        "total_value": total_value,
        "total_invested": total_invested,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "holdings": holdings_data,
        "cash_balance": 0.0  # TODO: 실제 예수금 계산
    }


# ──── Holdings ────
@router.get("/holdings")
async def get_holdings(session: Session = Depends(get_session)):
    """보유 종목 목록 조회"""
    holdings = get_portfolio_holdings(session)
    return {
        "holdings": [
            {
                "ticker": h.ticker,
                "name": h.name,
                "shares": h.shares,
                "avg_price": h.avg_price,
                "market": h.market,
                "sector": h.sector,
                "thesis": h.thesis
            }
            for h in holdings
        ]
    }


@router.post("/holdings")
async def create_holding(
    ticker: str,
    name: str,
    shares: float,
    avg_price: float,
    market: str = "KR",
    sector: Optional[str] = None,
    thesis: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """새 보유 종목 추가"""
    from storage.db import get_or_create_holding

    holding = get_or_create_holding(session, ticker, name, market)
    holding.shares = shares
    holding.avg_price = avg_price
    holding.sector = sector
    holding.thesis = thesis

    session.add(holding)
    session.commit()
    session.refresh(holding)

    return {"holding": holding}


@router.put("/holdings/{ticker}")
async def update_holding(
    ticker: str,
    shares: float,
    avg_price: float,
    session: Session = Depends(get_session)
):
    """보유 종목 업데이트"""
    from storage.db import update_holding

    holding = update_holding(session, ticker, shares, avg_price)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    return {"holding": holding}


# ──── Stock Prices ────
@router.get("/prices/{ticker}")
async def get_stock_price(ticker: str, session: Session = Depends(get_session)):
    """특정 종목의 최신 가격 조회"""
    price = get_latest_stock_price(session, ticker)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")

    return {
        "ticker": price.ticker,
        "name": price.name,
        "price": price.price,
        "change_pct": price.change_pct,
        "volume": price.volume,
        "high": price.high,
        "low": price.low,
        "market": price.market,
        "recorded_at": price.recorded_at
    }


@router.post("/prices/fetch")
async def fetch_prices():
    """모든 주식 가격 수집 (주기적 실행용)"""
    result = await fetch_all_prices()
    return result


# ──── Transactions ────
@router.post("/transactions")
async def create_transaction(
    ticker: str,
    action: str,  # BUY, SELL
    shares: float,
    price: float,
    reason: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """매수/매도 기록"""
    transaction = Transaction(
        ticker=ticker,
        action=action.upper(),
        shares=shares,
        price=price,
        total_amount=shares * price,
        reason=reason,
        date=date.today()
    )

    add_transaction(session, transaction)

    return {"transaction": transaction}


@router.get("/transactions")
async def get_transactions(
    ticker: Optional[str] = None,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """거래 내역 조회"""
    from sqlmodel import select

    query = select(Transaction)
    if ticker:
        query = query.where(Transaction.ticker == ticker)

    query = query.order_by(Transaction.date.desc()).limit(limit)

    transactions = session.exec(query).all()

    return {
        "transactions": [
            {
                "id": t.id,
                "ticker": t.ticker,
                "action": t.action,
                "shares": t.shares,
                "price": t.price,
                "total_amount": t.total_amount,
                "reason": t.reason,
                "date": t.date,
                "created_at": t.created_at
            }
            for t in transactions
        ]
    }


# ──── Daily Snapshot ────
@router.get("/snapshots")
async def get_snapshots(days: int = 30, session: Session = Depends(get_session)):
    """일별 스냅샷 조회"""
    from storage.db import get_recent_snapshots

    snapshots = get_recent_snapshots(session, days)

    return {
        "snapshots": [
            {
                "date": s.date,
                "total_value": s.total_value,
                "total_invested": s.total_invested,
                "total_pnl": s.total_pnl,
                "total_pnl_pct": s.total_pnl_pct,
                "cash_balance": s.cash_balance,
                "top_gainer": s.top_gainer,
                "top_loser": s.top_loser
            }
            for s in snapshots
        ]
    }
