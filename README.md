# Market Insight

개인 투자 인텔리전스 시스템 - 포트폴리오 추적, 생각 기록, AI 기반 분석

## 프로젝트 구조

```
market-insight/
├── backend/              # Python 백엔드 (FastAPI)
│   ├── collector/         # 데이터 수집
│   ├── storage/           # 데이터베이스 & 벡터 저장소
│   ├── analyzer/          # 분석 엔진
│   ├── api/              # FastAPI 라우트
│   ├── interface/         # CLI 인터페이스
│   ├── config/           # 설정 파일
│   └── data/             # 데이터 저장
├── dashboard/            # Next.js 프론트엔드
│   ├── src/
│   └── package.json
└── README.md
```

## 기능

### 백엔드 (Python/FastAPI)
- **주식 가격 추적**: 한국투자증권 API, Yahoo Finance
- **생각 기록**: CLI/Telegram으로 생각 기록, PostgreSQL + pgvector로 의미 검색
- **포트폴리오 관리**: 보유 종목, 매수/매도 기록
- **API 엔드포인트**: RESTful API (포트 3000)

### 프론트엔드 (Next.js)
- **대시보드**: 포트폴리오 현황 시각화
- **반응형 디자인**: Tailwind CSS

## 시작하기

### 백엔드

```bash
cd backend

# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 의존성 설치 (uv 사용 권장)
pip install -r requirements.txt  # 또는
uv sync

# Docker로 PostgreSQL + pgvector 컨테이너 시작
cd ..
docker-compose up -d

# .env 파일 설정
cd backend
cp .env.example .env
# .env 파일에 API 키 등 설정

# 데이터베이스 초기화
uv run python -c "from storage.db import init_database; init_database()"

# API 서버 실행
uv run python api/main.py
# 또는
uv run uvicorn api.main:app --host 0.0.0.0 --port 3000 --reload
```

### CLI 사용

```bash
# 데이터베이스 초기화
inv init

# 포트폴리오 현황
inv portfolio

# 주식 가격 수집
inv collect

# 생각 기록
inv think "삼성전자 반도체 수요 증가로 상승 예상" -t stock_idea -k 005930 -c 7

# 과거 생각 검색
inv recall "반도체" -n 10

# 최근 생각 목록
inv thoughts
```

### 프론트엔드

```bash
cd dashboard

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

## 시작하기

### 빠른 시작

```bash
# 1. Ollama 설치 및 모델 다운로드
brew install ollama
brew services start ollama
ollama pull nomic-embed-text
ollama pull llama3.2

# 2. PostgreSQL + pgvector 시작
cd market-insight
docker-compose up -d

# 3. 백엔드 설정
cd backend
cp .env.example .env
uv sync

# 4. 데이터베이스 초기화
uv run python -c "from storage.db import init_database; init_database()"

# 5. API 서버 실행
uv run python api/main.py
```

상세 설정 방법은 [설치 및 설정 가이드](SETUP_GUIDE.md)를 참조하세요.

## 설정

### config/watchlist.yaml
보유 종목과 관심종목 설정

### config/sources.yaml
콘텐츠 수집 소스 설정 (YouTube, Naver Blog 등)

### config/prompts.yaml
LLM 프롬프트 템플릿 설정

### .env
API 키 및 환경 변수 설정

### docker-compose.yml
PostgreSQL + pgvector 컨테이너 설정

## 기술 스택

### 백엔드
- Python 3.10+
- FastAPI
- SQLModel (PostgreSQL)
- PostgreSQL + pgvector (벡터 저장소)
- APScheduler (스케줄링)
- Ollama (LLM, 임베딩)

### 프론트엔드
- Next.js 14
- TypeScript
- Tailwind CSS
- Recharts

## 문서

- [설치 및 설정 가이드](SETUP_GUIDE.md) - 처음부터 설정하는 방법
- [시퀀스 다이어그램](SEQUENCE_DIAGRAMS.md) - 시스템 흐름과 API 상호작용
- [구현 진행 상황](IMPLEMENTATION_PROGRESS.md) - 상세 구현 상태
- [배포 매뉴얼](DEPLOYMENT_MANUAL.md) - 배포 및 설정 가이드
- [PostgreSQL 마이그레이션](MIGRATION_TO_POSTGRESQL.md) - DB 마이그레이션 가이드

## 개발 로드맵

### Week 1
- [x] 기반 환경 세팅
- [x] DB 스키마 설계
- [x] 주식 가격 수집
- [x] 생각 기록 기능
- [x] FastAPI 백엔드
- [x] CLI 인터페이스
- [x] Next.js 대시보드 기본 구조

### Week 2
- [x] YouTube/네이버 콘텐츠 수집
- [x] 일일/주간 리포트 생성
- [x] 스케줄러 자동화
- [x] LLM 라우터 (Ollama 연동)
- [x] API Routes (Content, Reports)
- [x] MCP 서버 (Claude Desktop 연동)
- [x] Telegram Bot (생각 기록 인터페이스)

### Week 3
- [x] MCP 서버 구현
- [x] 대시보드 기능 확장 (생각 기록 UI, 리포트 조회)
- [x] Telegram Bot 구현
- [x] KIS API 연동 (한국투자증권 OpenAPI)
- [ ] 대시보드 실시간 업데이트 (WebSocket)
- [ ] 알림 시스템 (이메일, 텔레그램)

## 라이선스

MIT
