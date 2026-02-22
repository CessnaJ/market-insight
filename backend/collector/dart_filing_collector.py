"""DART Filing Collector

Collects DART (Data Analysis, Retrieval and Transfer System) filings for Korean stocks.
Uses DART Open API to retrieve company filings.

DART API Documentation: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=001
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx
from sqlmodel import Session

from storage.db import get_session, add_primary_source
from storage.models import PrimarySource


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DARTFiling:
    """DART filing data structure"""
    corp_code: str  # DART corporation code
    corp_name: str  # Company name
    rcept_no: str  # Unique filing ID
    report_nm: str  # Report name
    rcept_dt: str  # Receipt date (YYYYMMDD)
    flr_nm: str  # Filer name
    report_url: str  # URL to download
    content: str  # Extracted text content
    source_type: str = "DART_FILING"
    authority_weight: float = 1.0


class DARTFilingCollector:
    """
    DART filing collector using DART Open API.

    Usage:
        collector = DARTFilingCollector()
        await collector.collect_filings("005930", days=30)
    """

    # DART API endpoints
    BASE_URL = "https://opendart.fss.or.kr/api"
    
    # Filing types
    FILING_TYPES = {
        "A": "반기보고서",  # Semi-annual report
        "Q": "사업보고서",  # Annual report
        "D": "분기보고서",  # Quarterly report
        "C": "감사보고서",  # Audit report
        "G": "주주총회소집",  # Shareholder meeting
        "M": "합병/분할보고서",  # M&A report
    }

    def __init__(self):
        """Initialize DART filing collector"""
        self.api_key = os.getenv("DART_API_KEY")
        if not self.api_key:
            logger.warning("DART_API_KEY not found in environment variables")
        
        self.corp_code_cache: Dict[str, str] = {}  # ticker -> corp_code cache

    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make async request to DART API.

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            API response as dictionary
        """
        if not self.api_key:
            raise ValueError("DART_API_KEY is required")

        params["crtfc_key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/{endpoint}",
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"DART API request failed: {e}")
            raise

    async def get_corp_code(self, corp_name: str) -> Optional[str]:
        """
        Get DART corporation code by company name.

        Args:
            corp_name: Company name (e.g., "삼성전자")

        Returns:
            Corporation code or None if not found
        """
        try:
            # Download corp code list
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/corpCode.xml",
                    params={"crtfc_key": self.api_key}
                )
                response.raise_for_status()
                
                # Parse XML response
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                
                for elem in root.findall("list"):
                    if elem.find("corp_name").text == corp_name:
                        return elem.find("corp_code").text
                
                logger.warning(f"Corporation code not found for {corp_name}")
                return None
        except Exception as e:
            logger.error(f"Failed to get corporation code: {e}")
            return None

    async def get_corp_code_by_ticker(self, ticker: str) -> Optional[str]:
        """
        Get DART corporation code by stock ticker.

        Note: This requires a mapping between tickers and corp codes.
        For now, we'll use a simple cache and common mappings.

        Args:
            ticker: Stock ticker (e.g., "005930")

        Returns:
            Corporation code or None if not found
        """
        # Check cache first
        if ticker in self.corp_code_cache:
            return self.corp_code_cache[ticker]
        
        # Common mappings (should be expanded or loaded from database)
        ticker_to_corp = {
            "005930": "00126380",  # 삼성전자
            "000660": "00567578",  # SK하이닉스
            "035420": "00634142",  # NAVER
            "035720": "00541938",  # 카카오
            "005380": "00164742",  # 현대차
            "051910": "00164761",  # LG화학
            "066570": "00126385",  # LG전자
        }
        
        corp_code = ticker_to_corp.get(ticker)
        if corp_code:
            self.corp_code_cache[ticker] = corp_code
        
        return corp_code

    async def search_filings(
        self,
        corp_code: str,
        start_date: str,
        end_date: str,
        filing_type: Optional[str] = None,
        page_count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for filings using DART API.

        Args:
            corp_code: DART corporation code
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            filing_type: Optional filing type filter (A, Q, D, C, G, M)
            page_count: Number of items per page

        Returns:
            List of filing metadata
        """
        params = {
            "bgn_de": start_date,
            "end_de": end_date,
            "corp_code": corp_code,
            "page_count": page_count
        }
        
        if filing_type:
            params["pblntf_ty"] = filing_type
        
        result = await self._make_request("list.json", params)
        
        if result.get("status") != "000":
            logger.error(f"DART API error: {result.get('message')}")
            return []
        
        return result.get("list", [])

    async def get_filing_detail(self, rcept_no: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed filing content.

        Args:
            rcept_no: Unique filing ID

        Returns:
            Filing detail data or None
        """
        params = {"rcept_no": rcept_no}
        result = await self._make_request("dses001.ax", params)
        
        if result.get("status") != "000":
            logger.error(f"DART API error: {result.get('message')}")
            return None
        
        return result.get("list", [{}])[0] if result.get("list") else None

    async def _extract_filing_content(self, filing_url: str) -> str:
        """
        Extract text content from filing URL.

        Args:
            filing_url: URL to filing document

        Returns:
            Extracted text content
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(filing_url)
                response.raise_for_status()
                
                # For HTML filings, extract text
                if "html" in response.headers.get("content-type", ""):
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.content, "html.parser")
                    return soup.get_text(separator="\n", strip=True)
                
                # For other formats, return raw content
                return response.text[:10000]  # Limit content size
        except Exception as e:
            logger.error(f"Failed to extract filing content: {e}")
            return ""

    async def collect_filings(
        self,
        ticker: str,
        company_name: str,
        days: int = 30,
        filing_type: Optional[str] = None,
        session: Optional[Session] = None
    ) -> List[PrimarySource]:
        """
        Collect DART filings for a ticker.

        Args:
            ticker: Stock ticker (e.g., "005930")
            company_name: Company name (e.g., "삼성전자")
            days: Number of days to look back
            filing_type: Optional filing type filter
            session: Database session (optional)

        Returns:
            List of created PrimarySource objects
        """
        logger.info(f"Collecting DART filings for {ticker} ({company_name})")
        
        # Get corporation code
        corp_code = await self.get_corp_code_by_ticker(ticker)
        if not corp_code:
            logger.error(f"Could not find corporation code for {ticker}")
            return []
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")
        
        # Search for filings
        filings = await self.search_filings(
            corp_code=corp_code,
            start_date=start_date_str,
            end_date=end_date_str,
            filing_type=filing_type
        )
        
        logger.info(f"Found {len(filings)} filings")
        
        # Process filings
        created_sources = []
        session_provided = session is not None
        
        if not session_provided:
            session = next(get_session())
        
        try:
            for filing in filings:
                # Check if already exists
                existing = session.exec(
                    select(PrimarySource).where(
                        PrimarySource.source_url == filing.get("rcept_no")
                    )
                ).first()
                
                if existing:
                    logger.debug(f"Filing already exists: {filing.get('rcept_no')}")
                    continue
                
                # Create primary source
                primary_source = PrimarySource(
                    ticker=ticker,
                    company_name=company_name,
                    source_type="DART_FILING",
                    title=filing.get("report_nm", ""),
                    published_at=datetime.strptime(filing.get("rcept_dt"), "%Y%m%d"),
                    content="",  # Will be updated if detail is fetched
                    authority_weight=1.0,  # Primary source
                    extra_metadata=str(filing),  # Store metadata as JSON string
                    source_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={filing.get('rcept_no')}"
                )
                
                # Try to get detail content
                try:
                    detail = await self.get_filing_detail(filing.get("rcept_no"))
                    if detail:
                        primary_source.content = str(detail)
                except Exception as e:
                    logger.warning(f"Failed to get filing detail: {e}")
                
                # Save to database
                created_source = add_primary_source(session, primary_source)
                created_sources.append(created_source)
                logger.info(f"Created primary source: {primary_source.title}")
        
        finally:
            if not session_provided:
                session.close()
        
        logger.info(f"Created {len(created_sources)} primary sources")
        return created_sources

    async def collect_quarterly_reports(
        self,
        ticker: str,
        company_name: str,
        quarters: int = 4,
        session: Optional[Session] = None
    ) -> List[PrimarySource]:
        """
        Collect quarterly reports for a ticker.

        Args:
            ticker: Stock ticker
            company_name: Company name
            quarters: Number of quarters to collect
            session: Database session (optional)

        Returns:
            List of created PrimarySource objects
        """
        days = quarters * 90  # Approximate days per quarter
        return await self.collect_filings(
            ticker=ticker,
            company_name=company_name,
            days=days,
            filing_type="D",  # Quarterly report
            session=session
        )

    async def collect_annual_reports(
        self,
        ticker: str,
        company_name: str,
        years: int = 2,
        session: Optional[Session] = None
    ) -> List[PrimarySource]:
        """
        Collect annual reports for a ticker.

        Args:
            ticker: Stock ticker
            company_name: Company name
            years: Number of years to collect
            session: Database session (optional)

        Returns:
            List of created PrimarySource objects
        """
        days = years * 365
        return await self.collect_filings(
            ticker=ticker,
            company_name=company_name,
            days=days,
            filing_type="Q",  # Annual report
            session=session
        )


# ──── CLI Functions ────
async def main():
    """CLI entry point for testing"""
    import asyncio
    
    collector = DARTFilingCollector()
    
    # Test with Samsung Electronics
    ticker = "005930"
    company_name = "삼성전자"
    
    print(f"Collecting DART filings for {company_name} ({ticker})...")
    
    sources = await collector.collect_quarterly_reports(
        ticker=ticker,
        company_name=company_name,
        quarters=2
    )
    
    print(f"Collected {len(sources)} filings")


if __name__ == "__main__":
    asyncio.run(main())
