# 설치 및 설정 가이드 (Setup Guide)

이 가이드는 Market Insight 시스템을 처음부터 설정하는 방법을 설명합니다.

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [Ollama 설치 및 설정](#ollama-설치-및-설정)
3. [PostgreSQL + pgvector 설치](#postgresql--pgvector-설치)
4. [Python 백엔드 설정](#python-백엔드-설정)
5. [Next.js 대시보드 설정](#nextjs-대시보드-설정)
6. [MCP 서버 설정 (Claude Desktop 연동)](#mcp-서버-설정-claude-desktop-연동)
7. [데이터베이스 초기화](#데이터베이스-초기화)
8. [서버 실행](#서버-실행)
9. [문제 해결](#문제-해결)

---

## 사전 요구사항

### 필수 소프트웨어

- **macOS**: 10.15 (Catalina) 이상
- **Homebrew**: 패키지 관리자
- **Python**: 3.10 이상
- **Node.js**: 18 이상
- **Docker**: PostgreSQL 컨테이너 실행용

### 하드웨어 요구사항

- **RAM**: 최소 8GB, 권장 16GB 이상
- **스토리지**: 최소 10GB 여유 공간

---

## Ollama 설치 및 설정

Ollama는 로컬 LLM(Large Language Model)을 실행하기 위한 도구입니다. 이 시스템에서는 텍스트 생성과 임베딩 생성에 사용합니다.

### 1. Homebrew로 Ollama 설치

```bash
brew install ollama
```

### 2. Ollama 서버 시작

Ollama는 백그라운드 서비스로 실행하거나 직접 실행할 수 있습니다.

**옵션 A: 백그라운드 서비스로 실행 (권장)**

```bash
brew services start ollama
```

서버가 실행 중인지 확인:

```bash
# Ollama 서버 상태 확인
brew services list | grep ollama

# 또는 직접 API 테스트
curl http://localhost:11434/api/tags
```

**옵션 B: 직접 실행 (개발용)**

```bash
# 터미널에서 직접 실행 (종료하려면 Ctrl+C)
ollama serve
```

서버가 성공적으로 시작되면 다음과 같은 메시지가 표시됩니다:

```
time=2026-02-16T01:40:39.852+09:00 level=INFO source=routes.go:1739 msg="Listening on 127.0.0.1:11434 (version 0.15.6)"
```

### 3. 필수 모델 다운로드

이 시스템에서는 두 가지 모델이 필요합니다:

1. **nomic-embed-text**: 텍스트 임베딩 생성용 (약 274MB)
2. **llama3.2**: 텍스트 생성용 (약 2GB)

```bash
# 임베딩 모델 (필수)
ollama pull nomic-embed-text

# 텍스트 생성 모델 (필수)
ollama pull llama3.2

# 다운로드된 모델 확인
ollama list
```

**참고**: 더 작은 모델을 사용하려면 `llama3.2:3b` (약 2GB) 대신 `llama3.2:1b` (약 700MB)를 사용할 수 있습니다.

### 4. Ollama 연결 테스트

```bash
# 임베딩 테스트
curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "Hello, world!"
}'

# 텍스트 생성 테스트
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

### 5. Ollama 서버 자동 시작 설정

시스템 부팅 시 Ollama가 자동으로 시작되도록 설정:

```bash
brew services start ollama
```

서버 중지:

```bash
brew services stop ollama
```

서버 재시작:

```bash
brew services restart ollama
```

---

## PostgreSQL + pgvector 설치

이 시스템은 PostgreSQL과 pgvector 확장을 사용하여 정형 데이터와 벡터 데이터를 저장합니다.

### 1. Docker로 PostgreSQL + pgvector 컨테이너 실행

```bash
cd market-insight
docker-compose up -d
```

### 2. 컨테이너 상태 확인

```bash
docker ps
```

다음과 같은 출력이 표시되어야 합니다:

```
CONTAINER ID   IMAGE                           COMMAND                  CREATED         STATUS         PORTS                    NAMES
abc123456789   pgvector/pgvector:pg16          "docker-entrypoint.s…"   2 minutes ago   Up 2 minutes   0.0.0.0:5432->5432/tcp   market-insight-db-1
```

### 3. PostgreSQL 연결 테스트

```bash
# 컨테이너 내에서 PostgreSQL 클라이언트 실행
docker exec -it market-insight-db-1 psql -U postgres -d market_insight

# pgvector 확장 확인
\dx pgvector

# 종료
\q
```

### 4. 컨테이너 관리 명령어

```bash
# 컨테이너 중지
docker-compose stop

# 컨테이너 시작
docker-compose start

# 컨테이너 재시작
docker-compose restart

# 컨테이너 및 데이터 삭제 (주의: 모든 데이터가 삭제됩니다)
docker-compose down -v

# 로그 확인
docker-compose logs -f
```

---

## Python 백엔드 설정

### 1. 가상환경 생성 (선택 사항)

```bash
cd market-insight/backend

# Python venv 사용
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 또는
source .venv/Scripts/activate  # Windows
```

### 2. 의존성 설치

**옵션 A: uv 사용 (권장, 빠름)**

```bash
cd market-insight/backend

# uv 설치 (아직 설치되지 않은 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv sync
```

**옵션 B: pip 사용**

```bash
cd market-insight/backend

# requirements.txt가 있는 경우
pip install -r requirements.txt

# 또는 pyproject.toml에서 직접 설치
pip install fastapi uvicorn sqlmodel psycopg2-binary pgvector apscheduler httpx feedparser yt-dlp beautifulsoup4 anthropic python-telegram-bot pydantic-settings rich ollama schedule
```

### 3. 환경 변수 설정

```bash
cd market-insight/backend

# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env  # 또는 원하는 에디터 사용
```

**.env 파일 예시**:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/market_insight

# API
API_HOST=0.0.0.0
API_PORT=3000
LOG_LEVEL=INFO

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3.2

# KIS API (선택 사항)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret

# Telegram Bot (선택 사항)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Anthropic Claude (선택 사항)
ANTHROPIC_API_KEY=your_api_key
```

### 4. 데이터베이스 초기화

```bash
cd market-insight/backend

# 데이터베이스 초기화
uv run python -c "from storage.db import init_database; init_database()"

# 또는
python -c "from storage.db import init_database; init_database()"
```

성공하면 다음과 같은 메시지가 표시됩니다:

```
Database initialized successfully
```

---

## Next.js 대시보드 설정

### 1. 의존성 설치

```bash
cd market-insight/dashboard

# npm 사용
npm install

# 또는 yarn 사용
yarn install

# 또는 pnpm 사용
pnpm install
```

### 2. 환경 변수 설정 (선택 사항)

```bash
cd market-insight/dashboard

# .env.local 파일 생성
touch .env.local

# API URL 설정 (기본값: http://localhost:3000)
echo "NEXT_PUBLIC_API_URL=http://localhost:3000" > .env.local
```

---

## MCP 서버 설정 (Claude Desktop 연동)

MCP (Model Context Protocol) 서버를 사용하면 Claude Desktop에서 Market Insight 시스템과 직접 상호작용할 수 있습니다.

### 1. MCP 의존성 설치

```bash
cd market-insight/backend

# MCP 의존성 설치
uv pip install -e ".[mcp]"
```

### 2. Claude Desktop 설정

Claude Desktop 설정 파일을 엽니다:

```bash
# macOS
open ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 또는 직접 편집
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

다음 설정을 추가합니다:

```json
{
  "mcpServers": {
    "portfolio": {
      "command": "uv",
      "args": [
        "--directory", "/Users/cessnaj/Desktop/codes/market-insight/backend/mcp_servers/portfolio_mcp",
        "run", "server.py"
      ]
    },
    "memory": {
      "command": "uv",
      "args": [
        "--directory", "/Users/cessnaj/Desktop/codes/market-insight/backend/mcp_servers/memory_mcp",
        "run", "server.py"
      ]
    },
    "content": {
      "command": "uv",
      "args": [
        "--directory", "/Users/cessnaj/Desktop/codes/market-insight/backend/mcp_servers/content_mcp",
        "run", "server.py"
      ]
    }
  }
}
```

**중요**: `/Users/cessnaj/Desktop/codes/market-insight`를 실제 프로젝트 경로로 변경하세요.

### 3. Claude Desktop 재시작

Claude Desktop을 재시작하면 MCP 서버가 자동으로 연결됩니다.

### 4. MCP 서버 테스트

Claude Desktop에서 다음과 같은 명령어를 사용할 수 있습니다:

```
"Show me my portfolio summary"
"What are my recent thoughts about Samsung Electronics?"
"Search for content about semiconductor stocks"
"Log a new thought: I think AI stocks will continue to rise this quarter"
```

### 5. MCP 서버 기능

#### Portfolio MCP Server
- `get_portfolio_summary` - 포트폴리오 요약 조회
- `get_stock_price` - 특정 종목 가격 조회
- `get_portfolio_history` - 포트폴리오 수익률 히스토리
- `log_transaction` - 매수/매도 기록
- `get_holdings` - 보유 종목 목록

#### Memory MCP Server
- `log_thought` - 투자 생각 기록
- `recall_thoughts` - 과거 생각 의미 검색
- `get_thought_timeline` - 특정 종목/주제에 대한 생각 타임라인
- `get_recent_thoughts` - 최근 생각 목록
- `search_by_ticker` - 종목 관련 생각 검색

#### Content MCP Server
- `get_recent_contents` - 최근 수집된 콘텐츠 목록
- `search_content` - 의미 기반 콘텐츠 검색
- `get_content_stats` - 콘텐츠 통계
- `search_by_source` - 특정 소스의 콘텐츠 검색

### 6. MCP 서버 개별 테스트

각 MCP 서버를 개별적으로 테스트할 수 있습니다:

```bash
# Portfolio MCP Server
cd market-insight/backend/mcp_servers/portfolio_mcp
uv run server.py

# Memory MCP Server
cd market-insight/backend/mcp_servers/memory_mcp
uv run server.py

# Content MCP Server
cd market-insight/backend/mcp_servers/content_mcp
uv run server.py
```

### 7. MCP 서버 문제 해결

#### MCP 서버가 Claude Desktop에 표시되지 않음

1. Claude Desktop을 재시작합니다
2. 설정 파일 경로가 올바른지 확인합니다
3. MCP 서버가 개별적으로 실행되는지 테스트합니다

#### 데이터베이스 연결 오류

1. PostgreSQL 컨테이너가 실행 중인지 확인합니다:
```bash
cd market-insight
docker-compose ps
```

2. `.env` 파일에 올바른 데이터베이스 설정이 있는지 확인합니다

3. 데이터베이스가 초기화되었는지 확인합니다:
```bash
cd market-insight/backend
uv run python -c "from storage.db import init_database; init_database()"
```

---

## 데이터베이스 초기화

### 1. 테스트 데이터 생성 (선택 사항)

```bash
cd market-insight/backend

# CLI를 사용하여 테스트 데이터 생성
uv run python -m interface.cli init

# 생각 기록 테스트
uv run python -m interface.cli think "삼성전자 반도체 수요 증가로 상승 예상" -t stock_idea -k 005930 -c 7

# 주식 가격 수집 테스트
uv run python -m interface.cli collect
```

### 2. 데이터베이스 스키마 확인

```bash
# PostgreSQL 컨테이너에 접속
docker exec -it market-insight-db-1 psql -U postgres -d market_insight

# 테이블 목록 확인
\dt

# 테이블 구조 확인
\d stockprice
\d thought
\d contentitem
\d dailyreport

# 종료
\q
```

---

## 서버 실행

### 1. FastAPI 백엔드 실행

**옵션 A: 개발 모드 (자동 재시작)**

```bash
cd market-insight/backend

# uv 사용
uv run uvicorn api.main:app --host 0.0.0.0 --port 3000 --reload

# 또는
uv run python api/main.py
```

**옵션 B: 프로덕션 모드**

```bash
cd market-insight/backend

uv run uvicorn api.main:app --host 0.0.0.0 --port 3000 --workers 4
```

서버가 성공적으로 시작되면 다음과 같은 메시지가 표시됩니다:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
Database initialized
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
```

### 2. API 테스트

```bash
# Health check
curl http://localhost:3000/health

# API 문서 (브라우저에서 접속)
open http://localhost:3000/docs
```

### 3. Next.js 대시보드 실행

```bash
cd market-insight/dashboard

# 개발 모드
npm run dev

# 또는
yarn dev
```

브라우저에서 `http://localhost:3001` 접속 (기본 포트)

### 4. CLI 사용

```bash
cd market-insight/backend

# 포트폴리오 현황
uv run python -m interface.cli portfolio

# 종목 가격 조회
uv run python -m interface.cli price 005930

# 생각 기록
uv run python -m interface.cli think "테스트 메모"

# 과거 생각 검색
uv run python -m interface.cli recall "반도체" -n 10

# 최근 생각 목록
uv run python -m interface.cli thoughts
```

---

## 문제 해결

### Ollama 관련 문제

**문제: "could not connect to ollama server" 오류**

```bash
# 해결 1: Ollama 서버가 실행 중인지 확인
brew services list | grep ollama

# 해결 2: 서버 시작
brew services start ollama

# 해결 3: 포트 확인
lsof -i :11434

# 해결 4: 직접 실행으로 테스트
ollama serve
```

**문제: 모델 다운로드 실패**

```bash
# 해결 1: 인터넷 연결 확인
ping ollama.com

# 해결 2: 다시 시도
ollama pull nomic-embed-text

# 해결 3: 모델 목록 확인
ollama list
```

**문제: 임베딩 생성 실패**

```bash
# 해결 1: 모델이 다운로드되었는지 확인
ollama list

# 해결 2: API 테스트
curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "Hello, world!"
}'

# 해결 3: .env 파일에서 OLLAMA_BASE_URL 확인
cat .env | grep OLLAMA
```

### PostgreSQL 관련 문제

**문제: 컨테이너가 시작되지 않음**

```bash
# 해결 1: 포트 충돌 확인
lsof -i :5432

# 해결 2: 다른 포트 사용 (docker-compose.yml 수정)
# ports:
#   - "5433:5432"

# 해결 3: 컨테이너 로그 확인
docker-compose logs
```

**문제: 데이터베이스 연결 실패**

```bash
# 해결 1: 컨테이너가 실행 중인지 확인
docker ps | grep market-insight-db

# 해결 2: 연결 테스트
docker exec -it market-insight-db-1 psql -U postgres -d market_insight

# 해결 3: .env 파일에서 DATABASE_URL 확인
cat .env | grep DATABASE_URL
```

**문제: pgvector 확장이 없음**

```bash
# 해결 1: pgvector 이미지 사용 중인지 확인
docker ps | grep pgvector

# 해결 2: 확장 수동 설치
docker exec -it market-insight-db-1 psql -U postgres -d market_insight -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 해결 3: 확장 확인
docker exec -it market-insight-db-1 psql -U postgres -d market_insight -c "\dx vector"
```

### Python 백엔드 관련 문제

**문제: 모듈 임포트 오류**

```bash
# 해결 1: 가상환경 활성화 확인
which python

# 해결 2: 의존성 재설치
uv sync

# 해결 3: PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**문제: 데이터베이스 초기화 실패**

```bash
# 해결 1: PostgreSQL 컨테이너 확인
docker ps | grep market-insight-db

# 해결 2: 데이터베이스 연결 테스트
python -c "from storage.db import get_session; next(get_session())"

# 해결 3: 테이블 수동 생성
python -c "from storage.models import SQLModel; from storage.db import engine; SQLModel.metadata.create_all(engine)"
```

### Next.js 대시보드 관련 문제

**문제: TypeScript 에러**

```bash
# 해결 1: 의존성 설치
cd dashboard
npm install

# 해결 2: 타입 검증 건너뛰기 (개발용)
npm run dev -- --no-verify

# 해결 3: 캐시 삭제
rm -rf node_modules .next
npm install
```

**문제: API 연결 실패**

```bash
# 해결 1: 백엔드 서버 확인
curl http://localhost:3000/health

# 해결 2: CORS 설정 확인
# api/main.py에서 allow_origins 확인

# 해결 3: .env.local 확인
cat .env.local | grep API_URL
```

### 스케줄러 관련 문제

**문제: 스케줄러가 작동하지 않음**

```bash
# 해결 1: 스케줄러 로그 확인
tail -f logs/scheduler.log

# 해결 2: APScheduler 설치 확인
python -c "import apscheduler; print(apscheduler.__version__)"

# 해결 3: 스케줄러 수동 실행
python scheduler/daily_jobs.py
```

---

## 추가 리소스

- [시퀀스 다이어그램](SEQUENCE_DIAGRAMS.md) - 시스템 흐름 이해
- [구현 진행 상황](IMPLEMENTATION_PROGRESS.md) - 상세 구현 상태
- [배포 매뉴얼](DEPLOYMENT_MANUAL.md) - 프로덕션 배포 가이드
- [PostgreSQL 마이그레이션](MIGRATION_TO_POSTGRESQL.md) - DB 마이그레이션 가이드

---

## 지원

문제가 발생하면 다음을 확인하세요:

1. 로그 파일: `backend/logs/`
2. Docker 로그: `docker-compose logs`
3. Ollama 로그: `~/.ollama/logs/`

추가 도움이 필요하면 GitHub Issues를 확인하거나 새 이슈를 생성하세요.
