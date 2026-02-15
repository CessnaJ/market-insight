# 구현 진행 상황

## 완료된 작업

### Phase 0: 기반 환경 세팅 ✅
- [x] 프로젝트 디렉토리 구조 생성 (`backend/`, `dashboard/` 분리)
- [x] `backend/pyproject.toml` 생성 (FastAPI 포함)
- [x] `backend/.env.example` 파일 생성
- [x] `docker-compose.yml` 생성 (PostgreSQL + pgvector)
- [x] `config/watchlist.yaml` 생성
- [x] `config/sources.yaml` 생성
- [x] `config/prompts.yaml` 생성

### Phase 1-A: 주식 가격 수집 ✅
- [x] `storage/models.py` 생성 (PostgreSQL + pgvector 스키마)
  - StockPrice, PortfolioHolding, Transaction, DailySnapshot
  - ContentItem, Thought, DailyReport
  - VectorStore 모델 (pgvector용)
- [x] `storage/db.py` 생성 (PostgreSQL + pgvector 연결)
  - Settings, get_session, init_database
  - Portfolio, Thought, Content, Snapshot operations
  - pgvector 확장 활성화
- [x] `storage/vector_store.py` 생성 (PostgreSQL + pgvector)
  - VectorStore 클래스
  - add_thought(), add_content(), add_ai_chat()
  - search_similar_thoughts(), search_related_content()
  - 개발용 해시 기반 임베딩 (Ollama 연동 필요)
- [x] `collector/stock_tracker.py` 생성
  - fetch_korean_stock() (KIS API - TODO)
  - fetch_us_stock() (Yahoo Finance)
  - track_portfolio(), track_watchlist()

### Phase 1-B: 생각 기록 기능 ✅
- [x] `collector/thought_logger.py` 생성
  - ThoughtType enum (market_view, stock_idea, risk_concern, etc.)
  - log(), get_thought(), search_thoughts()
  - Markdown 원본 저장

### Phase 2: FastAPI 백엔드 ✅
- [x] `api/main.py` 생성 (포트 3000)
  - CORS middleware
  - Health check endpoint
  - Router includes (portfolio, thoughts, content, reports)
- [x] `api/routes/portfolio.py` 생성
  - GET /summary - 포트폴리오 요약
  - GET /holdings - 보유 종목 목록
  - POST /holdings - 종목 추가
  - GET /prices/{ticker} - 종목 가격
  - POST /prices/fetch - 가격 수집
  - POST /transactions - 매수/매도 기록
  - GET /snapshots - 일별 스냅샷
- [x] `api/routes/thoughts.py` 생성
  - POST / - 생각 기록
  - GET / - 최근 생각 목록
  - GET /{thought_id} - 특정 생각 조회
  - PUT /{thought_id} - 생각 업데이트
  - DELETE /{thought_id} - 생각 삭제
  - POST /search - 의미 기반 검색
  - GET /ticker/{ticker} - 종목 관련 생각
- [x] `api/routes/content.py` 생성
  - GET /content/ - 최근 콘텐츠 목록
  - GET /content/{content_id} - 특정 콘텐츠 조회
  - GET /content/ticker/{ticker} - 종목 관련 콘텐츠
  - POST /content/collect/youtube - YouTube 수집 시작
  - POST /content/collect/naver - 네이버 블로그 수집 시작
  - POST /content/collect/all - 전체 콘텐츠 수집 시작
  - POST /content/search - 콘텐츠 검색
- [x] `api/routes/reports.py` 생성
  - GET /reports/ - 최근 리포트 목록
  - GET /reports/latest - 최신 리포트
  - GET /reports/{report_id} - 특정 리포트 조회
  - GET /reports/date/{target_date} - 날짜별 리포트
  - POST /reports/generate/daily - 일일 리포트 생성
  - POST /reports/generate/weekly - 주간 리포트 생성

### Phase 3: 기본 인터페이스 ✅
- [x] `interface/cli.py` 생성 (Click + Rich)
  - `inv portfolio` - 포트폴리오 현황
  - `inv price <ticker>` - 종목 가격 조회
  - `inv think <content>` - 생각 기록
  - `inv recall <query>` - 과거 생각 검색
  - `inv thoughts` - 최근 생각 목록
  - `inv init` - 데이터베이스 초기화
  - `inv collect` - 주식 가격 수집

### Phase 4: Next.js 대시보드 (기본 구조) ✅
- [x] `dashboard/package.json` 생성
  - Next.js 14, React 18, TypeScript
  - Recharts, Lucide React, Tailwind CSS
- [x] `dashboard/tsconfig.json` 생성
- [x] `dashboard/tailwind.config.ts` 생성
- [x] `dashboard/postcss.config.js` 생성
- [x] `dashboard/next.config.js` 생성
- [x] `dashboard/src/app/globals.css` 생성
- [x] `dashboard/src/app/layout.tsx` 생성
- [x] `dashboard/src/app/page.tsx` 생성
  - 포트폴리오 요약 카드 (총 평가액, 총 손익, 수익률)
  - 보유 종목 테이블
  - Refresh 버튼
  - 로딩/에러 상태 처리
- [x] `dashboard/README.md` 생성
- [x] 프로젝트 README 업데이트

## 마이그레이션 완료

### SQLite + ChromaDB → PostgreSQL + pgvector ✅
- [x] `docker-compose.yml` 생성 (PostgreSQL + pgvector 컨테이너)
- [x] `storage/db.py` PostgreSQL 연동 완료
- [x] `storage/vector_store.py` pgvector로 마이그레이션
- [x] `.env.example` PostgreSQL 설정 추가
- [x] `pyproject.toml` 의존성 업데이트 (psycopg2-binary, pgvector)

**참고**: `MIGRATION_TO_POSTGRESQL.md` 파일에서 상세 마이그레이션 가이드 확인

## 다음 단계

### 의존성 설치 및 테스트
- [x] PostgreSQL + pgvector Docker 컨테이너 설정
  ```bash
  cd market-insight
  docker-compose up -d
  # 확인: docker ps
  ```
- [ ] `backend/` 의존성 설치
  ```bash
  cd backend
  uv sync  # 또는 pip install -r requirements.txt
  ```
- [ ] `.env` 파일 설정
  ```bash
  cp .env.example .env
  # .env 파일에서 DB_PASSWORD 등 필요한 설정 수정
  ```
- [ ] 데이터베이스 초기화 테스트
  ```bash
  cd backend
  uv run python -c "from storage.db import init_database; init_database()"
  ```
- [ ] FastAPI 서버 실행 테스트
  ```bash
  cd backend
  uv run python api/main.py
  # http://localhost:3000/docs 확인
  ```
- [ ] CLI 명령어 테스트
  ```bash
  inv init
  inv portfolio
  inv think "테스트 메모"
  ```

### Week 2 완료 ✅
- [x] YouTube 콘텐츠 수집기 (`collector/youtube_collector.py`)
  - RSS feed 파싱
  - 동영상 정보 추출 (제목, 설명, URL)
  - LLM 기반 요약 및 엔티티 추출
  - 벡터 저장소에 임베딩 저장
- [x] 네이버 블로그 수집기 (`collector/naver_blog_collector.py`)
  - RSS feed 파싱
  - 블로그 게시글 정보 추출
  - LLM 기반 요약 및 엔티티 추출
  - 벡터 저장소에 임베딩 저장
- [x] 일일/주간 리포트 생성기 (`analyzer/report_builder.py`)
  - 포트폴리오 데이터 수집
  - 최근 생각 및 콘텐츠 요약
  - LLM 기반 리포트 생성
  - 과거 유사 생각 검색 (주간 리포트)
- [x] 스케줄러 (`scheduler/daily_jobs.py`)
  - YouTube 수집 (6시간마다)
  - 네이버 블로그 수집 (12시간마다)
  - 주식 가격 추적 (장중 1시간마다)
  - 일일 리포트 생성 (매일 8시)
  - 주간 리포트 생성 (일요일 9시)
  - 일일 스냅샷 생성 (매일 6시)
- [x] LLM 라우터 (`analyzer/llm_router.py`)
  - Ollama 지원 (llama3.2, nomic-embed-text)
  - Anthropic Claude 지원 (선택적)
  - 텍스트 생성
  - 임베딩 생성
  - 구조화된 출력 (JSON)
  - 생각 분류
  - 콘텐츠 요약
  - 엔티티 추출
- [x] Ollama 임베딩 연동 (nomic-embed-text)
  - vector_store.py 업데이트
  - 해시 기반 임베딩에서 실제 임베딩으로 변경
  - 폴백 메커니즘 (Ollama 연결 실패 시 해시 기반 사용)

### Week 2 완료 ✅ (API Routes)
- [x] `api/routes/content.py` 생성
  - 콘텐츠 조회 엔드포인트 (목록, 상세, 종목별)
  - 콘텐츠 수집 엔드포인트 (YouTube, Naver, 전체)
  - 콘텐츠 검색 엔드포인트
- [x] `api/routes/reports.py` 생성
  - 리포트 조회 엔드포인트 (목록, 최신, 상세, 날짜별)
  - 리포트 생성 엔드포인트 (일일, 주간)
- [x] `api/main.py` 업데이트
  - content, reports 라우터 포함

### Week 3 예정
- [x] MCP 서버 구현 (`mcp_servers/`)
  - [x] Portfolio MCP Server (`portfolio_mcp/server.py`)
  - [x] Memory MCP Server (`memory_mcp/server.py`)
  - [x] Content MCP Server (`content_mcp/server.py`)
  - [x] MCP 서버 README (`mcp_servers/README.md`)
  - [x] pyproject.toml에 mcp 의존성 추가
- [x] 대시보드 기능 확장 (생각 기록 UI, 리포트 조회)
  - [x] 생각 기록 페이지 (`dashboard/src/app/thoughts/page.tsx`)
  - [x] 리포트 조회 페이지 (`dashboard/src/app/reports/page.tsx`)
  - [x] 네비게이션 추가
- [x] Telegram Bot 구현 (`interface/telegram_bot.py`)
  - [x] 기본 명령어 (/start, /portfolio, /think, /recall, /report, /ask, /help)
  - [x] 자동 생각 기록 (일반 메시지)
  - [x] LLM 기반 분류
  - [x] 벡터 검색 통합
- [x] KIS API 연동 (한국투자증권 OpenAPI)
  - [x] OAuth 토큰 발급 구현
  - [x] 주식현재가 시세 API 연동
  - [x] 폴백 메커니즘 (API 키 없으면 mock 데이터)
- [ ] 대시보드 실시간 업데이트 (WebSocket)
- [ ] 알림 시스템 (이메일, 텔레그램)

## 파일 구조

```
market-insight/
├── docker-compose.yml ✅
├── MIGRATION_TO_POSTGRESQL.md ✅
├── README.md ✅
├── backend/
│   ├── api/
│   │   ├── main.py ✅
│   │   └── routes/
│   │       ├── portfolio.py ✅
│   │       ├── thoughts.py ✅
│   │       ├── content.py ✅
│   │       └── reports.py ✅
│   ├── collector/
│   │   ├── stock_tracker.py ✅
│   │   ├── thought_logger.py ✅
│   │   ├── youtube_collector.py ✅
│   │   └── naver_blog_collector.py ✅
│   ├── storage/
│   │   ├── models.py ✅
│   │   ├── db.py ✅
│   │   └── vector_store.py ✅
│   ├── interface/
│   │   └── cli.py ✅
│   ├── analyzer/
│   │   ├── llm_router.py ✅
│   │   └── report_builder.py ✅
│   ├── scheduler/
│   │   └── daily_jobs.py ✅
│   ├── config/
│   │   ├── watchlist.yaml ✅
│   │   ├── sources.yaml ✅
│   │   └── prompts.yaml ✅
│   ├── data/
│   │   ├── raw/          # 원본 데이터 저장
│   │   └── reports/      # 생성된 리포트
│   ├── logs/
│   ├── mcp_servers/      # (예정) MCP 서버들
│   ├── pyproject.toml ✅
│   └── .env.example ✅
├── dashboard/
│   ├── src/
│   │   └── app/
│   │       ├── layout.tsx ✅
│   │       ├── page.tsx ✅
│   │       └── globals.css ✅
│   ├── package.json ✅
│   ├── tsconfig.json ✅
│   ├── tailwind.config.ts ✅
│   ├── postcss.config.js ✅
│   ├── next.config.js ✅
│   └── README.md ✅
```

**참고**: `data/chroma/` 및 `data/sqlite/` 디렉토리는 마이그레이션 이후 사용되지 않습니다.

## 알려진 문제

### TypeScript 에러 (dashboard/)
- `react`, `next`, `lucide-react` 모듈을 찾을 수 없음
- 원인: `npm install` 아직 실행 안 함
- 해결: `cd dashboard && npm install`

### Ollama 임베딩 (backend/)
- 현재: Ollama nomic-embed-text 연동 완료 ✅
- 해결:
  1. Ollama 설치: `brew install ollama`
  2. 모델 다운로드: `ollama pull nomic-embed-text`
  3. `storage/vector_store.py`의 `_embed()` 메서드 수정 완료
  4. 폴백 메커니즘: Ollama 연결 실패 시 해시 기반 임베딩 사용

### PostgreSQL + pgvector (backend/)
- 현재: PostgreSQL + pgvector로 마이그레이션 완료 ✅
- 필요: Docker 컨테이너 시작 (`docker-compose up -d`)
- 참고: `docker-compose down -v`로 컨테이너 및 데이터 정리 가능
- 상세: `MIGRATION_TO_POSTGRESQL.md` 참조

### KIS API (backend/)
- 현재: mock 데이터 반환
- TODO: 한국투자증권 OpenAPI 연동

### Telegram Bot (예정)
- 현재: 구현되지 않음
- 계획: Week 3에 구현 예정
- 설치: `uv pip install -e ".[telegram]"`
- 설정: `.env` 파일에 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 설정
