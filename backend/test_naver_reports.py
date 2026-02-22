"""
Test suite for Naver Finance Report Collector

Tests the Naver Finance report collection, indexing, and API endpoints.
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from storage.models import PrimarySource
from storage.db import init_db, get_session
from collector.naver_report_collector import NaverReportCollector, NaverReport, save_naver_report_to_db
from analyzer.parent_child_indexer import ParentChildIndexer


# Test database URL (SQLite for testing)
TEST_DATABASE_URL = "sqlite:///./test_naver_reports.db"


@pytest.fixture(scope="module")
def test_engine():
    """Create test database engine"""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    init_db(engine)
    yield engine
    # Cleanup
    import os
    if os.path.exists("./test_naver_reports.db"):
        os.remove("./test_naver_reports.db")


@pytest.fixture
def test_session(test_engine):
    """Create test session"""
    with Session(test_engine) as session:
        yield session


class TestNaverReportCollector:
    """Test Naver Report Collector"""
    
    @pytest.mark.asyncio
    async def test_collector_initialization(self):
        """Test that collector initializes correctly"""
        collector = NaverReportCollector(headless=True)
        
        assert collector.headless is True
        assert collector.base_url == "https://finance.naver.com"
        assert collector.timeout == 30000
    
    def test_parse_date(self):
        """Test date parsing"""
        collector = NaverReportCollector()
        
        # Test format: "2024.02.15"
        date1 = collector._parse_date("2024.02.15")
        assert date1.year == 2024
        assert date1.month == 2
        assert date1.day == 15
        
        # Test format: "24.02.15"
        date2 = collector._parse_date("24.02.15")
        assert date2.year == 2024
        assert date2.month == 2
        assert date2.day == 15
    
    def test_parse_opinion(self):
        """Test opinion parsing"""
        collector = NaverReportCollector()
        
        assert collector._parse_opinion("매수") == "BUY"
        assert collector._parse_opinion("BUY") == "BUY"
        assert collector._parse_opinion("매도") == "SELL"
        assert collector._parse_opinion("SELL") == "SELL"
        assert collector._parse_opinion("홀드") == "HOLD"
        assert collector._parse_opinion("HOLD") == "HOLD"
        assert collector._parse_opinion("중립") == "HOLD"
        assert collector._parse_opinion("알수없음") == "NEUTRAL"
    
    def test_parse_target_price(self):
        """Test target price parsing"""
        collector = NaverReportCollector()
        
        assert collector._parse_target_price("85,000") == 85000.0
        assert collector._parse_target_price("100,000") == 100000.0
        assert collector._parse_target_price("N/A") is None
        assert collector._parse_target_price("-") is None
        assert collector._parse_target_price("") is None


class TestNaverReportStorage:
    """Test Naver report storage in database"""
    
    def test_save_naver_report_to_db(self, test_session):
        """Test saving Naver report to database"""
        # Create a test report
        report = NaverReport(
            ticker="005930",
            company_name="삼성전자",
            title="Test Report Title",
            analyst="Test Analyst",
            brokerage="Test Brokerage",
            published_at=datetime(2024, 2, 15),
            opinion="BUY",
            target_price=85000.0,
            pdf_url="https://example.com/test.pdf",
            report_url="https://example.com/report",
            full_text="This is a test report content for testing purposes."
        )
        
        # Save to database
        saved = asyncio.run(save_naver_report_to_db(report, test_session))
        
        # Verify
        assert saved.id is not None
        assert saved.ticker == "005930"
        assert saved.company_name == "삼성전자"
        assert saved.source_type == "NAVER_REPORT"
        assert saved.title == "Test Report Title"
        assert saved.authority_weight == 0.4  # Secondary source
        assert saved.content == "This is a test report content for testing purposes."
        
        # Verify metadata
        import json
        metadata = json.loads(saved.extra_metadata)
        assert metadata["analyst"] == "Test Analyst"
        assert metadata["brokerage"] == "Test Brokerage"
        assert metadata["opinion"] == "BUY"
        assert metadata["target_price"] == 85000.0


class TestParentChildIndexing:
    """Test parent-child indexing for Naver reports"""
    
    def test_index_naver_report(self, test_session):
        """Test indexing a Naver report"""
        # Create and save a test report
        report = NaverReport(
            ticker="005930",
            company_name="삼성전자",
            title="Test Report for Indexing",
            analyst="Test Analyst",
            brokerage="Test Brokerage",
            published_at=datetime(2024, 2, 15),
            opinion="BUY",
            target_price=85000.0,
            pdf_url="https://example.com/test.pdf",
            report_url="https://example.com/report",
            full_text="This is a test report content for indexing. " * 20  # Make it longer
        )
        
        saved = asyncio.run(save_naver_report_to_db(report, test_session))
        
        # Index the report
        indexer = ParentChildIndexer()
        result = indexer.index_primary_source(saved.id)
        
        # Verify
        assert result["source_id"] == saved.id
        assert result["source_type"] == "PRIMARY"
        assert result["total_chunks"] > 0
        assert result["summary_chunks"] > 0
        assert result["detail_chunks"] > 0
        assert result["chunk_ids"] is not None
        assert len(result["chunk_ids"]) == result["total_chunks"]


class TestAuthorityWeight:
    """Test authority weight for Naver reports"""
    
    def test_naver_report_authority_weight(self, test_session):
        """Test that Naver reports have correct authority weight"""
        report = NaverReport(
            ticker="005930",
            company_name="삼성전자",
            title="Test Report",
            analyst="Test Analyst",
            brokerage="Test Brokerage",
            published_at=datetime(2024, 2, 15),
            opinion="BUY",
            target_price=85000.0,
            pdf_url="https://example.com/test.pdf",
            report_url="https://example.com/report",
            full_text="Test content"
        )
        
        saved = asyncio.run(save_naver_report_to_db(report, test_session))
        
        # Verify authority weight is 0.4 (secondary source)
        assert saved.authority_weight == 0.4
        
        # Verify source type is NAVER_REPORT
        assert saved.source_type == "NAVER_REPORT"


# Integration tests
class TestNaverReportIntegration:
    """Integration tests for Naver report collection and indexing"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires actual Naver Finance access")
    async def test_collect_and_index_naver_reports(self):
        """
        Integration test: Collect and index Naver reports.
        Skipped by default as it requires actual Naver Finance access.
        """
        collector = NaverReportCollector(headless=True)
        
        # Collect reports
        reports = await collector.collect_reports(
            ticker="005930",
            company_name="삼성전자",
            limit=2
        )
        
        # Verify collection
        assert len(reports) > 0
        
        # Save to database
        engine = create_engine(TEST_DATABASE_URL, echo=False)
        with Session(engine) as session:
            for report in reports:
                if report.full_text:
                    saved = await save_naver_report_to_db(report, session)
                    
                    # Index the report
                    indexer = ParentChildIndexer()
                    result = indexer.index_primary_source(saved.id)
                    
                    assert result["total_chunks"] > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
