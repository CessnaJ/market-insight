"""Database Connection and Utilities (PostgreSQL + pgvector)"""

import os
from datetime import datetime, date
from pathlib import Path
from sqlmodel import Session, create_engine, select
from storage.models import (
    StockPrice, PortfolioHolding, Transaction, DailySnapshot,
    ContentItem, Thought, DailyReport, init_db
)
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application Settings"""
    # PostgreSQL connection string (with pgvector support)
    # Format: postgresql+psycopg://user:password@host:port/database
    database_url: str = "postgresql+psycopg://investor:changeme@localhost:5432/market_insight"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Create PostgreSQL engine with pgvector support
engine = create_engine(settings.database_url, echo=False)


def get_session():
    """Get database session"""
    with Session(engine) as session:
        yield session


def init_database():
    """Initialize database tables"""
    init_db(engine)


# ──── Portfolio Operations ────
def get_portfolio_holdings(session: Session) -> list[PortfolioHolding]:
    """Get all portfolio holdings"""
    return session.exec(select(PortfolioHolding)).all()


def get_or_create_holding(session: Session, ticker: str, name: str, market: str = "KR") -> PortfolioHolding:
    """Get or create portfolio holding"""
    holding = session.exec(
        select(PortfolioHolding).where(PortfolioHolding.ticker == ticker)
    ).first()
    if not holding:
        holding = PortfolioHolding(ticker=ticker, name=name, market=market, shares=0, avg_price=0)
        session.add(holding)
        session.commit()
        session.refresh(holding)
    return holding


def update_holding(session: Session, ticker: str, shares: float, avg_price: float) -> PortfolioHolding:
    """Update portfolio holding"""
    holding = session.exec(
        select(PortfolioHolding).where(PortfolioHolding.ticker == ticker)
    ).first()
    if holding:
        holding.shares = shares
        holding.avg_price = avg_price
        holding.updated_at = datetime.now()
        session.add(holding)
        session.commit()
        session.refresh(holding)
    return holding


def add_transaction(session: Session, transaction: Transaction) -> Transaction:
    """Add transaction"""
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def get_latest_stock_price(session: Session, ticker: str) -> StockPrice | None:
    """Get latest stock price for ticker"""
    return session.exec(
        select(StockPrice)
        .where(StockPrice.ticker == ticker)
        .order_by(StockPrice.recorded_at.desc())
    ).first()


def add_stock_price(session: Session, price: StockPrice) -> StockPrice:
    """Add stock price"""
    session.add(price)
    session.commit()
    session.refresh(price)
    return price


# ──── Thought Operations ────
def add_thought(session: Session, thought: Thought) -> Thought:
    """Add thought"""
    session.add(thought)
    session.commit()
    session.refresh(thought)
    return thought


def get_recent_thoughts(session: Session, limit: int = 10) -> list[Thought]:
    """Get recent thoughts"""
    return session.exec(
        select(Thought)
        .order_by(Thought.created_at.desc())
        .limit(limit)
    ).all()


def get_thoughts_by_ticker(session: Session, ticker: str) -> list[Thought]:
    """Get thoughts related to ticker"""
    return session.exec(
        select(Thought).where(Thought.related_tickers.contains(ticker))
    ).all()


# ──── Content Operations ────
def add_content(session: Session, content: ContentItem) -> ContentItem:
    """Add content"""
    session.add(content)
    session.commit()
    session.refresh(content)
    return content


def get_recent_contents(session: Session, limit: int = 10) -> list[ContentItem]:
    """Get recent contents"""
    return session.exec(
        select(ContentItem)
        .order_by(ContentItem.collected_at.desc())
        .limit(limit)
    ).all()


# ──── Daily Snapshot Operations ────
def get_daily_snapshot(session: Session, date: date) -> DailySnapshot | None:
    """Get daily snapshot for date"""
    return session.exec(
        select(DailySnapshot).where(DailySnapshot.date == date)
    ).first()


def add_daily_snapshot(session: Session, snapshot: DailySnapshot) -> DailySnapshot:
    """Add daily snapshot"""
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def get_recent_snapshots(session: Session, days: int = 30) -> list[DailySnapshot]:
    """Get recent daily snapshots"""
    return session.exec(
        select(DailySnapshot)
        .order_by(DailySnapshot.date.desc())
        .limit(days)
    ).all()


# ──── Daily Report Operations ────
def get_latest_daily_report(session: Session) -> DailyReport | None:
    """Get latest daily report"""
    return session.exec(
        select(DailyReport)
        .order_by(DailyReport.date.desc())
    ).first()


def add_daily_report(session: Session, report: DailyReport) -> DailyReport:
    """Add daily report"""
    session.add(report)
    session.commit()
    session.refresh(report)
    return report
