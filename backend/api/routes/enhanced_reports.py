"""Enhanced Reports API Routes

API endpoints for comprehensive report generation integrating all sprint components.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
import logging

from analyzer.enhanced_report_builder import (
    EnhancedReportBuilder,
    generate_comprehensive_report,
    generate_daily_report_with_analysis,
    generate_asset_report
)
from storage.models import DailyReport

logger = logging.getLogger(__name__)

router = APIRouter()


# ──── Request/Response Models ────

class ComprehensiveReportRequest(BaseModel):
    """Request for comprehensive report generation"""
    target_date: Optional[date] = Field(default=None, description="Target date (defaults to today)")
    tickers: Optional[List[str]] = Field(default=None, description="List of tickers to focus on")


class DailyReportEnhancedRequest(BaseModel):
    """Request for enhanced daily report generation"""
    target_date: Optional[date] = Field(default=None, description="Target date (defaults to today)")


class AssetReportRequest(BaseModel):
    """Request for asset-specific report generation"""
    ticker: str = Field(..., description="Stock ticker")
    target_date: Optional[date] = Field(default=None, description="Target date (defaults to today)")


class BatchReportRequest(BaseModel):
    """Request for batch report generation"""
    tickers: List[str] = Field(..., description="List of tickers")
    target_date: Optional[date] = Field(default=None, description="Target date (defaults to today)")


class ExportReportRequest(BaseModel):
    """Request for report export"""
    report_id: str = Field(..., description="Report ID to export")
    format: str = Field(default="markdown", description="Export format: markdown, json, pdf")


class ReportResponse(BaseModel):
    """Response for report generation"""
    id: str
    report_date: date
    report_markdown: str
    created_at: datetime
    message: str


class AssetReportResponse(BaseModel):
    """Response for asset report generation"""
    ticker: str
    company_name: Optional[str]
    holding: Optional[dict]
    primary_sources: List[dict]
    temporal_attributions: List[dict]
    investment_assumptions: List[dict]
    search_results: List[dict]
    generated_at: str


class BatchReportResponse(BaseModel):
    """Response for batch report generation"""
    reports: List[dict]
    total_count: int
    success_count: int
    failed_count: int
    generated_at: datetime


# ──── Background Tasks ────

async def generate_report_background(
    target_date: date,
    tickers: Optional[List[str]],
    task_id: str
):
    """Background task for comprehensive report generation"""
    try:
        builder = EnhancedReportBuilder()
        report = builder.generate_comprehensive_report(target_date, tickers)
        logger.info(f"Background report generated: {report.id}")
    except Exception as e:
        logger.error(f"Background report generation failed: {e}")


# ──── API Endpoints ────

@router.post("/comprehensive", response_model=ReportResponse)
async def generate_comprehensive_report_endpoint(
    request: ComprehensiveReportRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate comprehensive investment report integrating all sprint components

    - Primary sources (Sprint 1): DART filings, earnings calls
    - Temporal signal decomposition (Sprint 2): Price event analysis
    - Assumption tracking (Sprint 3): Investment assumptions and validation
    - Weighted search (Sprint 4): Authority-weighted content search
    """
    try:
        builder = EnhancedReportBuilder()
        report = builder.generate_comprehensive_report(request.target_date, request.tickers)

        return ReportResponse(
            id=report.id,
            report_date=report.report_date,
            report_markdown=report.report_markdown,
            created_at=report.created_at,
            message="Comprehensive report generated successfully"
        )
    except Exception as e:
        logger.error(f"Comprehensive report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comprehensive/async")
async def generate_comprehensive_report_async(
    request: ComprehensiveReportRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate comprehensive report asynchronously in background

    Returns immediately and processes report in background.
    """
    task_id = datetime.now().strftime("%Y%m%d%H%M%S")
    background_tasks.add_task(
        generate_report_background,
        request.target_date,
        request.tickers,
        task_id
    )

    return {
        "message": "Comprehensive report generation started",
        "task_id": task_id,
        "status": "processing"
    }


@router.post("/daily-enhanced", response_model=ReportResponse)
async def generate_daily_report_enhanced_endpoint(
    request: DailyReportEnhancedRequest
):
    """
    Generate enhanced daily report with temporal analysis and assumptions

    Integrates:
    - Portfolio summary
    - Recent contents and thoughts
    - Primary sources (last 7 days)
    - Temporal price attributions (last 7 days)
    - Pending investment assumptions
    """
    try:
        builder = EnhancedReportBuilder()
        report = builder.generate_daily_report_with_analysis(request.target_date)

        return ReportResponse(
            id=report.id,
            report_date=report.report_date,
            report_markdown=report.report_markdown,
            created_at=report.created_at,
            message="Enhanced daily report generated successfully"
        )
    except Exception as e:
        logger.error(f"Enhanced daily report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/asset", response_model=AssetReportResponse)
async def generate_asset_report_endpoint(
    request: AssetReportRequest
):
    """
    Generate asset-specific report with all integrated data

    Returns comprehensive data for a single ticker including:
    - Holding information
    - Primary sources (last 90 days)
    - Temporal attributions (last 90 days)
    - Investment assumptions
    - Weighted search results
    """
    try:
        builder = EnhancedReportBuilder()
        report = builder.generate_asset_report(request.ticker, request.target_date)

        return AssetReportResponse(
            ticker=report["ticker"],
            company_name=report.get("company_name"),
            holding=report.get("holding"),
            primary_sources=report["primary_sources"],
            temporal_attributions=report["temporal_attributions"],
            investment_assumptions=report["investment_assumptions"],
            search_results=report["search_results"],
            generated_at=report["generated_at"]
        )
    except Exception as e:
        logger.error(f"Asset report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchReportResponse)
async def generate_batch_reports_endpoint(
    request: BatchReportRequest
):
    """
    Generate reports for multiple assets in batch

    Processes multiple tickers and returns all generated reports.
    """
    try:
        builder = EnhancedReportBuilder()
        reports = []
        success_count = 0
        failed_count = 0

        for ticker in request.tickers:
            try:
                report = builder.generate_asset_report(ticker, request.target_date)
                reports.append({
                    "ticker": ticker,
                    "success": True,
                    "data": report
                })
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to generate report for {ticker}: {e}")
                reports.append({
                    "ticker": ticker,
                    "success": False,
                    "error": str(e)
                })
                failed_count += 1

        return BatchReportResponse(
            reports=reports,
            total_count=len(request.tickers),
            success_count=success_count,
            failed_count=failed_count,
            generated_at=datetime.now()
        )
    except Exception as e:
        logger.error(f"Batch report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_report_endpoint(request: ExportReportRequest):
    """
    Export a report in specified format

    Supported formats:
    - markdown: Returns markdown text
    - json: Returns structured JSON
    - pdf: Returns PDF (placeholder for future implementation)
    """
    try:
        from storage.db import get_session
        from sqlmodel import select

        with next(get_session()) as session:
            report = session.exec(
                select(DailyReport).where(DailyReport.id == request.report_id)
            ).first()

            if not report:
                raise HTTPException(status_code=404, detail="Report not found")

            if request.format == "markdown":
                return {
                    "format": "markdown",
                    "content": report.report_markdown,
                    "filename": f"report_{report.report_date}.md"
                }
            elif request.format == "json":
                return {
                    "format": "json",
                    "content": {
                        "id": report.id,
                        "report_date": report.report_date.isoformat(),
                        "report_markdown": report.report_markdown,
                        "portfolio_section": report.portfolio_section,
                        "content_section": report.content_section,
                        "thought_section": report.thought_section,
                        "ai_opinion": report.ai_opinion,
                        "action_items": report.action_items,
                        "created_at": report.created_at.isoformat()
                    },
                    "filename": f"report_{report.report_date}.json"
                }
            elif request.format == "pdf":
                # Placeholder for PDF generation
                return {
                    "format": "pdf",
                    "message": "PDF export not yet implemented",
                    "markdown_content": report.report_markdown
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported format: {request.format}"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for enhanced reports service"""
    return {
        "status": "ok",
        "service": "enhanced_reports",
        "components": {
            "enhanced_report_builder": "available",
            "temporal_decomposer": "available",
            "assumption_extractor": "available",
            "weighted_search": "available"
        }
    }
