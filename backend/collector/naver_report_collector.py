"""
Naver Finance Report Collector

Collects securities reports from Naver Finance using Playwright.
Secondary source with authority weight 0.4.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser
import httpx
import PyPDF2
import re

from ..storage.models import PrimarySource


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NaverReport:
    """Data class for Naver Finance report"""
    ticker: str
    company_name: str
    title: str
    analyst: str
    brokerage: str
    published_date: datetime
    opinion: str  # "BUY", "HOLD", "SELL", "NEUTRAL"
    target_price: Optional[float]
    pdf_url: str
    report_url: str
    full_text: Optional[str] = None


class NaverReportCollector:
    """
    Collect securities reports from Naver Finance using Playwright.
    
    Authority Weight: 0.4 (Secondary Source)
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.base_url = "https://finance.naver.com"
        self.reports_url_template = "https://finance.naver.com/item/main.naver?code={ticker}"
        self.timeout = 30000  # 30 seconds

    async def collect_reports(
        self,
        ticker: str,
        company_name: str,
        limit: int = 50
    ) -> List[NaverReport]:
        """
        Collect recent reports for a given ticker.
        
        Args:
            ticker: Stock ticker (e.g., "005930" for 삼성전자)
            company_name: Company name (e.g., "삼성전자")
            limit: Maximum number of reports to collect
            
        Returns:
            List of NaverReport objects
        """
        logger.info(f"Starting Naver report collection for {ticker} ({company_name})")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            
            try:
                # Navigate to main page
                await page.goto(
                    self.reports_url_template.format(ticker=ticker),
                    timeout=self.timeout
                )
                await page.wait_for_load_state("networkidle")
                
                # Click on "종목분석" tab
                await page.click('a[href*="#tab1"]', timeout=self.timeout)
                await page.wait_for_load_state("networkidle")
                
                # Click on "투자의견종합" or "애널리스트"
                try:
                    await page.click('text="투자의견종합"', timeout=5000)
                except:
                    try:
                        await page.click('text="애널리스트"', timeout=5000)
                    except:
                        logger.warning("Could not find analyst report tab")
                        await browser.close()
                        return []
                
                await page.wait_for_load_state("networkidle")
                
                # Extract report list
                reports = await self._extract_report_list(page, ticker, company_name, limit)
                
                # Download and extract text for each report
                for report in reports:
                    try:
                        report.full_text = await self._extract_report_text(report)
                    except Exception as e:
                        logger.error(f"Failed to extract text for report {report.title}: {e}")
                        report.full_text = None
                
                await browser.close()
                return reports
                
            except Exception as e:
                logger.error(f"Error collecting reports for {ticker}: {e}")
                await browser.close()
                return []

    async def _extract_report_list(
        self,
        page: Page,
        ticker: str,
        company_name: str,
        limit: int
    ) -> List[NaverReport]:
        """
        Extract report list from the page.
        
        Args:
            page: Playwright page object
            ticker: Stock ticker
            company_name: Company name
            limit: Maximum number of reports
            
        Returns:
            List of NaverReport objects
        """
        reports = []
        
        # Wait for table to load
        try:
            await page.wait_for_selector('table.type_2', timeout=10000)
        except:
            logger.warning("Report table not found")
            return reports
        
        # Extract rows from table
        rows = await page.query_selector_all('table.type_2 tbody tr')
        
        for i, row in enumerate(rows[:limit]):
            try:
                # Extract cells
                cells = await row.query_selector_all('td')
                if len(cells) < 6:
                    continue
                
                # Date
                date_text = await cells[0].inner_text()
                published_date = self._parse_date(date_text)
                
                # Opinion (BUY/HOLD/SELL)
                opinion_text = await cells[1].inner_text()
                opinion = self._parse_opinion(opinion_text)
                
                # Target price
                target_price_text = await cells[2].inner_text()
                target_price = self._parse_target_price(target_price_text)
                
                # Brokerage
                brokerage = await cells[3].inner_text()
                brokerage = brokerage.strip()
                
                # Analyst
                analyst = await cells[4].inner_text()
                analyst = analyst.strip()
                
                # Title and URL
                title_link = await cells[5].query_selector('a')
                if title_link:
                    title = await title_link.inner_text()
                    report_url = await title_link.get_attribute('href')
                    if report_url and not report_url.startswith('http'):
                        report_url = self.base_url + report_url
                    
                    # Get PDF URL
                    pdf_url = await self._get_pdf_url(page, report_url)
                    
                    report = NaverReport(
                        ticker=ticker,
                        company_name=company_name,
                        title=title.strip(),
                        analyst=analyst,
                        brokerage=brokerage,
                        published_date=published_date,
                        opinion=opinion,
                        target_price=target_price,
                        pdf_url=pdf_url,
                        report_url=report_url
                    )
                    reports.append(report)
                    
            except Exception as e:
                logger.warning(f"Failed to parse row {i}: {e}")
                continue
        
        logger.info(f"Extracted {len(reports)} reports from Naver")
        return reports

    async def _get_pdf_url(self, page: Page, report_url: str) -> Optional[str]:
        """
        Get PDF URL from report detail page.
        
        Args:
            page: Playwright page object
            report_url: URL of the report
            
        Returns:
            PDF URL or None
        """
        try:
            # Navigate to report page
            await page.goto(report_url, timeout=self.timeout)
            await page.wait_for_load_state("networkidle")
            
            # Look for PDF download link
            pdf_link = await page.query_selector('a[href*=".pdf"]')
            if pdf_link:
                pdf_url = await pdf_link.get_attribute('href')
                if pdf_url and not pdf_url.startswith('http'):
                    pdf_url = self.base_url + pdf_url
                return pdf_url
            
            # Alternative: look for download button
            download_button = await page.query_selector('button:has-text("PDF")')
            if download_button:
                # This might trigger a download, return None for now
                return None
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get PDF URL from {report_url}: {e}")
            return None

    async def _extract_report_text(self, report: NaverReport) -> Optional[str]:
        """
        Extract text from PDF report.
        
        Args:
            report: NaverReport object
            
        Returns:
            Extracted text or None
        """
        if not report.pdf_url:
            return None
        
        try:
            # Download PDF
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(report.pdf_url)
                response.raise_for_status()
                
                # Save to temporary file
                temp_path = Path(f"/tmp/naver_report_{report.ticker}_{datetime.now().timestamp()}.pdf")
                temp_path.write_bytes(response.content)
                
                # Extract text using PyPDF2
                text = ""
                with open(temp_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                
                # Clean up
                temp_path.unlink()
                
                return text.strip()
                
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {report.pdf_url}: {e}")
            return None

    def _parse_date(self, date_text: str) -> datetime:
        """
        Parse date string from Naver format.
        
        Args:
            date_text: Date string (e.g., "2024.02.15")
            
        Returns:
            datetime object
        """
        try:
            # Format: "2024.02.15"
            match = re.match(r'(\d{4})\.(\d{2})\.(\d{2})', date_text)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day))
            
            # Alternative format: "24.02.15"
            match = re.match(r'(\d{2})\.(\d{2})\.(\d{2})', date_text)
            if match:
                year, month, day = match.groups()
                year = 2000 + int(year)  # Assume 20xx
                return datetime(year, int(month), int(day))
            
            return datetime.now()
            
        except Exception as e:
            logger.warning(f"Failed to parse date {date_text}: {e}")
            return datetime.now()

    def _parse_opinion(self, opinion_text: str) -> str:
        """
        Parse opinion string.
        
        Args:
            opinion_text: Opinion text (e.g., "매수", "홀드")
            
        Returns:
            Opinion code ("BUY", "HOLD", "SELL", "NEUTRAL")
        """
        opinion_text = opinion_text.strip().upper()
        
        if "매수" in opinion_text or "BUY" in opinion_text:
            return "BUY"
        elif "매도" in opinion_text or "SELL" in opinion_text:
            return "SELL"
        elif "홀드" in opinion_text or "HOLD" in opinion_text or "중립" in opinion_text:
            return "HOLD"
        else:
            return "NEUTRAL"

    def _parse_target_price(self, price_text: str) -> Optional[float]:
        """
        Parse target price string.
        
        Args:
            price_text: Price text (e.g., "85,000", "N/A")
            
        Returns:
            Target price or None
        """
        try:
            # Remove commas and whitespace
            cleaned = price_text.replace(',', '').strip()
            
            # Check for N/A or similar
            if cleaned in ['N/A', '-', '', '없음']:
                return None
            
            return float(cleaned)
            
        except Exception as e:
            logger.warning(f"Failed to parse target price {price_text}: {e}")
            return None


async def save_naver_report_to_db(
    report: NaverReport,
    db_session
) -> PrimarySource:
    """
    Save Naver report to database as PrimarySource.
    
    Args:
        report: NaverReport object
        db_session: Database session
        
    Returns:
        PrimarySource object
    """
    # Create metadata JSON
    metadata = {
        "analyst": report.analyst,
        "brokerage": report.brokerage,
        "opinion": report.opinion,
        "target_price": report.target_price,
        "pdf_url": report.pdf_url,
        "report_url": report.report_url
    }
    
    import json
    metadata_json = json.dumps(metadata, ensure_ascii=False)
    
    primary_source = PrimarySource(
        ticker=report.ticker,
        company_name=report.company_name,
        source_type="NAVER_REPORT",  # New source type
        title=report.title,
        published_at=report.published_date,
        content=report.full_text or "",
        authority_weight=0.4,  # Secondary source
        extra_metadata=metadata_json,
        source_url=report.report_url
    )
    
    db_session.add(primary_source)
    db_session.commit()
    db_session.refresh(primary_source)
    
    logger.info(f"Saved Naver report to DB: {report.title}")
    return primary_source


# CLI for testing
async def main():
    """Test the collector"""
    collector = NaverReportCollector(headless=False)
    
    # Test with 삼성전자
    reports = await collector.collect_reports(
        ticker="005930",
        company_name="삼성전자",
        limit=5
    )
    
    print(f"\nCollected {len(reports)} reports:")
    for i, report in enumerate(reports, 1):
        print(f"\n{i}. {report.title}")
        print(f"   Date: {report.published_date}")
        print(f"   Opinion: {report.opinion}")
        print(f"   Target Price: {report.target_price}")
        print(f"   Brokerage: {report.brokerage}")
        print(f"   Analyst: {report.analyst}")
        print(f"   PDF URL: {report.pdf_url}")
        if report.full_text:
            print(f"   Text length: {len(report.full_text)} characters")


if __name__ == "__main__":
    asyncio.run(main())
