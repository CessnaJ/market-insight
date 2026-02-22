"""Temporal Analysis API Routes

Endpoints for temporal signal decomposition and price attribution analysis.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlmodel import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel
import json

from storage.db import (
    get_session,
    add_price_attribution,
    get_price_attributions_by_ticker,
    get_price_attribution_by_id,
    get_price_attribution_by_date,
    update_price_attribution,
    delete_price_attribution
)
from storage.models import PriceAttribution
from analyzer.temporal_decomposer import (
    TemporalSignalDecomposer,
    TemporalAnalysisResult,
    decompose_price_signal
)


router = APIRouter(prefix="/temporal-analysis", tags=["Temporal Analysis"])


# ──── Pydantic Models for Request/Response ────
class PriceAttributionRequest(BaseModel):
    """Request model for price attribution analysis"""
    ticker: str
    company_name: Optional[str] = None
    event_date: date
    price_change_pct: float
    save_to_db: bool = True


class PriceAttributionResponse(BaseModel):
    """Response model for price attribution"""
    id: Optional[str]
    ticker: str
    company_name: Optional[str]
    event_date: date
    price_change_pct: float
    temporal_breakdown: Optional[str]
    ai_analysis_summary: Optional[str]
    confidence_score: Optional[float]
    dominant_timeframe: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemporalAnalysisDetailResponse(BaseModel):
    """Detailed response model for temporal analysis"""
    ticker: str
    company_name: Optional[str]
    event_date: date
    price_change_pct: float
    short_term_analysis: Dict[str, Any]
    medium_term_analysis: Dict[str, Any]
    long_term_analysis: Dict[str, Any]
    comprehensive_analysis: Dict[str, Any]
    confidence_score: float
    dominant_timeframe: str
    ai_analysis_summary: str


# ──── Price Attribution Retrieval ────
@router.get("/attributions", response_model=List[dict])
async def list_price_attributions(
    ticker: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 50
):
    """
    Get price attributions.

    Args:
        ticker: Filter by ticker
        start_date: Filter by start date
        end_date: Filter by end date
        limit: Number of items to return

    Returns:
        List of price attribution items
    """
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker parameter is required")

    with next(get_session()) as session:
        attributions = get_price_attributions_by_ticker(
            session=session,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return [
            {
                "id": a.id,
                "ticker": a.ticker,
                "company_name": a.company_name,
                "event_date": a.event_date.isoformat(),
                "price_change_pct": a.price_change_pct,
                "temporal_breakdown": a.temporal_breakdown,
                "ai_analysis_summary": a.ai_analysis_summary,
                "confidence_score": a.confidence_score,
                "dominant_timeframe": a.dominant_timeframe,
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat()
            }
            for a in attributions
        ]


@router.get("/attributions/{attribution_id}", response_model=dict)
async def get_price_attribution(attribution_id: str):
    """
    Get a specific price attribution by ID.

    Args:
        attribution_id: Price attribution ID

    Returns:
        Price attribution details
    """
    with next(get_session()) as session:
        attribution = get_price_attribution_by_id(session, attribution_id)

        if not attribution:
            raise HTTPException(status_code=404, detail="Price attribution not found")

        return {
            "id": attribution.id,
            "ticker": attribution.ticker,
            "company_name": attribution.company_name,
            "event_date": attribution.event_date.isoformat(),
            "price_change_pct": attribution.price_change_pct,
            "temporal_breakdown": attribution.temporal_breakdown,
            "ai_analysis_summary": attribution.ai_analysis_summary,
            "confidence_score": attribution.confidence_score,
            "dominant_timeframe": attribution.dominant_timeframe,
            "created_at": attribution.created_at.isoformat(),
            "updated_at": attribution.updated_at.isoformat()
        }


@router.get("/attributions/ticker/{ticker}/date/{event_date}", response_model=dict)
async def get_price_attribution_by_date_endpoint(ticker: str, event_date: date):
    """
    Get price attribution for a specific ticker and date.

    Args:
        ticker: Stock ticker
        event_date: Event date

    Returns:
        Price attribution details
    """
    with next(get_session()) as session:
        attribution = get_price_attribution_by_date(session, ticker, event_date)

        if not attribution:
            raise HTTPException(status_code=404, detail="Price attribution not found")

        return {
            "id": attribution.id,
            "ticker": attribution.ticker,
            "company_name": attribution.company_name,
            "event_date": attribution.event_date.isoformat(),
            "price_change_pct": attribution.price_change_pct,
            "temporal_breakdown": attribution.temporal_breakdown,
            "ai_analysis_summary": attribution.ai_analysis_summary,
            "confidence_score": attribution.confidence_score,
            "dominant_timeframe": attribution.dominant_timeframe,
            "created_at": attribution.created_at.isoformat(),
            "updated_at": attribution.updated_at.isoformat()
        }


# ──── Temporal Analysis ────
@router.post("/analyze", response_model=TemporalAnalysisDetailResponse)
async def analyze_price_signal(
    request: PriceAttributionRequest,
    background_tasks: Optional[BackgroundTasks] = None
):
    """
    Analyze price signal and decompose into temporal factors.

    Args:
        request: Price attribution request
        background_tasks: FastAPI background tasks

    Returns:
        Complete temporal analysis result
    """
    try:
        if background_tasks and request.save_to_db:
            # Run analysis in background
            def analyze_task():
                result = decompose_price_signal(
                    ticker=request.ticker,
                    event_date=request.event_date,
                    price_change_pct=request.price_change_pct,
                    company_name=request.company_name,
                    save_to_db=True
                )
                return result
            
            background_tasks.add_task(analyze_task)
            
            return {
                "ticker": request.ticker,
                "company_name": request.company_name,
                "event_date": request.event_date,
                "price_change_pct": request.price_change_pct,
                "short_term_analysis": {},
                "medium_term_analysis": {},
                "long_term_analysis": {},
                "comprehensive_analysis": {},
                "confidence_score": 0.0,
                "dominant_timeframe": "processing",
                "ai_analysis_summary": "Analysis running in background"
            }
        else:
            # Run synchronously
            result = decompose_price_signal(
                ticker=request.ticker,
                event_date=request.event_date,
                price_change_pct=request.price_change_pct,
                company_name=request.company_name,
                save_to_db=request.save_to_db
            )
            
            return {
                "ticker": result.ticker,
                "company_name": result.company_name,
                "event_date": result.event_date,
                "price_change_pct": result.price_change_pct,
                "short_term_analysis": result.short_term_analysis,
                "medium_term_analysis": result.medium_term_analysis,
                "long_term_analysis": result.long_term_analysis,
                "comprehensive_analysis": result.comprehensive_analysis,
                "confidence_score": result.confidence_score,
                "dominant_timeframe": result.dominant_timeframe,
                "ai_analysis_summary": result.ai_analysis_summary
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze/batch", response_model=List[dict])
async def analyze_price_signals_batch(
    requests: List[PriceAttributionRequest],
    background_tasks: BackgroundTasks
):
    """
    Analyze multiple price signals in batch.

    Args:
        requests: List of price attribution requests
        background_tasks: FastAPI background tasks

    Returns:
        Batch analysis status
    """
    def batch_analyze():
        results = []
        for request in requests:
            try:
                result = decompose_price_signal(
                    ticker=request.ticker,
                    event_date=request.event_date,
                    price_change_pct=request.price_change_pct,
                    company_name=request.company_name,
                    save_to_db=request.save_to_db
                )
                results.append({
                    "ticker": request.ticker,
                    "event_date": request.event_date.isoformat(),
                    "status": "success",
                    "result_id": getattr(result, 'id', None)
                })
            except Exception as e:
                results.append({
                    "ticker": request.ticker,
                    "event_date": request.event_date.isoformat(),
                    "status": "failed",
                    "error": str(e)
                })
        return results
    
    background_tasks.add_task(batch_analyze)
    
    return {
        "status": "started",
        "message": f"Batch analysis started for {len(requests)} items",
        "items": [
            {
                "ticker": r.ticker,
                "event_date": r.event_date.isoformat(),
                "price_change_pct": r.price_change_pct
            }
            for r in requests
        ]
    }


# ──── Price Attribution Management ────
@router.put("/attributions/{attribution_id}", response_model=dict)
async def update_price_attribution_endpoint(
    attribution_id: str,
    price_change_pct: Optional[float] = None,
    temporal_breakdown: Optional[str] = None,
    ai_analysis_summary: Optional[str] = None,
    confidence_score: Optional[float] = None,
    dominant_timeframe: Optional[str] = None
):
    """
    Update a price attribution.

    Args:
        attribution_id: Price attribution ID
        price_change_pct: New price change percentage
        temporal_breakdown: New temporal breakdown (JSON string)
        ai_analysis_summary: New AI analysis summary
        confidence_score: New confidence score
        dominant_timeframe: New dominant timeframe

    Returns:
        Updated price attribution
    """
    with next(get_session()) as session:
        # Build update kwargs
        update_kwargs = {}
        if price_change_pct is not None:
            update_kwargs["price_change_pct"] = price_change_pct
        if temporal_breakdown is not None:
            update_kwargs["temporal_breakdown"] = temporal_breakdown
        if ai_analysis_summary is not None:
            update_kwargs["ai_analysis_summary"] = ai_analysis_summary
        if confidence_score is not None:
            update_kwargs["confidence_score"] = confidence_score
        if dominant_timeframe is not None:
            update_kwargs["dominant_timeframe"] = dominant_timeframe
        
        if not update_kwargs:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        attribution = update_price_attribution(
            session=session,
            attribution_id=attribution_id,
            **update_kwargs
        )
        
        if not attribution:
            raise HTTPException(status_code=404, detail="Price attribution not found")
        
        return {
            "id": attribution.id,
            "ticker": attribution.ticker,
            "company_name": attribution.company_name,
            "event_date": attribution.event_date.isoformat(),
            "price_change_pct": attribution.price_change_pct,
            "temporal_breakdown": attribution.temporal_breakdown,
            "ai_analysis_summary": attribution.ai_analysis_summary,
            "confidence_score": attribution.confidence_score,
            "dominant_timeframe": attribution.dominant_timeframe,
            "created_at": attribution.created_at.isoformat(),
            "updated_at": attribution.updated_at.isoformat()
        }


@router.delete("/attributions/{attribution_id}", response_model=dict)
async def delete_price_attribution_endpoint(attribution_id: str):
    """
    Delete a price attribution by ID.

    Args:
        attribution_id: Price attribution ID

    Returns:
        Deletion status
    """
    with next(get_session()) as session:
        success = delete_price_attribution(session, attribution_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Price attribution not found")
        
        return {
            "status": "deleted",
            "id": attribution_id
        }


# ──── Analysis Info ────
@router.get("/info/timeframes", response_model=dict)
async def get_timeframe_info():
    """
    Get information about temporal timeframes.

    Returns:
        Timeframe information
    """
    return {
        "short_term": {
            "description": "1 week or less",
            "factors": [
                "Supply and demand (foreigner, institution, retail)",
                "Market sentiment",
                "Macro shocks (interest rates, exchange rates)",
                "Recent news and filings"
            ]
        },
        "medium_term": {
            "description": "1 week to 3 months",
            "factors": [
                "Earnings revisions",
                "Sector rotation",
                "Valuation changes",
                "Analyst opinion changes",
                "Recent earnings announcements"
            ]
        },
        "long_term": {
            "description": "3 months or more",
            "factors": [
                "Structural competitiveness",
                "Market share trends",
                "Industry structure changes",
                "Technology and business model innovation",
                "Growth potential"
            ]
        }
    }


@router.get("/info/confidence-levels", response_model=dict)
async def get_confidence_level_info():
    """
    Get information about confidence levels.

    Returns:
        Confidence level information
    """
    return {
        "high": {
            "range": "0.7 - 1.0",
            "description": "High confidence in analysis with sufficient data"
        },
        "medium": {
            "range": "0.4 - 0.7",
            "description": "Moderate confidence with some data limitations"
        },
        "low": {
            "range": "0.0 - 0.4",
            "description": "Low confidence due to insufficient data"
        }
    }
