"""Weighted Search with Authority Weighting

Implements hybrid search combining:
- Vector similarity (semantic search)
- Authority weights (primary sources rank higher)
- Keyword filtering (exact match bonus)

Formula: score = (similarity * authority_weight) + keyword_bonus
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlmodel import Session, select, col
from sqlalchemy import text, func, or_

from storage.db import engine, get_session
from storage.models import ReportChunk, PrimarySource, DailyReport
from analyzer.llm_router import get_embedding


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeightedSearch:
    """
    Weighted search combining vector similarity with authority weights
    
    Usage:
        search = WeightedSearch()
        results = search.search(
            query="삼성전자 HBM 매출",
            limit=10,
            source_type_filter=None
        )
    """
    
    def __init__(self):
        """Initialize weighted search"""
        self._ensure_pgvector_extension()
    
    def _ensure_pgvector_extension(self):
        """Ensure pgvector extension is enabled"""
        with Session(engine) as session:
            try:
                session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                session.commit()
            except Exception as e:
                logger.warning(f"pgvector extension check: {e}")
    
    def search(
        self,
        query: str,
        limit: int = 10,
        source_type_filter: Optional[str] = None,
        chunk_type_filter: Optional[str] = None,
        ticker_filter: Optional[str] = None,
        keyword_bonus: float = 0.1,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Perform weighted search combining vector similarity and authority weights
        
        Args:
            query: Search query
            limit: Maximum number of results
            source_type_filter: Filter by source type ('REPORT' or 'PRIMARY')
            chunk_type_filter: Filter by chunk type ('SUMMARY' or 'DETAIL')
            ticker_filter: Filter by ticker
            keyword_bonus: Bonus for exact keyword matches (0.0-1.0)
            min_similarity: Minimum similarity threshold (0.0-1.0)
            
        Returns:
            List of search results with scores
        """
        # Get query embedding
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []
        
        # Build SQL query
        with Session(engine) as session:
            # Base query with vector similarity
            sql_query = text("""
                SELECT 
                    rc.id,
                    rc.source_id,
                    rc.source_type,
                    rc.content,
                    rc.authority_weight,
                    rc.chunk_type,
                    rc.chunk_index,
                    rc.parent_id,
                    rc.created_at,
                    CASE 
                        WHEN rc.parent_id IS NOT NULL THEN 
                            (SELECT content FROM report_chunks WHERE id = rc.parent_id)
                        ELSE NULL
                    END as parent_content,
                    1 - (rc.embedding <=> :embedding::vector) as similarity
                FROM report_chunks rc
                WHERE 1 - (rc.embedding <=> :embedding::vector) >= :min_similarity
            """)
            
            # Add filters
            params = {
                "embedding": f"[{','.join(str(x) for x in query_embedding)}]",
                "min_similarity": min_similarity
            }
            
            if source_type_filter:
                sql_query = text(sql_query.text + " AND rc.source_type = :source_type")
                params["source_type"] = source_type_filter
            
            if chunk_type_filter:
                sql_query = text(sql_query.text + " AND rc.chunk_type = :chunk_type")
                params["chunk_type"] = chunk_type_filter
            
            # Execute query
            result = session.execute(sql_query, params).fetchall()
            
            # Calculate weighted scores
            results = []
            for row in result:
                # Base score: similarity * authority_weight
                base_score = row.similarity * row.authority_weight
                
                # Keyword bonus for exact matches
                keyword_score = self._calculate_keyword_bonus(query, row.content, keyword_bonus)
                
                # Final score
                final_score = base_score + keyword_score
                
                # Get additional metadata
                metadata = self._get_chunk_metadata(
                    session,
                    row.source_id,
                    row.source_type
                )
                
                results.append({
                    "id": row.id,
                    "source_id": row.source_id,
                    "source_type": row.source_type,
                    "content": row.content,
                    "authority_weight": row.authority_weight,
                    "chunk_type": row.chunk_type,
                    "chunk_index": row.chunk_index,
                    "parent_id": row.parent_id,
                    "parent_content": row.parent_content,
                    "similarity": row.similarity,
                    "keyword_bonus": keyword_score,
                    "weighted_score": final_score,
                    "metadata": metadata,
                    "created_at": row.created_at.isoformat() if row.created_at else None
                })
            
            # Sort by weighted score
            results.sort(key=lambda x: x["weighted_score"], reverse=True)
            
            # Limit results
            results = results[:limit]
            
            logger.info(f"Search '{query}' returned {len(results)} results")
            
            return results
    
    def search_with_parent_context(
        self,
        query: str,
        limit: int = 10,
        include_siblings: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search with full parent context and sibling chunks
        
        Args:
            query: Search query
            limit: Maximum number of parent chunks to return
            include_siblings: Include all detail chunks for matched parents
            
        Returns:
            List of parent chunks with their detail chunks
        """
        # First, search for matching chunks
        all_results = self.search(
            query=query,
            limit=limit * 5,  # Get more results to find parents
            min_similarity=0.1
        )
        
        # Group by parent
        parent_groups: Dict[str, Dict[str, Any]] = {}
        
        for result in all_results:
            parent_id = result["parent_id"] if result["chunk_type"] == "DETAIL" else result["id"]
            
            if parent_id not in parent_groups:
                # Get parent chunk
                if result["chunk_type"] == "SUMMARY":
                    parent_chunk = result
                else:
                    parent_chunk = self._get_chunk_by_id(parent_id)
                
                if parent_chunk:
                    parent_groups[parent_id] = {
                        "parent": parent_chunk,
                        "detail_chunks": [],
                        "max_score": 0.0
                    }
            
            # Add detail chunk if this is a detail chunk
            if result["chunk_type"] == "DETAIL" and parent_id in parent_groups:
                parent_groups[parent_id]["detail_chunks"].append(result)
                parent_groups[parent_id]["max_score"] = max(
                    parent_groups[parent_id]["max_score"],
                    result["weighted_score"]
                )
            elif result["chunk_type"] == "SUMMARY":
                parent_groups[parent_id]["max_score"] = max(
                    parent_groups[parent_id]["max_score"],
                    result["weighted_score"]
                )
        
        # If include_siblings, get all detail chunks for matched parents
        if include_siblings:
            for parent_id, group in parent_groups.items():
                existing_detail_ids = {dc["id"] for dc in group["detail_chunks"]}
                all_detail_chunks = self._get_child_chunks(parent_id)
                
                for detail_chunk in all_detail_chunks:
                    if detail_chunk["id"] not in existing_detail_ids:
                        group["detail_chunks"].append(detail_chunk)
        
        # Sort by max score and limit
        sorted_parents = sorted(
            parent_groups.values(),
            key=lambda x: x["max_score"],
            reverse=True
        )[:limit]
        
        return sorted_parents
    
    def _get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a chunk by ID"""
        with Session(engine) as session:
            chunk = session.get(ReportChunk, chunk_id)
            if chunk:
                return {
                    "id": chunk.id,
                    "source_id": chunk.source_id,
                    "source_type": chunk.source_type,
                    "content": chunk.content,
                    "authority_weight": chunk.authority_weight,
                    "chunk_type": chunk.chunk_type,
                    "chunk_index": chunk.chunk_index,
                    "parent_id": chunk.parent_id,
                    "created_at": chunk.created_at.isoformat() if chunk.created_at else None
                }
        return None
    
    def _get_child_chunks(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get all child chunks for a parent"""
        with Session(engine) as session:
            chunks = session.exec(
                select(ReportChunk).where(ReportChunk.parent_id == parent_id)
                .order_by(ReportChunk.chunk_index)
            ).all()
            
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
    
    def _get_chunk_metadata(
        self,
        session: Session,
        source_id: str,
        source_type: str
    ) -> Dict[str, Any]:
        """Get metadata for the source of a chunk"""
        if source_type == "PRIMARY":
            primary_source = session.get(PrimarySource, source_id)
            if primary_source:
                return {
                    "ticker": primary_source.ticker,
                    "company_name": primary_source.company_name,
                    "source_subtype": primary_source.source_type,
                    "title": primary_source.title,
                    "published_at": primary_source.published_at.isoformat() if primary_source.published_at else None
                }
        elif source_type == "REPORT":
            report = session.get(DailyReport, source_id)
            if report:
                return {
                    "report_date": report.report_date.isoformat() if report.report_date else None,
                    "created_at": report.created_at.isoformat() if report.created_at else None
                }
        
        return {}
    
    def _calculate_keyword_bonus(
        self,
        query: str,
        content: str,
        max_bonus: float
    ) -> float:
        """
        Calculate keyword bonus for exact matches
        
        Args:
            query: Search query
            content: Chunk content
            max_bonus: Maximum bonus (0.0-1.0)
            
        Returns:
            Keyword bonus score
        """
        if max_bonus <= 0:
            return 0.0
        
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Check for exact phrase match
        if query_lower in content_lower:
            return max_bonus
        
        # Check for individual word matches
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        if not query_words:
            return 0.0
        
        # Calculate overlap ratio
        overlap = len(query_words & content_words) / len(query_words)
        
        return overlap * max_bonus
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text"""
        try:
            return get_embedding(text)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def compare_search_results(
        self,
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Compare search results with and without authority weighting
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Comparison of weighted vs unweighted results
        """
        # Weighted search (with authority weights)
        weighted_results = self.search(query=query, limit=limit)
        
        # Unweighted search (similarity only)
        unweighted_results = self._search_unweighted(query=query, limit=limit)
        
        # Compare primary source rankings
        primary_ranked_weighted = [
            i for i, r in enumerate(weighted_results)
            if r["source_type"] == "PRIMARY"
        ]
        
        primary_ranked_unweighted = [
            i for i, r in enumerate(unweighted_results)
            if r["source_type"] == "PRIMARY"
        ]
        
        return {
            "query": query,
            "weighted_results": weighted_results,
            "unweighted_results": unweighted_results,
            "primary_source_rankings": {
                "weighted": primary_ranked_weighted,
                "unweighted": primary_ranked_unweighted
            },
            "avg_primary_rank_weighted": sum(primary_ranked_weighted) / len(primary_ranked_weighted) if primary_ranked_weighted else None,
            "avg_primary_rank_unweighted": sum(primary_ranked_unweighted) / len(primary_ranked_unweighted) if primary_ranked_unweighted else None
        }
    
    def _search_unweighted(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search without authority weighting (similarity only)"""
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return []
        
        with Session(engine) as session:
            sql_query = text("""
                SELECT 
                    rc.id,
                    rc.source_id,
                    rc.source_type,
                    rc.content,
                    rc.authority_weight,
                    rc.chunk_type,
                    rc.chunk_index,
                    rc.parent_id,
                    rc.created_at,
                    1 - (rc.embedding <=> :embedding::vector) as similarity
                FROM report_chunks rc
                WHERE 1 - (rc.embedding <=> :embedding::vector) >= :min_similarity
                ORDER BY similarity DESC
                LIMIT :limit
            """)
            
            params = {
                "embedding": f"[{','.join(str(x) for x in query_embedding)}]",
                "min_similarity": min_similarity,
                "limit": limit
            }
            
            result = session.execute(sql_query, params).fetchall()
            
            return [
                {
                    "id": row.id,
                    "source_id": row.source_id,
                    "source_type": row.source_type,
                    "content": row.content,
                    "authority_weight": row.authority_weight,
                    "chunk_type": row.chunk_type,
                    "chunk_index": row.chunk_index,
                    "parent_id": row.parent_id,
                    "similarity": row.similarity,
                    "weighted_score": row.similarity,  # No weighting
                    "created_at": row.created_at.isoformat() if row.created_at else None
                }
                for row in result
            ]


# Convenience function
def search(
    query: str,
    limit: int = 10,
    source_type_filter: Optional[str] = None,
    chunk_type_filter: Optional[str] = None,
    keyword_bonus: float = 0.1,
    min_similarity: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Perform weighted search
    
    Args:
        query: Search query
        limit: Maximum number of results
        source_type_filter: Filter by source type ('REPORT' or 'PRIMARY')
        chunk_type_filter: Filter by chunk type ('SUMMARY' or 'DETAIL')
        keyword_bonus: Bonus for exact keyword matches (0.0-1.0)
        min_similarity: Minimum similarity threshold (0.0-1.0)
        
    Returns:
        List of search results with scores
    """
    search_engine = WeightedSearch()
    return search_engine.search(
        query=query,
        limit=limit,
        source_type_filter=source_type_filter,
        chunk_type_filter=chunk_type_filter,
        keyword_bonus=keyword_bonus,
        min_similarity=min_similarity
    )
