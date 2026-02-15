"""Vector Store using PostgreSQL + pgvector for Semantic Search"""

from typing import Optional, List, Dict, Any, Tuple
from sqlmodel import Session, select, col
from storage.db import engine
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import text
import hashlib


# ──── Vector Table Models ────
class ThoughtVector(SQLModel, table=True):
    """Thought embeddings stored in PostgreSQL"""
    __tablename__ = "thought_vectors"

    id: str = Field(primary_key=True)
    content: str
    embedding: List[float] = Field(sa_column=Column("embedding", None))  # pgvector type
    metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", None))


class ContentVector(SQLModel, table=True):
    """Content embeddings stored in PostgreSQL"""
    __tablename__ = "content_vectors"

    id: str = Field(primary_key=True)
    content: str
    embedding: List[float] = Field(sa_column=Column("embedding", None))  # pgvector type
    metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", None))


class AIChatVector(SQLModel, table=True):
    """AI chat embeddings stored in PostgreSQL"""
    __tablename__ = "ai_chat_vectors"

    id: str = Field(primary_key=True)
    content: str
    embedding: List[float] = Field(sa_column=Column("embedding", None))  # pgvector type
    metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", None))


class VectorStore:
    """
    PostgreSQL + pgvector 기반 벡터 저장소

    용도: 과거 생각/콘텐츠를 의미 기반으로 검색
    "내가 반도체에 대해 어떻게 생각했었지?" 같은 질문에 대응
    """

    def __init__(self):
        """Initialize vector store and ensure pgvector extension is enabled"""
        self._ensure_pgvector_extension()
        self._create_tables()

    def _ensure_pgvector_extension(self):
        """Ensure pgvector extension is enabled in PostgreSQL"""
        with Session(engine) as session:
            session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            session.commit()

    def _create_tables(self):
        """Create vector tables if they don't exist"""
        SQLModel.metadata.create_all(engine)

    def add_thought(
        self,
        thought_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        생각을 벡터 저장소에 추가

        Args:
            thought_id: 고유 ID
            content: 생각 내용
            metadata: 메타데이터 (type, tags, tickers, created_at 등)
        """
        embedding = self._embed(content)

        with Session(engine) as session:
            # Check if exists, update or create
            existing = session.get(ThoughtVector, thought_id)
            if existing:
                existing.content = content
                existing.embedding = embedding
                existing.metadata = metadata
            else:
                vector = ThoughtVector(
                    id=thought_id,
                    content=content,
                    embedding=embedding,
                    metadata=metadata
                )
                session.add(vector)
            session.commit()

    def add_content(
        self,
        content_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        콘텐츠를 벡터 저장소에 추가

        Args:
            content_id: 고유 ID
            content: 콘텐츠 내용
            metadata: 메타데이터 (source_type, source_name, tickers 등)
        """
        embedding = self._embed(content)

        with Session(engine) as session:
            existing = session.get(ContentVector, content_id)
            if existing:
                existing.content = content
                existing.embedding = embedding
                existing.metadata = metadata
            else:
                vector = ContentVector(
                    id=content_id,
                    content=content,
                    embedding=embedding,
                    metadata=metadata
                )
                session.add(vector)
            session.commit()

    def add_ai_chat(
        self,
        chat_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        AI 대화를 벡터 저장소에 추가

        Args:
            chat_id: 고유 ID
            content: 대화 내용
            metadata: 메타데이터 (platform, date 등)
        """
        embedding = self._embed(content)

        with Session(engine) as session:
            existing = session.get(AIChatVector, chat_id)
            if existing:
                existing.content = content
                existing.embedding = embedding
                existing.metadata = metadata
            else:
                vector = AIChatVector(
                    id=chat_id,
                    content=content,
                    embedding=embedding,
                    metadata=metadata
                )
                session.add(vector)
            session.commit()

    def search_similar_thoughts(
        self,
        query: str,
        n: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        의미 기반 과거 생각 검색

        Args:
            query: 검색 쿼리
            n: 반환할 결과 수
            filter_metadata: 메타데이터 필터

        Returns:
            검색 결과 (id, content, metadata, distance)
        """
        return self._search("thought_vectors", query, n, filter_metadata)

    def search_related_content(
        self,
        query: str,
        n: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        관련 콘텐츠 검색

        Args:
            query: 검색 쿼리
            n: 반환할 결과 수
            filter_metadata: 메타데이터 필터

        Returns:
            검색 결과 (id, content, metadata, distance)
        """
        return self._search("content_vectors", query, n, filter_metadata)

    def search_ai_chats(
        self,
        query: str,
        n: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        AI 대화 검색

        Args:
            query: 검색 쿼리
            n: 반환할 결과 수
            filter_metadata: 메타데이터 필터

        Returns:
            검색 결과 (id, content, metadata, distance)
        """
        return self._search("ai_chat_vectors", query, n, filter_metadata)

    def _search(
        self,
        table_name: str,
        query: str,
        n: int,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        pgvector를 사용한 코사인 유사도 검색

        Args:
            table_name: 테이블 이름 (thought_vectors, content_vectors, ai_chat_vectors)
            query: 검색 쿼리
            n: 반환할 결과 수
            filter_metadata: 메타데이터 필터

        Returns:
            검색 결과 (id, content, metadata, distance)
        """
        query_embedding = self._embed(query)
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        with Session(engine) as session:
            # Build SQL query with pgvector cosine similarity
            sql = f"""
                SELECT id, content, metadata,
                       1 - (embedding <=> :embedding) as similarity
                FROM {table_name}
                WHERE 1=1
            """

            params = {"embedding": embedding_str}

            # Add metadata filtering if provided
            if filter_metadata:
                for key, value in filter_metadata.items():
                    sql += f" AND metadata->>'{key}' = :{key}"
                    params[key] = str(value)

            sql += f" ORDER BY embedding <=> :embedding LIMIT {n}"

            result = session.execute(text(sql), params)
            rows = result.fetchall()

            return [
                {
                    "id": row.id,
                    "content": row.content,
                    "metadata": row.metadata,
                    "distance": 1 - row.similarity  # Convert similarity to distance
                }
                for row in rows
            ]

    def _embed(self, text: str) -> List[float]:
        """
        텍스트 임베딩

        참고: 실제 구현에서는 Ollama nomic-embed-text 또는
        다른 임베딩 모델을 사용해야 합니다.

        현재는 간단한 해시 기반 임베딩 (개발용)
        """
        # TODO: Ollama 임베딩 구현
        # import ollama
        # response = ollama.embeddings(
        #     model="nomic-embed-text",
        #     prompt=text
        # )
        # return response["embedding"]

        # 개발용: 간단한 해시 기반 임베딩
        hash_obj = hashlib.sha256(text.encode())
        hash_hex = hash_obj.hexdigest()

        # 384차원 벡터 생성 (pgvector 기본)
        embedding = []
        for i in range(0, len(hash_hex), 2):
            val = int(hash_hex[i:i+2], 16) / 255.0
            embedding.append(val)

        # 384차원으로 패딩
        while len(embedding) < 384:
            embedding.append(0.0)

        return embedding[:384]

    def delete_thought(self, thought_id: str) -> None:
        """생각 삭제"""
        with Session(engine) as session:
            vector = session.get(ThoughtVector, thought_id)
            if vector:
                session.delete(vector)
                session.commit()

    def delete_content(self, content_id: str) -> None:
        """콘텐츠 삭제"""
        with Session(engine) as session:
            vector = session.get(ContentVector, content_id)
            if vector:
                session.delete(vector)
                session.commit()

    def delete_ai_chat(self, chat_id: str) -> None:
        """AI 대화 삭제"""
        with Session(engine) as session:
            vector = session.get(AIChatVector, chat_id)
            if vector:
                session.delete(vector)
                session.commit()

    def get_thought_count(self) -> int:
        """저장된 생각 수"""
        with Session(engine) as session:
            return session.exec(select(ThoughtVector)).all().__len__()

    def get_content_count(self) -> int:
        """저장된 콘텐츠 수"""
        with Session(engine) as session:
            return session.exec(select(ContentVector)).all().__len__()

    def get_ai_chat_count(self) -> int:
        """저장된 AI 대화 수"""
        with Session(engine) as session:
            return session.exec(select(AIChatVector)).all().__len__()


# ──── Convenience Functions ────
def get_vector_store() -> VectorStore:
    """VectorStore 인스턴스 반환"""
    return VectorStore()
