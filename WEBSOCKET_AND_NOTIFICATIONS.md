# WebSocket 및 알림 시스템 가이드

## WebSocket 실시간 업데이트

### 개요

WebSocket을 사용하여 대시보드에 실시간으로 데이터를 푸시할 수 있습니다. 포트폴리오 업데이트, 새로운 생각, 리포트 생성 등의 이벤트를 실시간으로 수신할 수 있습니다.

### 백엔드 설정

#### 1. 의존성 설치

```bash
cd backend
uv sync
```

`pyproject.toml`에 이미 `websockets` 의존성이 포함되어 있습니다.

#### 2. WebSocket 엔드포인트

WebSocket 엔드포인트: `ws://localhost:3000/api/v1/ws`

#### 3. 채널 구독

클라이언트는 다음 채널 중 하나 이상을 구독할 수 있습니다:

- `portfolio`: 포트폴리오 업데이트
- `thoughts`: 새로운 생각
- `reports`: 새로운 리포트
- `alerts`: 가격 알림 및 알림

#### 4. 클라이언트 메시지 형식

**구독 요청:**
```json
{
  "type": "subscribe",
  "channels": ["portfolio", "thoughts", "reports"]
}
```

**핑/퐁:**
```json
{
  "type": "ping"
}
```

**포트폴리오 데이터 요청:**
```json
{
  "type": "get_portfolio"
}
```

#### 5. 서버 메시지 형식

**연결 확인:**
```json
{
  "type": "connected",
  "message": "Connected to Market Insight WebSocket",
  "channels": ["portfolio", "thoughts", "reports"],
  "timestamp": "2024-01-01T00:00:00"
}
```

**포트폴리오 업데이트:**
```json
{
  "type": "portfolio_update",
  "data": {
    "total_value": 1000000,
    "total_pnl": 50000,
    "total_pnl_pct": 5.0,
    "holdings": [...]
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

**가격 업데이트:**
```json
{
  "type": "price_update",
  "ticker": "005930",
  "data": {
    "price": 75000,
    "change_pct": 2.5
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

**새로운 생각:**
```json
{
  "type": "new_thought",
  "data": {
    "id": "uuid",
    "content": "생각 내용",
    "thought_type": "stock_idea",
    "ticker": "005930"
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

**새로운 리포트:**
```json
{
  "type": "new_report",
  "data": {
    "id": "uuid",
    "title": "일일 리포트",
    "content": "리포트 내용",
    "report_type": "daily"
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

**알림:**
```json
{
  "type": "alert",
  "data": {
    "title": "가격 알림",
    "message": "삼성전자가 목표 가격에 도달했습니다",
    "priority": "high"
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

### 프론트엔드 사용

#### WebSocket Hook 사용

```tsx
"use client";

import { useWebSocket } from "@/hooks/useWebSocket";

function Dashboard() {
  const { isConnected, lastMessage, connectionStatus } = useWebSocket("ws://localhost:3000/api/v1/ws");

  return (
    <div>
      <div>연결 상태: {connectionStatus}</div>
      {isConnected && <div>연결됨</div>}
    </div>
  );
}
```

#### 메시지 처리

```tsx
useEffect(() => {
  if (lastMessage) {
    switch (lastMessage.type) {
      case "portfolio_update":
        setPortfolio(lastMessage.data);
        break;
      case "price_update":
        // 특정 종목 가격 업데이트
        break;
      case "new_thought":
        // 새로운 생각 추가
        break;
      default:
        break;
    }
  }
}, [lastMessage]);
```

### 브로드캐스팅 함수

백엔드에서 다음 함수를 사용하여 메시지를 브로드캐스팅할 수 있습니다:

```python
from api.routes.websocket import (
    broadcast_portfolio_update,
    broadcast_new_thought,
    broadcast_new_report,
    broadcast_alert,
    broadcast_price_update
)

# 포트폴리오 업데이트 브로드캐스팅
await broadcast_portfolio_update(portfolio_data)

# 새로운 생각 브로드캐스팅
await broadcast_new_thought(thought_data)

# 가격 업데이트 브로드캐스팅
await broadcast_price_update("005930", {"price": 75000, "change_pct": 2.5})
```

---

## 알림 시스템

### 개요

이메일 및 텔레그램을 통해 알림을 보낼 수 있습니다. 우선순위 기반 필터링, 조용한 시간 설정 등의 기능을 제공합니다.

### 설정

#### 환경 변수

`.env` 파일에 다음 설정을 추가합니다:

```bash
# 이메일 알림 설정
NOTIFICATION_EMAIL_ENABLED=true
NOTIFICATION_EMAIL_HOST=smtp.gmail.com
NOTIFICATION_EMAIL_PORT=587
NOTIFICATION_EMAIL_USERNAME=your_email@gmail.com
NOTIFICATION_EMAIL_PASSWORD=your_app_password_here
NOTIFICATION_EMAIL_FROM=your_email@gmail.com
NOTIFICATION_EMAIL_TO=recipient1@example.com,recipient2@example.com

# 텔레그램 알림 설정
NOTIFICATION_TELEGRAM_ENABLED=true
NOTIFICATION_TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
NOTIFICATION_TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# 일반 설정
NOTIFICATION_NOTIFICATION_MIN_PRIORITY=normal
NOTIFICATION_QUIET_HOURS_START=22
NOTIFICATION_QUIET_HOURS_END=8
```

#### 우선순위

- `low`: 낮은 우선순위
- `normal`: 일반 우선순위 (기본값)
- `high`: 높은 우선순위
- `urgent`: 긴급 우선순위 (조용한 시간에도 전송)

### 사용법

#### 기본 알림 보내기

```python
from analyzer.notifications import send_notification, NotificationType, NotificationPriority

result = await send_notification(
    title="알림 제목",
    message="알림 내용",
    notification_type=NotificationType.PORTFOLIO_UPDATE,
    priority=NotificationPriority.NORMAL,
    ticker="005930",
    data={"additional": "info"}
)

# 결과: {"email": True, "telegram": True}
```

#### 가격 알림

```python
from analyzer.notifications import send_price_alert

result = await send_price_alert(
    ticker="005930",
    name="삼성전자",
    current_price=76000,
    target_price=75000,
    alert_type="above"  # 또는 "below"
)
```

#### 포트폴리오 요약

```python
from analyzer.notifications import notification_manager

result = await notification_manager.send_portfolio_summary(
    total_value=1000000,
    total_pnl=50000,
    total_pnl_pct=5.0,
    top_gainers=[
        {"ticker": "005930", "pnl_pct": 5.0},
        {"ticker": "000660", "pnl_pct": 3.0}
    ],
    top_losers=[
        {"ticker": "035420", "pnl_pct": -2.0}
    ]
)
```

#### 오류 알림

```python
from analyzer.notifications import notification_manager

result = await notification_manager.send_error_notification(
    error_message="API 호출 실패",
    context={"endpoint": "/api/v1/portfolio", "error": "Connection timeout"}
)
```

### 알림 타입

- `portfolio_update`: 포트폴리오 업데이트
- `price_alert`: 가격 알림
- `new_thought`: 새로운 생각
- `new_report`: 새로운 리포트
- `market_summary`: 시장 요약
- `error`: 오류

### 조용한 시간

`NOTIFICATION_QUIET_HOURS_START`와 `NOTIFICATION_QUIET_HOURS_END`로 조용한 시간을 설정할 수 있습니다.

- 기본값: 22:00 ~ 08:00
- 긴급(`urgent`) 우선순위 알림은 조용한 시간에도 전송됩니다.

### 이메일 템플릿

이메일 알림은 HTML 형식으로 전송되며, 다음 요소를 포함합니다:

- 헤더 (Market Insight 로고)
- 알림 제목 및 내용
- 우선순위 표시 (색상 구분)
- 추가 정보 (있는 경우)
- 전송 시간

### 텔레그램 메시지 형식

텔레그램 알림은 다음 형식으로 전송됩니다:

```
🟢 Market Insight

📊 알림 제목

알림 내용

🏷️ Ticker: 005930

🏰 2024-01-01 12:00
```

---

## API 엔드포인트

### WebSocket 관련

#### 연결 상태 확인

```bash
GET /api/v1/connections
```

응답:
```json
{
  "active_connections": 2,
  "subscriptions": {
    "portfolio": 2,
    "thoughts": 2,
    "reports": 1,
    "alerts": 1
  }
}
```

#### 포트폴리오 브로드캐스트 트리거 (테스트용)

```bash
POST /api/v1/broadcast/portfolio
```

응답:
```json
{
  "status": "ok",
  "message": "Portfolio update broadcasted"
}
```

---

## 트러블슈팅

### WebSocket 연결 문제

1. **연결 실패**
   - 백엔드 서버가 실행 중인지 확인: `http://localhost:3000/health`
   - CORS 설정 확인: `api/main.py`의 `CORSMiddleware`

2. **연결 끊김**
   - WebSocket은 자동으로 재연결을 시도합니다 (5초 후)
   - 브라우저 콘솔에서 연결 상태를 확인하세요

### 이메일 알림 문제

1. **Gmail 사용 시**
   - 앱 비밀번호를 사용하세요 (일반 비밀번호 X)
   - [Google 계정 보안](https://myaccount.google.com/security)에서 앱 비밀번호 생성

2. **SMTP 연결 실패**
   - 이메일 호스트와 포트를 확인하세요.
   - 방화벽 설정을 확인하세요.

### 텔레그램 알림 문제

1. **봇 토큰**
   - [@BotFather](https://t.me/botfather)에서 봇 생성 및 토큰 발급

2. **채팅 ID**
   - 봇에게 메시지를 보낸 후 `https://api.telegram.org/bot<token>/getUpdates`로 확인
