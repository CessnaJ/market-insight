"""Database Models using SQLModel"""

from sqlmodel import SQLModel, Field
from datetime import datetime, date
from typing import Optional
import uuid
from sqlalchemy import Column, JSON


# ──── Portfolio Related ────
class StockPrice(SQLModel, table=True):
    """주식 가격 기록"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    ticker: str = Field(index=True)
    name: Optional[str] = None
    price: float
    change_pct: float
    volume: Optional[int] = None
    high: Optional[float] = None
    low: Optional[float] = None
    market: str = "KR"  # KR or US
    recorded_at: datetime = Field(default_factory=datetime.now)
    price_date: date = Field(default_factory=lambda: date.today(), index=True)


class PortfolioHolding(SQLModel, table=True):
    """포트폴리오 보유 종목"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    ticker: str = Field(index=True)
    name: str
    shares: float
    avg_price: float
    market: str = "KR"
    sector: Optional[str] = None
    thesis: Optional[str] = None  # 왜 이 종목을 샀는지
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Transaction(SQLModel, table=True):
    """매수/매도 기록"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    ticker: str
    action: str  # BUY, SELL
    shares: float
    price: float
    total_amount: float
    reason: Optional[str] = None
    transaction_date: date
    created_at: datetime = Field(default_factory=datetime.now)


# ──── Daily Snapshot ────
class DailySnapshot(SQLModel, table=True):
    """일별 포트폴리오 스냅샷"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    snapshot_date: date = Field(index=True, unique=True)
    total_value: float  # 총 평가액
    total_invested: float  # 총 투자원금
    total_pnl: float  # 총 손익
    total_pnl_pct: float  # 총 수익률
    cash_balance: float  # 예수금
    top_gainer: Optional[str] = None  # 오늘 최고 수익 종목
    top_loser: Optional[str] = None  # 오늘 최대 손실 종목
    holdings_json: Optional[str] = None  # 종목별 상세 JSON
    created_at: datetime = Field(default_factory=datetime.now)


# ──── Content Related ────
class ContentItem(SQLModel, table=True):
    """수집된 콘텐츠"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    source_type: str  # youtube, naver_blog, facebook, ai_chat
    source_name: str
    title: str
    url: Optional[str] = None
    content_preview: str  # 앞 2000자
    full_content_path: Optional[str] = None  # 전체 내용 파일 경로
    summary: Optional[str] = None  # LLM 요약
    key_tickers: Optional[str] = None  # 관련 종목 (JSON)
    key_topics: Optional[str] = None  # 핵심 토픽 (JSON)
    sentiment: Optional[str] = None  # bullish, bearish, neutral
    collected_at: datetime = Field(default_factory=datetime.now)
    published_at: Optional[datetime] = None


# ──── Primary Sources (Korean Securities Data) ────
class PrimarySource(SQLModel, table=True):
    """Primary data sources for Korean securities (EARNINGS_CALL, DART_FILING, IR_MATERIAL)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    ticker: str = Field(index=True)  # Stock ticker (e.g., "005930")
    company_name: Optional[str] = None  # Company name (e.g., "삼성전자")
    source_type: str = Field(index=True)  # 'EARNINGS_CALL', 'DART_FILING', 'IR_MATERIAL'
    title: str  # Title of the document
    published_at: datetime = Field(index=True)  # Publication date
    content: str  # Full text content
    authority_weight: float = Field(default=1.0)  # Primary=1.0, Secondary=0.4
    extra_metadata: Optional[str] = None  # Additional metadata as JSON string
    source_url: Optional[str] = None  # URL to original source
    file_path: Optional[str] = None  # Path to stored file (if applicable)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ──── Price Attribution (Temporal Signal Decomposition) ────
class PriceAttribution(SQLModel, table=True):
    """Price attribution analysis with temporal breakdown"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    ticker: str = Field(index=True)  # Stock ticker (e.g., "005930")
    company_name: Optional[str] = None  # Company name
    event_date: date = Field(index=True)  # Date of price event
    price_change_pct: float  # Price change percentage
    temporal_breakdown: Optional[str] = None  # JSON string of temporal breakdown
    ai_analysis_summary: Optional[str] = None  # AI-generated summary
    confidence_score: Optional[float] = None  # Overall confidence score (0.0-1.0)
    dominant_timeframe: Optional[str] = None  # 'short', 'medium', or 'long'
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ──── Thoughts/Memo ────
class Thought(SQLModel, table=True):
    """사용자 생각/메모"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    content: str
    thought_type: str  # market_view, stock_idea, risk_concern, ai_insight, content_note, general
    tags: Optional[str] = None  # JSON array
    related_tickers: Optional[str] = None  # JSON array
    confidence: Optional[int] = None  # 1-10, 내 확신도
    outcome: Optional[str] = None  # 나중에 회고할 때 결과
    created_at: datetime = Field(default_factory=datetime.now)


# ──── Daily Report ────
class DailyReport(SQLModel, table=True):
    """일일 리포트"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    report_date: date = Field(index=True)
    report_markdown: str
    portfolio_section: Optional[str] = None
    content_section: Optional[str] = None
    thought_section: Optional[str] = None
    ai_opinion: Optional[str] = None  # LLM의 종합 의견
    action_items: Optional[str] = None  # 확인해야 할 것들
    created_at: datetime = Field(default_factory=datetime.now)


# ──── Database Engine ────
def get_engine(database_url: str = "sqlite:///./data/sqlite/main.db"):
    """데이터베이스 엔진 생성"""
    return create_engine(database_url, echo=False)


def init_db(engine=None):
    """데이터베이스 초기화"""
    if engine is None:
        engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session(engine=None):
    """세션 생성"""
    if engine is None:
        engine = get_engine()
    with Session(engine) as session:
        yield session
