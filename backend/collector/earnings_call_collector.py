"""Earnings Call Transcript Collector

Collects earnings call transcripts for Korean stocks.
Phase 1: Manual upload functionality
Phase 2: Automated collection from IR pages (future)
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from sqlmodel import Session

from storage.db import get_session, add_primary_source
from storage.models import PrimarySource


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EarningsCall:
    """Earnings call data structure"""
    ticker: str  # Stock ticker
    company_name: str  # Company name
    quarter: str  # e.g., "2024Q3"
    call_date: datetime  # Call date
    transcript_url: str  # URL to transcript
    full_text: str  # Full transcript text
    source_type: str = "EARNINGS_CALL"
    authority_weight: float = 1.0


class EarningsCallCollector:
    """
    Earnings call transcript collector.

    Phase 1: Manual upload functionality
    Phase 2: Automated collection from IR pages (future)

    Usage:
        collector = EarningsCallCollector()
        source = await collector.upload_transcript(
            ticker="005930",
            company_name="삼성전자",
            quarter="2024Q3",
            content="Transcript text...",
            metadata={"call_date": "2024-10-24"}
        )
    """

    def __init__(self, storage_dir: str = "data/earnings_calls"):
        """
        Initialize earnings call collector.

        Args:
            storage_dir: Directory to store uploaded files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            # Try PyPDF2 first
            try:
                import PyPDF2
                text = ""
                with open(pdf_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                return text
            except ImportError:
                pass
            
            # Try pdfplumber as fallback
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                return text
            except ImportError:
                pass
            
            logger.warning("No PDF library available (PyPDF2 or pdfplumber)")
            return ""
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return ""

    def _save_uploaded_file(self, file_content: bytes, filename: str) -> Path:
        """
        Save uploaded file to storage directory.

        Args:
            file_content: File content bytes
            filename: Original filename

        Returns:
            Path to saved file
        """
        # Create unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        file_path = self.storage_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        logger.info(f"Saved uploaded file: {file_path}")
        return file_path

    async def upload_transcript(
        self,
        ticker: str,
        company_name: str,
        quarter: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        file_content: Optional[bytes] = None,
        filename: Optional[str] = None,
        session: Optional[Session] = None
    ) -> PrimarySource:
        """
        Manually upload an earnings call transcript.

        Args:
            ticker: Stock ticker (e.g., "005930")
            company_name: Company name (e.g., "삼성전자")
            quarter: Quarter identifier (e.g., "2024Q3")
            content: Transcript text content
            metadata: Additional metadata (call_date, participants, etc.)
            file_content: Optional file content bytes
            filename: Optional original filename
            session: Database session (optional)

        Returns:
            Created PrimarySource object
        """
        logger.info(f"Uploading earnings call transcript for {ticker} - {quarter}")
        
        # Process file if provided
        file_path = None
        if file_content and filename:
            file_path = self._save_uploaded_file(file_content, filename)
            
            # Extract text from PDF if needed
            if filename.lower().endswith(".pdf") and not content:
                content = self._extract_text_from_pdf(file_path)
        
        # Parse call date from metadata
        call_date = datetime.now()
        if metadata and "call_date" in metadata:
            try:
                call_date = datetime.fromisoformat(metadata["call_date"])
            except (ValueError, TypeError):
                logger.warning(f"Invalid call_date format: {metadata['call_date']}")
        
        # Create metadata string
        metadata_str = str(metadata) if metadata else None
        
        # Create primary source
        primary_source = PrimarySource(
            ticker=ticker,
            company_name=company_name,
            source_type="EARNINGS_CALL",
            title=f"{company_name} {quarter} Earnings Call",
            published_at=call_date,
            content=content,
            authority_weight=1.0,  # Primary source
            extra_metadata=metadata_str,
            file_path=str(file_path) if file_path else None
        )
        
        # Save to database
        session_provided = session is not None
        if not session_provided:
            session = next(get_session())
        
        try:
            created_source = add_primary_source(session, primary_source)
            logger.info(f"Created primary source: {primary_source.title}")
            return created_source
        finally:
            if not session_provided:
                session.close()

    async def upload_transcript_from_file(
        self,
        ticker: str,
        company_name: str,
        quarter: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        session: Optional[Session] = None
    ) -> PrimarySource:
        """
        Upload earnings call transcript from file path.

        Args:
            ticker: Stock ticker
            company_name: Company name
            quarter: Quarter identifier
            file_path: Path to transcript file
            metadata: Additional metadata
            session: Database session (optional)

        Returns:
            Created PrimarySource object
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file content
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        # Extract text if PDF
        content = ""
        if file_path.suffix.lower() == ".pdf":
            content = self._extract_text_from_pdf(file_path)
        else:
            content = file_content.decode("utf-8", errors="ignore")
        
        return await self.upload_transcript(
            ticker=ticker,
            company_name=company_name,
            quarter=quarter,
            content=content,
            metadata=metadata,
            file_content=file_content,
            filename=file_path.name,
            session=session
        )

    async def get_transcripts_by_ticker(
        self,
        ticker: str,
        session: Optional[Session] = None
    ) -> List[PrimarySource]:
        """
        Get all earnings call transcripts for a ticker.

        Args:
            ticker: Stock ticker
            session: Database session (optional)

        Returns:
            List of PrimarySource objects
        """
        session_provided = session is not None
        if not session_provided:
            session = next(get_session())
        
        try:
            from sqlmodel import select
            transcripts = session.exec(
                select(PrimarySource).where(
                    PrimarySource.ticker == ticker,
                    PrimarySource.source_type == "EARNINGS_CALL"
                ).order_by(PrimarySource.published_at.desc())
            ).all()
            return transcripts
        finally:
            if not session_provided:
                session.close()

    async def get_transcript_by_quarter(
        self,
        ticker: str,
        quarter: str,
        session: Optional[Session] = None
    ) -> Optional[PrimarySource]:
        """
        Get earnings call transcript by ticker and quarter.

        Args:
            ticker: Stock ticker
            quarter: Quarter identifier (e.g., "2024Q3")
            session: Database session (optional)

        Returns:
            PrimarySource object or None
        """
        session_provided = session is not None
        if not session_provided:
            session = next(get_session())
        
        try:
            from sqlmodel import select
            transcript = session.exec(
                select(PrimarySource).where(
                    PrimarySource.ticker == ticker,
                    PrimarySource.source_type == "EARNINGS_CALL",
                    PrimarySource.title.contains(quarter)
                ).order_by(PrimarySource.published_at.desc())
            ).first()
            return transcript
        finally:
            if not session_provided:
                session.close()

    def extract_management_guidance(self, content: str) -> Dict[str, Any]:
        """
        Extract management guidance from transcript content.

        This is a simple extraction that looks for common guidance patterns.
        For production use, consider using LLM-based extraction.

        Args:
            content: Transcript content

        Returns:
            Dictionary with extracted guidance
        """
        guidance = {
            "revenue_outlook": None,
            "margin_outlook": None,
            "capex_outlook": None,
            "market_outlook": None,
            "key_points": []
        }
        
        # Simple keyword-based extraction (can be improved with LLM)
        content_lower = content.lower()
        
        # Look for revenue guidance
        if "revenue" in content_lower or "매출" in content:
            # Extract sentences containing revenue guidance
            for line in content.split("\n"):
                if any(word in line.lower() for word in ["revenue guidance", "매출 가이던스", "revenue outlook"]):
                    guidance["revenue_outlook"] = line.strip()
                    break
        
        # Look for margin guidance
        if "margin" in content_lower or "마진" in content:
            for line in content.split("\n"):
                if any(word in line.lower() for word in ["margin guidance", "마진 가이던스", "margin outlook"]):
                    guidance["margin_outlook"] = line.strip()
                    break
        
        # Look for capex guidance
        if "capex" in content_lower or "설비투자" in content:
            for line in content.split("\n"):
                if any(word in line.lower() for word in ["capex guidance", "설비투자 가이던스"]):
                    guidance["capex_outlook"] = line.strip()
                    break
        
        return guidance


# ──── CLI Functions ────
async def main():
    """CLI entry point for testing"""
    import asyncio
    
    collector = EarningsCallCollector()
    
    # Test manual upload
    ticker = "005930"
    company_name = "삼성전자"
    quarter = "2024Q3"
    content = """
    [Earnings Call Transcript]
    
    Q3 2024 Earnings Call
    
    Management Guidance:
    - Revenue outlook: Strong growth expected in Q4
    - Margin outlook: Stable margins maintained
    - Capex: Continued investment in new technologies
    
    Q&A Session:
    ...
    """
    
    metadata = {
        "call_date": "2024-10-24",
        "participants": ["CEO", "CFO", "Analysts"]
    }
    
    print(f"Uploading earnings call transcript for {company_name} ({ticker})...")
    
    source = await collector.upload_transcript(
        ticker=ticker,
        company_name=company_name,
        quarter=quarter,
        content=content,
        metadata=metadata
    )
    
    print(f"Created primary source: {source.title}")
    
    # Test guidance extraction
    guidance = collector.extract_management_guidance(content)
    print(f"Extracted guidance: {guidance}")


if __name__ == "__main__":
    asyncio.run(main())
