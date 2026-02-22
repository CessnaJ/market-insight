"""Search API Routes (Sprint 4)

Endpoints for weighted search with authority weighting and parent-child context.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlmodel import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from storage.db import get_session
from analyzer.weighted_search import WeightedSearch, search
from analyzer.parent_child_indexer import index_report, index_primary_source


router = APIRouter(prefix="/search", tags=["search"])


# ──── Request/Response Models ────
class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    source_type_filter: Optional[str] = Field(
        default=None,
        description="Filter by source type ('REPORT' or 'PRIMARY')"
    )
    chunk_type_filter: Optional[str] = Field(
        default=None,
        description="Filter by chunk type ('SUMMARY' or 'DETAIL')"
    )
    keyword_bonus: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Bonus for exact keyword matches (0.0-1.0)"
    )
    min_similarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold (0.0-1.0)"
    )


class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    primary_source_count: int
    report_count: int


class ChunkResponse(BaseModel):
    """Chunk response model"""
    chunk: Dict[str, Any]
    parent: Optional[Dict[str, Any]] = None
    siblings: List[Dict[str, Any]] = []


class ReindexResponse(BaseModel):
    """Reindex response model"""
    source_id: str
    source_type: str
    status: str
    message: str
    chunk_count: Optional[int] = None


# ──── Search Endpoints ────
@router.post("/", response_model=SearchResponse)
async def weighted_search(request: SearchRequest):
    """
    Perform weighted search combining vector similarity and authority weights
    
    Formula: score = (similarity * authority_weight) + keyword_bonus
    
    Args:
        request: Search request with query and filters
        
    Returns:
        Search results with weighted scores
    """
    try:
        results = search(
            query=request.query,
            limit=request.limit,
            source_type_filter=request.source_type_filter,
            chunk_type_filter=request.chunk_type_filter,
            keyword_bonus=request.keyword_bonus,
            min_similarity=request.min_similarity
        )
        
        primary_count = sum(1 for r in results if r["source_type"] == "PRIMARY")
        report_count = sum(1 for r in results if r["source_type"] == "REPORT")
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            primary_source_count=primary_count,
            report_count=report_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/with-context", response_model=List[Dict[str, Any]])
async def search_with_parent_context(
    query: str,
    limit: int = 10,
    include_siblings: bool = True
):
    """
    Search with full parent context and sibling chunks
    
    Returns parent chunks with all their detail chunks for better context.
    
    Args:
        query: Search query
        limit: Maximum number of parent chunks to return
        include_siblings: Include all detail chunks for matched parents
        
    Returns:
        List of parent chunks with their detail chunks
    """
    try:
        search_engine = WeightedSearch()
        results = search_engine.search_with_parent_context(
            query=query,
            limit=limit,
            include_siblings=include_siblings
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/chunks/{chunk_id}", response_model=ChunkResponse)
async def get_chunk_with_context(
    chunk_id: str,
    include_siblings: bool = True
):
    """
    Get a chunk with its parent context and siblings
    
    Args:
        chunk_id: Chunk ID
        include_siblings: Include sibling detail chunks
        
    Returns:
        Chunk with parent and siblings
    """
    from storage.db import get_chunks_with_parent_context
    
    try:
        with next(get_session()) as session:
            result = get_chunks_with_parent_context(
                session=session,
                chunk_id=chunk_id,
                include_siblings=include_siblings
            )
            
            if not result:
                raise HTTPException(status_code=404, detail="Chunk not found")
            
            return ChunkResponse(
                chunk=result["chunk"],
                parent=result.get("parent"),
                siblings=result.get("siblings", [])
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunk: {str(e)}")


@router.get("/parent/{source_id}")
async def get_parent_chunks(
    source_id: str,
    source_type: str
):
    """
    Get all parent (summary) chunks for a source
    
    Args:
        source_id: Source ID
        source_type: 'REPORT' or 'PRIMARY'
        
    Returns:
        List of parent chunks
    """
    from storage.db import get_parent_chunks
    
    try:
        with next(get_session()) as session:
            chunks = get_parent_chunks(
                session=session,
                source_id=source_id,
                source_type=source_type
            )
            
            return [
                {
                    "id": c.id,
                    "source_id": c.source_id,
                    "source_type": c.source_type,
                    "content": c.content,
                    "authority_weight": c.authority_weight,
                    "chunk_type": c.chunk_type,
                    "chunk_index": c.chunk_index,
                    "parent_id": c.parent_id,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in chunks
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get parent chunks: {str(e)}")


@router.post("/reindex/report/{report_id}", response_model=ReindexResponse)
async def reindex_report(
    report_id: str,
    background_tasks: BackgroundTasks
):
    """
    Trigger reindexing of a report
    
    Args:
        report_id: Report ID from DailyReport table
        background_tasks: FastAPI background tasks
        
    Returns:
        Reindex response
    """
    def reindex_task():
        try:
            result = index_report(report_id)
            logger.info(f"Reindexed report {report_id}: {result}")
        except Exception as e:
            logger.error(f"Failed to reindex report {report_id}: {e}")
    
    try:
        background_tasks.add_task(reindex_task)
        
        return ReindexResponse(
            source_id=report_id,
            source_type="REPORT",
            status="started",
            message="Reindexing started in background"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start reindexing: {str(e)}")


@router.post("/reindex/primary/{primary_source_id}", response_model=ReindexResponse)
async def reindex_primary_source(
    primary_source_id: str,
    background_tasks: BackgroundTasks
):
    """
    Trigger reindexing of a primary source
    
    Args:
        primary_source_id: PrimarySource ID
        background_tasks: FastAPI background tasks
        
    Returns:
        Reindex response
    """
    def reindex_task():
        try:
            result = index_primary_source(primary_source_id)
            logger.info(f"Reindexed primary source {primary_source_id}: {result}")
        except Exception as e:
            logger.error(f"Failed to reindex primary source {primary_source_id}: {e}")
    
    try:
        background_tasks.add_task(reindex_task)
        
        return ReindexResponse(
            source_id=primary_source_id,
            source_type="PRIMARY",
            status="started",
            message="Reindexing started in background"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start reindexing: {str(e)}")


@router.get("/compare")
async def compare_search_results(
    query: str,
    limit: int = 10
):
    """
    Compare search results with and without authority weighting
    
    Useful for understanding the impact of authority weights on search results.
    
    Args:
        query: Search query
        limit: Maximum number of results
        
    Returns:
        Comparison of weighted vs unweighted results
    """
    try:
        search_engine = WeightedSearch()
        results = search_engine.compare_search_results(
            query=query,
            limit=limit
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/statistics")
async def get_chunk_statistics(
    source_id: Optional[str] = None,
    source_type: Optional[str] = None
):
    """
    Get statistics about indexed chunks
    
    Args:
        source_id: Optional source ID filter
        source_type: Optional source type filter ('REPORT' or 'PRIMARY')
        
    Returns:
        Chunk statistics
    """
    from storage.db import get_chunk_statistics
    
    try:
        with next(get_session()) as session:
            stats = get_chunk_statistics(
                session=session,
                source_id=source_id,
                source_type=source_type
            )
            return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# Configure logging
import logging
logger = logging.getLogger(__name__)
