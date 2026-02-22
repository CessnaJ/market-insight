"""Context Gatherer for Temporal Signal Decomposition

Collects and assembles context data for price attribution analysis:
- Macro data (interest rates, exchange rates)
- Recent reports (earnings calls, DART filings)
- Market sentiment indicators
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from sqlmodel import Session, select
from storage.db import get_session
from storage.models import PrimarySource, StockPrice

logger = logging.getLogger(__name__)


class ContextGatherer:
    """
    Gathers context data for temporal signal decomposition analysis
    
    Usage:
        gatherer = ContextGatherer()
        context = gatherer.gather_context("005930", date(2024, 1, 15))
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize Context Gatherer
        
        Args:
            session: Database session (creates new if not provided)
        """
        self.session = session
        self._session_created = False
        
        if self.session is None:
            self.session = next(get_session())
            self._session_created = True

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session if created"""
        if self._session_created and self.session:
            self.session.close()

    def gather_context(
        self,
        ticker: str,
        event_date: date,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gather comprehensive context for price event analysis
        
        Args:
            ticker: Stock ticker symbol
            event_date: Date of price event
            company_name: Optional company name
            
        Returns:
            Dictionary containing all context data
        """
        logger.info(f"Gathering context for {ticker} on {event_date}")
        
        context = {
            "ticker": ticker,
            "company_name": company_name,
            "event_date": event_date,
            "macro_context": self._get_macro_context(event_date),
            "supply_demand_data": self._get_supply_demand_data(ticker, event_date),
            "recent_news": self._get_recent_news(ticker, event_date),
            "sentiment_indicators": self._get_sentiment_indicators(ticker, event_date),
            "earnings_revision": self._get_earnings_revision(ticker, event_date),
            "sector_rotation": self._get_sector_rotation(ticker, event_date),
            "recent_earnings": self._get_recent_earnings(ticker, event_date),
            "analyst_opinions": self._get_analyst_opinions(ticker, event_date),
            "structural_competitiveness": self._get_structural_competitiveness(ticker),
            "market_share": self._get_market_share(ticker),
            "industry_structure": self._get_industry_structure(ticker),
            "innovation": self._get_innovation(ticker),
        }
        
        return context

    def _get_macro_context(self, event_date: date) -> str:
        """
        Get macro economic context
        
        Args:
            event_date: Date of event
            
        Returns:
            Macro context description
        """
        # TODO: Integrate with actual macro data sources
        # For now, return placeholder with structure
        
        # Typical macro indicators for Korean market:
        # - KOSPI index level
        # - KOSDAQ index level
        # - US Treasury yields (10-year)
        # - USD/KRW exchange rate
        # - Fed policy rate
        
        context = """
        ## 매크로 환경 (자동 수집 예정)
        
        ### 금리
        - 미국 국채 10년물: [데이터 필요]
        - 한국 국채 10년물: [데이터 필요]
        - 기준금리 (한국은행): [데이터 필요]
        
        ### 환율
        - 원/달러 환율: [데이터 필요]
        - 원/엔 환율: [데이터 필요]
        
        ### 지수
        - KOSPI: [데이터 필요]
        - KOSDAQ: [데이터 필요]
        - S&P 500: [데이터 필요]
        
        ### 해외 변수
        - WTI 원유: [데이터 필요]
        - 금 가격: [데이터 필요]
        """
        
        return context

    def _get_supply_demand_data(self, ticker: str, event_date: date) -> str:
        """
        Get supply and demand data for a stock
        
        Args:
            ticker: Stock ticker
            event_date: Date of event
            
        Returns:
            Supply demand data description
        """
        # TODO: Integrate with actual supply/demand data sources
        # For now, return placeholder with structure
        
        data = f"""
        ## 수급 데이터 - {ticker} (자동 수집 예정)
        
        ### 최근 5일 수급 추이
        - 외국인: [순매수/순매도 금액]
        - 기관: [순매수/순매도 금액]
        - 개인: [순매수/순매도 금액]
        
        ### 공매도 현황
        - 공매도 잔고: [잔고량]
        - 공매도 비율: [비율]
        
        ### 프로그램 매매
        - 프로그램 순매수: [금액]
        """
        
        return data

    def _get_recent_news(self, ticker: str, event_date: date) -> str:
        """
        Get recent news and filings for a stock
        
        Args:
            ticker: Stock ticker
            event_date: Date of event
            
        Returns:
            Recent news description
        """
        # Get recent DART filings from database
        start_date = event_date - timedelta(days=7)
        
        try:
            filings = self.session.exec(
                select(PrimarySource)
                .where(PrimarySource.ticker == ticker)
                .where(PrimarySource.source_type == "DART_FILING")
                .where(PrimarySource.published_at >= datetime.combine(start_date, datetime.min.time()))
                .where(PrimarySource.published_at <= datetime.combine(event_date, datetime.max.time()))
                .order_by(PrimarySource.published_at.desc())
                .limit(5)
            ).all()
            
            if filings:
                news_text = "## 최근 공시 (최근 7일)\n\n"
                for filing in filings:
                    news_text += f"- {filing.title}\n"
                    news_text += f"  일자: {filing.published_at.strftime('%Y-%m-%d')}\n"
                    if filing.content:
                        preview = filing.content[:200] + "..." if len(filing.content) > 200 else filing.content
                        news_text += f"  요약: {preview}\n\n"
                return news_text
            else:
                return "## 최근 공시 (최근 7일)\n\n데이터 없음"
                
        except Exception as e:
            logger.error(f"Error fetching recent news for {ticker}: {e}")
            return "## 최근 공시 (최근 7일)\n\n데이터 조회 실패"

    def _get_sentiment_indicators(self, ticker: str, event_date: date) -> str:
        """
        Get market sentiment indicators
        
        Args:
            ticker: Stock ticker
            event_date: Date of event
            
        Returns:
            Sentiment indicators description
        """
        # TODO: Integrate with actual sentiment data sources
        # For now, return placeholder with structure
        
        indicators = f"""
        ## 시장 심리 지표 - {ticker} (자동 수집 예정)
        
        ### 기술적 지표
        - RSI (14일): [값]
        - MACD: [값]
        - 이동평균선 (20일/60일): [값]
        
        ### 투자자 심리
        - 외국인 보유 비중: [비율]
        - 기관 보유 비중: [비율]
        - 공매도 비율: [비율]
        """
        
        return indicators

    def _get_earnings_revision(self, ticker: str, event_date: date) -> str:
        """
        Get earnings revision trend
        
        Args:
            ticker: Stock ticker
            event_date: Date of event
            
        Returns:
            Earnings revision description
        """
        # TODO: Integrate with actual earnings revision data sources
        # For now, return placeholder with structure
        
        revision = f"""
        ## 실적 리비전 동향 - {ticker} (자동 수집 예정)
        
        ### 최근 3개월 실적 리비전
        - FY24 예상 EPS: [이전값] → [현재값]
        - FY25 예상 EPS: [이전값] → [현재값]
        - 리비전 트렌드: 상향/하향/유지
        
        ### 주요 리비전 요인
        - [요인 1]
        - [요인 2]
        """
        
        return revision

    def _get_sector_rotation(self, ticker: str, event_date: date) -> str:
        """
        Get sector rotation information
        
        Args:
            ticker: Stock ticker
            event_date: Date of event
            
        Returns:
            Sector rotation description
        """
        # TODO: Integrate with actual sector data sources
        # For now, return placeholder with structure
        
        rotation = """
        ## 섹터 로테이션 (자동 수집 예정)
        
        ### 최근 섹터 성과
        - 반도체: [수익률]
        - 자동차: [수익률]
        - 바이오: [수익률]
        - IT: [수익률]
        
        ### 자금 흐름
        - 섹터별 자금 유입/유출: [데이터]
        """
        
        return rotation

    def _get_recent_earnings(self, ticker: str, event_date: date) -> str:
        """
        Get recent earnings call data
        
        Args:
            ticker: Stock ticker
            event_date: Date of event
            
        Returns:
            Recent earnings description
        """
        # Get recent earnings calls from database
        start_date = event_date - timedelta(days=90)
        
        try:
            earnings_calls = self.session.exec(
                select(PrimarySource)
                .where(PrimarySource.ticker == ticker)
                .where(PrimarySource.source_type == "EARNINGS_CALL")
                .where(PrimarySource.published_at >= datetime.combine(start_date, datetime.min.time()))
                .where(PrimarySource.published_at <= datetime.combine(event_date, datetime.max.time()))
                .order_by(PrimarySource.published_at.desc())
                .limit(3)
            ).all()
            
            if earnings_calls:
                earnings_text = "## 최근 실적 발표 (최근 3개월)\n\n"
                for call in earnings_calls:
                    earnings_text += f"- {call.title}\n"
                    earnings_text += f"  일자: {call.published_at.strftime('%Y-%m-%d')}\n"
                    if call.content:
                        preview = call.content[:300] + "..." if len(call.content) > 300 else call.content
                        earnings_text += f"  요약: {preview}\n\n"
                return earnings_text
            else:
                return "## 최근 실적 발표 (최근 3개월)\n\n데이터 없음"
                
        except Exception as e:
            logger.error(f"Error fetching recent earnings for {ticker}: {e}")
            return "## 최근 실적 발표 (최근 3개월)\n\n데이터 조회 실패"

    def _get_analyst_opinions(self, ticker: str, event_date: date) -> str:
        """
        Get analyst opinion changes
        
        Args:
            ticker: Stock ticker
            event_date: Date of event
            
        Returns:
            Analyst opinions description
        """
        # TODO: Integrate with actual analyst opinion data sources
        # For now, return placeholder with structure
        
        opinions = f"""
        ## 애널리스트 의견 변화 - {ticker} (자동 수집 예정)
        
        ### 최근 3개월 의견 변화
        - Buy: [이전] → [현재]
        - Hold: [이전] → [현재]
        - Sell: [이전] → [현재]
        
        ### 목표가
        - 평균 목표가: [금액]
        - 목표가 변화: [이전] → [현재]
        """
        
        return opinions

    def _get_structural_competitiveness(self, ticker: str) -> str:
        """
        Get structural competitiveness information
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Structural competitiveness description
        """
        # TODO: Integrate with actual competitiveness data sources
        # For now, return placeholder with structure
        
        competitiveness = f"""
        ## 구조적 경쟁력 - {ticker} (자동 수집 예정)
        
        ### 경쟁 우위 유형
        - 비용 우위: [평가]
        - 차별화: [평가]
        - 집중화: [평가]
        
        ### 지속 가능성
        - 진입 장벽: [높음/중간/낮음]
        - 규모의 경제: [높음/중간/낮음]
        - 기술 우위: [높음/중간/낮음]
        """
        
        return competitiveness

    def _get_market_share(self, ticker: str) -> str:
        """
        Get market share information
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Market share description
        """
        # TODO: Integrate with actual market share data sources
        # For now, return placeholder with structure
        
        share = f"""
        ## 시장 점유율 - {ticker} (자동 수집 예정)
        
        ### 글로벌 시장 점유율
        - 현재: [비율]
        - 전년 대비: [변화]
        
        ### 국내 시장 점유율
        - 현재: [비율]
        - 전년 대비: [변화]
        
        ### 경쟁 환경
        - 주요 경쟁사: [목록]
        - 시장 순위: [순위]
        """
        
        return share

    def _get_industry_structure(self, ticker: str) -> str:
        """
        Get industry structure information
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Industry structure description
        """
        # TODO: Integrate with actual industry structure data sources
        # For now, return placeholder with structure
        
        structure = f"""
        ## 산업 구조 변화 - {ticker} (자동 수집 예정)
        
        ### 산업 성장성
        - 연평균 성장률: [비율]
        - 성장 단계: [성장기/성숙기/쇠퇴기]
        
        ### 구조적 변화
        - 기술 변화: [설명]
        - 규제 변화: [설명]
        - 소비자 트렌드: [설명]
        """
        
        return structure

    def _get_innovation(self, ticker: str) -> str:
        """
        Get innovation information
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Innovation description
        """
        # TODO: Integrate with actual innovation data sources
        # For now, return placeholder with structure
        
        innovation = f"""
        ## 기술/사업 모델 혁신 - {ticker} (자동 수집 예정)
        
        ### R&D 투자
        - R&D 비용 비중: [비율]
        - R&D 인력: [인원]
        
        ### 주요 혁신
        - [혁신 1]
        - [혁신 2]
        
        ### 특허/지식재산권
        - 특허 보유 수: [개수]
        - 주요 특허: [목록]
        """
        
        return innovation


# Convenience function
def get_context_for_analysis(
    ticker: str,
    event_date: date,
    company_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick function to get context for analysis
    
    Args:
        ticker: Stock ticker
        event_date: Date of event
        company_name: Optional company name
        
    Returns:
        Context dictionary
    """
    with ContextGatherer() as gatherer:
        return gatherer.gather_context(ticker, event_date, company_name)
