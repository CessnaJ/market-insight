"""Thought Logger - Record and manage investment thoughts"""

import os
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pathlib import Path

from storage.models import Thought
from storage.db import get_session
from storage.vector_store import VectorStore


class ThoughtType(str, Enum):
    """생각 유형"""
    MARKET_VIEW = "market_view"       # 시장 전망
    STOCK_IDEA = "stock_idea"         # 종목 아이디어
    RISK_CONCERN = "risk_concern"     # 리스크/우려
    AI_INSIGHT = "ai_insight"         # AI 대화에서 얻은 인사이트
    CONTENT_NOTE = "content_note"     # 컨텐츠 보고 메모
    GENERAL = "general"


class ThoughtLogger:
    """
    생각 기록기

    CLI에서 빠르게 입력하거나 Telegram으로 전송
    """

    def __init__(self, raw_data_dir: str = "./data/raw"):
        self.raw_data_dir = Path(raw_data_dir)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store = VectorStore()

    def log(
        self,
        content: str,
        thought_type: ThoughtType,
        tags: Optional[List[str]] = None,
        related_tickers: Optional[List[str]] = None,
        confidence: Optional[int] = None
    ) -> Thought:
        """
        생각 기록

        Args:
            content: 생각 내용
            thought_type: 생각 유형
            tags: 태그 리스트
            related_tickers: 관련 종목코드 리스트
            confidence: 확신도 (1-10)

        Returns:
            저장된 Thought 객체
        """
        thought = Thought(
            content=content,
            thought_type=thought_type.value,
            tags=json.dumps(tags or [], ensure_ascii=False),
            related_tickers=json.dumps(related_tickers or [], ensure_ascii=False),
            confidence=confidence
        )

        # 1. SQLite에 메타데이터 저장
        with next(get_session()) as session:
            session.add(thought)
            session.commit()
            session.refresh(thought)

        # 2. ChromaDB에 벡터 임베딩 저장 (검색용)
        self.vector_store.add_thought(
            thought_id=thought.id,
            content=content,
            metadata={
                "type": thought_type.value,
                "tags": tags or [],
                "tickers": related_tickers or [],
                "created_at": thought.created_at.isoformat()
            }
        )

        # 3. Markdown 원본 저장 (백업)
        self._save_to_markdown(thought, tags or [], related_tickers or [])

        return thought

    def _save_to_markdown(
        self,
        thought: Thought,
        tags: List[str],
        related_tickers: List[str]
    ) -> None:
        """
        날짜별 마크다운 파일로 저장

        Args:
            thought: Thought 객체
            tags: 태그 리스트
            related_tickers: 관련 종목코드 리스트
        """
        today = datetime.now().strftime("%Y/%m/%d")
        path = self.raw_data_dir / today / "thoughts.md"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n## [{thought.thought_type}] {thought.created_at.strftime('%H:%M')}\n")
            f.write(f"ID: {thought.id}\n")
            if tags:
                f.write(f"Tags: {', '.join(tags)}\n")
            if related_tickers:
                f.write(f"Tickers: {', '.join(related_tickers)}\n")
            if thought.confidence:
                f.write(f"Confidence: {thought.confidence}/10\n")
            f.write(f"\n{thought.content}\n")
            f.write("---\n")

    def get_thought(self, thought_id: str) -> Optional[Thought]:
        """
        ID로 생각 조회

        Args:
            thought_id: 생각 ID

        Returns:
            Thought 객체 또는 None
        """
        with next(get_session()) as session:
            from sqlmodel import select
            return session.exec(
                select(Thought).where(Thought.id == thought_id)
            ).first()

    def get_recent_thoughts(self, limit: int = 10) -> List[Thought]:
        """
        최근 생각 조회

        Args:
            limit: 반환할 개수

        Returns:
            Thought 리스트
        """
        with next(get_session()) as session:
            from storage.db import get_recent_thoughts
            return get_recent_thoughts(session, limit)

    def search_thoughts(
        self,
        query: str,
        limit: int = 5,
        thought_type: Optional[ThoughtType] = None
    ) -> List[dict]:
        """
        의미 기반 생각 검색

        Args:
            query: 검색 쿼리
            limit: 반환할 개수
            thought_type: 필터링할 생각 유형

        Returns:
            검색 결과 리스트 (id, content, metadata, distance)
        """
        filter_metadata = None
        if thought_type:
            filter_metadata = {"type": thought_type.value}

        results = self.vector_store.search_similar_thoughts(
            query=query,
            n=limit,
            filter_metadata=filter_metadata
        )

        # 결과 포맷팅
        formatted = []
        if results.get("ids") and results["ids"][0]:
            for i, thought_id in enumerate(results["ids"][0]):
                formatted.append({
                    "id": thought_id,
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                })

        return formatted

    def update_outcome(self, thought_id: str, outcome: str) -> Optional[Thought]:
        """
        생각의 결과 업데이트 (회고용)

        Args:
            thought_id: 생각 ID
            outcome: 결과 내용

        Returns:
            업데이트된 Thought 객체 또는 None
        """
        with next(get_session()) as session:
            from sqlmodel import select
            thought = session.exec(
                select(Thought).where(Thought.id == thought_id)
            ).first()

            if thought:
                thought.outcome = outcome
                session.add(thought)
                session.commit()
                session.refresh(thought)
                return thought

        return None


# ──── Convenience Functions ────
def log_thought(
    content: str,
    thought_type: str = "general",
    tags: Optional[List[str]] = None,
    related_tickers: Optional[List[str]] = None,
    confidence: Optional[int] = None
) -> Thought:
    """
    생각 기록 (간편 함수)

    Args:
        content: 생각 내용
        thought_type: 생각 유형 (문자열)
        tags: 태그 리스트
        related_tickers: 관련 종목코드 리스트
        confidence: 확신도 (1-10)

    Returns:
        저장된 Thought 객체
    """
    logger = ThoughtLogger()
    return logger.log(
        content=content,
        thought_type=ThoughtType(thought_type),
        tags=tags,
        related_tickers=related_tickers,
        confidence=confidence
    )


def search_thoughts(query: str, limit: int = 5) -> List[dict]:
    """
    생각 검색 (간편 함수)

    Args:
        query: 검색 쿼리
        limit: 반환할 개수

    Returns:
        검색 결과 리스트
    """
    logger = ThoughtLogger()
    return logger.search_thoughts(query=query, limit=limit)
