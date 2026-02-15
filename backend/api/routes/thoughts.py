"""Thoughts API Routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
from pydantic import BaseModel

from storage.models import Thought
from storage.db import get_session
from collector.thought_logger import ThoughtLogger, ThoughtType


router = APIRouter()


# ──── Request/Response Models ────
class ThoughtCreate(BaseModel):
    content: str
    thought_type: str = "general"
    tags: Optional[List[str]] = None
    related_tickers: Optional[List[str]] = None
    confidence: Optional[int] = None


class ThoughtUpdate(BaseModel):
    outcome: Optional[str] = None


class ThoughtSearch(BaseModel):
    query: str
    limit: int = 5
    thought_type: Optional[str] = None


# ──── Thoughts CRUD ────
@router.post("/")
async def create_thought(
    thought: ThoughtCreate,
    session: Session = Depends(get_session)
):
    """
    새 생각 기록

    Args:
        thought: 생각 데이터 (content, thought_type, tags, related_tickers, confidence)

    Returns:
        저장된 Thought 객체
    """
    logger = ThoughtLogger()

    saved_thought = logger.log(
        content=thought.content,
        thought_type=ThoughtType(thought.thought_type),
        tags=thought.tags,
        related_tickers=thought.related_tickers,
        confidence=thought.confidence
    )

    return {
        "id": saved_thought.id,
        "content": saved_thought.content,
        "thought_type": saved_thought.thought_type,
        "tags": saved_thought.tags,
        "related_tickers": saved_thought.related_tickers,
        "confidence": saved_thought.confidence,
        "created_at": saved_thought.created_at
    }


@router.get("/")
async def get_thoughts(
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """
    최근 생각 목록 조회

    Args:
        limit: 반환할 개수

    Returns:
        Thought 리스트
    """
    from storage.db import get_recent_thoughts

    thoughts = get_recent_thoughts(session, limit)

    return {
        "thoughts": [
            {
                "id": t.id,
                "content": t.content,
                "thought_type": t.thought_type,
                "tags": t.tags,
                "related_tickers": t.related_tickers,
                "confidence": t.confidence,
                "outcome": t.outcome,
                "created_at": t.created_at
            }
            for t in thoughts
        ]
    }


@router.get("/{thought_id}")
async def get_thought(
    thought_id: str,
    session: Session = Depends(get_session)
):
    """
    특정 생각 조회

    Args:
        thought_id: 생각 ID

    Returns:
        Thought 객체
    """
    logger = ThoughtLogger()
    thought = logger.get_thought(thought_id)

    if not thought:
        raise HTTPException(status_code=404, detail="Thought not found")

    return {
        "id": thought.id,
        "content": thought.content,
        "thought_type": thought.thought_type,
        "tags": thought.tags,
        "related_tickers": thought.related_tickers,
        "confidence": thought.confidence,
        "outcome": thought.outcome,
        "created_at": thought.created_at
    }


@router.put("/{thought_id}")
async def update_thought(
    thought_id: str,
    thought_update: ThoughtUpdate,
    session: Session = Depends(get_session)
):
    """
    생각 업데이트 (주로 outcome 업데이트용)

    Args:
        thought_id: 생각 ID
        thought_update: 업데이트할 데이터

    Returns:
        업데이트된 Thought 객체
    """
    logger = ThoughtLogger()

    if thought_update.outcome:
        updated_thought = logger.update_outcome(thought_id, thought_update.outcome)
        if not updated_thought:
            raise HTTPException(status_code=404, detail="Thought not found")

        return {
            "id": updated_thought.id,
            "content": updated_thought.content,
            "thought_type": updated_thought.thought_type,
            "outcome": updated_thought.outcome,
            "created_at": updated_thought.created_at
        }

    raise HTTPException(status_code=400, detail="No update data provided")


@router.delete("/{thought_id}")
async def delete_thought(
    thought_id: str,
    session: Session = Depends(get_session)
):
    """
    생각 삭제

    Args:
        thought_id: 생각 ID
    """
    from sqlmodel import select

    thought = session.exec(
        select(Thought).where(Thought.id == thought_id)
    ).first()

    if not thought:
        raise HTTPException(status_code=404, detail="Thought not found")

    session.delete(thought)
    session.commit()

    # Vector store에서도 삭제
    logger = ThoughtLogger()
    logger.vector_store.delete_thought(thought_id)

    return {"message": "Thought deleted successfully"}


# ──── Search ────
@router.post("/search")
async def search_thoughts(search: ThoughtSearch):
    """
    의미 기반 생각 검색

    Args:
        search: 검색 쿼리 (query, limit, thought_type)

    Returns:
        검색 결과 리스트
    """
    logger = ThoughtLogger()

    thought_type_filter = None
    if search.thought_type:
        thought_type_filter = ThoughtType(search.thought_type)

    results = logger.search_thoughts(
        query=search.query,
        limit=search.limit,
        thought_type=thought_type_filter
    )

    return {
        "results": results,
        "count": len(results)
    }


# ──── Thoughts by Ticker ────
@router.get("/ticker/{ticker}")
async def get_thoughts_by_ticker(
    ticker: str,
    session: Session = Depends(get_session)
):
    """
    특정 종목 관련 생각 조회

    Args:
        ticker: 종목코드

    Returns:
        Thought 리스트
    """
    from storage.db import get_thoughts_by_ticker

    thoughts = get_thoughts_by_ticker(session, ticker)

    return {
        "thoughts": [
            {
                "id": t.id,
                "content": t.content,
                "thought_type": t.thought_type,
                "tags": t.tags,
                "related_tickers": t.related_tickers,
                "confidence": t.confidence,
                "created_at": t.created_at
            }
            for t in thoughts
        ]
    }
