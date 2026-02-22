"""Database Connection and Utilities (PostgreSQL + pgvector)"""

import os
from datetime import datetime, date
from pathlib import Path
from sqlmodel import Session, create_engine, select
from storage.models import (
    StockPrice, PortfolioHolding, Transaction, DailySnapshot,
    ContentItem, Thought, DailyReport, PrimarySource, PriceAttribution,
    InvestmentAssumption, init_db
)
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application Settings"""
    # PostgreSQL connection string (with pgvector support)
    # Format: postgresql+psycopg2://user:password@host:port/database
    database_url: str = "postgresql+psycopg2://investor:changeme@localhost:5432/market_insight"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra fields in .env file


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


# ──── Primary Source Operations ────
def add_primary_source(session: Session, primary_source: PrimarySource) -> PrimarySource:
    """Add primary source"""
    session.add(primary_source)
    session.commit()
    session.refresh(primary_source)
    return primary_source


def get_primary_sources_by_ticker(
    session: Session,
    ticker: str,
    source_type: str | None = None,
    limit: int = 50
) -> list[PrimarySource]:
    """Get primary sources for a ticker"""
    query = select(PrimarySource).where(PrimarySource.ticker == ticker)
    
    if source_type:
        query = query.where(PrimarySource.source_type == source_type)
    
    return session.exec(
        query.order_by(PrimarySource.published_at.desc()).limit(limit)
    ).all()


def get_primary_source_by_id(session: Session, source_id: str) -> PrimarySource | None:
    """Get primary source by ID"""
    return session.get(PrimarySource, source_id)


def get_recent_primary_sources(
    session: Session,
    source_type: str | None = None,
    limit: int = 20
) -> list[PrimarySource]:
    """Get recent primary sources"""
    query = select(PrimarySource)
    
    if source_type:
        query = query.where(PrimarySource.source_type == source_type)
    
    return session.exec(
        query.order_by(PrimarySource.published_at.desc()).limit(limit)
    ).all()


def delete_primary_source(session: Session, source_id: str) -> bool:
    """Delete primary source by ID"""
    source = session.get(PrimarySource, source_id)
    if source:
        session.delete(source)
        session.commit()
        return True
    return False


# ──── Price Attribution Operations ────
def add_price_attribution(session: Session, attribution: PriceAttribution) -> PriceAttribution:
    """Add price attribution analysis"""
    session.add(attribution)
    session.commit()
    session.refresh(attribution)
    return attribution


def get_price_attributions_by_ticker(
    session: Session,
    ticker: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50
) -> list[PriceAttribution]:
    """Get price attributions for a ticker"""
    query = select(PriceAttribution).where(PriceAttribution.ticker == ticker)
    
    if start_date:
        query = query.where(PriceAttribution.event_date >= start_date)
    if end_date:
        query = query.where(PriceAttribution.event_date <= end_date)
    
    return session.exec(
        query.order_by(PriceAttribution.event_date.desc()).limit(limit)
    ).all()


def get_price_attribution_by_id(session: Session, attribution_id: str) -> PriceAttribution | None:
    """Get price attribution by ID"""
    return session.get(PriceAttribution, attribution_id)


def get_price_attribution_by_date(
    session: Session,
    ticker: str,
    event_date: date
) -> PriceAttribution | None:
    """Get price attribution for a specific date"""
    return session.exec(
        select(PriceAttribution)
        .where(PriceAttribution.ticker == ticker)
        .where(PriceAttribution.event_date == event_date)
    ).first()


def update_price_attribution(
    session: Session,
    attribution_id: str,
    **kwargs
) -> PriceAttribution | None:
    """Update price attribution"""
    attribution = session.get(PriceAttribution, attribution_id)
    if attribution:
        for key, value in kwargs.items():
            if hasattr(attribution, key):
                setattr(attribution, key, value)
        attribution.updated_at = datetime.now()
        session.add(attribution)
        session.commit()
        session.refresh(attribution)
    return attribution


def delete_price_attribution(session: Session, attribution_id: str) -> bool:
    """Delete price attribution by ID"""
    attribution = session.get(PriceAttribution, attribution_id)
    if attribution:
        session.delete(attribution)
        session.commit()
        return True
    return False


# ──── Investment Assumption Operations (Sprint 3) ────
def add_investment_assumption(
    session: Session,
    assumption: InvestmentAssumption
) -> InvestmentAssumption:
    """Add investment assumption"""
    session.add(assumption)
    session.commit()
    session.refresh(assumption)
    return assumption


def get_assumptions_by_ticker(
    session: Session,
    ticker: str,
    category: str | None = None,
    status: str | None = None,
    limit: int = 50
) -> list[InvestmentAssumption]:
    """Get assumptions for a ticker"""
    query = select(InvestmentAssumption).where(InvestmentAssumption.ticker == ticker)
    
    if category:
        query = query.where(InvestmentAssumption.assumption_category == category)
    if status:
        query = query.where(InvestmentAssumption.status == status)
    
    return session.exec(
        query.order_by(InvestmentAssumption.created_at.desc()).limit(limit)
    ).all()


def get_pending_assumptions(
    session: Session,
    ticker: str | None = None,
    limit: int = 50
) -> list[InvestmentAssumption]:
    """Get pending assumptions for validation"""
    query = select(InvestmentAssumption).where(InvestmentAssumption.status == "PENDING")
    
    if ticker:
        query = query.where(InvestmentAssumption.ticker == ticker)
    
    # Only return assumptions where verification date is today or in the past
    today = date.today()
    query = query.where(
        (InvestmentAssumption.verification_date <= today) |
        (InvestmentAssumption.verification_date == None)
    )
    
    return session.exec(
        query.order_by(InvestmentAssumption.created_at.asc()).limit(limit)
    ).all()


def get_assumption_by_id(session: Session, assumption_id: str) -> InvestmentAssumption | None:
    """Get assumption by ID"""
    return session.get(InvestmentAssumption, assumption_id)


def validate_assumption(
    session: Session,
    assumption_id: str,
    actual_value: str,
    is_correct: bool,
    validation_source: str | None = None
) -> InvestmentAssumption | None:
    """Validate an assumption with actual data"""
    assumption = session.get(InvestmentAssumption, assumption_id)
    if assumption:
        assumption.actual_value = actual_value
        assumption.is_correct = is_correct
        assumption.validation_source = validation_source
        assumption.status = "VERIFIED" if is_correct else "FAILED"
        assumption.updated_at = datetime.now()
        session.add(assumption)
        session.commit()
        session.refresh(assumption)
    return assumption


def get_assumption_accuracy_stats(
    session: Session,
    ticker: str | None = None,
    category: str | None = None,
    time_horizon: str | None = None
) -> dict[str, Any]:
    """Get assumption accuracy statistics"""
    from typing import Any
    
    query = select(InvestmentAssumption).where(
        InvestmentAssumption.status.in_(["VERIFIED", "FAILED"])
    )
    
    if ticker:
        query = query.where(InvestmentAssumption.ticker == ticker)
    if category:
        query = query.where(InvestmentAssumption.assumption_category == category)
    if time_horizon:
        query = query.where(InvestmentAssumption.time_horizon == time_horizon)
    
    assumptions = session.exec(query).all()
    
    total = len(assumptions)
    if total == 0:
        return {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "accuracy": 0.0,
            "by_category": {},
            "by_time_horizon": {}
        }
    
    correct = sum(1 for a in assumptions if a.is_correct)
    incorrect = total - correct
    
    # Stats by category
    by_category = {}
    for cat in ["REVENUE", "MARGIN", "MACRO", "CAPACITY", "MARKET_SHARE"]:
        cat_assumptions = [a for a in assumptions if a.assumption_category == cat]
        if cat_assumptions:
            cat_correct = sum(1 for a in cat_assumptions if a.is_correct)
            by_category[cat] = {
                "total": len(cat_assumptions),
                "correct": cat_correct,
                "accuracy": cat_correct / len(cat_assumptions) if cat_assumptions else 0.0
            }
    
    # Stats by time horizon
    by_time_horizon = {}
    for horizon in ["SHORT", "MEDIUM", "LONG"]:
        horizon_assumptions = [a for a in assumptions if a.time_horizon == horizon]
        if horizon_assumptions:
            horizon_correct = sum(1 for a in horizon_assumptions if a.is_correct)
            by_time_horizon[horizon] = {
                "total": len(horizon_assumptions),
                "correct": horizon_correct,
                "accuracy": horizon_correct / len(horizon_assumptions) if horizon_assumptions else 0.0
            }
    
    return {
        "total": total,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": correct / total if total > 0 else 0.0,
        "by_category": by_category,
        "by_time_horizon": by_time_horizon
    }


def delete_assumption(session: Session, assumption_id: str) -> bool:
    """Delete assumption by ID"""
    assumption = session.get(InvestmentAssumption, assumption_id)
    if assumption:
        session.delete(assumption)
        session.commit()
        return True
    return False


def get_all_assumptions(
    session: Session,
    ticker: str | None = None,
    category: str | None = None,
    status: str | None = None,
    limit: int = 100
) -> list[InvestmentAssumption]:
    """Get all assumptions with optional filters"""
    query = select(InvestmentAssumption)
    
    if ticker:
        query = query.where(InvestmentAssumption.ticker == ticker)
    if category:
        query = query.where(InvestmentAssumption.assumption_category == category)
    if status:
        query = query.where(InvestmentAssumption.status == status)
    
    return session.exec(
        query.order_by(InvestmentAssumption.created_at.desc()).limit(limit)
    ).all()
