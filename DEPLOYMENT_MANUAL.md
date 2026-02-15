# 배포 매뉴얼 (Deployment Manual)

이 문서는 Market Insight 시스템을 설치하고 실행하는 방법을 설명합니다.

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [데이터베이스 설치](#데이터베이스-설치)
3. [Ollama 설치](#ollama-설치)
4. [백엔드 설정](#백엔드-설정)
5. [대시보드 설정](#대시보드-설정)
6. [MCP 서버 설정 (Claude Desktop)](#mcp-서버-설정-claude-desktop)
7. [시스템 실행](#시스템-실행)
8. [CLI 명령어 가이드](#cli-명령어-가이드)
9. [API 엔드포인트](#api-엔드포인트)
10. [스케줄러 설정](#스케줄러-설정)
11. [문제 해결](#문제-해결)

---

## 사전 요구사항

### 필수 소프트웨어

- **Python**: 3.10 이상
- **Node.js**: 18 이상
- **Docker**: 20.10 이상
- **Docker Compose**: 2.0 이상
- **Git**: 최신 버전

### 설치 확인

```bash
python --version    # Python 3.10+
node --version      # Node.js 18+
docker --version    # Docker 20.10+
docker-compose --version  # Docker Compose 2.0+
git --version       # Git
```

---

## 데이터베이스 설치

### 1. PostgreSQL + pgvector 컨테이너 시작

```bash
cd market-insight
docker-compose up -d
```

### 2. 컨테이너 상태 확인

```bash
docker ps
```

다음과 같은 출력이 보여야 합니다:

```
CONTAINER ID   IMAGE                    COMMAND                  CREATED         STATUS         PORTS
abc123         pgvector/pgvector:pg16   "docker-entrypoint.s…"   5 seconds ago   Up 4 seconds   0.0.0.0:5432->5432/tcp
```

### 3. 데이터베이스 연결 확인

```bash
docker exec -it market-insight-db-1 psql -U investor -d market_insight
```

데이터베이스 프롬프트가 나타나면 성공입니다. `\q`를 입력하여 종료합니다.

### 4. 컨테이너 정리 (필요시)

```bash
# 컨테이너 중지
docker-compose down

# 컨테이너 및 데이터 정리
docker-compose down -v
```

---

## Ollama 설치

### macOS

```bash
brew install ollama
```

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Windows

[Ollama 공식 웹사이트](https://ollama.com/download)에서 설치 파일을 다운로드합니다.

### 모델 다운로드

```bash
# 임베딩 모델 (필수)
ollama pull nomic-embed-text

# 텍스트 생성 모델 (필수)
ollama pull llama3.2

# 선택: 더 큰 모델
ollama pull llama3.2:70b
```

### Ollama 서버 시작

```bash
ollama serve
```

서버는 기본적으로 `http://localhost:11434`에서 실행됩니다.

### Ollama 테스트

```bash
# 임베딩 테스트
curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "Hello, world!"
}'

# 텍스트 생성 테스트
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

---

## 백엔드 설정

### 1. 의존성 설치

```bash
cd backend

# uv 사용 (권장)
uv sync

# 또는 pip 사용
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 필요한 설정을 수정합니다:

```env
# PostgreSQL 연결
database_url=postgresql+psycopg://investor:changeme@localhost:5432/market_insight

# Ollama 설정
ollama_base_url=http://localhost:11434
ollama_model=llama3.2
ollama_embed_model=nomic-embed-text

# Anthropic API (선택)
# anthropic_api_key=your_api_key_here
# anthropic_model=claude-3-5-sonnet-20241022

# API 설정
api_host=0.0.0.0
api_port=3000
log_level=INFO
```

### 3. 데이터베이스 초기화

```bash
cd backend
uv run python -c "from storage.db import init_database; init_database()"
```

### 4. 설정 파일 확인

다음 설정 파일들이 올바르게 구성되어 있는지 확인합니다:

- [`config/watchlist.yaml`](market-insight/backend/config/watchlist.yaml:1) - 관심 종목 목록
- [`config/sources.yaml`](market-insight/backend/config/sources.yaml:1) - 콘텐츠 수집 소스
- [`config/prompts.yaml`](market-insight/backend/config/prompts.yaml:1) - LLM 프롬프트

---

## 대시보드 설정

### 1. 의존성 설치

```bash
cd dashboard
npm install
```

### 2. 환경 변수 설정

```bash
cp .env.example .env.local
```

`.env.local` 파일을 편집합니다:

```env
NEXT_PUBLIC_API_URL=http://localhost:3000
```

### 3. TypeScript 에러 해결

TypeScript 에러가 발생하면 다음을 실행합니다:

```bash
npm install
```

---

## MCP 서버 설정 (Claude Desktop)

MCP (Model Context Protocol) 서버를 사용하면 Claude Desktop에서 Market Insight 시스템과 직접 상호작용할 수 있습니다.

### 1. MCP 의존성 설치

```bash
cd backend

# MCP 의존성 설치
uv pip install -e ".[mcp]"
```

### 2. Claude Desktop 설정

Claude Desktop 설정 파일을 엽니다:

```bash
# macOS
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

다음 설정을 추가합니다:

```json
{
  "mcpServers": {
    "portfolio": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/market-insight/backend/mcp_servers/portfolio_mcp",
        "run", "server.py"
      ]
    },
    "memory": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/market-insight/backend/mcp_servers/memory_mcp",
        "run", "server.py"
      ]
    },
    "content": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/market-insight/backend/mcp_servers/content_mcp",
        "run", "server.py"
      ]
    }
  }
}
```

**중요**: `/path/to/market-insight`를 실제 프로젝트 경로로 변경하세요.

### 3. Claude Desktop 재시작

Claude Desktop을 재시작하면 MCP 서버가 자동으로 연결됩니다.

### 4. 사용 예시

Claude Desktop에서 다음과 같은 명령어를 사용할 수 있습니다:

```
"Show me my portfolio summary"
"What are my recent thoughts about Samsung Electronics?"
"Search for content about semiconductor stocks"
"Log a new thought: I think AI stocks will continue to rise this quarter"
```

### 5. MCP 서버 테스트

각 MCP 서버를 개별적으로 테스트할 수 있습니다:

```bash
# Portfolio MCP Server
cd backend/mcp_servers/portfolio_mcp
uv run server.py

# Memory MCP Server
cd backend/mcp_servers/memory_mcp
uv run server.py

# Content MCP Server
cd backend/mcp_servers/content_mcp
uv run server.py
```

---

## 시스템 실행

### 옵션 1: 개발 모드 (여러 터미널 사용)

#### 터미널 1: FastAPI 서버

```bash
cd backend
uv run python api/main.py
```

서버가 `http://localhost:3000`에서 실행됩니다.

#### 터미널 2: Next.js 대시보드

```bash
cd dashboard
npm run dev
```

대시보드가 `http://localhost:3001`에서 실행됩니다.

#### 터미널 3: 스케줄러 (선택)

```bash
cd backend
uv run python -c "from scheduler.daily_jobs import start_scheduler; start_scheduler()"
```

### 옵션 2: 프로덕션 모드

#### FastAPI 서버 (Gunicorn)

```bash
cd backend
pip install gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3000
```

#### Next.js 대시보드

```bash
cd dashboard
npm run build
npm start
```

---

## CLI 명령어 가이드

### 포트폴리오 관리

```bash
# 포트폴리오 현황 조회
inv portfolio

# 종목 가격 조회
inv price 005930

# 주식 가격 수집
inv collect
```

### 생각 기록

```bash
# 생각 기록
inv think "삼성전자 반도체 수요 증가로 상승 예상" -t stock_idea -k 005930 -c 7

# 과거 생각 검색
inv recall "반도체" -n 10

# 최근 생각 목록
inv thoughts
```

### 콘텐츠 수집

```bash
# YouTube 콘텐츠 수집
inv content youtube

# 네이버 블로그 콘텐츠 수집
inv content naver

# 최근 콘텐츠 목록
inv content list -n 10
```

### 리포트 생성

```bash
# 일일 리포트 생성
inv report daily

# 특정 날짜의 일일 리포트
inv report daily -d 2024-01-15

# 주간 리포트 생성
inv report weekly

# 최근 리포트 목록
inv report list-reports -n 5
```

### 스케줄러 관리

```bash
# 스케줄러 시작
inv scheduler start

# 예약된 작업 목록
inv scheduler jobs

# 작업 즉시 실행
inv scheduler run collect_youtube
inv scheduler run daily_report
```

### 유틸리티

```bash
# 데이터베이스 초기화
inv init
```

---

## API 엔드포인트

### API 문서

```
http://localhost:3000/docs
```

### 헬스 체크

```bash
curl http://localhost:3000/health
```

### 포트폴리오 엔드포인트

```bash
# 포트폴리오 요약
curl http://localhost:3000/api/v1/portfolio/summary

# 보유 종목 목록
curl http://localhost:3000/api/v1/portfolio/holdings

# 종목 가격
curl http://localhost:3000/api/v1/portfolio/prices/005930

# 가격 수집
curl -X POST http://localhost:3000/api/v1/portfolio/prices/fetch
```

### 생각 엔드포인트

```bash
# 생각 기록
curl -X POST http://localhost:3000/api/v1/thoughts \
  -H "Content-Type: application/json" \
  -d '{"content": "테스트 메모", "thought_type": "general"}'

# 최근 생각 목록
curl http://localhost:3000/api/v1/thoughts?limit=10

# 생각 검색
curl -X POST http://localhost:3000/api/v1/thoughts/search \
  -H "Content-Type: application/json" \
  -d '{"query": "반도체", "limit": 5}'
```

### 콘텐츠 엔드포인트

```bash
# 최근 콘텐츠 목록
curl http://localhost:3000/api/v1/content/?limit=10

# 특정 콘텐츠 조회
curl http://localhost:3000/api/v1/content/{content_id}

# YouTube 수집 시작
curl -X POST http://localhost:3000/api/v1/content/collect/youtube

# 네이버 블로그 수집 시작
curl -X POST http://localhost:3000/api/v1/content/collect/naver
```

### 리포트 엔드포인트

```bash
# 최근 리포트 목록
curl http://localhost:3000/api/v1/reports/?limit=5

# 최신 리포트
curl http://localhost:3000/api/v1/reports/latest

# 일일 리포트 생성
curl -X POST http://localhost:3000/api/v1/reports/generate/daily

# 주간 리포트 생성
curl -X POST http://localhost:3000/api/v1/reports/generate/weekly
```

---

## 스케줄러 설정

### 기본 스케줄

| 작업 | 스케줄 | 설명 |
|------|---------|------|
| YouTube 수집 | 6시간마다 | YouTube 채널에서 새 동영상 수집 |
| 네이버 블로그 수집 | 12시간마다 | 네이버 블로그에서 새 게시글 수집 |
| 주식 가격 추적 | 장중 1시간마다 (9-15시) | 포트폴리오 및 관심종목 가격 수집 |
| 일일 리포트 | 매일 20:00 | 일일 투자 리포트 생성 |
| 주간 리포트 | 일요일 21:00 | 주간 투자 리포트 생성 |
| 일일 스냅샷 | 매일 18:00 | 포트폴리오 일일 스냅샷 생성 |

### 스케줄러 실행

```bash
# 백그라운드에서 실행
nohup uv run python -c "from scheduler.daily_jobs import start_scheduler; start_scheduler()" > scheduler.log 2>&1 &

# 또는 systemd 서비스로 실행 (권장)
sudo cp market-insight.service /etc/systemd/system/
sudo systemctl enable market-insight
sudo systemctl start market-insight
```

### 스케줄러 로그 확인

```bash
# 백그라운드 실행 시
tail -f scheduler.log

# systemd 서비스 실행 시
sudo journalctl -u market-insight -f
```

---

## 문제 해결

### PostgreSQL 연결 실패

**증상**: `psycopg2.OperationalError: could not connect to server`

**해결**:
```bash
# Docker 컨테이너 상태 확인
docker ps

# 컨테이너 재시작
docker-compose restart

# 로그 확인
docker-compose logs
```

### Ollama 연결 실패

**증상**: `Error connecting to Ollama server`

**해결**:
```bash
# Ollama 서버 실행 확인
ollama serve

# 다른 터미널에서 테스트
curl http://localhost:11434/api/tags

# 모델 확인
ollama list
```

### 의존성 설치 실패

**증상**: `uv sync` 또는 `npm install` 실패

**해결**:
```bash
# Python 의존성
pip install --upgrade pip
pip install uv
uv sync --reinstall

# Node.js 의존성
rm -rf node_modules package-lock.json
npm install
```

### 벡터 임베딩 오류

**증상**: `Warning: Ollama embedding failed, using hash-based fallback`

**해결**:
```bash
# Ollama 서버 확인
curl http://localhost:11434/api/tags

# 임베딩 모델 확인
ollama list

# 모델 재다운로드
ollama pull nomic-embed-text
```

### API CORS 오류

**증상**: 브라우저에서 CORS 에러 발생

**해결**:
[`api/main.py`](market-insight/backend/api/main.py:1)에서 CORS 설정 확인:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 스케줄러 작업 실패

**증상**: 스케줄러 작업이 실행되지 않음

**해결**:
```bash
# 스케줄러 로그 확인
tail -f scheduler.log

# 작업 수동 실행 테스트
inv scheduler run daily_report

# 스케줄러 재시작
pkill -f scheduler
inv scheduler start
```

---

## 추가 리소스

- [README.md](market-insight/README.md:1) - 프로젝트 개요
- [IMPLEMENTATION_PROGRESS.md](market-insight/IMPLEMENTATION_PROGRESS.md:1) - 구현 진행 상황
- [MIGRATION_TO_POSTGRESQL.md](market-insight/MIGRATION_TO_POSTGRESQL.md:1) - PostgreSQL 마이그레이션 가이드

---

## 지원

문제가 발생하면 다음을 확인하세요:

1. 이 매뉴얼의 문제 해결 섹션
2. 로그 파일 (`logs/` 디렉토리)
3. API 문서 (`http://localhost:3000/docs`)
