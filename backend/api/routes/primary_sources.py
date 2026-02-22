"""Primary Sources API Routes

Endpoints for managing primary data sources (DART filings, earnings calls, etc.)
for Korean securities data.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from pydantic import BaseModel

from storage.db import (
    get_session,
    add_primary_source,
    get_primary_sources_by_ticker,
    get_primary_source_by_id,
    get_recent_primary_sources,
    delete_primary_source
)
from storage.models import PrimarySource
from collector.dart_filing_collector import DARTFilingCollector
from collector.earnings_call_collector import EarningsCallCollector


router = APIRouter(prefix="/primary-sources", tags=["Primary Sources"])


# ──── Pydantic Models for Request/Response ────
class PrimarySourceResponse(BaseModel):
    """Primary source response model"""
    id: str
    ticker: str
    company_name: Optional[str]
    source_type: str
    title: str
    published_at: datetime
    authority_weight: float
    extra_metadata: Optional[str]
    source_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class EarningsCallUploadRequest(BaseModel):
    """Request model for earnings call upload"""
    ticker: str
    company_name: str
    quarter: str
    call_date: str
    content: str
    extra_metadata: Optional[Dict[str, Any]] = None


class DARTCollectionRequest(BaseModel):
    """Request model for DART collection"""
    ticker: str
    company_name: str
    days: int = 30
    filing_type: Optional[str] = None


# ──── Primary Source Retrieval ────
@router.get("/", response_model=List[dict])
async def list_primary_sources(
    limit: int = 20,
    source_type: Optional[str] = None,
    ticker: Optional[str] = None
):
    """
    Get recent primary sources.

    Args:
        limit: Number of items to return
        source_type: Filter by source type (EARNINGS_CALL, DART_FILING, IR_MATERIAL)
        ticker: Filter by ticker

    Returns:
        List of primary source items
    """
    with next(get_session()) as session:
        if ticker:
            sources = get_primary_sources_by_ticker(
                session=session,
                ticker=ticker,
                source_type=source_type,
                limit=limit
            )
        else:
            sources = get_recent_primary_sources(
                session=session,
                source_type=source_type,
                limit=limit
            )

        return [
            {
                "id": s.id,
                "ticker": s.ticker,
                "company_name": s.company_name,
                "source_type": s.source_type,
                "title": s.title,
                "published_at": s.published_at.isoformat(),
                "authority_weight": s.authority_weight,
                "extra_metadata": s.extra_metadata,
                "source_url": s.source_url,
                "created_at": s.created_at.isoformat()
            }
            for s in sources
        ]


@router.get("/{source_id}", response_model=dict)
async def get_primary_source(source_id: str):
    """
    Get a specific primary source by ID.

    Args:
        source_id: Primary source ID

    Returns:
        Primary source details
    """
    with next(get_session()) as session:
        source = get_primary_source_by_id(session, source_id)

        if not source:
            raise HTTPException(status_code=404, detail="Primary source not found")

        return {
            "id": source.id,
            "ticker": source.ticker,
            "company_name": source.company_name,
            "source_type": source.source_type,
            "title": source.title,
            "published_at": source.published_at.isoformat(),
            "content": source.content,
            "authority_weight": source.authority_weight,
            "extra_metadata": source.extra_metadata,
            "source_url": source.source_url,
            "file_path": source.file_path,
            "created_at": source.created_at.isoformat()
        }


@router.get("/ticker/{ticker}", response_model=List[dict])
async def get_primary_sources_by_ticker_endpoint(
    ticker: str,
    source_type: Optional[str] = None,
    limit: int = 50
):
    """
    Get primary sources for a specific ticker.

    Args:
        ticker: Stock ticker
        source_type: Filter by source type
        limit: Number of items to return

    Returns:
        List of primary source items
    """
    with next(get_session()) as session:
        sources = get_primary_sources_by_ticker(
            session=session,
            ticker=ticker,
            source_type=source_type,
            limit=limit
        )

        return [
            {
                "id": s.id,
                "ticker": s.ticker,
                "company_name": s.company_name,
                "source_type": s.source_type,
                "title": s.title,
                "published_at": s.published_at.isoformat(),
                "authority_weight": s.authority_weight,
                "extra_metadata": s.extra_metadata,
                "source_url": s.source_url,
                "created_at": s.created_at.isoformat()
            }
            for s in sources
        ]


@router.get("/earnings-calls/{ticker}", response_model=List[dict])
async def get_earnings_calls(ticker: str, limit: int = 20):
    """
    Get earnings call transcripts for a ticker.

    Args:
        ticker: Stock ticker
        limit: Number of items to return

    Returns:
        List of earnings call transcripts
    """
    with next(get_session()) as session:
        sources = get_primary_sources_by_ticker(
            session=session,
            ticker=ticker,
            source_type="EARNINGS_CALL",
            limit=limit
        )

        return [
            {
                "id": s.id,
                "ticker": s.ticker,
                "company_name": s.company_name,
                "title": s.title,
                "published_at": s.published_at.isoformat(),
                "authority_weight": s.authority_weight,
                "created_at": s.created_at.isoformat()
            }
            for s in sources
        ]


@router.get("/dart-filings/{ticker}", response_model=List[dict])
async def get_dart_filings(ticker: str, limit: int = 50):
    """
    Get DART filings for a ticker.

    Args:
        ticker: Stock ticker
        limit: Number of items to return

    Returns:
        List of DART filings
    """
    with next(get_session()) as session:
        sources = get_primary_sources_by_ticker(
            session=session,
            ticker=ticker,
            source_type="DART_FILING",
            limit=limit
        )

        return [
            {
                "id": s.id,
                "ticker": s.ticker,
                "company_name": s.company_name,
                "title": s.title,
                "published_at": s.published_at.isoformat(),
                "authority_weight": s.authority_weight,
                "extra_metadata": s.extra_metadata,
                "source_url": s.source_url,
                "created_at": s.created_at.isoformat()
            }
            for s in sources
        ]


# ──── Earnings Call Upload ────
@router.post("/earnings-calls/upload", response_model=dict)
async def upload_earnings_call(request: EarningsCallUploadRequest):
    """
    Upload an earnings call transcript.

    Args:
        request: Earnings call upload request

    Returns:
        Created primary source
    """
    collector = EarningsCallCollector()
    
    extra_metadata = request.extra_metadata or {}
    extra_metadata["call_date"] = request.call_date
    
    try:
        source = await collector.upload_transcript(
            ticker=request.ticker,
            company_name=request.company_name,
            quarter=request.quarter,
            content=request.content,
            metadata=extra_metadata
        )
        
        return {
            "id": source.id,
            "ticker": source.ticker,
            "company_name": source.company_name,
            "source_type": source.source_type,
            "title": source.title,
            "published_at": source.published_at.isoformat(),
            "authority_weight": source.authority_weight,
            "created_at": source.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload earnings call: {str(e)}")


@router.post("/earnings-calls/upload-file", response_model=dict)
async def upload_earnings_call_file(
    ticker: str,
    company_name: str,
    quarter: str,
    call_date: str,
    file: UploadFile = File(...),
    extra_metadata: Optional[str] = None
):
    """
    Upload an earnings call transcript from file.

    Args:
        ticker: Stock ticker
        company_name: Company name
        quarter: Quarter identifier
        call_date: Call date
        file: Uploaded file
        extra_metadata: Optional metadata as JSON string

    Returns:
        Created primary source
    """
    collector = EarningsCallCollector()
    
    # Parse metadata
    metadata_dict = json.loads(extra_metadata) if extra_metadata else {}
    metadata_dict["call_date"] = call_date
    
    # Read file content
    file_content = await file.read()
    
    try:
        source = await collector.upload_transcript(
            ticker=ticker,
            company_name=company_name,
            quarter=quarter,
            content="",  # Will be extracted from file
            metadata=metadata_dict,
            file_content=file_content,
            filename=file.filename
        )
        
        return {
            "id": source.id,
            "ticker": source.ticker,
            "company_name": source.company_name,
            "source_type": source.source_type,
            "title": source.title,
            "published_at": source.published_at.isoformat(),
            "authority_weight": source.authority_weight,
            "file_path": source.file_path,
            "created_at": source.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload earnings call file: {str(e)}")


# ──── DART Collection ────
@router.post("/dart/collect", response_model=dict)
async def collect_dart_filings(
    request: DARTCollectionRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger DART filing collection for a ticker.

    Args:
        request: DART collection request
        background_tasks: FastAPI background tasks

    Returns:
        Collection status
    """
    collector = DARTFilingCollector()
    
    def collect_task():
        import asyncio
        asyncio.run(collector.collect_filings(
            ticker=request.ticker,
            company_name=request.company_name,
            days=request.days,
            filing_type=request.filing_type
        ))
    
    background_tasks.add_task(collect_task)
    
    return {
        "status": "started",
        "message": f"DART collection started for {request.ticker}",
        "ticker": request.ticker,
        "company_name": request.company_name,
        "days": request.days,
        "filing_type": request.filing_type
    }


@router.post("/dart/quarterly-reports", response_model=dict)
async def collect_quarterly_reports(
    ticker: str,
    company_name: str,
    quarters: int = 4,
    background_tasks: BackgroundTasks = None
):
    """
    Collect quarterly reports from DART for a ticker.

    Args:
        ticker: Stock ticker
        company_name: Company name
        quarters: Number of quarters to collect
        background_tasks: FastAPI background tasks

    Returns:
        Collection status
    """
    collector = DARTFilingCollector()
    
    def collect_task():
        import asyncio
        asyncio.run(collector.collect_quarterly_reports(
            ticker=ticker,
            company_name=company_name,
            quarters=quarters
        ))
    
    if background_tasks:
        background_tasks.add_task(collect_task)
    else:
        # Run synchronously if no background tasks
        import asyncio
        asyncio.run(collect_task())
    
    return {
        "status": "started",
        "message": f"Quarterly reports collection started for {ticker}",
        "ticker": ticker,
        "company_name": company_name,
        "quarters": quarters
    }


@router.post("/dart/annual-reports", response_model=dict)
async def collect_annual_reports(
    ticker: str,
    company_name: str,
    years: int = 2,
    background_tasks: BackgroundTasks = None
):
    """
    Collect annual reports from DART for a ticker.

    Args:
        ticker: Stock ticker
        company_name: Company name
        years: Number of years to collect
        background_tasks: FastAPI background tasks

    Returns:
        Collection status
    """
    collector = DARTFilingCollector()
    
    def collect_task():
        import asyncio
        asyncio.run(collector.collect_annual_reports(
            ticker=ticker,
            company_name=company_name,
            years=years
        ))
    
    if background_tasks:
        background_tasks.add_task(collect_task)
    else:
        # Run synchronously if no background tasks
        import asyncio
        asyncio.run(collect_task())
    
    return {
        "status": "started",
        "message": f"Annual reports collection started for {ticker}",
        "ticker": ticker,
        "company_name": company_name,
        "years": years
    }


# ──── Primary Source Management ────
@router.delete("/{source_id}", response_model=dict)
async def delete_primary_source_endpoint(source_id: str):
    """
    Delete a primary source by ID.

    Args:
        source_id: Primary source ID

    Returns:
        Deletion status
    """
    with next(get_session()) as session:
        success = delete_primary_source(session, source_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Primary source not found")
        
        return {
            "status": "deleted",
            "id": source_id
        }


# ──── Source Authority Info ────
@router.get("/authority/weights", response_model=dict)
async def get_authority_weights():
    """
    Get information about source authority weights.

    Returns:
        Authority weight information
    """
    return {
        "primary_sources": {
            "weight": 1.0,
            "description": "Primary sources have full authority weight",
            "types": ["EARNINGS_CALL", "DART_FILING", "IR_MATERIAL"]
        },
        "secondary_sources": {
            "weight": 0.4,
            "description": "Secondary sources have reduced authority weight",
            "types": ["NAVER_REPORT", "YOUTUBE", "BLOG"]
        }
    }
