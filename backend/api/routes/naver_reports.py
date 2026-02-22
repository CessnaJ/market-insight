"""
Naver Finance Reports API

API endpoints for collecting and managing Naver Finance reports.
Secondary source with authority weight 0.4.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ...storage.db import get_session
from ...storage.models import PrimarySource
from ...collector.naver_report_collector import NaverReportCollector, save_naver_report_to_db
from ...analyzer.parent_child_indexer import ParentChildIndexer


router = APIRouter(prefix="/api/v1/naver-reports", tags=["naver-reports"])


# Request/Response Models
class NaverReportCollectionRequest(BaseModel):
    """Request model for collecting Naver reports"""
    ticker: str = Field(..., description="Stock ticker (e.g., '005930' for 삼성전자)")
    company_name: str = Field(..., description="Company name (e.g., '삼성전자')")
    limit: int = Field(default=50, ge=1, le=200, description="Maximum number of reports to collect")
    headless: bool = Field(default=True, description="Run browser in headless mode")


class NaverReportResponse(BaseModel):
    """Response model for Naver report"""
    id: str
    ticker: str
    company_name: str
    title: str
    analyst: str
    brokerage: str
    published_at: datetime
    opinion: str
    target_price: Optional[float]
    pdf_url: Optional[str]
    report_url: str
    content_length: Optional[int] = None


class BatchCollectionRequest(BaseModel):
    """Request model for batch collection"""
    tickers: List[dict] = Field(
        ...,
        description="List of {ticker, company_name} pairs"
    )
    limit_per_ticker: int = Field(default=20, ge=1, le=100)


class CollectionStatusResponse(BaseModel):
    """Response model for collection status"""
    status: str
    message: str
    reports_collected: int
    ticker: str


# Background task for async collection
async def collect_naver_reports_background(
    ticker: str,
    company_name: str,
    limit: int,
    headless: bool,
    session: Session
) -> dict:
    """
    Background task to collect Naver reports.
    
    Args:
        ticker: Stock ticker
        company_name: Company name
        limit: Maximum number of reports
        headless: Browser headless mode
        session: Database session
        
    Returns:
        Result dict with status and count
    """
    try:
        collector = NaverReportCollector(headless=headless)
        reports = await collector.collect_reports(ticker, company_name, limit)
        
        saved_count = 0
        for report in reports:
            if report.full_text:  # Only save reports with extracted text
                try:
                    await save_naver_report_to_db(report, session)
                    saved_count += 1
                except Exception as e:
                    print(f"Failed to save report: {e}")
        
        return {
            "status": "success",
            "message": f"Collected and saved {saved_count} reports",
            "reports_collected": saved_count,
            "ticker": ticker
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "reports_collected": 0,
            "ticker": ticker
        }


# API Endpoints
@router.post("/collect", response_model=CollectionStatusResponse)
async def collect_reports(
    request: NaverReportCollectionRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Collect Naver Finance reports for a given ticker.
    
    This endpoint runs the collection in the background and returns immediately.
    Use the /status endpoint to check collection progress.
    
    Authority Weight: 0.4 (Secondary Source)
    """
    # Start background task
    background_tasks.add_task(
        collect_naver_reports_background,
        request.ticker,
        request.company_name,
        request.limit,
        request.headless,
        session
    )
    
    return CollectionStatusResponse(
        status="started",
        message=f"Collection started for {request.ticker}",
        reports_collected=0,
        ticker=request.ticker
    )


@router.post("/collect/sync", response_model=List[NaverReportResponse])
async def collect_reports_sync(
    request: NaverReportCollectionRequest,
    session: Session = Depends(get_session)
):
    """
    Collect Naver Finance reports synchronously.
    
    This endpoint waits for collection to complete before returning.
    Use for small collections or testing.
    
    Authority Weight: 0.4 (Secondary Source)
    """
    collector = NaverReportCollector(headless=request.headless)
    reports = await collector.collect_reports(
        request.ticker,
        request.company_name,
        request.limit
    )
    
    saved_reports = []
    for report in reports:
        if report.full_text:
            try:
                saved = await save_naver_report_to_db(report, session)
                saved_reports.append(NaverReportResponse(
                    id=saved.id,
                    ticker=saved.ticker,
                    company_name=saved.company_name,
                    title=saved.title,
                    analyst=report.analyst,
                    brokerage=report.brokerage,
                    published_at=saved.published_at,
                    opinion=report.opinion,
                    target_price=report.target_price,
                    pdf_url=report.pdf_url,
                    report_url=report.report_url,
                    content_length=len(report.full_text) if report.full_text else None
                ))
            except Exception as e:
                print(f"Failed to save report: {e}")
    
    return saved_reports


@router.post("/batch", response_model=List[CollectionStatusResponse])
async def collect_batch(
    request: BatchCollectionRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Collect Naver reports for multiple tickers.
    
    Starts background tasks for each ticker.
    
    Authority Weight: 0.4 (Secondary Source)
    """
    results = []
    
    for item in request.tickers:
        ticker = item.get("ticker")
        company_name = item.get("company_name")
        
        if not ticker or not company_name:
            continue
        
        # Start background task
        background_tasks.add_task(
            collect_naver_reports_background,
            ticker,
            company_name,
            request.limit_per_ticker,
            True,  # headless
            session
        )
        
        results.append(CollectionStatusResponse(
            status="started",
            message=f"Collection started for {ticker}",
            reports_collected=0,
            ticker=ticker
        ))
    
    return results


@router.get("/list", response_model=List[NaverReportResponse])
async def list_reports(
    ticker: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session)
):
    """
    List collected Naver reports.
    
    Authority Weight: 0.4 (Secondary Source)
    """
    query = session.query(PrimarySource).filter(
        PrimarySource.source_type == "NAVER_REPORT"
    )
    
    if ticker:
        query = query.filter(PrimarySource.ticker == ticker)
    
    query = query.order_by(PrimarySource.published_at.desc())
    query = query.offset(offset).limit(limit)
    
    reports = query.all()
    
    result = []
    for report in reports:
        # Parse metadata
        import json
        metadata = {}
        if report.extra_metadata:
            try:
                metadata = json.loads(report.extra_metadata)
            except:
                pass
        
        result.append(NaverReportResponse(
            id=report.id,
            ticker=report.ticker,
            company_name=report.company_name or "",
            title=report.title,
            analyst=metadata.get("analyst", ""),
            brokerage=metadata.get("brokerage", ""),
            published_at=report.published_at,
            opinion=metadata.get("opinion", "NEUTRAL"),
            target_price=metadata.get("target_price"),
            pdf_url=metadata.get("pdf_url"),
            report_url=report.source_url,
            content_length=len(report.content) if report.content else None
        ))
    
    return result


@router.get("/{report_id}", response_model=NaverReportResponse)
async def get_report(
    report_id: str,
    session: Session = Depends(get_session)
):
    """
    Get a specific Naver report by ID.
    
    Authority Weight: 0.4 (Secondary Source)
    """
    report = session.query(PrimarySource).filter(
        PrimarySource.id == report_id,
        PrimarySource.source_type == "NAVER_REPORT"
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Parse metadata
    import json
    metadata = {}
    if report.extra_metadata:
        try:
            metadata = json.loads(report.extra_metadata)
        except:
            pass
    
    return NaverReportResponse(
        id=report.id,
        ticker=report.ticker,
        company_name=report.company_name or "",
        title=report.title,
        analyst=metadata.get("analyst", ""),
        brokerage=metadata.get("brokerage", ""),
        published_at=report.published_at,
        opinion=metadata.get("opinion", "NEUTRAL"),
        target_price=metadata.get("target_price"),
        pdf_url=metadata.get("pdf_url"),
        report_url=report.source_url,
        content_length=len(report.content) if report.content else None
    )


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    session: Session = Depends(get_session)
):
    """
    Delete a Naver report.
    """
    report = session.query(PrimarySource).filter(
        PrimarySource.id == report_id,
        PrimarySource.source_type == "NAVER_REPORT"
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    session.delete(report)
    session.commit()
    
    return {"status": "deleted", "report_id": report_id}


@router.get("/stats/summary")
async def get_stats(
    ticker: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Get statistics about collected Naver reports.
    
    Authority Weight: 0.4 (Secondary Source)
    """
    query = session.query(PrimarySource).filter(
        PrimarySource.source_type == "NAVER_REPORT"
    )
    
    if ticker:
        query = query.filter(PrimarySource.ticker == ticker)
    
    total_reports = query.count()
    
    # Get opinion distribution
    import json
    opinion_counts = {"BUY": 0, "HOLD": 0, "SELL": 0, "NEUTRAL": 0}
    
    for report in query.all():
        if report.extra_metadata:
            try:
                metadata = json.loads(report.extra_metadata)
                opinion = metadata.get("opinion", "NEUTRAL")
                opinion_counts[opinion] = opinion_counts.get(opinion, 0) + 1
            except:
                pass
    
    return {
        "total_reports": total_reports,
        "opinion_distribution": opinion_counts,
        "authority_weight": 0.4,
        "source_type": "NAVER_REPORT"
    }


@router.post("/index/{report_id}")
async def index_report(
    report_id: str,
    session: Session = Depends(get_session)
):
    """
    Index a Naver report into parent-child chunks for weighted search.
    
    Authority Weight: 0.4 (Secondary Source)
    """
    report = session.query(PrimarySource).filter(
        PrimarySource.id == report_id,
        PrimarySource.source_type == "NAVER_REPORT"
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    try:
        indexer = ParentChildIndexer()
        result = indexer.index_primary_source(report_id)
        
        return {
            "status": "indexed",
            "report_id": report_id,
            "total_chunks": result.get("total_chunks", 0),
            "summary_chunks": result.get("summary_chunks", 0),
            "detail_chunks": result.get("detail_chunks", 0),
            "authority_weight": 0.4
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.post("/index/batch")
async def index_batch(
    ticker: Optional[str] = None,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """
    Index multiple Naver reports into parent-child chunks.
    
    Authority Weight: 0.4 (Secondary Source)
    """
    query = session.query(PrimarySource).filter(
        PrimarySource.source_type == "NAVER_REPORT"
    )
    
    if ticker:
        query = query.filter(PrimarySource.ticker == ticker)
    
    query = query.order_by(PrimarySource.published_at.desc())
    query = query.limit(limit)
    
    reports = query.all()
    
    indexer = ParentChildIndexer()
    results = []
    
    for report in reports:
        try:
            result = indexer.index_primary_source(report.id)
            results.append({
                "report_id": report.id,
                "status": "indexed",
                "total_chunks": result.get("total_chunks", 0)
            })
        except Exception as e:
            results.append({
                "report_id": report.id,
                "status": "failed",
                "error": str(e)
            })
    
    return {
        "total_reports": len(reports),
        "indexed": len([r for r in results if r["status"] == "indexed"]),
        "failed": len([r for r in results if r["status"] == "failed"]),
        "results": results
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "naver-reports"}
