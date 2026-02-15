# SQLite + ChromaDB → PostgreSQL + pgvector 마이그레이션 가이드

## 개요

이 프로젝트는 SQLite + ChromaDB에서 PostgreSQL + pgvector로 마이그레이션되었습니다. 이 가이드는 마이그레이션 과정과 새로운 설정 방법을 설명합니다.

## 변경 사항

### 이전 설정 (SQLite + ChromaDB)
- **관계형 DB**: SQLite (`./data/sqlite/main.db`)
- **벡터 DB**: ChromaDB (`./data/chroma`)
- **설치**: 시스템에 직접 설치
- **삭제**: 수동으로 파일 삭제 필요

### 새로운 설정 (PostgreSQL + pgvector)
- **관계형 DB + 벡터 DB**: PostgreSQL + pgvector (Docker 컨테이너)
- **설치**: `docker-compose up -d`
- **삭제**: `docker-compose down -v`

## 마이그레이션 단계

### 1. Docker 컨테이너 시작

```bash
cd market-insight
docker-compose up -d
```

컨테이너가 실행 중인지 확인:
```bash
docker ps
```

### 2. 의존성 업데이트

```bash
cd backend
uv sync
```

또는 pip을 사용하는 경우:
```bash
pip install psycopg2-binary pgvector
```

### 3. 환경 변수 설정

```bash
cd backend
cp .env.example .env
```

`.env` 파일에서 필요한 설정을 수정합니다:
```env
DB_PASSWORD=changeme
DATABASE_URL=postgresql+psycopg://investor:${DB_PASSWORD}@localhost:5432/market_insight
```

### 4. 데이터베이스 초기화

```bash
cd backend
uv run python -c "from storage.db import init_database; init_database()"
```

이 명령은 다음을 수행합니다:
- PostgreSQL에 관계형 데이터 테이블 생성
- pgvector 확장 활성화
- 벡터 저장소 테이블 생성

### 5. 기존 데이터 마이그레이션 (선택사항)

**중요**: 기존 SQLite + ChromaDB 데이터를 마이그레이션하려면 추가 스크립트가 필요합니다. 현재는 새로운 데이터베이스로 시작하는 것을 권장합니다.

기존 데이터를 보존해야 하는 경우:
1. SQLite 데이터 내보내기
2. ChromaDB 데이터 내보내기
3. PostgreSQL로 가져오기

## Docker Compose 명령어

### 컨테이너 시작
```bash
docker-compose up -d
```

### 컨테이너 중지
```bash
docker-compose stop
```

### 컨테이너 및 데이터 삭제
```bash
docker-compose down -v
```

### 로그 확인
```bash
docker-compose logs -f postgres
```

### PostgreSQL에 직접 접속
```bash
docker exec -it market-insight-db psql -U investor -d market_insight
```

## 파일 변경 사항

### 새로 추가된 파일
- `docker-compose.yml` - PostgreSQL + pgvector 컨테이너 설정

### 수정된 파일
- `backend/pyproject.toml` - `chromadb` 제거, `psycopg2-binary`, `pgvector` 추가
- `backend/storage/db.py` - SQLite → PostgreSQL 연결로 변경
- `backend/storage/vector_store.py` - ChromaDB → pgvector로 변경
- `backend/.env.example` - PostgreSQL 연결 설정으로 변경

### 삭제된 디렉토리 (더 이상 사용 안 함)
- `backend/data/sqlite/` - SQLite 데이터 파일
- `backend/data/chroma/` - ChromaDB 데이터 파일

## 테스트

### 1. 데이터베이스 연결 테스트
```bash
cd backend
uv run python -c "from storage.db import engine; print('DB 연결 성공:', engine.url)"
```

### 2. 벡터 저장소 테스트
```bash
cd backend
uv run python -c "from storage.vector_store import get_vector_store; vs = get_vector_store(); print('벡터 저장소 초기화 성공')"
```

### 3. CLI 테스트
```bash
cd backend
inv init
inv think "테스트 생각"
inv recall "테스트"
```

## 문제 해결

### 포트 5432 이미 사용 중
```bash
# 다른 포트 사용하도록 docker-compose.yml 수정
ports:
  - "5433:5432"  # 5433으로 변경
```

### 연결 거부 오류
```bash
# 컨테이너가 실행 중인지 확인
docker ps

# 로그 확인
docker-compose logs postgres

# 컨테이너 재시작
docker-compose restart postgres
```

### pgvector 확장 오류
```bash
# PostgreSQL에 직접 접속하여 수동으로 확장 설치
docker exec -it market-insight-db psql -U investor -d market_insight
CREATE EXTENSION IF NOT EXISTS vector;
```

## 장점

1. **환경 격리**: Docker 컨테이너로 실행되므로 macOS 환경이 깨끗하게 유지됩니다.
2. **삭제 용이**: `docker-compose down -v`로 즉시 정리할 수 있습니다.
3. **통합 관리**: 하나의 데이터베이스로 관계형 데이터와 벡터 데이터를 모두 관리합니다.
4. **프로덕션 준비**: 실제 운영 환경과 동일한 스택을 사용합니다.
5. **SQL 쿼리**: 포트폴리오 데이터와 벡터 검색을 SQL로 조합할 수 있습니다.

## 참고

- PostgreSQL + pgvector 문서: https://github.com/pgvector/pgvector
- Docker Compose 문서: https://docs.docker.com/compose/
