"""Sprint 2 Tests: Temporal Signal Decomposition

Test cases for temporal signal decomposition and price attribution analysis.
"""

import pytest
from datetime import date, datetime
from sqlmodel import Session

from analyzer.temporal_decomposer import (
    TemporalSignalDecomposer,
    TemporalAnalysisResult,
    decompose_price_signal
)
from analyzer.context_gatherer import ContextGatherer, get_context_for_analysis
from storage.db import (
    get_session,
    add_price_attribution,
    get_price_attributions_by_ticker,
    get_price_attribution_by_date,
    delete_price_attribution
)
from storage.models import PriceAttribution, PrimarySource


# ──── Test Fixtures ────
@pytest.fixture
def session():
    """Database session fixture"""
    with next(get_session()) as session:
        yield session


@pytest.fixture
def sample_samsung_data(session: Session):
    """Create sample Samsung Electronics data"""
    # Create sample primary sources
    earnings_call = PrimarySource(
        ticker="005930",
        company_name="삼성전자",
        source_type="EARNINGS_CALL",
        title="2024년 1분기 실적 발표 콜",
        published_at=datetime(2024, 1, 15, 14, 0),
        content="삼성전자 2024년 1분기 실적 발표 콜 내용...",
        authority_weight=1.0
    )
    
    dart_filing = PrimarySource(
        ticker="005930",
        company_name="삼성전자",
        source_type="DART_FILING",
        title="반기보고서",
        published_at=datetime(2024, 2, 20, 9, 0),
        content="삼성전자 반기보고서 내용...",
        authority_weight=1.0
    )
    
    session.add(earnings_call)
    session.add(dart_filing)
    session.commit()
    
    return {
        "ticker": "005930",
        "company_name": "삼성전자",
        "earnings_call": earnings_call,
        "dart_filing": dart_filing
    }


# ──── Context Gatherer Tests ────
class TestContextGatherer:
    """Tests for ContextGatherer class"""
    
    def test_context_gatherer_initialization(self):
        """Test ContextGatherer initialization"""
        with ContextGatherer() as gatherer:
            assert gatherer.session is not None
    
    def test_gather_context_basic(self, sample_samsung_data):
        """Test basic context gathering"""
        with ContextGatherer() as gatherer:
            context = gatherer.gather_context(
                ticker="005930",
                event_date=date(2024, 1, 20),
                company_name="삼성전자"
            )
            
            assert context["ticker"] == "005930"
            assert context["company_name"] == "삼성전자"
            assert context["event_date"] == date(2024, 1, 20)
            assert "macro_context" in context
            assert "supply_demand_data" in context
            assert "recent_news" in context
            assert "sentiment_indicators" in context
    
    def test_gather_context_with_primary_sources(self, sample_samsung_data):
        """Test context gathering with primary sources"""
        with ContextGatherer() as gatherer:
            context = gatherer.gather_context(
                ticker="005930",
                event_date=date(2024, 2, 25),
                company_name="삼성전자"
            )
            
            # Should include recent news from primary sources
            recent_news = context["recent_news"]
            assert "삼성전자" in recent_news or "데이터 없음" in recent_news
    
    def test_convenience_function(self):
        """Test convenience function for context gathering"""
        context = get_context_for_analysis(
            ticker="005930",
            event_date=date(2024, 1, 20),
            company_name="삼성전자"
        )
        
        assert context["ticker"] == "005930"
        assert context["event_date"] == date(2024, 1, 20)


# ──── Temporal Signal Decomposer Tests ────
class TestTemporalSignalDecomposer:
    """Tests for TemporalSignalDecomposer class"""
    
    def test_decomposer_initialization(self):
        """Test TemporalSignalDecomposer initialization"""
        with TemporalSignalDecomposer() as decomposer:
            assert decomposer.llm_router is not None
            assert decomposer.session is not None
    
    def test_decompose_price_signal_basic(self):
        """Test basic price signal decomposition"""
        with TemporalSignalDecomposer() as decomposer:
            result = decomposer.decompose_price_signal(
                ticker="005930",
                company_name="삼성전자",
                event_date=date(2024, 1, 20),
                price_change_pct=3.5,
                save_to_db=False
            )
            
            assert isinstance(result, TemporalAnalysisResult)
            assert result.ticker == "005930"
            assert result.company_name == "삼성전자"
            assert result.event_date == date(2024, 1, 20)
            assert result.price_change_pct == 3.5
            assert "short_term_analysis" in result.to_dict()
            assert "medium_term_analysis" in result.to_dict()
            assert "long_term_analysis" in result.to_dict()
            assert "comprehensive_analysis" in result.to_dict()
    
    def test_decompose_price_signal_with_db_save(self, session: Session):
        """Test price signal decomposition with database save"""
        with TemporalSignalDecomposer(session=session) as decomposer:
            result = decomposer.decompose_price_signal(
                ticker="005930",
                company_name="삼성전자",
                event_date=date(2024, 1, 20),
                price_change_pct=3.5,
                save_to_db=True
            )
            
            # Verify it was saved to database
            saved = get_price_attribution_by_date(session, "005930", date(2024, 1, 20))
            assert saved is not None
            assert saved.ticker == "005930"
            assert saved.price_change_pct == 3.5
            
            # Cleanup
            delete_price_attribution(session, saved.id)
    
    def test_decompose_price_signal_without_company_name(self):
        """Test price signal decomposition without company name"""
        with TemporalSignalDecomposer() as decomposer:
            result = decomposer.decompose_price_signal(
                ticker="005930",
                event_date=date(2024, 1, 20),
                price_change_pct=-2.1,
                save_to_db=False
            )
            
            assert result.ticker == "005930"
            assert result.company_name is None
    
    def test_convenience_function(self):
        """Test convenience function for price signal decomposition"""
        result = decompose_price_signal(
            ticker="005930",
            event_date=date(2024, 1, 20),
            price_change_pct=3.5,
            company_name="삼성전자",
            save_to_db=False
        )
        
        assert isinstance(result, TemporalAnalysisResult)
        assert result.ticker == "005930"


# ──── Database Operations Tests ────
class TestPriceAttributionDatabase:
    """Tests for price attribution database operations"""
    
    def test_add_price_attribution(self, session: Session):
        """Test adding price attribution to database"""
        attribution = PriceAttribution(
            ticker="005930",
            company_name="삼성전자",
            event_date=date(2024, 1, 20),
            price_change_pct=3.5,
            temporal_breakdown='{"test": "data"}',
            ai_analysis_summary="Test summary",
            confidence_score=0.8,
            dominant_timeframe="medium"
        )
        
        saved = add_price_attribution(session, attribution)
        
        assert saved.id is not None
        assert saved.ticker == "005930"
        assert saved.price_change_pct == 3.5
        
        # Cleanup
        delete_price_attribution(session, saved.id)
    
    def test_get_price_attributions_by_ticker(self, session: Session):
        """Test getting price attributions by ticker"""
        # Add sample attributions
        attribution1 = PriceAttribution(
            ticker="005930",
            company_name="삼성전자",
            event_date=date(2024, 1, 15),
            price_change_pct=2.5,
            temporal_breakdown='{"test": "data1"}',
            ai_analysis_summary="Test summary 1",
            confidence_score=0.7,
            dominant_timeframe="short"
        )
        
        attribution2 = PriceAttribution(
            ticker="005930",
            company_name="삼성전자",
            event_date=date(2024, 1, 20),
            price_change_pct=3.5,
            temporal_breakdown='{"test": "data2"}',
            ai_analysis_summary="Test summary 2",
            confidence_score=0.8,
            dominant_timeframe="medium"
        )
        
        saved1 = add_price_attribution(session, attribution1)
        saved2 = add_price_attribution(session, attribution2)
        
        # Get attributions
        attributions = get_price_attributions_by_ticker(
            session=session,
            ticker="005930",
            limit=10
        )
        
        assert len(attributions) >= 2
        assert all(a.ticker == "005930" for a in attributions)
        
        # Cleanup
        delete_price_attribution(session, saved1.id)
        delete_price_attribution(session, saved2.id)
    
    def test_get_price_attribution_by_date(self, session: Session):
        """Test getting price attribution by date"""
        attribution = PriceAttribution(
            ticker="005930",
            company_name="삼성전자",
            event_date=date(2024, 1, 20),
            price_change_pct=3.5,
            temporal_breakdown='{"test": "data"}',
            ai_analysis_summary="Test summary",
            confidence_score=0.8,
            dominant_timeframe="medium"
        )
        
        saved = add_price_attribution(session, attribution)
        
        # Get by date
        found = get_price_attribution_by_date(session, "005930", date(2024, 1, 20))
        
        assert found is not None
        assert found.id == saved.id
        assert found.event_date == date(2024, 1, 20)
        
        # Cleanup
        delete_price_attribution(session, saved.id)
    
    def test_delete_price_attribution(self, session: Session):
        """Test deleting price attribution"""
        attribution = PriceAttribution(
            ticker="005930",
            company_name="삼성전자",
            event_date=date(2024, 1, 20),
            price_change_pct=3.5,
            temporal_breakdown='{"test": "data"}',
            ai_analysis_summary="Test summary",
            confidence_score=0.8,
            dominant_timeframe="medium"
        )
        
        saved = add_price_attribution(session, attribution)
        
        # Delete
        success = delete_price_attribution(session, saved.id)
        assert success is True
        
        # Verify deletion
        found = get_price_attribution_by_date(session, "005930", date(2024, 1, 20))
        assert found is None


# ──── Integration Tests ────
class TestTemporalAnalysisIntegration:
    """Integration tests for temporal analysis"""
    
    def test_full_analysis_workflow(self, session: Session, sample_samsung_data):
        """Test full workflow from context gathering to database save"""
        # Step 1: Gather context
        with ContextGatherer(session=session) as gatherer:
            context = gatherer.gather_context(
                ticker="005930",
                event_date=date(2024, 2, 25),
                company_name="삼성전자"
            )
            
            assert context["ticker"] == "005930"
        
        # Step 2: Decompose price signal
        with TemporalSignalDecomposer(session=session) as decomposer:
            result = decomposer.decompose_price_signal(
                ticker="005930",
                company_name="삼성전자",
                event_date=date(2024, 2, 25),
                price_change_pct=4.2,
                save_to_db=True
            )
            
            assert isinstance(result, TemporalAnalysisResult)
            assert result.ticker == "005930"
        
        # Step 3: Verify database save
        saved = get_price_attribution_by_date(session, "005930", date(2024, 2, 25))
        assert saved is not None
        assert saved.price_change_pct == 4.2
        assert saved.confidence_score is not None
        
        # Step 4: Retrieve and verify
        attributions = get_price_attributions_by_ticker(
            session=session,
            ticker="005930",
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 28),
            limit=10
        )
        
        assert len(attributions) >= 1
        assert any(a.event_date == date(2024, 2, 25) for a in attributions)
        
        # Cleanup
        delete_price_attribution(session, saved.id)
    
    def test_multiple_analysis_events(self, session: Session):
        """Test analyzing multiple price events"""
        events = [
            {"date": date(2024, 1, 15), "change": 2.5},
            {"date": date(2024, 1, 20), "change": -1.8},
            {"date": date(2024, 1, 25), "change": 3.2},
        ]
        
        saved_ids = []
        
        for event in events:
            with TemporalSignalDecomposer(session=session) as decomposer:
                result = decomposer.decompose_price_signal(
                    ticker="005930",
                    company_name="삼성전자",
                    event_date=event["date"],
                    price_change_pct=event["change"],
                    save_to_db=True
                )
                saved_ids.append(result.ticker)  # Just for tracking
        
        # Verify all events were saved
        attributions = get_price_attributions_by_ticker(
            session=session,
            ticker="005930",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            limit=10
        )
        
        assert len(attributions) >= 3
        
        # Cleanup
        for attribution in attributions:
            delete_price_attribution(session, attribution.id)


# ──── Historical Event Tests ────
class TestHistoricalEvents:
    """Tests with historical price events"""
    
    def test_samsung_earnings_event(self, session: Session, sample_samsung_data):
        """Test analysis of Samsung earnings event"""
        with TemporalSignalDecomposer(session=session) as decomposer:
            result = decomposer.decompose_price_signal(
                ticker="005930",
                company_name="삼성전자",
                event_date=date(2024, 1, 20),  # After earnings call
                price_change_pct=3.5,
                save_to_db=False
            )
            
            assert result.dominant_timeframe in ["short", "medium", "long"]
            assert result.confidence_score >= 0.0
            assert result.confidence_score <= 1.0
    
    def test_negative_price_change(self, session: Session):
        """Test analysis of negative price change"""
        with TemporalSignalDecomposer(session=session) as decomposer:
            result = decomposer.decompose_price_signal(
                ticker="005930",
                company_name="삼성전자",
                event_date=date(2024, 1, 20),
                price_change_pct=-5.2,
                save_to_db=False
            )
            
            assert result.price_change_pct == -5.2
            assert "short_term_analysis" in result.to_dict()
    
    def test_large_price_change(self, session: Session):
        """Test analysis of large price change"""
        with TemporalSignalDecomposer(session=session) as decomposer:
            result = decomposer.decompose_price_signal(
                ticker="005930",
                company_name="삼성전자",
                event_date=date(2024, 1, 20),
                price_change_pct=10.5,
                save_to_db=False
            )
            
            assert result.price_change_pct == 10.5
            assert result.comprehensive_analysis is not None


# ──── Run Tests ────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
