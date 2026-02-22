"""Sprint 5 Integration Tests

End-to-end tests for integrated report builder and all sprint components.
"""

import pytest
from datetime import date, datetime
from sqlmodel import Session, select

from analyzer.enhanced_report_builder import EnhancedReportBuilder
from storage.models import (
    DailyReport, PrimarySource, PriceAttribution,
    InvestmentAssumption, PortfolioHolding
)
from storage.db import get_session, add_daily_report


class TestEnhancedReportBuilder:
    """Test Enhanced Report Builder integration"""

    def test_initialization(self):
        """Test enhanced report builder initialization"""
        builder = EnhancedReportBuilder()
        assert builder.llm is not None
        assert builder.vector_store is not None
        assert builder.temporal_decomposer is not None
        assert builder.assumption_extractor is not None
        assert builder.weighted_search is not None

    def test_get_portfolio_summary(self):
        """Test portfolio summary gathering"""
        builder = EnhancedReportBuilder()
        with next(get_session()) as session:
            summary = builder._get_portfolio_summary(session, date.today())
            assert "holdings" in summary
            assert "snapshot" in summary
            assert "recent_transactions" in summary

    def test_get_primary_sources(self):
        """Test primary sources gathering"""
        builder = EnhancedReportBuilder()
        with next(get_session()) as session:
            sources = builder._get_primary_sources(session, date.today(), days=30)
            assert isinstance(sources, list)

    def test_get_temporal_attributions(self):
        """Test temporal attributions gathering"""
        builder = EnhancedReportBuilder()
        with next(get_session()) as session:
            attributions = builder._get_temporal_attributions(session, date.today(), days=30)
            assert isinstance(attributions, list)

    def test_get_investment_assumptions(self):
        """Test investment assumptions gathering"""
        builder = EnhancedReportBuilder()
        with next(get_session()) as session:
            assumptions = builder._get_investment_assumptions(session, date.today())
            assert isinstance(assumptions, list)

    def test_format_primary_sources(self):
        """Test primary sources formatting"""
        builder = EnhancedReportBuilder()
        sources = [
            PrimarySource(
                id="1",
                ticker="005930",
                company_name="삼성전자",
                source_type="DART_FILING",
                title="Test Filing",
                published_at=datetime.now(),
                content="Test content",
                authority_weight=1.0
            )
        ]
        formatted = builder._format_primary_sources(sources)
        assert "1차 데이터 소스" in formatted
        assert "삼성전자" in formatted

    def test_format_temporal_attributions(self):
        """Test temporal attributions formatting"""
        builder = EnhancedReportBuilder()
        import json
        attributions = [
            PriceAttribution(
                id="1",
                ticker="005930",
                company_name="삼성전자",
                event_date=date.today(),
                price_change_pct=5.0,
                temporal_breakdown=json.dumps({
                    "short_term": "단기 요인",
                    "medium_term": "중기 요인",
                    "long_term": "장기 요인"
                }),
                ai_analysis_summary="AI 분석",
                confidence_score=0.8,
                dominant_timeframe="short"
            )
        ]
        formatted = builder._format_temporal_attributions(attributions)
        assert "시계열 가격 분석" in formatted
        assert "삼성전자" in formatted

    def test_format_investment_assumptions(self):
        """Test investment assumptions formatting"""
        builder = EnhancedReportBuilder()
        assumptions = [
            InvestmentAssumption(
                id="1",
                ticker="005930",
                company_name="삼성전자",
                assumption_text="HBM 매출 1조 달성",
                assumption_category="REVENUE",
                time_horizon="SHORT",
                predicted_value="1조",
                status="PENDING",
                model_confidence_at_generation=0.8
            )
        ]
        formatted = builder._format_investment_assumptions(assumptions)
        assert "투자 가정" in formatted
        assert "HBM 매출 1조 달성" in formatted


class TestComprehensiveReportGeneration:
    """Test comprehensive report generation"""

    def test_generate_comprehensive_report(self):
        """Test comprehensive report generation"""
        builder = EnhancedReportBuilder()
        report = builder.generate_comprehensive_report()
        assert report is not None
        assert report.report_date is not None
        assert report.report_markdown is not None
        assert "종합 투자 리포트" in report.report_markdown

    def test_generate_daily_report_with_analysis(self):
        """Test enhanced daily report generation"""
        builder = EnhancedReportBuilder()
        report = builder.generate_daily_report_with_analysis()
        assert report is not None
        assert report.report_date is not None
        assert report.report_markdown is not None

    def test_generate_asset_report(self):
        """Test asset-specific report generation"""
        builder = EnhancedReportBuilder()
        report = builder.generate_asset_report("005930")
        assert report is not None
        assert report["ticker"] == "005930"
        assert "primary_sources" in report
        assert "temporal_attributions" in report
        assert "investment_assumptions" in report
        assert "search_results" in report


class TestIntegration:
    """End-to-end integration tests"""

    def test_full_report_workflow(self):
        """Test full report generation workflow"""
        # This test verifies that all components work together
        builder = EnhancedReportBuilder()

        # 1. Gather all data
        with next(get_session()) as session:
            portfolio_summary = builder._get_portfolio_summary(session, date.today())
            primary_sources = builder._get_primary_sources(session, date.today(), days=30)
            temporal_attributions = builder._get_temporal_attributions(session, date.today(), days=30)
            assumptions = builder._get_investment_assumptions(session, date.today())

        # 2. Verify data gathering
        assert isinstance(portfolio_summary, dict)
        assert isinstance(primary_sources, list)
        assert isinstance(temporal_attributions, list)
        assert isinstance(assumptions, list)

        # 3. Generate comprehensive report
        report = builder.generate_comprehensive_report()
        assert report is not None
        assert report.report_markdown is not None

    def test_data_consistency(self):
        """Test data consistency across components"""
        builder = EnhancedReportBuilder()

        with next(get_session()) as session:
            # Get data from different sources
            sources = builder._get_primary_sources(session, date.today(), days=30)
            attributions = builder._get_temporal_attributions(session, date.today(), days=30)
            assumptions = builder._get_investment_assumptions(session, date.today())

            # Verify data types
            for source in sources:
                assert isinstance(source, PrimarySource)
                assert source.ticker is not None

            for attr in attributions:
                assert isinstance(attr, PriceAttribution)
                assert attr.ticker is not None

            for assumption in assumptions:
                assert isinstance(assumption, InvestmentAssumption)
                assert assumption.ticker is not None


class TestPerformance:
    """Performance tests for Sprint 5"""

    def test_report_generation_performance(self):
        """Test report generation performance"""
        import time
        builder = EnhancedReportBuilder()

        start_time = time.time()
        report = builder.generate_comprehensive_report()
        end_time = time.time()

        generation_time = end_time - start_time
        assert report is not None
        # Report generation should complete within 60 seconds
        assert generation_time < 60, f"Report generation took {generation_time:.2f}s, expected < 60s"

    def test_data_gathering_performance(self):
        """Test data gathering performance"""
        import time
        builder = EnhancedReportBuilder()

        with next(get_session()) as session:
            start_time = time.time()
            portfolio_summary = builder._get_portfolio_summary(session, date.today())
            primary_sources = builder._get_primary_sources(session, date.today(), days=30)
            temporal_attributions = builder._get_temporal_attributions(session, date.today(), days=30)
            assumptions = builder._get_investment_assumptions(session, date.today())
            end_time = time.time()

        gathering_time = end_time - start_time
        # Data gathering should complete within 10 seconds
        assert gathering_time < 10, f"Data gathering took {gathering_time:.2f}s, expected < 10s"


class TestErrorHandling:
    """Test error handling in integrated system"""

    def test_empty_database_handling(self):
        """Test handling of empty database"""
        builder = EnhancedReportBuilder()

        # Should not crash with empty data
        with next(get_session()) as session:
            sources = builder._get_primary_sources(session, date.today(), days=30)
            attributions = builder._get_temporal_attributions(session, date.today(), days=30)
            assumptions = builder._get_investment_assumptions(session, date.today())

        assert isinstance(sources, list)
        assert isinstance(attributions, list)
        assert isinstance(assumptions, list)

    def test_invalid_ticker_handling(self):
        """Test handling of invalid ticker"""
        builder = EnhancedReportBuilder()

        # Should handle invalid ticker gracefully
        report = builder.generate_asset_report("INVALID_TICKER")
        assert report is not None
        assert report["ticker"] == "INVALID_TICKER"
        # Should return empty lists for invalid ticker
        assert isinstance(report["primary_sources"], list)
        assert isinstance(report["temporal_attributions"], list)
        assert isinstance(report["investment_assumptions"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
