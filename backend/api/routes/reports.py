"""Reports API Routes

Endpoints for report generation and retrieval.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, date

from storage.db import get_session, get_latest_daily_report
from storage.models import DailyReport
from analyzer.report_builder import ReportBuilder


router = APIRouter(prefix="/reports", tags=["reports"])


# ──── Report Retrieval ────
@router.get("/", response_model=List[dict])
async def list_reports(limit: int = 10):
    """
    Get recent reports

    Args:
        limit: Number of reports to return

    Returns:
        List of reports
    """
    with next(get_session()) as session:
        reports = session.exec(
            select(DailyReport)
            .order_by(DailyReport.date.desc())
            .limit(limit)
        ).all()

        return [
            {
                "id": r.id,
                "date": r.date.isoformat(),
                "created_at": r.created_at.isoformat(),
                "preview": r.report_markdown[:200] + "..." if len(r.report_markdown) > 200 else r.report_markdown,
            }
            for r in reports
        ]


@router.get("/latest", response_model=dict)
async def get_latest_report():
    """
    Get the latest report

    Returns:
        Latest report details
    """
    report = get_latest_daily_report(next(get_session()))

    if not report:
        raise HTTPException(status_code=404, detail="No reports found")

    return {
        "id": report.id,
        "date": report.date.isoformat(),
        "report_markdown": report.report_markdown,
        "portfolio_section": report.portfolio_section,
        "content_section": report.content_section,
        "thought_section": report.thought_section,
        "ai_opinion": report.ai_opinion,
        "action_items": report.action_items,
        "created_at": report.created_at.isoformat(),
    }


@router.get("/{report_id}", response_model=dict)
async def get_report(report_id: str):
    """
    Get a specific report by ID

    Args:
        report_id: Report ID

    Returns:
        Report details
    """
    with next(get_session()) as session:
        report = session.get(DailyReport, report_id)

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        return {
            "id": report.id,
            "date": report.date.isoformat(),
            "report_markdown": report.report_markdown,
            "portfolio_section": report.portfolio_section,
            "content_section": report.content_section,
            "thought_section": report.thought_section,
            "ai_opinion": report.ai_opinion,
            "action_items": report.action_items,
            "created_at": report.created_at.isoformat(),
        }


@router.get("/date/{target_date}", response_model=dict)
async def get_report_by_date(target_date: str):
    """
    Get a report for a specific date

    Args:
        target_date: Target date (YYYY-MM-DD)

    Returns:
        Report details
    """
    try:
        date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    with next(get_session()) as session:
        report = session.exec(
            select(DailyReport)
            .where(DailyReport.date == date_obj)
            .order_by(DailyReport.created_at.desc())
        ).first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found for this date")

        return {
            "id": report.id,
            "date": report.date.isoformat(),
            "report_markdown": report.report_markdown,
            "portfolio_section": report.portfolio_section,
            "content_section": report.content_section,
            "thought_section": report.thought_section,
            "ai_opinion": report.ai_opinion,
            "action_items": report.action_items,
            "created_at": report.created_at.isoformat(),
        }


# ──── Report Generation ────
@router.post("/generate/daily")
async def generate_daily_report(
    background_tasks: BackgroundTasks,
    target_date: Optional[str] = None
):
    """
    Generate a daily report

    Args:
        target_date: Target date (YYYY-MM-DD), defaults to today

    Returns:
        Generated report
    """
    date_obj = None
    if target_date:
        try:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    def run_generation():
        builder = ReportBuilder()
        builder.generate_daily_report(date_obj)

    # For now, run synchronously to return the result
    # In production, you might want to run this in background
    builder = ReportBuilder()
    report = builder.generate_daily_report(date_obj)

    return {
        "id": report.id,
        "date": report.date.isoformat(),
        "report_markdown": report.report_markdown,
        "created_at": report.created_at.isoformat(),
    }


@router.post("/generate/weekly")
async def generate_weekly_report(
    background_tasks: BackgroundTasks,
    target_date: Optional[str] = None
):
    """
    Generate a weekly report

    Args:
        target_date: Target date (YYYY-MM-DD), defaults to today

    Returns:
        Generated report
    """
    date_obj = None
    if target_date:
        try:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # For now, run synchronously to return the result
    builder = ReportBuilder()
    report = builder.generate_weekly_report(date_obj)

    return {
        "id": report.id,
        "date": report.date.isoformat(),
        "report_markdown": report.report_markdown,
        "created_at": report.created_at.isoformat(),
    }
