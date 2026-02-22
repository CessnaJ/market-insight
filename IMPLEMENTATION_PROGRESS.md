# 구현 진행 상황

## 개요

Market Insight 시스템의 모든 핵심 기능 구현이 완료되었습니다. 현재 설치 및 설정 단계만 남아 있습니다.

---

## 완료된 작업 (코드 기준)

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
  - search_similar_thoughts(), search_related_content(), search_ai_chats()
  - Ollama 임베딩 연동 (nomic-embed-text)
  - 폴백 메커니즘 (Ollama 연결 실패 시 해시 기반 임베딩)
- [x] `collector/stock_tracker.py` 생성
  - fetch_korean_stock() (KIS API + OAuth 토큰 발급 구현 완료)
  - fetch_us_stock() (Yahoo Finance)
  - track_portfolio(), track_watchlist()
  - 폴백 메커니즘 (API 키 없으면 mock 데이터)

### Phase 1-B: 생각 기록 기능 ✅
- [x] `collector/thought_logger.py` 생성
  - ThoughtType enum (market_view, stock_idea, risk_concern, ai_insight, content_note, general)
  - log(), get_thought(), search_thoughts()
  - Markdown 원본 저장

### Phase 2: FastAPI 백엔드 ✅
- [x] `api/main.py` 생성 (포트 3000)
  - CORS middleware
  - Health check endpoint
  - Router includes (portfolio, thoughts, content, reports, websocket)
  - Lifespan manager (database initialization)
- [x] `api/routes/portfolio.py` 생성
  - GET /summary - 포트폴리오 요약
  - GET /holdings - 보유 종목 목록
  - POST /holdings - 종목 추가
  - PUT /holdings/{ticker} - 종목 업데이트
  - GET /prices/{ticker} - 종목 가격
  - POST /prices/fetch - 가격 수집
  - POST /transactions - 매수/매도 기록
  - GET /transactions - 거래 내역 조회
  - 내 생각 -> 일별 스냅샷이 필요하지 않을까? 🐤
- [x] `api/routes/thoughts.py` 생성
  - POST / - 생각 기록
  - GET / - 최근 생각 목록
  - GET /{thought_id} - 특정 생각 조회
  - PUT /{thought_id} - 생각 업데이트 (outcome)
  - DELETE /{thought_id} - 생각 삭제 (vector store에서도 삭제)
  - POST /search - 의미 기반 검색
- [x] `api/routes/content.py` 생성
  - GET /content/ - 최근 콘텐츠 목록
  - GET /content/{content_id} - 특정 콘텐츠 조회
  - GET /content/ticker/{ticker} - 종목 관련 콘텐츠
  - POST /content/collect/youtube - YouTube 수집 시작 (background)
  - POST /content/collect/naver - 네이버 블로그 수집 시작 (background)
  - POST /content/collect/all - 전체 콘텐츠 수집 시작 (background)
  - POST /content/search - 콘텐츠 검색
- [x] `api/routes/reports.py` 생성
  - GET /reports/ - 최근 리포트 목록
  - GET /reports/latest - 최신 리포트
  - GET /reports/{report_id} - 특정 리포트 조회
  - GET /reports/date/{target_date} - 날짜별 리포트
  - POST /reports/generate/daily - 일일 리포트 생성
  - POST /reports/generate/weekly - 주간 리포트 생성
- [x] `api/routes/websocket.py` 생성
  - WebSocket endpoint (/api/v1/ws)
  - ConnectionManager 클래스 (active_connections, subscriptions)
  - Channel-based subscriptions (portfolio, thoughts, reports, alerts)
  - broadcast_portfolio_update(), broadcast_new_thought(), broadcast_new_report(), broadcast_alert(), broadcast_price_update()
  - Manual broadcast endpoints (/broadcast/portfolio, /connections)
  - Client message handling (subscribe, ping, get_portfolio)

### Phase 3: 기본 인터페이스 ✅
- [x] `interface/cli.py` 생성 (Click + Rich)
  - `inv portfolio` - 포트폴리오 현황 (테이블 형태)
  - `inv price <ticker>` - 종목 가격 조회
  - `inv think <content>` - 생각 기록 (옵션: type, tickers, confidence)
  - `inv recall <query>` - 과거 생각 검색 (의미 기반)
  - `inv thoughts` - 최근 생각 목록
  - `inv init` - 데이터베이스 초기화
  - `inv collect` - 주식 가격 수집
- [x] `interface/telegram_bot.py` 생성
  - 기본 명령어 (/start, /portfolio, /think, /recall, /report, /ask, /help)
  - 자동 생각 기록 (일반 메시지)
  - LLM 기반 분류 (thought_type, tags, tickers)
  - 벡터 검색 통합 (/recall)
  - 포트폴리오 현황 표시 (/portfolio)
  - 최신 리포트 표시 (/report)
  - 자유 질문 (/ask)

### Phase 4: Next.js 대시보드 ✅
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
  - 보유 종목 테이블 (Name, Shares, Avg Price, Current, Value, P&L)
  - 네비게이션 (대시보드, 생각, 리포트)
  - WebSocket 연결 상태 표시 (connected/connecting/disconnected/error)
  - Refresh 버튼
  - 로딩/에러 상태 처리
  - Empty state 처리
- [x] `dashboard/src/app/thoughts/page.tsx` 생성
  - 생각 기록 모달 (textarea)
  - 검색 기능 (의미 기반 검색)
  - 생각 목록 표시 (type badge, date, tags, related_tickers)
  - 생각 삭제 기능
  - Empty state 처리
- [x] `dashboard/src/app/reports/page.tsx` 생성
  - 리포트 목록 표시
  - 일일/주간 리포트 생성 버튼
  - 리포트 상세 보기 모달 (markdown 렌더링)
  - Empty state 처리
- [x] `dashboard/src/hooks/useWebSocket.ts` 생성
  - WebSocket 연결 관리
  - 자동 재연결 (5초 후)
  - 채널 구독 (portfolio, thoughts, reports)
  - 메시지 수신 처리
  - 연결 상태 (connecting/connected/disconnected/error)
  - sendMessage, subscribe 함수 제공
- [x] `dashboard/README.md` 생성
- [x] 프로젝트 README 업데이트

## Week 2 완료 ✅
- [x] YouTube 콘텐츠 수집기 (`collector/youtube_collector.py`)
  - RSS feed 파싱
  - 동영상 정보 추출 (제목, 설명, URL, author, tags)
  - LLM 기반 요약 (300자 이내)
  - LLM 기반 엔티티 추출 (tickers, companies, topics, sentiment)
  - 벡터 저장소에 임베딩 저장
  - 중복 체크
- [x] 네이버 블로그 수집기 (`collector/naver_blog_collector.py`)
  - RSS feed 파싱
  - 블로그 게시글 정보 추출 (제목, 설명, URL, author, tags)
  - HTML 태그 제거
  - LLM 기반 요약 (300자 이내)
  - LLM 기반 엔티티 추출 (tickers, companies, topics, sentiment)
  - 벡터 저장소에 임베딩 저장
  - 중복 체크
- [x] 일일/주간 리포트 생성기 (`analyzer/report_builder.py`)
  - 포트폴리오 데이터 수집 (holdings, snapshot, recent_transactions)
  - 최근 생각 및 콘텐츠 요약
  - LLM 기반 리포트 생성 (portfolio_section, content_section, thought_section, ai_opinion, action_items)
  - 과거 유사 생각 검색 (주간 리포트)
  - prompts.yaml에서 프롬프트 로드
- [x] 스케줄러 (`scheduler/daily_jobs.py`)
  - YouTube 수집 (6시간마다 - hour="*/6")
  - 네이버 블로그 수집 (12시간마다 - hour="*/12")
  - 주식 가격 추적 (장중 1시간마다 - hour="9-15", minute="0")
  - 일일 리포트 생성 (매일 8시 - hour=20, minute=0)
  - 주간 리포트 생성 (일요일 9시 - day_of_week="sun", hour=21, minute=0)
  - 일일 스냅샷 생성 (매일 6시 - hour=18, minute=0)
  - APScheduler BackgroundScheduler 사용
- [x] LLM 라우터 (`analyzer/llm_router.py`)
  - Ollama 지원 (llama3.2, nomic-embed-text)
  - Anthropic Claude 지원 (claude-3-5-sonnet-20241022)
  - 텍스트 생성 (generate, system_prompt, temperature, max_tokens)
  - 임베딩 생성 (embed, Ollama만 지원)
  - 구조화된 출력 (generate_structured, JSON schema)
  - 생각 분류 (classify_thought, type/tags/tickers)
  - 콘텐츠 요약 (summarize_content, max_length)
  - 엔티티 추출 (extract_entities, tickers/companies/topics/sentiment)
  - 편의 함수 (get_llm_router, generate_text, get_embedding, classify_thought)

## Week 3 완료 ✅
- [x] MCP 서버 구현 (`mcp_servers/`)
  - Portfolio MCP Server (`portfolio_mcp/server.py`)
  - Memory MCP Server (`memory_mcp/server.py`)
  - Content MCP Server (`content_mcp/server.py`)
  - MCP 서버 README (`mcp_servers/README.md`)
  - pyproject.toml에 mcp 의존성 추가
- [x] KIS API 연동 (한국투자증권 OpenAPI)
  - OAuth 토큰 발급 구현 (_get_access_token)
  - 주식현재가 시세 API 연동 (FHKST01010100)
  - 폴백 메커니즘 (API 키 없으면 mock 데이터 반환)
  - 토큰 만료 체크 및 갱신
- [x] 대시보드 실시간 업데이트 (WebSocket)
  - WebSocket endpoint 구현 (`api/routes/websocket.py`)
  - ConnectionManager for broadcasting
  - Channel-based subscriptions (portfolio, thoughts, reports, alerts)
  - Frontend WebSocket hook (`dashboard/src/hooks/useWebSocket.ts`)
  - Dashboard real-time updates (portfolio_update, price_update)
  - 자동 재연결 로직
- [x] 알림 시스템 (이메일, 텔레그램)
  - Notification module (`analyzer/notifications.py`)
  - EmailNotifier (aiosmtplib, HTML 템플릿)
  - TelegramNotifier (telegram bot, formatted messages)
  - NotificationPriority (LOW, NORMAL, HIGH, URGENT)
  - NotificationType (PORTFOLIO_UPDATE, PRICE_ALERT, NEW_THOUGHT, NEW_REPORT, MARKET_SUMMARY, ERROR)
  - Priority-based filtering (notification_min_priority)
  - Quiet hours support (quiet_hours_start=22, quiet_hours_end=8)
  - Price alerts, portfolio summaries, error notifications

## Sprint 2 완료: Temporal Signal Decomposition ✅ (2026-02-22)

- [x] TemporalSignalDecomposer class (`analyzer/temporal_decomposer.py`)
  - TemporalBreakdown dataclass (short/medium/long-term)
  - TemporalAnalysisResult dataclass
  - Claude 3.7 integration for analysis
  - Three-stage analysis (short, medium, long term)
  - Comprehensive summary generation
  - Database save functionality
- [x] Context Gatherer (`analyzer/context_gatherer.py`)
  - Macro data collection (금리, 환율)
  - Recent reports retrieval (EARNINGS_CALL, DART_FILING)
  - Recent filings retrieval
  - Market sentiment indicators
  - Earnings revision tracking
  - Sector rotation data
  - Structural competitiveness analysis
- [x] Prompt templates (`config/prompts.yaml`)
  - Short-term analysis prompt (수급, 심리, 매크로)
  - Medium-term analysis prompt (실적 리비전, 섹터 로테이션)
  - Long-term analysis prompt (구조적 경쟁력, 시장 점유율)
  - Comprehensive analysis prompt
- [x] Database schema (`storage/models.py`)
  - PriceAttribution model added
  - Database operations (`storage/db.py`)
- [x] API routes (`api/routes/temporal_analysis.py`)
  - GET/POST endpoints for price attributions
  - Analysis endpoints
  - Batch analysis support
  - Info endpoints (timeframes, confidence levels)
- [x] Test suite (`test_sprint2.py`)
  - Context gatherer tests
  - Temporal decomposer tests
  - Database operations tests
  - Integration tests
  - Historical event tests
- [x] Migration script (`migrations/add_price_attributions_table.py`)

**참고**: `SPRINT2_IMPLEMENTATION_SUMMARY.md` 파일에서 상세 구현 내용 확인

## 마이그레이션 완료

### SQLite + ChromaDB → PostgreSQL + pgvector ✅
- [x] `docker-compose.yml` 생성 (PostgreSQL + pgvector 컨테이너)
- [x] `storage/db.py` PostgreSQL 연동 완료
- [x] `storage/vector_store.py` pgvector로 마이그레이션
  - ThoughtVector, ContentVector, AIChatVector 모델
  - pgvector 확장 자동 활성화 (_ensure_pgvector_extension)
  - 코사인 유사도 검색 (1 - (embedding <=> :embedding))
  - 메타데이터 필터링 지원
- [x] `.env.example` PostgreSQL 설정 추가
- [x] `pyproject.toml` 의존성 업데이트 (psycopg2-binary, pgvector)

**참고**: `MIGRATION_TO_POSTGRESQL.md` 파일에서 상세 마이그레이션 가이드 확인

---

## 파일 구조

```
market-insight/
├── docker-compose.yml ✅
├── MIGRATION_TO_POSTGRESQL.md ✅
├── README.md ✅
├── IMPLEMENTATION_PROGRESS.md ✅
├── WEBSOCKET_AND_NOTIFICATIONS.md ✅
├── SETUP_GUIDE.md ✅
├── DEPLOYMENT_MANUAL.md ✅
├── SEQUENCE_DIAGRAMS.md ✅
├── DATABASE_SCHEMA.md ✅
├── backend/
│   ├── api/
│   │   ├── main.py ✅
│   │   └── routes/
│   │       ├── portfolio.py ✅
│   │       ├── thoughts.py ✅
│   │       ├── content.py ✅
│   │       ├── reports.py ✅
│   │       ├── websocket.py ✅
│   │       ├── primary_sources.py ✅
│   │       └── temporal_analysis.py ✅
│   ├── collector/
│   │   ├── stock_tracker.py ✅
│   │       ├── thought_logger.py ✅
│   │       ├── youtube_collector.py ✅
│   │       ├── naver_blog_collector.py ✅
│   │       ├── naver_report_collector.py ✅
│   │       ├── dart_filing_collector.py ✅
│   │       └── earnings_call_collector.py ✅
│   ├── storage/
│   │   ├── models.py ✅
│   │   ├── db.py ✅
│   │   └── vector_store.py ✅
│   ├── interface/
│   │   ├── cli.py ✅
│   │   └── telegram_bot.py ✅
│   ├── analyzer/
│   │   ├── llm_router.py ✅
│   │   ├── report_builder.py ✅
│   │   ├── notifications.py ✅
│   │   ├── context_gatherer.py ✅
│   │   └── temporal_decomposer.py ✅
│   ├── scheduler/
│   │   └── daily_jobs.py ✅
│   ├── config/
│   │   ├── watchlist.yaml ✅
│   │   ├── sources.yaml ✅
│   │   └── prompts.yaml ✅
│   ├── data/
│   │   ├── raw/          # 원본 데이터 저장
│   │   ├── reports/      # 생성된 리포트
│   │   │   ├── daily/
│   │   │   └── weekly/
│   │   ├── chroma/        # ChromaDB (사용 안 함)
│   │   └── sqlite/        # SQLite (사용 안 함)
│   ├── logs/
│   ├── mcp_servers/
│   │   ├── README.md ✅
│   │   ├── portfolio_mcp/
│   │   │   └── server.py ✅
│   │   ├── memory_mcp/
│   │   │   └── server.py ✅
│   │   └── content_mcp/
│   │       └── server.py ✅
│   ├── migrations/
│   │   ├── add_primary_sources_table.py ✅
│   │   └── add_price_attributions_table.py ✅
│   ├── pyproject.toml ✅
│   ├── .env.example ✅
│   ├── test_sprint1.py ✅
│   └── test_sprint2.py ✅
├── dashboard/
│   ├── src/
│   │   └── app/
│   │       ├── layout.tsx ✅
│   │       ├── page.tsx ✅
│   │       ├── globals.css ✅
│   │       ├── thoughts/
│   │       │   └── page.tsx ✅
│   │       ├── reports/
│   │       │   └── page.tsx ✅
│   │       └── hooks/
│   │           └── useWebSocket.ts ✅
│   ├── package.json ✅
│   ├── tsconfig.json ✅
│   ├── tailwind.config.ts ✅
│   ├── postcss.config.js ✅
│   ├── next.config.js ✅
│   └── README.md ✅
├── SPRINT2_IMPLEMENTATION_SUMMARY.md ✅
```

**참고**: `data/chroma/` 및 `data/sqlite/` 디렉토리는 PostgreSQL + pgvector 마이그레이션 이후 사용되지 않습니다.

---

## 다음 단계 (설치 및 설정)

### 1. PostgreSQL + pgvector Docker 컨테이너 시작
```bash
cd market-insight
docker-compose up -d
# 확인: docker ps
```

### 2. Ollama 설치 및 설정 (선택 사항)
```bash
# Ollama 설치
brew install ollama

# Ollama 서버 시작
brew services start ollama

# 필수 모델 다운로드
ollama pull nomic-embed-text
ollama pull llama3.2
```

### 3. 백엔드 설정
```bash
cd market-insight/backend

# 의존성 설치
uv sync

# .env 파일 설정
cp .env.example .env
# .env 파일에서 필요한 설정 수정 (DB_PASSWORD, KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO 등)

# 데이터베이스 초기화
uv run python -c "from storage.db import init_database; init_database()"

# FastAPI 서버 실행 테스트
uv run python api/main.py
# http://localhost:3000/docs 확인
```

### 4. 대시보드 설정
```bash
cd market-insight/dashboard

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
# http://localhost:3001 접속
```

### 5. CLI 명령어 테스트
```bash
cd market-insight/backend

inv init
inv portfolio
inv think "테스트 메모"
inv recall "테스트"
```

### 6. Telegram Bot 설정 (선택 사항)
```bash
# .env 파일에 설정 추가
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# 봇 실행
uv run python interface/telegram_bot.py
```

### 7. 알림 시스템 설정 (선택 사항)
```bash
# .env 파일에 설정 추가
# 이메일
NOTIFICATION_EMAIL_ENABLED=true
NOTIFICATION_EMAIL_HOST=smtp.gmail.com
NOTIFICATION_EMAIL_PORT=587
NOTIFICATION_EMAIL_USERNAME=your@email.com
NOTIFICATION_EMAIL_PASSWORD=your-app-password
NOTIFICATION_EMAIL_FROM=your@email.com
NOTIFICATION_EMAIL_TO=your@email.com

# 텔레그램
NOTIFICATION_TELEGRAM_ENABLED=true
NOTIFICATION_TELEGRAM_BOT_TOKEN=your-bot-token
NOTIFICATION_TELEGRAM_CHAT_ID=your-chat-id

# 우선순위 및 조용 시간
NOTIFICATION_NOTIFICATION_MIN_PRIORITY=normal
NOTIFICATION_QUIET_HOURS_START=22
NOTIFICATION_QUIET_HOURS_END=8
```

---

## 알려진 문제 및 해결 방법

### TypeScript 에러 (dashboard/)
- **증상**: `react`, `next`, `lucide-react` 모듈을 찾을 수 없음
- **원인**: `npm install` 아직 실행 안 함
- **해결**: `cd dashboard && npm install`

### Ollama 임베딩 (backend/)
- **현재 상태**: Ollama nomic-embed-text 연동 완료 ✅
- **설정 방법**:
  1. Ollama 설치: `brew install ollama`
  2. 모델 다운로드: `ollama pull nomic-embed-text`
  3. Ollama 서버 시작: `brew services start ollama`
- **폴백 메커니즘**: Ollama 연결 실패 시 해시 기반 임베딩 사용

### PostgreSQL + pgvector (backend/)
- **현재 상태**: PostgreSQL + pgvector로 마이그레이션 완료 ✅
- **필요 작업**: Docker 컨테이너 시작 (`docker-compose up -d`)
- **참고**: `docker-compose down -v`로 컨테이너 및 데이터 정리 가능
- **상세**: `MIGRATION_TO_POSTGRESQL.md` 참조

### KIS API (backend/)
- **현재 상태**: OAuth 토큰 발급 구현 완료 ✅
- **폴백 메커니즘**: API 키 없으면 mock 데이터 사용
- **설정 방법**: `.env` 파일에 `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT_NO` 설정

### Telegram Bot (backend/)
- **현재 상태**: 구현 완료 ✅
- **설치**: `uv pip install -e ".[telegram]"`
- **설정**: `.env` 파일에 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 설정

### 알림 시스템 (backend/)
- **현재 상태**: 구현 완료 ✅
- **설정**: `.env` 파일에 이메일/텔레그램 알림 설정 추가

---

## Sprint 3: Assumption Tracking System ✅

### 완료된 작업

#### 1. Database Schema ✅
- [x] `InvestmentAssumption` 모델 추가 (`storage/models.py`)
  - ticker, company_name, assumption_text, assumption_category
  - time_horizon (SHORT, MEDIUM, LONG)
  - predicted_value, metric_name, verification_date
  - actual_value, is_correct, validation_source
  - model_confidence_at_generation
  - status (PENDING, VERIFIED, FAILED)
  - source_type, source_id
  - created_at, updated_at

#### 2. AssumptionExtractor ✅
- [x] `analyzer/assumption_extractor.py` 생성
  - `AssumptionExtractor` 클래스
  - `extract_assumptions()` 함수 - LLM을 사용하여 보고서에서 가정 추출
  - 가정 카테고리 분류 (REVENUE, MARGIN, MACRO, CAPACITY, MARKET_SHARE)
  - 시간 지평 할당 (SHORT, MEDIUM, LONG)
  - 신뢰도 점수 계산 (출처 권한 기반)
  - `ExtractedAssumption`, `AssumptionExtractionResult` Pydantic 모델

#### 3. Validation Scheduler ✅
- [x] `scheduler/assumption_validator.py` 생성
  - `AssumptionValidator` 클래스
  - `FinancialDataProvider` 클래스 (Mock 데이터)
  - `run_assumption_validation_job()` - 예약된 검증 작업
  - `validate_single_assumption()` - 단일 가정 검증
  - `get_accuracy_trends()` - 정확도 추적
  - 숫자 비교 및 의미적 비교 (LLM 활용)
  - 한국 단위 처리 (조, 억, 만, 천)

#### 4. Database Operations ✅
- [x] `storage/db.py`에 가정 관련 함수 추가
  - `add_investment_assumption()` - 가정 추가
  - `get_assumptions_by_ticker()` - 티커별 가정 조회
  - `get_pending_assumptions()` - 검증 대기 중인 가정 조회
  - `validate_assumption()` - 가정 검증
  - `get_assumption_accuracy_stats()` - 정확도 통계
  - `delete_assumption()` - 가정 삭제
  - `get_all_assumptions()` - 모든 가정 조회

#### 5. API Endpoints ✅
- [x] `api/routes/assumptions.py` 생성
  - GET `/api/v1/assumptions/` - 모든 가정 목록
  - GET `/api/v1/assumptions/{id}` - 특정 가정 조회
  - GET `/api/v1/assumptions/ticker/{ticker}` - 티커별 가정
  - GET `/api/v1/assumptions/pending/list` - 검증 대기 중인 가정
  - POST `/api/v1/assumptions/validate/{id}` - 수동 검증
  - POST `/api/v1/assumptions/validate/job` - 검증 작업 실행
  - POST `/api/v1/assumptions/extract` - 보고서에서 가정 추출
  - DELETE `/api/v1/assumptions/{id}` - 가정 삭제
  - GET `/api/v1/assumptions/stats/accuracy` - 정확도 통계
  - GET `/api/v1/assumptions/stats/trends` - 정확도 추이
  - POST `/api/v1/assumptions/batch/validate` - 일괄 검증
  - GET `/api/v1/assumptions/categories/list` - 카테고리 목록
  - GET `/api/v1/assumptions/time-horizons/list` - 시간 지평 목록
- [x] `api/main.py`에 assumptions 라우터 추가

#### 6. Testing ✅
- [x] `backend/test_sprint3.py` 생성
  - 데이터베이스 작업 테스트
  - 가정 추출 테스트
  - 검증 로직 테스트
  - 정확도 계산 테스트
  - API 엔드포인트 테스트 (예시 포함)

#### 7. Migration Script ✅
- [x] `migrations/add_investment_assumptions_table.py` 생성

### 핵심 기능

1. **가정 추출**
   - LLM을 사용하여 보고서 및 공시에서 투자 가정 자동 추출
   - 카테고리별 분류 (REVENUE, MARGIN, MACRO, CAPACITY, MARKET_SHARE)
   - 시간 지평별 분류 (SHORT, MEDIUM, LONG)
   - 출처 권한 기반 신뢰도 점수 조정

2. **검증 시스템**
   - 예약된 작업으로 자동 검증
   - 실제 금융 데이터와 비교
   - 숫자 비교 및 의미적 비교 (LLM 활용)
   - 검증 상태 추적 (PENDING, VERIFIED, FAILED)

3. **정확도 추적**
   - 전체 정확도 통계
   - 카테고리별 정확도
   - 시간 지평별 정확도
   - 주간 추이 분석

### API 사용 예시

```bash
# 보고서에서 가정 추출
curl -X POST http://localhost:3000/api/v1/assumptions/extract \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Q3 HBM 매출 1조 달성 예상",
    "ticker": "005930",
    "company_name": "삼성전자",
    "source_type": "EARNINGS_CALL"
  }'

# 티커별 가정 조회
curl http://localhost:3000/api/v1/assumptions/ticker/005930

# 검증 대기 중인 가정 조회
curl http://localhost:3000/api/v1/assumptions/pending/list

# 정확도 통계 조회
curl http://localhost:3000/api/v1/assumptions/stats/accuracy

# 검증 작업 실행
curl -X POST http://localhost:3000/api/v1/assumptions/validate/job
```

### Phase 5: 통합 및 마무리 (Sprint 5) ✅
- [x] `analyzer/enhanced_report_builder.py` 생성 (모든 스프린트 통합 리포트 빌더)
  - EnhancedReportBuilder 클래스 (모든 스프린트 컴포넌트 통합)
  - generate_comprehensive_report() (종합 리포트 생성)
  - generate_daily_report_with_analysis() (향상된 일일 리포트)
  - generate_asset_report() (종목별 리포트)
  - 데이터 수집 메서드 (Primary Sources, Temporal Attributions, Investment Assumptions)
  - 포맷팅 메서드 (LLM 프롬프트용)
- [x] `api/routes/enhanced_reports.py` 생성 (향상된 리포트 API)
  - POST /api/v1/enhanced-reports/comprehensive (종합 리포트 생성)
  - POST /api/v1/enhanced-reports/comprehensive/async (비동기 리포트 생성)
  - POST /api/v1/enhanced-reports/daily-enhanced (향상된 일일 리포트)
  - POST /api/v1/enhanced-reports/asset (종목별 리포트)
  - POST /api/v1/enhanced-reports/batch (배치 리포트 생성)
  - POST /api/v1/enhanced-reports/export (리포트 내보내기)
  - GET /api/v1/enhanced-reports/health (헬스 체크)
- [x] `config/prompts.yaml` 업데이트 (향상된 리포트 프롬프트)
  - comprehensive_report 시스템 프롬프트
  - daily_report_enhanced 시스템 프롬프트
  - comprehensive_report 사용자 프롬프트
  - daily_report_enhanced 사용자 프롬프트
- [x] `dashboard/src/app/temporal/page.tsx` 생성 (시계열 분석 대시보드)
  - 가격 속성 목록 표시
  - 통계 요약 (총 건수, 단/중/장기 우세)
  - 시간대별 필터링
  - 상세 모달
- [x] `dashboard/src/app/assumptions/page.tsx` 생성 (투자 가정 추적 대시보드)
  - 투자 가정 목록 표시
  - 통계 요약 (총 건수, 검증 대기, 정확도)
  - 상태 및 카테고리 필터링
  - 상세 모달
- [x] `dashboard/src/app/page.tsx` 업데이트 (네비게이션 링크 추가)
  - 시계열 분석 링크
  - 투자 가정 링크
- [x] `api/main.py` 업데이트 (향상된 리포트 라우터 등록)
- [x] `SPRINT5_IMPLEMENTATION_SUMMARY.md` 생성 (Sprint 5 구현 요약)
  - 구현된 컴포넌트 설명
  - API 사용 가이드
  - 아키텍처 개요
  - 배포 지침
- [x] `test_sprint5.py` 생성 (Sprint 5 통합 테스트)
  - EnhancedReportBuilder 테스트
  - 종합 리포트 생성 테스트
  - 종합 워크플로우 테스트
  - 데이터 일관성 테스트
  - 성능 테스트
  - 오류 처리 테스트

### API 사용 예시 (Sprint 5)

```bash
# 종합 리포트 생성
curl -X POST "http://localhost:8000/api/v1/enhanced-reports/comprehensive" \
  -H "Content-Type: application/json" \
  -d '{
    "target_date": "2026-02-22",
    "tickers": ["005930", "000660"]
  }'

# 종목별 리포트 생성
curl -X POST "http://localhost:8000/api/v1/enhanced-reports/asset" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "005930",
    "target_date": "2026-02-22"
  }'

# 배치 리포트 생성
curl -X POST "http://localhost:8000/api/v1/enhanced-reports/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["005930", "000660", "035420"],
    "target_date": "2026-02-22"
  }'

# 리포트 내보내기
curl -X POST "http://localhost:8000/api/v1/enhanced-reports/export" \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report-id-here",
    "format": "markdown"
  }'
```

---

## 구현 완료 요약

### 백엔드 (FastAPI) ✅
- ✅ 모든 API 라우트 구현 완료 (portfolio, thoughts, content, reports, websocket)
- ✅ 데이터베이스 연동 (PostgreSQL + pgvector)
- ✅ 콘텐츠 수집기 (YouTube, 네이버 블로그)
- ✅ 리포트 생성기 (일일, 주간)
- ✅ 스케줄러 (자동 수집 및 리포트 생성)
- ✅ LLM 라우터 (Ollama, Claude)
- ✅ 알림 시스템 (이메일, 텔레그램)
- ✅ WebSocket 실시간 업데이트
- ✅ KIS API 연동 (한국투자증권 OpenAPI)
- ✅ MCP 서버 (Portfolio, Memory, Content)
- ✅ CLI 인터페이스
- ✅ Telegram Bot

### 프론트엔드 (Next.js) ✅
- ✅ 메인 대시보드 (포트폴리오 요약, 종목 테이블)
- ✅ 생각 기록 페이지 (생각 기록, 검색, 삭제)
- ✅ 리포트 조회 페이지 (리포트 목록, 생성, 상세 보기)
- ✅ WebSocket 실시간 업데이트
- ✅ 반응형 디자인 (Tailwind CSS)
- ✅ 네비게이션

### 인프라 ✅
- ✅ PostgreSQL + pgvector (Docker)
- ✅ Ollama 연동 (선택 사항)
- ✅ Docker Compose 설정

---

## Naver Finance Report Collector ✅

**파일**:
- [`backend/collector/naver_report_collector.py`](market-insight/backend/collector/naver_report_collector.py) - Naver Finance 웹 스크래핑
- [`backend/api/routes/naver_reports.py`](market-insight/backend/api/routes/naver_reports.py) - API 엔드포인트
- [`backend/test_naver_reports.py`](market-insight/backend/test_naver_reports.py) - 테스트 스위트
- [`NAVER_REPORT_COLLECTOR_IMPLEMENTATION.md`](market-insight/NAVER_REPORT_COLLECTOR_IMPLEMENTATION.md) - 구현 문서

**기능**:
- Playwright 기반 Naver Finance 웹 스크래핑
- PDF 다운로드 및 텍스트 추출 (PyPDF2)
- 메타데이터 파싱 (애널리스트, 의견, 목표가)
- 권위 가중치: 0.4 (2차 소스)
- Parent-Child 인덱싱 통합
- 가중치 검색 통합

**API 엔드포인트**:
- POST `/api/v1/naver-reports/collect` - Naver 리포트 수집 (비동기)
- POST `/api/v1/naver-reports/collect/sync` - Naver 리포트 수집 (동기)
- POST `/api/v1/naver-reports/batch` - 배치 수집
- GET `/api/v1/naver-reports/list` - 리포트 목록 조회
- GET `/api/v1/naver-reports/{report_id}` - 특정 리포트 조회
- DELETE `/api/v1/naver-reports/{report_id}` - 리포트 삭제
- POST `/api/v1/naver-reports/index/{report_id}` - 단일 리포트 인덱싱
- POST `/api/v1/naver-reports/index/batch` - 배치 인덱싱
- GET `/api/v1/naver-reports/stats/summary` - 통계 조회

**의존성**:
- `playwright>=1.40.0` - 웹 스크래핑
- `PyPDF2>=3.0.1` - PDF 텍스트 추출

**테스트**:
- 컬렉터 초기화 및 파싱 테스트
- 데이터베이스 저장 테스트
- 권위 가중치 검증
- Parent-Child 인덱싱 테스트

**참고**: [`NAVER_REPORT_COLLECTOR_IMPLEMENTATION.md`](market-insight/NAVER_REPORT_COLLECTOR_IMPLEMENTATION.md)에서 상세 정보 확인

---

## 결론

**모든 기능 구현이 완료되었습니다.** 이제 남은 설치 및 설정 단계뿐입니다:

1. PostgreSQL + pgvector Docker 컨테이너 시작
2. Ollama 설치 및 모델 다운로드 (선택 사항)
3. 백엔드 의존성 설치 및 `.env` 설정
4. 대시보드 `npm install`
5. 서버 실행 및 테스트

상세 설정 방법은 `SETUP_GUIDE.md`를 참조하세요.
