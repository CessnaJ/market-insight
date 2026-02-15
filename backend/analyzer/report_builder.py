"""Report Builder

Generates daily and weekly investment reports using LLM.
Aggregates portfolio data, thoughts, and collected content.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

from sqlmodel import Session, select

from storage.db import get_session, add_daily_report
from storage.models import (
    DailySnapshot, Thought, ContentItem, DailyReport,
    PortfolioHolding, Transaction
)
from analyzer.llm_router import get_llm_router
from storage.vector_store import VectorStore


class ReportBuilder:
    """
    Investment report builder using LLM

    Usage:
        builder = ReportBuilder()
        report = builder.generate_daily_report()
        report = builder.generate_weekly_report()
    """

    def __init__(self, config_path: str = "config/prompts.yaml"):
        """
        Initialize report builder

        Args:
            config_path: Path to prompts.yaml configuration file
        """
        self.config_path = Path(__file__).parent.parent / config_path
        self.prompts = self._load_prompts()
        self.llm = get_llm_router()
        self.vector_store = VectorStore()

    def _load_prompts(self) -> Dict[str, str]:
        """Load LLM prompts from configuration"""
        import yaml

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config.get("system", {})

    def _get_portfolio_summary(self, session: Session, target_date: date) -> Dict[str, Any]:
        """
        Get portfolio summary for target date

        Args:
            session: Database session
            target_date: Target date

        Returns:
            Portfolio summary dictionary
        """
        # Get holdings
        holdings = session.exec(select(PortfolioHolding)).all()

        # Get latest snapshot
        snapshot = session.exec(
            select(DailySnapshot)
            .where(DailySnapshot.date <= target_date)
            .order_by(DailySnapshot.date.desc())
        ).first()

        # Get recent transactions
        week_ago = target_date - timedelta(days=7)
        recent_transactions = session.exec(
            select(Transaction)
            .where(Transaction.date >= week_ago)
            .order_by(Transaction.date.desc())
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
                "date": snapshot.date if snapshot else None,
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
                    "date": t.date,
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
        """
        Get recent thoughts

        Args:
            session: Database session
            target_date: Target date
            days: Number of days to look back

        Returns:
            List of recent thoughts
        """
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
        """
        Get recent collected contents

        Args:
            session: Database session
            target_date: Target date
            days: Number of days to look back

        Returns:
            List of recent contents
        """
        start_date = target_date - timedelta(days=days)

        return session.exec(
            select(ContentItem)
            .where(ContentItem.collected_at >= datetime.combine(start_date, datetime.min.time()))
            .order_by(ContentItem.collected_at.desc())
        ).all()

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

    def _format_snapshots(self, snapshots: List[DailySnapshot]) -> str:
        """Format snapshots for weekly report"""
        lines = ["## 주간 포트폴리오 성과"]

        if not snapshots:
            lines.append("(스냅샷 데이터가 없습니다)")
            return "\n".join(lines)

        for s in snapshots:
            lines.append(
                f"\n### {s.date}\n"
                f"- 총 평가액: {s.total_value:,.0f}원\n"
                f"- 수익률: {s.total_pnl_pct:+.2f}%\n"
                f"- 최고 수익 종목: {s.top_gainer or '-'}\n"
                f"- 최대 손실 종목: {s.top_loser or '-'}"
            )

        return "\n".join(lines)

    def generate_daily_report(self, target_date: Optional[date] = None) -> DailyReport:
        """
        Generate daily investment report

        Args:
            target_date: Target date (defaults to today)

        Returns:
            Generated DailyReport object
        """
        if target_date is None:
            target_date = date.today()

        with next(get_session()) as session:
            # Gather data
            portfolio_summary = self._get_portfolio_summary(session, target_date)
            recent_thoughts = self._get_recent_thoughts(session, target_date, days=1)
            recent_contents = self._get_recent_contents(session, target_date, days=1)

            # Format data for LLM
            portfolio_text = self._format_portfolio_summary(portfolio_summary)
            contents_text = self._format_contents(recent_contents)
            thoughts_text = self._format_thoughts(recent_thoughts)

            # Build prompt
            user_prompt = self.prompts.get("daily_report", "").format(
                portfolio=portfolio_text,
                contents=contents_text,
                thoughts=thoughts_text,
            )

            system_prompt = self.prompts.get("system", {}).get("daily_report", "")

            # Generate report
            report_markdown = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            )

            # Create DailyReport
            report = DailyReport(
                date=target_date,
                report_markdown=report_markdown,
                portfolio_section=portfolio_text,
                content_section=contents_text,
                thought_section=thoughts_text,
            )

            # Save to database
            saved_report = add_daily_report(session, report)

            print(f"Generated daily report for {target_date}")

            return saved_report

    def generate_weekly_report(self, target_date: Optional[date] = None) -> DailyReport:
        """
        Generate weekly investment report

        Args:
            target_date: Target date (defaults to today)

        Returns:
            Generated DailyReport object
        """
        if target_date is None:
            target_date = date.today()

        with next(get_session()) as session:
            # Gather data
            start_date = target_date - timedelta(days=7)
            portfolio_summary = self._get_portfolio_summary(session, target_date)
            recent_thoughts = self._get_recent_thoughts(session, target_date, days=7)
            recent_contents = self._get_recent_contents(session, target_date, days=7)

            # Get snapshots
            snapshots = session.exec(
                select(DailySnapshot)
                .where(DailySnapshot.date >= start_date)
                .order_by(DailySnapshot.date.desc())
            ).all()

            # Search for similar past thoughts
            similar_past = []
            if recent_thoughts:
                for thought in recent_thoughts[:3]:
                    results = self.vector_store.search_similar_thoughts(
                        query=thought.content,
                        n=2,
                        filter_metadata={"thought_type": thought.thought_type}
                    )
                    similar_past.extend(results)

            # Format data for LLM
            snapshots_text = self._format_snapshots(snapshots)
            contents_text = self._format_contents(recent_contents)
            thoughts_text = self._format_thoughts(recent_thoughts)
            similar_past_text = "\n".join(
                [f"- {r['content']}" for r in similar_past[:5]]
            ) if similar_past else "(없음)"

            # Build prompt
            user_prompt = self.prompts.get("weekly_report", "").format(
                snapshots=snapshots_text,
                thoughts=thoughts_text,
                contents=contents_text,
                similar_past=similar_past_text,
            )

            system_prompt = self.prompts.get("system", {}).get("weekly_report", "")

            # Generate report
            report_markdown = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            )

            # Create DailyReport (using same table for weekly reports)
            report = DailyReport(
                date=target_date,
                report_markdown=f"# 주간 리포트 ({start_date} ~ {target_date})\n\n{report_markdown}",
                portfolio_section=snapshots_text,
                content_section=contents_text,
                thought_section=thoughts_text,
            )

            # Save to database
            saved_report = add_daily_report(session, report)

            print(f"Generated weekly report for {target_date}")

            return saved_report


# ──── Convenience Functions ────
def generate_daily_report(target_date: Optional[date] = None) -> DailyReport:
    """Quick daily report generation"""
    builder = ReportBuilder()
    return builder.generate_daily_report(target_date)


def generate_weekly_report(target_date: Optional[date] = None) -> DailyReport:
    """Quick weekly report generation"""
    builder = ReportBuilder()
    return builder.generate_weekly_report(target_date)
