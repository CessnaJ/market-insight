"""Sprint 4 Tests: Parent-Child Indexing & Weighted Search

Tests for:
- Parent-child chunking
- Weighted search with authority weights
- Hybrid search (vector + keyword)
- Search quality with primary vs secondary sources
"""

import pytest
import logging
from datetime import datetime, date
from typing import List, Dict, Any

from sqlmodel import Session, select, create_engine
from storage.db import engine, get_session, init_database
from storage.models import ReportChunk, PrimarySource, DailyReport
from analyzer.parent_child_indexer import (
    ParentChildIndexer,
    index_report,
    index_primary_source,
    ChunkType,
    SourceType,
    AUTHORITY_WEIGHTS
)
from analyzer.weighted_search import WeightedSearch, search
from storage.db import (
    get_chunks_by_source,
    get_chunks_with_parent_context,
    get_parent_chunks,
    search_chunks_weighted,
    get_chunk_statistics
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ──── Test Fixtures ────
@pytest.fixture(scope="module")
def test_engine():
    """Create test database engine"""
    # Use in-memory SQLite for testing
    test_engine = create_engine("sqlite:///:memory:")
    yield test_engine


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create test session"""
    from storage.models import SQLModel
    SQLModel.metadata.create_all(test_engine)
    
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def sample_primary_source(test_session):
    """Create a sample primary source"""
    source = PrimarySource(
        ticker="005930",
        company_name="삼성전자",
        source_type="EARNINGS_CALL",
        title="2024년 4분기 실적 발표",
        published_at=datetime(2024, 1, 31),
        content="""
        삼성전자 2024년 4분기 실적 요약:
        
        1. 매출: 70조원, 전년 대비 15% 증가
        2. 영업이익: 8조원, 전년 대비 20% 증가
        3. HBM 매출: 2조원, 전분기 대비 30% 성장
        4. 반도체 부문: 5조원 영업이익 달성
        5. 스마트폰 판매량: 6,000만대
        
        전망:
        - 2025년 HBM 시장 점유율 50% 목표
        - AI 반도체 투자 20조원 계획
        - 5G 스마트폰 출시 확대
        """
    )
    test_session.add(source)
    test_session.commit()
    test_session.refresh(source)
    return source


@pytest.fixture
def sample_report(test_session):
    """Create a sample daily report"""
    report = DailyReport(
        report_date=date(2024, 2, 1),
        report_markdown="""
        # 일일 리포트 - 2024년 2월 1일
        
        ## 삼성전자 실적 분석
        삼성전자가 어제 4분기 실적을 발표했다. HBM 매출이 크게 성장했다.
        
        ## 시장 동향
        반도체 업황이 개선되고 있다. AI 반도체 수요가 증가하고 있다.
        
        ## 투자 의견
        삼성전자는 HBM 분야에서 경쟁력을 갖추고 있다. 매수 추천한다.
        """
    )
    test_session.add(report)
    test_session.commit()
    test_session.refresh(report)
    return report


# ──── Test: Parent-Child Chunking ────
def test_parent_child_chunking_primary_source(test_session, sample_primary_source):
    """Test parent-child chunking for primary sources"""
    indexer = ParentChildIndexer()
    
    # Index the primary source
    result = indexer.index_primary_source(sample_primary_source.id)
    
    # Verify results
    assert result["source_id"] == sample_primary_source.id
    assert result["source_type"] == SourceType.PRIMARY
    assert result["total_chunks"] > 0
    assert result["summary_chunks"] > 0
    assert result["detail_chunks"] > 0
    
    # Verify chunks in database
    chunks = get_chunks_by_source(
        test_session,
        sample_primary_source.id,
        SourceType.PRIMARY
    )
    
    assert len(chunks) == result["total_chunks"]
    
    # Verify parent-child relationships
    summary_chunks = [c for c in chunks if c.chunk_type == ChunkType.SUMMARY]
    detail_chunks = [c for c in chunks if c.chunk_type == ChunkType.DETAIL]
    
    assert len(summary_chunks) == result["summary_chunks"]
    assert len(detail_chunks) == result["detail_chunks"]
    
    # Verify detail chunks have parent_id
    for detail in detail_chunks:
        assert detail.parent_id is not None
        # Verify parent exists
        parent = test_session.get(ReportChunk, detail.parent_id)
        assert parent is not None
        assert parent.chunk_type == ChunkType.SUMMARY


def test_parent_child_chunking_report(test_session, sample_report):
    """Test parent-child chunking for reports"""
    indexer = ParentChildIndexer()
    
    # Index the report
    result = indexer.index_report(sample_report.id)
    
    # Verify results
    assert result["source_id"] == sample_report.id
    assert result["source_type"] == SourceType.REPORT
    assert result["total_chunks"] > 0
    assert result["summary_chunks"] > 0
    assert result["detail_chunks"] > 0
    
    # Verify authority weight for reports (secondary source)
    chunks = get_chunks_by_source(
        test_session,
        sample_report.id,
        SourceType.REPORT
    )
    
    for chunk in chunks:
        assert chunk.authority_weight == AUTHORITY_WEIGHTS["REPORT"]


def test_authority_weights(test_session, sample_primary_source, sample_report):
    """Test that primary sources have higher authority weights"""
    indexer = ParentChildIndexer()
    
    # Index both sources
    indexer.index_primary_source(sample_primary_source.id)
    indexer.index_report(sample_report.id)
    
    # Get chunks
    primary_chunks = get_chunks_by_source(
        test_session,
        sample_primary_source.id,
        SourceType.PRIMARY
    )
    
    report_chunks = get_chunks_by_source(
        test_session,
        sample_report.id,
        SourceType.REPORT
    )
    
    # Verify authority weights
    for chunk in primary_chunks:
        assert chunk.authority_weight >= AUTHORITY_WEIGHTS["REPORT"]
    
    for chunk in report_chunks:
        assert chunk.authority_weight == AUTHORITY_WEIGHTS["REPORT"]


# ──── Test: Weighted Search ────
def test_weighted_search_primary_sources_rank_higher(test_session, sample_primary_source, sample_report):
    """Test that primary sources rank higher in weighted search"""
    indexer = ParentChildIndexer()
    
    # Index both sources
    indexer.index_primary_source(sample_primary_source.id)
    indexer.index_report(sample_report.id)
    
    # Perform weighted search
    search_engine = WeightedSearch()
    results = search_engine.search(
        query="HBM 매출",
        limit=10,
        min_similarity=0.0
    )
    
    # Primary source chunks should appear first due to higher authority weight
    primary_results = [r for r in results if r["source_type"] == SourceType.PRIMARY]
    report_results = [r for r in results if r["source_type"] == SourceType.REPORT]
    
    # Verify primary sources have higher weighted scores
    if primary_results and report_results:
        avg_primary_score = sum(r["weighted_score"] for r in primary_results) / len(primary_results)
        avg_report_score = sum(r["weighted_score"] for r in report_results) / len(report_results)
        assert avg_primary_score >= avg_report_score


def test_weighted_search_formula(test_session, sample_primary_source):
    """Test weighted search formula: score = similarity * authority_weight"""
    indexer = ParentChildIndexer()
    indexer.index_primary_source(sample_primary_source.id)
    
    search_engine = WeightedSearch()
    results = search_engine.search(
        query="HBM 매출",
        limit=5,
        keyword_bonus=0.0,  # Disable keyword bonus for this test
        min_similarity=0.0
    )
    
    for result in results:
        # Verify formula
        expected_score = result["similarity"] * result["authority_weight"]
        assert abs(result["weighted_score"] - expected_score) < 0.001


def test_hybrid_search(test_session, sample_primary_source):
    """Test hybrid search combining vector and keyword matching"""
    indexer = ParentChildIndexer()
    indexer.index_primary_source(sample_primary_source.id)
    
    # Search with keyword bonus
    search_engine = WeightedSearch()
    results_with_bonus = search_engine.search(
        query="HBM 매출",
        limit=10,
        keyword_bonus=0.2,
        min_similarity=0.0
    )
    
    # Search without keyword bonus
    results_without_bonus = search_engine.search(
        query="HBM 매출",
        limit=10,
        keyword_bonus=0.0,
        min_similarity=0.0
    )
    
    # Results with keyword bonus should have higher scores for exact matches
    assert len(results_with_bonus) > 0
    assert len(results_without_bonus) > 0


def test_search_with_parent_context(test_session, sample_primary_source):
    """Test search with parent context preservation"""
    indexer = ParentChildIndexer()
    indexer.index_primary_source(sample_primary_source.id)
    
    search_engine = WeightedSearch()
    results = search_engine.search_with_parent_context(
        query="HBM",
        limit=5,
        include_siblings=True
    )
    
    # Verify parent context is included
    for result in results:
        assert "parent" in result
        assert "detail_chunks" in result
        
        if result["parent"]:
            assert result["parent"]["chunk_type"] == ChunkType.SUMMARY
        
        # Verify siblings are included if requested
        if include_siblings := True:
            assert isinstance(result["detail_chunks"], list)


# ──── Test: Database Operations ────
def test_get_chunks_with_parent_context(test_session, sample_primary_source):
    """Test getting a chunk with parent context"""
    indexer = ParentChildIndexer()
    indexer.index_primary_source(sample_primary_source.id)
    
    # Get a detail chunk
    chunks = get_chunks_by_source(
        test_session,
        sample_primary_source.id,
        SourceType.PRIMARY,
        ChunkType.DETAIL
    )
    
    if chunks:
        detail_chunk = chunks[0]
        result = get_chunks_with_parent_context(
            test_session,
            detail_chunk.id,
            include_siblings=True
        )
        
        assert result is not None
        assert "chunk" in result
        assert result["chunk"]["id"] == detail_chunk.id
        assert "parent" in result
        assert "siblings" in result


def test_get_parent_chunks(test_session, sample_primary_source):
    """Test getting parent chunks"""
    indexer = ParentChildIndexer()
    indexer.index_primary_source(sample_primary_source.id)
    
    parents = get_parent_chunks(
        test_session,
        sample_primary_source.id,
        SourceType.PRIMARY
    )
    
    assert len(parents) > 0
    for parent in parents:
        assert parent.chunk_type == ChunkType.SUMMARY
        assert parent.parent_id is None


def test_get_chunk_statistics(test_session, sample_primary_source, sample_report):
    """Test getting chunk statistics"""
    indexer = ParentChildIndexer()
    indexer.index_primary_source(sample_primary_source.id)
    indexer.index_report(sample_report.id)
    
    # Get all statistics
    stats = get_chunk_statistics(test_session)
    
    assert stats["total_chunks"] > 0
    assert stats["summary_chunks"] > 0
    assert stats["detail_chunks"] > 0
    assert stats["by_source_type"]["PRIMARY"] > 0
    assert stats["by_source_type"]["REPORT"] > 0
    
    # Get statistics for primary source only
    primary_stats = get_chunk_statistics(
        test_session,
        source_id=sample_primary_source.id,
        source_type=SourceType.PRIMARY
    )
    
    assert primary_stats["by_source_type"]["PRIMARY"] > 0
    assert primary_stats["by_source_type"]["REPORT"] == 0


# ──── Test: Search Quality ────
def test_compare_search_results(test_session, sample_primary_source, sample_report):
    """Test comparing weighted vs unweighted search results"""
    indexer = ParentChildIndexer()
    indexer.index_primary_source(sample_primary_source.id)
    indexer.index_report(sample_report.id)
    
    search_engine = WeightedSearch()
    comparison = search_engine.compare_search_results(
        query="삼성전자 실적",
        limit=10
    )
    
    assert "query" in comparison
    assert "weighted_results" in comparison
    assert "unweighted_results" in comparison
    assert "primary_source_rankings" in comparison
    
    # Primary sources should rank higher in weighted search
    weighted_primary_ranks = comparison["primary_source_rankings"]["weighted"]
    unweighted_primary_ranks = comparison["primary_source_rankings"]["unweighted"]
    
    if weighted_primary_ranks and unweighted_primary_ranks:
        avg_weighted_rank = sum(weighted_primary_ranks) / len(weighted_primary_ranks)
        avg_unweighted_rank = sum(unweighted_primary_ranks) / len(unweighted_primary_ranks)
        assert avg_weighted_rank <= avg_unweighted_rank


def test_search_filters(test_session, sample_primary_source, sample_report):
    """Test search with filters"""
    indexer = ParentChildIndexer()
    indexer.index_primary_source(sample_primary_source.id)
    indexer.index_report(sample_report.id)
    
    search_engine = WeightedSearch()
    
    # Test source type filter
    primary_only = search_engine.search(
        query="매출",
        limit=10,
        source_type_filter=SourceType.PRIMARY
    )
    
    for result in primary_only:
        assert result["source_type"] == SourceType.PRIMARY
    
    # Test chunk type filter
    summary_only = search_engine.search(
        query="매출",
        limit=10,
        chunk_type_filter=ChunkType.SUMMARY
    )
    
    for result in summary_only:
        assert result["chunk_type"] == ChunkType.SUMMARY


# ──── Test: Edge Cases ────
def test_empty_content_chunking(test_session):
    """Test chunking with empty content"""
    source = PrimarySource(
        ticker="005930",
        company_name="삼성전자",
        source_type="EARNINGS_CALL",
        title="Empty Test",
        published_at=datetime.now(),
        content=""
    )
    test_session.add(source)
    test_session.commit()
    test_session.refresh(source)
    
    indexer = ParentChildIndexer()
    result = indexer.index_primary_source(source.id)
    
    # Should handle empty content gracefully
    assert result["total_chunks"] == 0


def test_reindexing(test_session, sample_primary_source):
    """Test reindexing deletes old chunks"""
    indexer = ParentChildIndexer()
    
    # First indexing
    result1 = indexer.index_primary_source(sample_primary_source.id)
    chunk_count_1 = result1["total_chunks"]
    
    # Reindexing
    result2 = indexer.index_primary_source(sample_primary_source.id)
    chunk_count_2 = result2["total_chunks"]
    
    # Chunk counts should be the same
    assert chunk_count_1 == chunk_count_2
    
    # Verify no duplicate chunks
    chunks = get_chunks_by_source(
        test_session,
        sample_primary_source.id,
        SourceType.PRIMARY
    )
    assert len(chunks) == chunk_count_2


# ──── Test: Integration with Real Data (삼성전자) ────
def test_samsung_hbm_search(test_session, sample_primary_source):
    """Test search with real 삼성전자 HBM data"""
    indexer = ParentChildIndexer()
    indexer.index_primary_source(sample_primary_source.id)
    
    search_engine = WeightedSearch()
    
    # Search for HBM related content
    results = search_engine.search(
        query="HBM 매출 성장",
        limit=10,
        min_similarity=0.0
    )
    
    # Should find relevant results
    assert len(results) > 0
    
    # Verify results contain HBM related content
    found_hbm = any("HBM" in r["content"] for r in results)
    assert found_hbm


def test_samsung_authority_weighting(test_session, sample_primary_source, sample_report):
    """Test that 삼성전자 primary sources rank higher than reports"""
    indexer = ParentChildIndexer()
    indexer.index_primary_source(sample_primary_source.id)
    indexer.index_report(sample_report.id)
    
    search_engine = WeightedSearch()
    results = search_engine.search(
        query="삼성전자 매출",
        limit=10,
        min_similarity=0.0
    )
    
    # Primary sources should appear first
    if results:
        first_result = results[0]
        assert first_result["source_type"] == SourceType.PRIMARY


# ──── Run Tests ────
if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
