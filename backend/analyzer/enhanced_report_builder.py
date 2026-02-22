"""Enhanced Report Builder

Generates comprehensive investment reports integrating:
- Primary sources (Sprint 1): DART filings, earnings calls
- Temporal signal decomposition (Sprint 2): Price event analysis
- Assumption tracking (Sprint 3): Investment assumptions and validation
- Parent-child indexing (Sprint 4): Weighted search with authority
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import logging

from sqlmodel import Session, select

from storage.db import get_session, add_daily_report
from storage.models import (
    DailySnapshot, Thought, ContentItem, DailyReport,
    PortfolioHolding, Transaction, PrimarySource,
    PriceAttribution, InvestmentAssumption
)
from analyzer.llm_router import get_llm_router
from storage.vector_store import VectorStore
from analyzer.temporal_decomposer import TemporalSignalDecomposer
from analyzer.assumption_extractor import AssumptionExtractor
from analyzer.weighted_search import WeightedSearch

logger = logging.getLogger(__name__)


class EnhancedReportBuilder:
    """
    Enhanced investment report builder integrating all sprint components

    Usage:
        builder = EnhancedReportBuilder()
        report = builder.generate_comprehensive_report()
        report = builder.generate_daily_report_with_analysis()
    """

    def __init__(self, config_path: str = "config/prompts.yaml"):
        """
        Initialize enhanced report builder

        Args:
            config_path: Path to prompts.yaml configuration file
        """
        self.config_path = Path(__file__).parent.parent / config_path
        self.prompts = self._load_prompts()
        self.llm = get_llm_router()
        self.vector_store = VectorStore()
        self.temporal_decomposer = TemporalSignalDecomposer()
        self.assumption_extractor = AssumptionExtractor()
        self.weighted_search = WeightedSearch()

    def _load_prompts(self) -> Dict[str, str]:
        """Load LLM prompts from configuration"""
        import yaml

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config.get("system", {})

    # ──── Data Gathering Methods ────

    def _get_portfolio_summary(self, session: Session, target_date: date) -> Dict[str, Any]:
        """Get portfolio summary for target date"""
        holdings = session.exec(select(PortfolioHolding)).all()

        snapshot = session.exec(
            select(DailySnapshot)
            .where(DailySnapshot.snapshot_date <= target_date)
            .order_by(DailySnapshot.snapshot_date.desc())
        ).first()

        week_ago = target_date - timedelta(days=7)
        recent_transactions = session.exec(
            select(Transaction)
            .where(Transaction.transaction_date >= week_ago)
            .order_by(Transaction.transaction_date.desc())
        ).all()

        return {
            "holdings": [
                {
                    "ticker": h.ticker,
                    "name": h.name,
                    "shares": h.shares,
                    "avg_price": h.avg_price,
                    "market": h.market,
                    "thesis": h.thesis,
                }
                for h in holdings
            ],
            "snapshot": {
                "date": snapshot.snapshot_date if snapshot else None,
                "total_value": snapshot.total_value if snapshot else 0,
                "total_invested": snapshot.total_invested if snapshot else 0,
                "total_pnl": snapshot.total_pnl if snapshot else 0,
                "total_pnl_pct": snapshot.total_pnl_pct if snapshot else 0,
                "cash_balance": snapshot.cash_balance if snapshot else 0,
            } if snapshot else None,
            "recent_transactions": [
                {
                    "ticker": t.ticker,
                    "action": t.action,
                    "shares": t.shares,
                    "price": t.price,
                    "total_amount": t.total_amount,
                    "reason": t.reason,
                    "date": t.transaction_date,
                }
                for t in recent_transactions
            ],
        }

    def _get_recent_thoughts(
        self,
        session: Session,
        target_date: date,
        days: int = 1
    ) -> List[Thought]:
        """Get recent thoughts"""
        start_date = target_date - timedelta(days=days)

        return session.exec(
            select(Thought)
            .where(Thought.created_at >= datetime.combine(start_date, datetime.min.time()))
            .order_by(Thought.created_at.desc())
        ).all()

    def _get_recent_contents(
        self,
        session: Session,
        target_date: date,
        days: int = 1
    ) -> List[ContentItem]:
        """Get recent collected contents"""
        start_date = target_date - timedelta(days=days)

        return session.exec(
            select(ContentItem)
            .where(ContentItem.collected_at >= datetime.combine(start_date, datetime.min.time()))
            .order_by(ContentItem.collected_at.desc())
        ).all()

    def _get_primary_sources(
        self,
        session: Session,
        target_date: date,
        days: int = 7,
        tickers: Optional[List[str]] = None
    ) -> List[PrimarySource]:
        """
        Get primary sources (Sprint 1)

        Args:
            session: Database session
            target_date: Target date
            days: Number of days to look back
            tickers: Optional list of tickers to filter

        Returns:
            List of primary sources
        """
        start_date = target_date - timedelta(days=days)

        query = select(PrimarySource).where(
            PrimarySource.published_at >= datetime.combine(start_date, datetime.min.time())
        )

        if tickers:
            query = query.where(PrimarySource.ticker.in_(tickers))

        return session.exec(query.order_by(PrimarySource.published_at.desc())).all()

    def _get_temporal_attributions(
        self,
        session: Session,
        target_date: date,
        days: int = 7,
        tickers: Optional[List[str]] = None
    ) -> List[PriceAttribution]:
        """
        Get temporal price attributions (Sprint 2)

        Args:
            session: Database session
            target_date: Target date
            days: Number of days to look back
            tickers: Optional list of tickers to filter

        Returns:
            List of price attributions
        """
        start_date = target_date - timedelta(days=days)

        query = select(PriceAttribution).where(
            PriceAttribution.event_date >= start_date
        )

        if tickers:
            query = query.where(PriceAttribution.ticker.in_(tickers))

        return session.exec(query.order_by(PriceAttribution.event_date.desc())).all()

    def _get_investment_assumptions(
        self,
        session: Session,
        target_date: date,
        tickers: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> List[InvestmentAssumption]:
        """
        Get investment assumptions (Sprint 3)

        Args:
            session: Database session
            target_date: Target date
            tickers: Optional list of tickers to filter
            status: Optional status filter (PENDING, VERIFIED, FAILED)

        Returns:
            List of investment assumptions
        """
        query = select(InvestmentAssumption)

        if tickers:
            query = query.where(InvestmentAssumption.ticker.in_(tickers))

        if status:
            query = query.where(InvestmentAssumption.status == status)

        return session.exec(query.order_by(InvestmentAssumption.created_at.desc())).all()

    # ──── Formatting Methods ────

    def _format_portfolio_summary(self, summary: Dict[str, Any]) -> str:
        """Format portfolio summary for LLM prompt"""
        lines = ["## 포트폴리오 현황"]

        if summary["snapshot"]:
            s = summary["snapshot"]
            lines.append(f"- 총 평가액: {s['total_value']:,.0f}원")
            lines.append(f"- 총 투자원금: {s['total_invested']:,.0f}원")
            lines.append(f"- 총 손익: {s['total_pnl']:,.0f}원 ({s['total_pnl_pct']:+.2f}%)")
            lines.append(f"- 예수금: {s['cash_balance']:,.0f}원")

        if summary["holdings"]:
            lines.append("\n### 보유 종목")
            for h in summary["holdings"]:
                lines.append(f"- {h['name']} ({h['ticker']}): {h['shares']}주")

        if summary["recent_transactions"]:
            lines.append("\n### 최근 매매")
            for t in summary["recent_transactions"]:
                action = "매수" if t["action"] == "BUY" else "매도"
                lines.append(
                    f"- {t['date']} {action} {t['ticker']} {t['shares']}주 "
                    f"@ {t['price']:,.0f}원"
                )

        return "\n".join(lines)

    def _format_contents(self, contents: List[ContentItem]) -> str:
        """Format contents for LLM prompt"""
        lines = ["## 오늘 수집된 콘텐츠 요약"]

        if not contents:
            lines.append("(수집된 콘텐츠가 없습니다)")
            return "\n".join(lines)

        for i, content in enumerate(contents[:10], 1):
            source_name = content.source_name or content.source_type
            lines.append(f"\n### {i}. {content.title}")
            lines.append(f"- 출처: {source_name}")
            lines.append(f"- URL: {content.url}")
            if content.summary:
                lines.append(f"- 요약: {content.summary}")
            if content.key_tickers:
                tickers = json.loads(content.key_tickers)
                if tickers:
                    lines.append(f"- 관련 종목: {', '.join(tickers)}")

        return "\n".join(lines)

    def _format_thoughts(self, thoughts: List[Thought]) -> str:
        """Format thoughts for LLM prompt"""
        lines = ["## 오늘 내가 기록한 생각들"]

        if not thoughts:
            lines.append("(기록된 생각이 없습니다)")
            return "\n".join(lines)

        for i, thought in enumerate(thoughts, 1):
            thought_type = thought.thought_type
            lines.append(f"\n### {i}. [{thought_type}]")
            lines.append(thought.content)
            if thought.related_tickers:
                tickers = json.loads(thought.related_tickers)
                if tickers:
                    lines.append(f"- 관련 종목: {', '.join(tickers)}")

        return "\n".join(lines)

    def _format_primary_sources(self, sources: List[PrimarySource]) -> str:
        """
        Format primary sources for LLM prompt (Sprint 1)

        Args:
            sources: List of primary sources

        Returns:
            Formatted string
        """
        lines = ["## 1차 데이터 소스 (공시, 실적발표)"]

        if not sources:
            lines.append("(1차 데이터가 없습니다)")
            return "\n".join(lines)

        for i, source in enumerate(sources[:10], 1):
            lines.append(f"\n### {i}. {source.title}")
            lines.append(f"- 종목: {source.company_name} ({source.ticker})")
            lines.append(f"- 유형: {source.source_type}")
            lines.append(f"- 공시일: {source.published_at.strftime('%Y-%m-%d')}")
            lines.append(f"- 권중: {source.authority_weight}")
            if source.source_url:
                lines.append(f"- URL: {source.source_url}")

            # Add preview of content
            content_preview = source.content[:500]
            if len(source.content) > 500:
                content_preview += "..."
            lines.append(f"- 내용 미리보기: {content_preview}")

        return "\n".join(lines)

    def _format_temporal_attributions(self, attributions: List[PriceAttribution]) -> str:
        """
        Format temporal price attributions for LLM prompt (Sprint 2)

        Args:
            attributions: List of price attributions

        Returns:
            Formatted string
        """
        lines = ["## 시계열 가격 분석 (가격 변동 원인 분석)"]

        if not attributions:
            lines.append("(시계열 분석 데이터가 없습니다)")
            return "\n".join(lines)

        for i, attr in enumerate(attributions[:10], 1):
            lines.append(f"\n### {i}. {attr.company_name} ({attr.ticker})")
            lines.append(f"- 일자: {attr.event_date}")
            lines.append(f"- 가격 변동: {attr.price_change_pct:+.2f}%")
            lines.append(f"- 주요 시간대: {attr.dominant_timeframe or 'N/A'}")
            lines.append(f"- 신뢰도: {attr.confidence_score or 0:.2f}")

            if attr.temporal_breakdown:
                try:
                    breakdown = json.loads(attr.temporal_breakdown)
                    lines.append("- 시간대별 분석:")
                    if breakdown.get("short_term"):
                        lines.append(f"  * 단기: {breakdown['short_term']}")
                    if breakdown.get("medium_term"):
                        lines.append(f"  * 중기: {breakdown['medium_term']}")
                    if breakdown.get("long_term"):
                        lines.append(f"  * 장기: {breakdown['long_term']}")
                except json.JSONDecodeError:
                    pass

            if attr.ai_analysis_summary:
                lines.append(f"- AI 분석 요약: {attr.ai_analysis_summary[:300]}")

        return "\n".join(lines)

    def _format_investment_assumptions(self, assumptions: List[InvestmentAssumption]) -> str:
        """
        Format investment assumptions for LLM prompt (Sprint 3)

        Args:
            assumptions: List of investment assumptions

        Returns:
            Formatted string
        """
        lines = ["## 투자 가정 (Assumptions)"]

        if not assumptions:
            lines.append("(투자 가정이 없습니다)")
            return "\n".join(lines)

        # Group by status
        pending = [a for a in assumptions if a.status == "PENDING"]
        verified = [a for a in assumptions if a.status == "VERIFIED"]
        failed = [a for a in assumptions if a.status == "FAILED"]

        if pending:
            lines.append("\n### 검증 대기 중")
            for i, a in enumerate(pending[:5], 1):
                lines.append(f"{i}. {a.company_name} ({a.ticker})")
                lines.append(f"   - 가정: {a.assumption_text}")
                lines.append(f"   - 카테고리: {a.assumption_category}")
                lines.append(f"   - 시간대: {a.time_horizon}")
                lines.append(f"   - 예상값: {a.predicted_value or 'N/A'}")
                lines.append(f"   - 검증일: {a.verification_date or 'N/A'}")

        if verified:
            lines.append(f"\n### 검증 완료 (정답) - {len(verified)}개")
            for i, a in enumerate(verified[:3], 1):
                lines.append(f"{i}. {a.company_name} ({a.ticker})")
                lines.append(f"   - 가정: {a.assumption_text}")
                lines.append(f"   - 예상: {a.predicted_value} → 실제: {a.actual_value}")

        if failed:
            lines.append(f"\n### 검증 완료 (오답) - {len(failed)}개")
            for i, a in enumerate(failed[:3], 1):
                lines.append(f"{i}. {a.company_name} ({a.ticker})")
                lines.append(f"   - 가정: {a.assumption_text}")
                lines.append(f"   - 예상: {a.predicted_value} → 실제: {a.actual_value}")

        return "\n".join(lines)

    def _format_search_results(self, query: str, results: List[Dict]) -> str:
        """
        Format weighted search results for LLM prompt (Sprint 4)

        Args:
            query: Search query
            results: List of search results

        Returns:
            Formatted string
        """
        lines = [f"## 가중치 검색 결과: '{query}'"]

        if not results:
            lines.append("(검색 결과가 없습니다)")
            return "\n".join(lines)

        for i, r in enumerate(results[:5], 1):
            lines.append(f"\n### {i}. 점수: {r['score']:.3f}")
            lines.append(f"- 출처 유형: {r['source_type']}")
            lines.append(f"- 권중: {r['authority_weight']}")
            lines.append(f"- 내용: {r['content'][:300]}")

        return "\n".join(lines)

    # ──── Report Generation Methods ────

    def generate_comprehensive_report(
        self,
        target_date: Optional[date] = None,
        tickers: Optional[List[str]] = None
    ) -> DailyReport:
        """
        Generate comprehensive investment report integrating all sprint components

        Args:
            target_date: Target date (defaults to today)
            tickers: Optional list of tickers to focus on

        Returns:
            Generated DailyReport object
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"Generating comprehensive report for {target_date}")

        with next(get_session()) as session:
            # Gather all data
            portfolio_summary = self._get_portfolio_summary(session, target_date)
            recent_thoughts = self._get_recent_thoughts(session, target_date, days=7)
            recent_contents = self._get_recent_contents(session, target_date, days=7)
            primary_sources = self._get_primary_sources(session, target_date, days=30, tickers=tickers)
            temporal_attributions = self._get_temporal_attributions(session, target_date, days=30, tickers=tickers)
            investment_assumptions = self._get_investment_assumptions(session, target_date, tickers=tickers)

            # Format data for LLM
            portfolio_text = self._format_portfolio_summary(portfolio_summary)
            contents_text = self._format_contents(recent_contents)
            thoughts_text = self._format_thoughts(recent_thoughts)
            primary_sources_text = self._format_primary_sources(primary_sources)
            temporal_text = self._format_temporal_attributions(temporal_attributions)
            assumptions_text = self._format_investment_assumptions(investment_assumptions)

            # Build comprehensive prompt
            user_prompt = self.prompts.get("comprehensive_report", "").format(
                portfolio=portfolio_text,
                contents=contents_text,
                thoughts=thoughts_text,
                primary_sources=primary_sources_text,
                temporal_analysis=temporal_text,
                assumptions=assumptions_text,
                date=target_date.strftime("%Y-%m-%d"),
            )

            system_prompt = self.prompts.get("system", {}).get("comprehensive_report", "")

            # Generate report
            report_markdown = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            )

            # Create DailyReport
            report = DailyReport(
                report_date=target_date,
                report_markdown=f"# 종합 투자 리포트 ({target_date})\n\n{report_markdown}",
                portfolio_section=portfolio_text,
                content_section=contents_text,
                thought_section=thoughts_text,
            )

            # Save to database
            saved_report = add_daily_report(session, report)

            logger.info(f"Generated comprehensive report for {target_date}")

            return saved_report

    def generate_daily_report_with_analysis(
        self,
        target_date: Optional[date] = None
    ) -> DailyReport:
        """
        Generate daily report with temporal analysis and assumptions

        Args:
            target_date: Target date (defaults to today)

        Returns:
            Generated DailyReport object
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"Generating daily report with analysis for {target_date}")

        with next(get_session()) as session:
            # Gather data
            portfolio_summary = self._get_portfolio_summary(session, target_date)
            recent_thoughts = self._get_recent_thoughts(session, target_date, days=1)
            recent_contents = self._get_recent_contents(session, target_date, days=1)
            primary_sources = self._get_primary_sources(session, target_date, days=7)
            temporal_attributions = self._get_temporal_attributions(session, target_date, days=7)
            investment_assumptions = self._get_investment_assumptions(session, target_date, status="PENDING")

            # Format data for LLM
            portfolio_text = self._format_portfolio_summary(portfolio_summary)
            contents_text = self._format_contents(recent_contents)
            thoughts_text = self._format_thoughts(recent_thoughts)
            primary_sources_text = self._format_primary_sources(primary_sources)
            temporal_text = self._format_temporal_attributions(temporal_attributions)
            assumptions_text = self._format_investment_assumptions(investment_assumptions)

            # Build prompt
            user_prompt = self.prompts.get("daily_report_enhanced", "").format(
                portfolio=portfolio_text,
                contents=contents_text,
                thoughts=thoughts_text,
                primary_sources=primary_sources_text,
                temporal_analysis=temporal_text,
                assumptions=assumptions_text,
            )

            system_prompt = self.prompts.get("system", {}).get("daily_report_enhanced", "")

            # Generate report
            report_markdown = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            )

            # Create DailyReport
            report = DailyReport(
                report_date=target_date,
                report_markdown=report_markdown,
                portfolio_section=portfolio_text,
                content_section=contents_text,
                thought_section=thoughts_text,
            )

            # Save to database
            saved_report = add_daily_report(session, report)

            logger.info(f"Generated daily report with analysis for {target_date}")

            return saved_report

    def generate_asset_report(
        self,
        ticker: str,
        target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Generate asset-specific report with all integrated data

        Args:
            ticker: Stock ticker
            target_date: Target date (defaults to today)

        Returns:
            Dictionary containing asset report data
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"Generating asset report for {ticker} on {target_date}")

        with next(get_session()) as session:
            # Get portfolio holding info
            holding = session.exec(
                select(PortfolioHolding).where(PortfolioHolding.ticker == ticker)
            ).first()

            # Gather asset-specific data
            primary_sources = self._get_primary_sources(session, target_date, days=90, tickers=[ticker])
            temporal_attributions = self._get_temporal_attributions(session, target_date, days=90, tickers=[ticker])
            investment_assumptions = self._get_investment_assumptions(session, target_date, tickers=[ticker])

            # Search for relevant content using weighted search
            search_results = self.weighted_search.search(
                query=ticker,
                limit=10,
                source_type_filter="PRIMARY"
            )

            return {
                "ticker": ticker,
                "company_name": holding.company_name if holding else None,
                "holding": {
                    "shares": holding.shares if holding else 0,
                    "avg_price": holding.avg_price if holding else 0,
                    "thesis": holding.thesis if holding else None,
                } if holding else None,
                "primary_sources": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "source_type": s.source_type,
                        "published_at": s.published_at.isoformat(),
                        "authority_weight": s.authority_weight,
                    }
                    for s in primary_sources[:10]
                ],
                "temporal_attributions": [
                    {
                        "id": a.id,
                        "event_date": a.event_date.isoformat(),
                        "price_change_pct": a.price_change_pct,
                        "dominant_timeframe": a.dominant_timeframe,
                        "confidence_score": a.confidence_score,
                        "ai_analysis_summary": a.ai_analysis_summary,
                    }
                    for a in temporal_attributions[:10]
                ],
                "investment_assumptions": [
                    {
                        "id": a.id,
                        "assumption_text": a.assumption_text,
                        "assumption_category": a.assumption_category,
                        "time_horizon": a.time_horizon,
                        "predicted_value": a.predicted_value,
                        "status": a.status,
                        "is_correct": a.is_correct,
                        "actual_value": a.actual_value,
                    }
                    for a in investment_assumptions[:10]
                ],
                "search_results": search_results[:5],
                "generated_at": datetime.now().isoformat(),
            }


# ──── Convenience Functions ────
def generate_comprehensive_report(target_date: Optional[date] = None, tickers: Optional[List[str]] = None) -> DailyReport:
    """Quick comprehensive report generation"""
    builder = EnhancedReportBuilder()
    return builder.generate_comprehensive_report(target_date, tickers)


def generate_daily_report_with_analysis(target_date: Optional[date] = None) -> DailyReport:
    """Quick daily report with analysis generation"""
    builder = EnhancedReportBuilder()
    return builder.generate_daily_report_with_analysis(target_date)


def generate_asset_report(ticker: str, target_date: Optional[date] = None) -> Dict[str, Any]:
    """Quick asset report generation"""
    builder = EnhancedReportBuilder()
    return builder.generate_asset_report(ticker, target_date)
