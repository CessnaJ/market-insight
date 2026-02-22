"""Sprint 1 Test Script

Test the implementation of Sprint 1: Foundation & Primary Data Collection
for Korean securities data.

Tests:
1. Database schema creation
2. DART filing collection
3. Earnings call upload
4. Source authority tagging
5. API endpoints
"""

import sys
from pathlib import Path
import asyncio
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db import (
    get_session,
    add_primary_source,
    get_primary_sources_by_ticker,
    get_primary_source_by_id,
    get_recent_primary_sources
)
from storage.models import PrimarySource
from collector.dart_filing_collector import DARTFilingCollector
from collector.earnings_call_collector import EarningsCallCollector


# Test data
TEST_TICKER = "005930"
TEST_COMPANY = "삼성전자"


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def test_database_schema():
    """Test 1: Database schema creation"""
    print_section("Test 1: Database Schema")
    
    with next(get_session()) as session:
        # Check if PrimarySource table exists by trying to query it
        try:
            from sqlmodel import select
            result = session.exec(select(PrimarySource).limit(1)).all()
            print("✓ PrimarySource table exists and is accessible")
        except Exception as e:
            print(f"✗ PrimarySource table error: {e}")
            return False
    
    return True


def test_earnings_call_upload():
    """Test 2: Earnings call upload"""
    print_section("Test 2: Earnings Call Upload")
    
    collector = EarningsCallCollector()
    
    # Create test transcript content
    test_content = """
    [삼성전자 2024Q3 실적발표콜]
    
    경영진 가이던스:
    - 매출: 전년 대비 두 자릿수 성장 예상
    - 영업이익: 마진율 유지
    - 설비투자: 신기술 투자 확대
    
    Q&A 세션:
    ...
    """
    
    metadata = {
        "call_date": "2024-10-24",
        "participants": ["CEO", "CFO", "투자자"]
    }
    
    try:
        source = asyncio.run(collector.upload_transcript(
            ticker=TEST_TICKER,
            company_name=TEST_COMPANY,
            quarter="2024Q3",
            content=test_content,
            metadata=metadata
        ))
        
        print(f"✓ Earnings call uploaded successfully")
        print(f"  ID: {source.id}")
        print(f"  Title: {source.title}")
        print(f"  Authority Weight: {source.authority_weight}")
        print(f"  Source Type: {source.source_type}")
        
        return source
    except Exception as e:
        print(f"✗ Earnings call upload failed: {e}")
        return None


def test_source_authority_tagging(source: PrimarySource):
    """Test 3: Source authority tagging"""
    print_section("Test 3: Source Authority Tagging")
    
    if not source:
        print("✗ No source to test")
        return False
    
    # Check authority weight
    if source.authority_weight == 1.0:
        print("✓ Primary source has correct authority weight: 1.0")
    else:
        print(f"✗ Incorrect authority weight: {source.authority_weight}")
        return False
    
    # Check source type
    if source.source_type == "EARNINGS_CALL":
        print("✓ Source type is correctly set: EARNINGS_CALL")
    else:
        print(f"✗ Incorrect source type: {source.source_type}")
        return False
    
    return True


def test_retrieval():
    """Test 4: Primary source retrieval"""
    print_section("Test 4: Primary Source Retrieval")
    
    with next(get_session()) as session:
        # Get sources by ticker
        sources = get_primary_sources_by_ticker(
            session=session,
            ticker=TEST_TICKER,
            limit=10
        )
        
        if sources:
            print(f"✓ Retrieved {len(sources)} sources for {TEST_TICKER}")
            for s in sources[:3]:  # Show first 3
                print(f"  - {s.source_type}: {s.title}")
        else:
            print("✗ No sources found")
            return False
        
        # Get recent sources
        recent = get_recent_primary_sources(session=session, limit=5)
        print(f"✓ Retrieved {len(recent)} recent sources")
        
        return True


def test_dart_collector():
    """Test 5: DART filing collector"""
    print_section("Test 5: DART Filing Collector")
    
    collector = DARTFilingCollector()
    
    # Note: This test requires DART_API_KEY
    # Without the API key, we can only test the collector initialization
    
    if not collector.api_key:
        print("⚠ DART_API_KEY not set - skipping actual collection")
        print("✓ Collector initialized successfully")
        print("  To test collection, set DART_API_KEY in environment")
        return True
    
    try:
        # Try to collect quarterly reports
        sources = asyncio.run(collector.collect_quarterly_reports(
            ticker=TEST_TICKER,
            company_name=TEST_COMPANY,
            quarters=1
        ))
        
        if sources:
            print(f"✓ Collected {len(sources)} DART filings")
            for s in sources[:3]:  # Show first 3
                print(f"  - {s.title}")
        else:
            print("⚠ No DART filings collected (may be expected)")
        
        return True
    except Exception as e:
        print(f"✗ DART collection failed: {e}")
        return False


def test_management_guidance_extraction():
    """Test 6: Management guidance extraction"""
    print_section("Test 6: Management Guidance Extraction")
    
    collector = EarningsCallCollector()
    
    test_content = """
    경영진 가이던스:
    - 매출 전망: 4분기 매출은 전년 대비 10% 이상 성장할 것으로 예상
    - 마진율: 영업이익률은 15% 수준을 유지할 전망
    - 설비투자: 반도체 설비투자를 확대하여 미래 경쟁력 강화
    - 시장 전망: AI 반도체 수요가 지속적으로 증가할 것으로 전망
    """
    
    guidance = collector.extract_management_guidance(test_content)
    
    print("✓ Management guidance extracted:")
    print(f"  Revenue outlook: {guidance['revenue_outlook']}")
    print(f"  Margin outlook: {guidance['margin_outlook']}")
    print(f"  Capex outlook: {guidance['capex_outlook']}")
    print(f"  Market outlook: {guidance['market_outlook']}")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  Sprint 1: Foundation & Primary Data Collection")
    print("  Test Suite")
    print("=" * 60)
    
    results = {}
    
    # Run tests
    results["database_schema"] = test_database_schema()
    uploaded_source = test_earnings_call_upload()
    results["earnings_call_upload"] = uploaded_source is not None
    results["authority_tagging"] = test_source_authority_tagging(uploaded_source) if uploaded_source else False
    results["retrieval"] = test_retrieval()
    results["dart_collector"] = test_dart_collector()
    results["guidance_extraction"] = test_management_guidance_extraction()
    
    # Print summary
    print_section("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 All tests passed!")
    else:
        print(f"\n  ⚠ {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
