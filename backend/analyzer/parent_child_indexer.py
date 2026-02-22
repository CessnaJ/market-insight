"""Parent-Child Indexer for Report Chunks

Implements two-level chunking strategy:
- Level 1: Summary chunks (2-3 sentences, broad topics)
- Level 2: Detail chunks (single sentences, specific claims)

Parent context preservation: 2-3 minute segments
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from sqlmodel import Session, select

from storage.db import engine, get_session
from storage.models import ReportChunk, PrimarySource, DailyReport
from storage.vector_store import VectorStore
from analyzer.llm_router import get_embedding


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChunkType:
    """Chunk type constants"""
    SUMMARY = "SUMMARY"
    DETAIL = "DETAIL"


class SourceType:
    """Source type constants"""
    REPORT = "REPORT"
    PRIMARY = "PRIMARY"


# Authority weights
AUTHORITY_WEIGHTS = {
    "EARNINGS_CALL": 1.0,
    "DART_FILING": 1.0,
    "IR_MATERIAL": 0.9,
    "NAVER_REPORT": 0.4,  # Secondary source (Naver Finance reports)
    "REPORT": 0.4,  # Secondary source
}


class ParentChildIndexer:
    """
    Parent-child chunking and indexing for reports and primary sources
    
    Usage:
        indexer = ParentChildIndexer()
        indexer.index_report(report_id)
        indexer.index_primary_source(primary_source_id)
    """
    
    def __init__(self):
        """Initialize the indexer"""
        self.vector_store = VectorStore()
        self._ensure_pgvector_extension()
    
    def _ensure_pgvector_extension(self):
        """Ensure pgvector extension is enabled"""
        from sqlalchemy import text
        with Session(engine) as session:
            try:
                session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                session.commit()
                logger.info("pgvector extension enabled")
            except Exception as e:
                logger.warning(f"pgvector extension check: {e}")
    
    def index_report(self, report_id: str) -> Dict[str, Any]:
        """
        Index a daily report into parent-child chunks
        
        Args:
            report_id: Report ID from DailyReport table
            
        Returns:
            Dictionary with indexing results
        """
        with Session(engine) as session:
            report = session.get(DailyReport, report_id)
            if not report:
                raise ValueError(f"Report not found: {report_id}")
            
            # Delete existing chunks for this report
            self._delete_existing_chunks(session, report_id, SourceType.REPORT)
            
            # Get authority weight for reports (secondary source)
            authority_weight = AUTHORITY_WEIGHTS.get("REPORT", 0.4)
            
            # Chunk the report content
            chunks = self._chunk_content(
                content=report.report_markdown,
                authority_weight=authority_weight
            )
            
            # Store chunks
            chunk_ids = []
            for chunk_data in chunks:
                chunk = ReportChunk(
                    source_id=report_id,
                    source_type=SourceType.REPORT,
                    content=chunk_data["content"],
                    embedding=chunk_data["embedding"],
                    authority_weight=authority_weight,
                    chunk_type=chunk_data["chunk_type"],
                    chunk_index=chunk_data["chunk_index"],
                    parent_id=chunk_data.get("parent_id")
                )
                session.add(chunk)
                session.flush()
                chunk_ids.append(chunk.id)
            
            session.commit()
            
            logger.info(f"Indexed report {report_id} into {len(chunks)} chunks")
            
            return {
                "source_id": report_id,
                "source_type": SourceType.REPORT,
                "total_chunks": len(chunks),
                "summary_chunks": len([c for c in chunks if c["chunk_type"] == ChunkType.SUMMARY]),
                "detail_chunks": len([c for c in chunks if c["chunk_type"] == ChunkType.DETAIL]),
                "chunk_ids": chunk_ids
            }
    
    def index_primary_source(self, primary_source_id: str) -> Dict[str, Any]:
        """
        Index a primary source into parent-child chunks
        
        Args:
            primary_source_id: PrimarySource ID
            
        Returns:
            Dictionary with indexing results
        """
        with Session(engine) as session:
            primary_source = session.get(PrimarySource, primary_source_id)
            if not primary_source:
                raise ValueError(f"Primary source not found: {primary_source_id}")
            
            # Delete existing chunks for this source
            self._delete_existing_chunks(session, primary_source_id, SourceType.PRIMARY)
            
            # Get authority weight based on source type
            authority_weight = AUTHORITY_WEIGHTS.get(
                primary_source.source_type,
                1.0
            )
            
            # Chunk the content
            chunks = self._chunk_content(
                content=primary_source.content,
                authority_weight=authority_weight
            )
            
            # Store chunks
            chunk_ids = []
            for chunk_data in chunks:
                chunk = ReportChunk(
                    source_id=primary_source_id,
                    source_type=SourceType.PRIMARY,
                    content=chunk_data["content"],
                    embedding=chunk_data["embedding"],
                    authority_weight=authority_weight,
                    chunk_type=chunk_data["chunk_type"],
                    chunk_index=chunk_data["chunk_index"],
                    parent_id=chunk_data.get("parent_id")
                )
                session.add(chunk)
                session.flush()
                chunk_ids.append(chunk.id)
            
            session.commit()
            
            logger.info(
                f"Indexed primary source {primary_source_id} "
                f"({primary_source.source_type}) into {len(chunks)} chunks"
            )
            
            return {
                "source_id": primary_source_id,
                "source_type": SourceType.PRIMARY,
                "source_subtype": primary_source.source_type,
                "total_chunks": len(chunks),
                "summary_chunks": len([c for c in chunks if c["chunk_type"] == ChunkType.SUMMARY]),
                "detail_chunks": len([c for c in chunks if c["chunk_type"] == ChunkType.DETAIL]),
                "chunk_ids": chunk_ids
            }
    
    def _delete_existing_chunks(
        self,
        session: Session,
        source_id: str,
        source_type: str
    ):
        """Delete existing chunks for a source"""
        existing_chunks = session.exec(
            select(ReportChunk).where(
                ReportChunk.source_id == source_id,
                ReportChunk.source_type == source_type
            )
        ).all()
        
        for chunk in existing_chunks:
            session.delete(chunk)
        
        session.flush()
    
    def _chunk_content(
        self,
        content: str,
        authority_weight: float
    ) -> List[Dict[str, Any]]:
        """
        Chunk content into parent-child structure
        
        Two-level chunking:
        - Level 1: Summary chunks (2-3 sentences, broad topics)
        - Level 2: Detail chunks (single sentences, specific claims)
        
        Args:
            content: Text content to chunk
            authority_weight: Authority weight from source
            
        Returns:
            List of chunk dictionaries
        """
        # Clean content
        content = self._clean_content(content)
        
        # Split into paragraphs
        paragraphs = self._split_into_paragraphs(content)
        
        chunks = []
        chunk_index = 0
        
        # Create summary chunks (Level 1)
        summary_chunks = self._create_summary_chunks(paragraphs)
        summary_chunk_ids = {}
        
        for summary_idx, summary_chunk in enumerate(summary_chunks):
            embedding = self._get_embedding(summary_chunk)
            
            chunk = {
                "content": summary_chunk,
                "embedding": embedding,
                "authority_weight": authority_weight,
                "chunk_type": ChunkType.SUMMARY,
                "chunk_index": chunk_index,
                "parent_id": None
            }
            chunks.append(chunk)
            summary_chunk_ids[summary_idx] = chunk["id"] = f"summary_{chunk_index}"
            chunk_index += 1
        
        # Create detail chunks (Level 2) linked to summary chunks
        for summary_idx, summary_chunk in enumerate(summary_chunks):
            # Get paragraphs for this summary
            summary_paragraphs = summary_chunks[summary_idx].split("\n")
            
            for para_idx, paragraph in enumerate(summary_paragraphs):
                if not paragraph.strip():
                    continue
                
                # Split paragraph into sentences
                sentences = self._split_into_sentences(paragraph)
                
                for sentence in sentences:
                    if len(sentence.strip()) < 10:  # Skip very short sentences
                        continue
                    
                    embedding = self._get_embedding(sentence)
                    
                    chunk = {
                        "content": sentence,
                        "embedding": embedding,
                        "authority_weight": authority_weight,
                        "chunk_type": ChunkType.DETAIL,
                        "chunk_index": chunk_index,
                        "parent_id": summary_chunk_ids[summary_idx]
                    }
                    chunks.append(chunk)
                    chunk_index += 1
        
        return chunks
    
    def _clean_content(self, content: str) -> str:
        """Clean content for chunking"""
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)
        return content.strip()
    
    def _split_into_paragraphs(self, content: str) -> List[str]:
        """Split content into paragraphs"""
        paragraphs = content.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting (can be improved with NLP)
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_summary_chunks(self, paragraphs: List[str]) -> List[str]:
        """
        Create summary chunks from paragraphs
        
        Summary chunks are 2-3 sentences covering broad topics
        """
        summary_chunks = []
        current_chunk = []
        sentence_count = 0
        
        for paragraph in paragraphs:
            sentences = self._split_into_sentences(paragraph)
            
            for sentence in sentences:
                if len(sentence.strip()) < 10:
                    continue
                
                current_chunk.append(sentence)
                sentence_count += 1
                
                # Create chunk every 2-3 sentences
                if sentence_count >= 3:
                    summary_chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    sentence_count = 0
            
            # Handle remaining sentences in current chunk
            if current_chunk and sentence_count >= 2:
                summary_chunks.append(" ".join(current_chunk))
                current_chunk = []
                sentence_count = 0
        
        # Add any remaining content
        if current_chunk:
            summary_chunks.append(" ".join(current_chunk))
        
        return summary_chunks
    
    def _get_embedding(self, text: str) -> str:
        """Get embedding for text and convert to string for pgvector"""
        try:
            embedding = get_embedding(text)
            # Convert to string format for pgvector: [0.1,0.2,...]
            return f"[{','.join(str(x) for x in embedding)}]"
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return "[]"


# Convenience functions
def index_report(report_id: str) -> Dict[str, Any]:
    """
    Index a report into parent-child chunks
    
    Args:
        report_id: Report ID from DailyReport table
        
    Returns:
        Dictionary with indexing results
    """
    indexer = ParentChildIndexer()
    return indexer.index_report(report_id)


def index_primary_source(primary_source_id: str) -> Dict[str, Any]:
    """
    Index a primary source into parent-child chunks
    
    Args:
        primary_source_id: PrimarySource ID
        
    Returns:
        Dictionary with indexing results
    """
    indexer = ParentChildIndexer()
    return indexer.index_primary_source(primary_source_id)
