"""Assumptions API Routes

Endpoints for managing investment assumptions extracted from reports and filings.
Part of Sprint 3: Assumption Tracking System.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlmodel import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from storage.db import (
    get_session,
    add_investment_assumption,
    get_assumptions_by_ticker,
    get_pending_assumptions,
    get_assumption_by_id,
    validate_assumption,
    get_assumption_accuracy_stats,
    delete_assumption,
    get_all_assumptions
)
from storage.models import InvestmentAssumption
from analyzer.assumption_extractor import (
    AssumptionExtractor,
    extract_assumptions_from_content,
    convert_to_assumption_models
)
from scheduler.assumption_validator import (
    run_assumption_validation_job,
    validate_single_assumption,
    get_accuracy_trends
)


router = APIRouter(prefix="/assumptions", tags=["Assumptions"])


# ──── Pydantic Models for Request/Response ────
class AssumptionResponse(BaseModel):
    """Assumption response model"""
    id: str
    ticker: str
    company_name: Optional[str]
    assumption_text: str
    assumption_category: str
    time_horizon: str
    predicted_value: Optional[str]
    metric_name: Optional[str]
    verification_date: Optional[datetime]
    actual_value: Optional[str]
    is_correct: Optional[bool]
    validation_source: Optional[str]
    model_confidence_at_generation: float
    status: str
    source_type: Optional[str]
    source_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExtractAssumptionsRequest(BaseModel):
    """Request model for extracting assumptions"""
    content: str
    ticker: str
    company_name: Optional[str] = None
    source_type: str = "EARNINGS_CALL"
    source_id: Optional[str] = None


class ValidateAssumptionRequest(BaseModel):
    """Request model for validating an assumption"""
    actual_value: str
    is_correct: bool
    validation_source: Optional[str] = None


class AccuracyStatsResponse(BaseModel):
    """Accuracy statistics response model"""
    total: int
    correct: int
    incorrect: int
    accuracy: float
    by_category: Dict[str, Dict[str, Any]]
    by_time_horizon: Dict[str, Dict[str, Any]]


class ValidationJobResponse(BaseModel):
    """Validation job response model"""
    total_assumptions_checked: int
    successful_validations: int
    verified: int
    failed: int
    no_data: int
    results: List[Dict[str, Any]]


# ──── List Assumptions ────
@router.get("/", response_model=List[AssumptionResponse])
async def list_assumptions(
    ticker: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """
    Get all assumptions with optional filters.

    Args:
        ticker: Filter by ticker
        category: Filter by assumption category (REVENUE, MARGIN, MACRO, CAPACITY, MARKET_SHARE)
        status: Filter by status (PENDING, VERIFIED, FAILED)
        limit: Maximum number of items to return

    Returns:
        List of assumptions
    """
    with next(get_session()) as session:
        assumptions = get_all_assumptions(
            session=session,
            ticker=ticker,
            category=category,
            status=status,
            limit=limit
        )

        return [
            AssumptionResponse.model_validate(assumption)
            for assumption in assumptions
        ]


@router.get("/{assumption_id}", response_model=AssumptionResponse)
async def get_assumption(assumption_id: str):
    """
    Get a specific assumption by ID.

    Args:
        assumption_id: Assumption ID

    Returns:
        Assumption details
    """
    with next(get_session()) as session:
        assumption = get_assumption_by_id(session, assumption_id)

        if not assumption:
            raise HTTPException(status_code=404, detail="Assumption not found")

        return AssumptionResponse.model_validate(assumption)


@router.get("/ticker/{ticker}", response_model=List[AssumptionResponse])
async def get_assumptions_by_ticker_endpoint(
    ticker: str,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """
    Get assumptions for a specific ticker.

    Args:
        ticker: Stock ticker symbol
        category: Filter by assumption category
        status: Filter by status
        limit: Maximum number of items to return

    Returns:
        List of assumptions for the ticker
    """
    with next(get_session()) as session:
        assumptions = get_assumptions_by_ticker(
            session=session,
            ticker=ticker,
            category=category,
            status=status,
            limit=limit
        )

        return [
            AssumptionResponse.model_validate(assumption)
            for assumption in assumptions
        ]


@router.get("/pending/list", response_model=List[AssumptionResponse])
async def get_pending_validations(
    ticker: Optional[str] = None,
    limit: int = 50
):
    """
    Get pending assumptions that need validation.

    Args:
        ticker: Optional ticker filter
        limit: Maximum number of items to return

    Returns:
        List of pending assumptions
    """
    with next(get_session()) as session:
        assumptions = get_pending_assumptions(
            session=session,
            ticker=ticker,
            limit=limit
        )

        return [
            AssumptionResponse.model_validate(assumption)
            for assumption in assumptions
        ]


# ──── Validate Assumptions ────
@router.post("/validate/{assumption_id}", response_model=AssumptionResponse)
async def validate_assumption_endpoint(
    assumption_id: str,
    request: ValidateAssumptionRequest
):
    """
    Manually validate an assumption with actual data.

    Args:
        assumption_id: Assumption ID
        request: Validation request with actual_value and is_correct

    Returns:
        Updated assumption
    """
    with next(get_session()) as session:
        assumption = validate_assumption(
            session=session,
            assumption_id=assumption_id,
            actual_value=request.actual_value,
            is_correct=request.is_correct,
            validation_source=request.validation_source
        )

        if not assumption:
            raise HTTPException(status_code=404, detail="Assumption not found")

        return AssumptionResponse.model_validate(assumption)


@router.post("/validate/job", response_model=ValidationJobResponse)
async def run_validation_job(
    background_tasks: BackgroundTasks,
    ticker: Optional[str] = None,
    limit: int = 50
):
    """
    Trigger the validation job to check pending assumptions against actual data.

    Args:
        ticker: Optional ticker filter
        limit: Maximum assumptions to validate

    Returns:
        Validation job results
    """
    # Run validation job
    results = run_assumption_validation_job(ticker=ticker, limit=limit)

    return ValidationJobResponse(**results)


# ──── Extract Assumptions ────
@router.post("/extract", response_model=List[AssumptionResponse])
async def extract_assumptions_from_report(
    request: ExtractAssumptionsRequest,
    save_to_db: bool = True
):
    """
    Extract assumptions from report content using LLM.

    Args:
        request: Extraction request with content and metadata
        save_to_db: Whether to save extracted assumptions to database

    Returns:
        List of extracted assumptions
    """
    # Extract assumptions using LLM
    extraction_result = extract_assumptions_from_content(
        content=request.content,
        ticker=request.ticker,
        company_name=request.company_name,
        source_type=request.source_type,
        source_id=request.source_id
    )

    # Convert to database models
    assumption_models = convert_to_assumption_models(extraction_result)

    # Save to database if requested
    saved_assumptions = []
    if save_to_db:
        with next(get_session()) as session:
            for assumption in assumption_models:
                saved = add_investment_assumption(session, assumption)
                saved_assumptions.append(saved)
    else:
        saved_assumptions = assumption_models

    return [
        AssumptionResponse.model_validate(assumption)
        for assumption in saved_assumptions
    ]


# ──── Delete Assumption ────
@router.delete("/{assumption_id}")
async def delete_assumption_endpoint(assumption_id: str):
    """
    Delete an assumption by ID.

    Args:
        assumption_id: Assumption ID

    Returns:
        Success message
    """
    with next(get_session()) as session:
        success = delete_assumption(session, assumption_id)

        if not success:
            raise HTTPException(status_code=404, detail="Assumption not found")

        return {"message": "Assumption deleted successfully"}


# ──── Statistics ────
@router.get("/stats/accuracy", response_model=AccuracyStatsResponse)
async def get_accuracy_statistics(
    ticker: Optional[str] = None,
    category: Optional[str] = None,
    time_horizon: Optional[str] = None
):
    """
    Get assumption accuracy statistics.

    Args:
        ticker: Optional ticker filter
        category: Optional category filter
        time_horizon: Optional time horizon filter

    Returns:
        Accuracy statistics
    """
    with next(get_session()) as session:
        stats = get_assumption_accuracy_stats(
            session=session,
            ticker=ticker,
            category=category,
            time_horizon=time_horizon
        )

        return AccuracyStatsResponse(**stats)


@router.get("/stats/trends")
async def get_accuracy_trends_endpoint(
    ticker: Optional[str] = None,
    days: int = 90
):
    """
    Get accuracy trends over time.

    Args:
        ticker: Optional ticker filter
        days: Number of days to look back

    Returns:
        Accuracy trends data
    """
    trends = get_accuracy_trends(ticker=ticker, days=days)

    return trends


# ──── Batch Operations ────
@router.post("/batch/validate")
async def batch_validate_assumptions(
    assumption_ids: List[str],
    background_tasks: BackgroundTasks
):
    """
    Batch validate multiple assumptions.

    Args:
        assumption_ids: List of assumption IDs to validate

    Returns:
        Batch validation results
    """
    results = []

    for assumption_id in assumption_ids:
        try:
            result = validate_single_assumption(assumption_id)
            results.append(result)
        except Exception as e:
            results.append({
                "assumption_id": assumption_id,
                "success": False,
                "error": str(e)
            })

    return {
        "total": len(assumption_ids),
        "successful": sum(1 for r in results if r.get("success", False)),
        "results": results
    }


@router.get("/categories/list")
async def list_assumption_categories():
    """
    Get list of available assumption categories.

    Returns:
        List of categories with descriptions
    """
    categories = [
        {
            "category": "REVENUE",
            "description": "Sales/revenue assumptions (e.g., 'Q3 HBM 매출 1조 달성')"
        },
        {
            "category": "MARGIN",
            "description": "Margin/profitability assumptions (e.g., 'GP 마진 20% 개선')"
        },
        {
            "category": "MACRO",
            "description": "Macro environment assumptions (e.g., '금리 인하')"
        },
        {
            "category": "CAPACITY",
            "description": "Production capacity assumptions"
        },
        {
            "category": "MARKET_SHARE",
            "description": "Market share assumptions"
        }
    ]

    return categories


@router.get("/time-horizons/list")
async def list_time_horizons():
    """
    Get list of available time horizons.

    Returns:
        List of time horizons with descriptions
    """
    horizons = [
        {
            "horizon": "SHORT",
            "description": "Less than 3 months (quarterly targets)"
        },
        {
            "horizon": "MEDIUM",
            "description": "3-12 months (annual targets)"
        },
        {
            "horizon": "LONG",
            "description": "More than 12 months (strategic goals)"
        }
    ]

    return horizons
