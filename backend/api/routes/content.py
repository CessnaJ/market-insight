"""Content API Routes

Endpoints for content collection and retrieval.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, date

from storage.db import get_session, get_recent_contents
from storage.models import ContentItem
from collector.youtube_collector import YouTubeCollector
from collector.naver_blog_collector import NaverBlogCollector


router = APIRouter(prefix="/content", tags=["content"])


# ──── Content Retrieval ────
@router.get("/", response_model=List[dict])
async def list_contents(
    limit: int = 10,
    source_type: Optional[str] = None
):
    """
    Get recent collected contents

    Args:
        limit: Number of items to return
        source_type: Filter by source type (youtube, naver_blog, etc.)

    Returns:
        List of content items
    """
    with next(get_session()) as session:
        query = select(ContentItem).order_by(ContentItem.collected_at.desc()).limit(limit)

        if source_type:
            query = query.where(ContentItem.source_type == source_type)

        contents = session.exec(query).all()

        return [
            {
                "id": c.id,
                "source_type": c.source_type,
                "source_name": c.source_name,
                "title": c.title,
                "url": c.url,
                "summary": c.summary,
                "key_tickers": c.key_tickers,
                "key_topics": c.key_topics,
                "sentiment": c.sentiment,
                "collected_at": c.collected_at.isoformat(),
                "published_at": c.published_at.isoformat() if c.published_at else None,
            }
            for c in contents
        ]


@router.get("/{content_id}", response_model=dict)
async def get_content(content_id: str):
    """
    Get a specific content item by ID

    Args:
        content_id: Content ID

    Returns:
        Content item details
    """
    with next(get_session()) as session:
        content = session.get(ContentItem, content_id)

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return {
            "id": content.id,
            "source_type": content.source_type,
            "source_name": content.source_name,
            "title": content.title,
            "url": content.url,
            "content_preview": content.content_preview,
            "summary": content.summary,
            "key_tickers": content.key_tickers,
            "key_topics": content.key_topics,
            "sentiment": content.sentiment,
            "collected_at": content.collected_at.isoformat(),
            "published_at": content.published_at.isoformat() if content.published_at else None,
        }


@router.get("/ticker/{ticker}", response_model=List[dict])
async def get_contents_by_ticker(ticker: str, limit: int = 10):
    """
    Get contents related to a specific ticker

    Args:
        ticker: Stock ticker symbol
        limit: Number of items to return

    Returns:
        List of content items
    """
    with next(get_session()) as session:
        # Simple search in key_tickers JSON field
        query = select(ContentItem).where(
            ContentItem.key_tickers.contains(ticker)
        ).order_by(ContentItem.collected_at.desc()).limit(limit)

        contents = session.exec(query).all()

        return [
            {
                "id": c.id,
                "source_type": c.source_type,
                "source_name": c.source_name,
                "title": c.title,
                "url": c.url,
                "summary": c.summary,
                "collected_at": c.collected_at.isoformat(),
            }
            for c in contents
        ]


# ──── Content Collection ────
@router.post("/collect/youtube")
async def collect_youtube(background_tasks: BackgroundTasks):
    """
    Trigger YouTube content collection

    This runs in the background.
    """
    def run_collection():
        collector = YouTubeCollector()
        collector.collect_all()

    background_tasks.add_task(run_collection)

    return {"message": "YouTube content collection started"}


@router.post("/collect/naver")
async def collect_naver(background_tasks: BackgroundTasks):
    """
    Trigger Naver blog content collection

    This runs in the background.
    """
    def run_collection():
        collector = NaverBlogCollector()
        collector.collect_all()

    background_tasks.add_task(run_collection)

    return {"message": "Naver blog content collection started"}


@router.post("/collect/all")
async def collect_all(background_tasks: BackgroundTasks):
    """
    Trigger all content collection

    This runs in the background.
    """
    def run_collection():
        # YouTube
        youtube_collector = YouTubeCollector()
        youtube_collector.collect_all()

        # Naver
        naver_collector = NaverBlogCollector()
        naver_collector.collect_all()

    background_tasks.add_task(run_collection)

    return {"message": "All content collection started"}


# ──── Content Search ────
@router.post("/search")
async def search_contents(query: str, limit: int = 10):
    """
    Search contents by text query

    Args:
        query: Search query
        limit: Number of results to return

    Returns:
        List of matching content items
    """
    with next(get_session()) as session:
        # Simple text search in title and summary
        query_lower = query.lower()

        contents = session.exec(
            select(ContentItem).where(
                (ContentItem.title.ilike(f"%{query}%")) |
                (ContentItem.summary.ilike(f"%{query}%"))
            ).order_by(ContentItem.collected_at.desc()).limit(limit)
        ).all()

        return [
            {
                "id": c.id,
                "source_type": c.source_type,
                "source_name": c.source_name,
                "title": c.title,
                "url": c.url,
                "summary": c.summary,
                "collected_at": c.collected_at.isoformat(),
            }
            for c in contents
        ]
