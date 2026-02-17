# Market Insight

개인 투자 인텔리전스 시스템 - 포트폴리오 추적, 생각 기록, AI 기반 분석, 리포트 생성

## 프로젝트 구조

```
market-insight/
├── backend/              # Python 백엔드 (FastAPI)
│   ├── collector/         # 데이터 수집
│   ├── storage/           # 데이터베이스 & 벡터 저장소
│   ├── analyzer/          # 분석 엔진
│   ├── api/              # FastAPI 라우트
│   ├── interface/         # CLI 및 Telegram Bot
│   ├── scheduler/         # 자동화 작업
│   ├── config/           # 설정 파일
│   ├── data/             # 데이터 저장소
│   ├── mcp_servers/       # MCP 서버 (Claude Desktop)
│   ├── pyproject.toml
│   └── .env.example
├── dashboard/           # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx          # 메인 대시보드
│   │   │   ├── thoughts/page.tsx  # 생각 기록
│   │   │   └── reports/page.tsx  # 리포트 조회
│   │   └── hooks/
│   │       └── useWebSocket.ts  # WebSocket hook
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── next.config.js
│   ├── globals.css
│   ├── layout.tsx
│   └── README.md
├── docker-compose.yml     # PostgreSQL + pgvector
├── IMPLEMENTATION_PROGRESS.md  # 구현 진행 상황
├── WEBSOCKET_AND_NOTIFICATIONS.md  # WebSocket 및 알림 시스템
├── SETUP_GUIDE.md        # 설치 및 설정 가이드
├── DATABASE_SCHEMA.md      # 데이터베이스 스키마
├── MIGRATION_TO_POSTGRESQL.md  # PostgreSQL 마이그레이션 가이드
├── SEQUENCE_DIAGRAMS.md   # 시퀀스 다이어그램
├── DEPLOYMENT_MANUAL.md   # 배포 매뉴얼
└── context/             # KIS API 문서
```

## 기능

### 백엔드 (Python/FastAPI)

#### 주식 가격 수집
- **한국 주식**: 한국투자증권 OpenAPI 연동 (OAuth 토큰 발급 구현 완료)
- **미국 주식**: Yahoo Finance API 연동
- **폴백 메커니즘**: API 키 없으면 mock 데이터 사용

#### 데이터베이스
- **PostgreSQL + pgvector**: 정형 데이터와 벡터 검색
- **벡터 저장소**: PostgreSQL pgvector 확장 사용
- **의미 기반 검색**: 과거 생각/콘텐츠 검색

#### 생각 기록
- **생각 유형**: market_view, stock_idea, risk_concern, ai_insight, content_note, general
- **태그 및 종목**: 자동 분류 및 관련 종목 추출
- **확신도**: 1-10 (사용자 설정)

#### 콘텐츠 수집
- **YouTube**: RSS feed 기반 동영상 정보 수집, LLM 요약
- **네이버 블로그**: RSS feed 기반 블로그 게시글 수집, LLM 요약
- **엔티티 추출**: 종목, 회사, 토픽 자동 추출

#### 리포트 생성
- **일일 리포트**: 매일 8시 자동 생성
- **주간 리포트**: 일요일 9시 자동 생성
- **LLM 기반**: 포트폴리오, 생각, 콘텐츠 종합 분석

#### 스케줄링
- **자동 수집**: YouTube (6시간마다), 네이버 블로그 (12시간마다)
- **주식 가격**: 장중 1시간마다
- **리포트 생성**: 일일 (8시), 주간 (일요일 9시)
- **일일 스냅샷**: 매일 6시

#### 알림 시스템
- **이메일 알림**: SMTP 기반 (Gmail 등)
- **텔레그램 알림**: Telegram Bot
- **우선순위**: low, normal, high, urgent
- **조용한 시간**: 22:00 ~ 08:00 (알림 제외)
- **알림 타입**: 포트폴리오 업데이트, 가격 알림, 새 생각, 새 리포트, 오류

#### API 라우트
- **포트폴리오**: 요약, 보유 종목, 매수/매도, 가격 조회
- **생각**: CRUD, 검색, 의미 기반 검색
- **콘텐츠**: 목록, 상세, 종목별, 검색
- **리포트**: 목록, 최신, 상세, 날짜별, 생성 (일일/주간)

#### WebSocket
- **실시간 업데이트**: 포트폴리오, 가격, 새 생각, 리포트
- **채널 구독**: portfolio, thoughts, reports, alerts
- **자동 재연결**: 5초 후 재시도

#### MCP 서버
- **Portfolio MCP**: 포트폴리오 요약, 종목 조회, 거래 기록
- **Memory MCP**: 생각 기록, 의미 검색
- **Content MCP**: 콘텐츠 검색, 통계

#### CLI 인터페이스
- **포트폴리오 현황**: 테이블 형태
- **가격 조회**: 종목별 현재가
- **생각 기록**: `inv think` 명령어
- **검색**: `inv recall` - 의미 기반 검색
- **데이터 초기화**: `inv init`

#### Telegram Bot
- **기본 명령어**: /start, /portfolio, /think, /recall, /report, /ask, /help
- **자동 기록**: 일반 메시지를 자동으로 생각으로 기록
- **LLLM 분류**: 생각 유형, 관련 종목 자동 추출

### 프론트엔드 (Next.js)

#### 메인 대시보드
- **포트폴리오 요약**: 총 평가액, 총 손익, 수익률
- **보유 종목 테이블**: 종목명, 티커, 보유수량, 평단가, 현재가, 손익, 수익률
- **네비게이션**: 대시보드, 생각, 리포트
- **WebSocket 연결 상태**: 연결됨/연결 중/연결 안됨/에러 표시
- **새로고침**: 데이터 갱신 버튼

#### 생각 기록 페이지
- **생각 기록 모달**: 텍스트 영역으로 생각 입력
- **검색 기능**: 의미 기반 검색
- **생각 목록**: 유형 배지, 날짜, 태그, 관련 종목
- **삭제 기능**: 개별 생각 삭제

#### 리포트 페이지
- **리포트 목록**: 날짜별 정렬
- **일일/주간 리포트 생성**: 버튼으로 생성
- **리포트 상세 보기**: 모달에서 마크다운 형식으로 표시
- **마크다운 렌더링**: 제목, 본문, 리스트, 체크박스 등

#### WebSocket 실시간 업데이트
- **자동 연결**: 페이지 로드 시 자동 연결
- **실시간 갱신**: 포트폴리오 업데이트, 가격 변동, 새 생각, 새 리포트
- **연결 상태 표시**: 연결 아이콘, 연결 끊김 아이콘

## 기술 스택

### 백엔드
- **FastAPI**: 웹 프레임워크
- **PostgreSQL**: pgvector 확장 (벡터 검색)
- **Ollama**: 로컬 LLM (llama3.2, nomic-embed-text)
- **Anthropic Claude** (선택): 클라우드 LLM (claude-3-5-sonnet-20241022)
- **APScheduler**: 스케줄링 (자동화 작업)
- **Telegram Bot**: python-telegram-bot
- **BeautifulSoup4**: HTML 파싱
- **feedparser**: RSS feed 파싱
- **httpx**: 비동기 HTTP 클라이언트

### 프론트엔드
- **Next.js 14**: React 프레임워크
- **TypeScript**: 타입스크립트
- **Tailwind CSS**: 유�리 프레임워크
- **Recharts**: 차트 라이브러리
- **Lucide React**: 아이콘 라이브러리

## 시작하기

### 1. 사전 요구사항

- **macOS**: 10.15 (Catalina) 이상
- **Homebrew**: 패키지 관리자
- **Python**: 3.10 이상
- **Node.js**: 18 이상
- **Docker**: PostgreSQL 컨테이너 실행용
- **RAM**: 최소 8GB, 권장 16GB 이상
- **스토리지**: 최소 10GB 여유 공간

### 2. 데이터베이스 시작

```bash
cd market-insight
docker-compose up -d
```

### 3. 백엔드 설정

```bash
cd market-insight/backend

# 의존성 설치
uv sync

# .env 파일 설정
cp .env.example .env
# .env 파일 편집하여 필요한 설정 수정 (DATABASE_URL, KIS_APP_KEY 등)
```

### 4. 데이터베이스 초기화

```bash
cd market-insight/backend
uv run python -c "from storage.db import init_database; init_database()"
```

### 5. FastAPI 서버 실행

```bash
cd market-insight/backend
uv run uvicorn api.main:app --host 0.0.0.0 --port 3000 --reload
```

API 문서: http://localhost:3000/docs

### 6. 대시보드 설정

```bash
cd market-insight/dashboard

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

대시보드: http://localhost:3001

## 설정

### 환경 변수

`.env` 파일에 다음 설정을 추가합니다:

```bash
# Database
DATABASE_URL=postgresql://postgres:changeme@localhost:5432/market_insight

# API
API_HOST=0.0.0.0
API_PORT=3000

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3.2

# KIS API (선택 사항)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NO=your_account_number

# Telegram Bot (선택 사항)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Notification Settings (선택 사항)
NOTIFICATION_EMAIL_ENABLED=false
NOTIFICATION_TELEGRAM_ENABLED=false
```

## 문서

- [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) - 구현 진행 상황
- [WEBSOCKET_AND_NOTIFICATIONS.md](WEBSOCKET_AND_NOTIFICATIONS.md) - WebSocket 및 알림 시스템
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - 설치 및 설정 가이드
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - 데이터베이스 스키마
- [MIGRATION_TO_POSTGRESQL.md](MIGRATION_TO_POSTGRESQL.md) - PostgreSQL 마이그레이션 가이드
- [SEQUENCE_DIAGRAMS.md](SEQUENCE_DIAGRAMS.md) - 시퀀스 다이어그램
- [DEPLOYMENT_MANUAL.md](DEPLOYMENT_MANUAL.md) - 배포 매뉴얼

## 라이선스

MIT License

## 저작권

Copyright (c) 2024 Market Insight
