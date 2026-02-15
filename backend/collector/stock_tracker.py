"""Stock Price Tracker - Korean and US Stocks"""

import httpx
from datetime import datetime, date
from typing import Optional
import yaml
import json
import base64
from sqlmodel import Session
from pydantic_settings import BaseSettings

from storage.models import StockPrice
from storage.db import get_session


class KISConfig(BaseSettings):
    """KIS API Configuration"""
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_account_no: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = ""


class StockTracker:
    """
    주식 가격 추적기

    데이터 소스 우선순위:
    1. 한국투자증권 OpenAPI (국내주식 실시간) - 무료
    2. Yahoo Finance (미국주식) - 무료
    """

    KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
    KIS_TOKEN_URL = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"

    def __init__(self, config_path: str = "config/watchlist.yaml"):
        self.config_path = config_path
        self.watchlist = self._load_watchlist()
        self.kis_config = KISConfig()
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def _load_watchlist(self) -> dict:
        """watchlist.yaml 로드"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {"portfolio": {"korean": [], "us": []}, "watchlist": {"korean": [], "us": []}}

    async def _get_access_token(self) -> Optional[str]:
        """
        KIS OAuth 액세스 토큰 발급
        """
        # Check if token is still valid
        if self._access_token and self._token_expiry:
            if datetime.now() < self._token_expiry:
                return self._access_token

        # Get new token
        if not self.kis_config.kis_app_key or not self.kis_config.kis_app_secret:
            print("Warning: KIS API keys not configured, using mock data")
            return None

        try:
            headers = {
                "Content-Type": "application/json",
            }

            body = {
                "grant_type": "client_credentials",
                "appkey": self.kis_config.kis_app_key,
                "appsecret": self.kis_config.kis_app_secret,
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.KIS_TOKEN_URL,
                    json=body,
                    headers=headers,
                    timeout=10.0
                )
                resp.raise_for_status()
                result = resp.json()

                self._access_token = result.get("access_token")
                # Token expires in 24 hours (86400 seconds)
                self._token_expiry = datetime.now().replace(
                    hour=23, minute=59, second=59
                )

                return self._access_token

        except Exception as e:
            print(f"Error getting KIS access token: {e}")
            return None

    async def fetch_korean_stock(self, ticker: str) -> Optional[dict]:
        """
        한국투자증권 API로 국내 주식 조회

        참고: 실제 사용하려면 KIS API 키가 필요합니다.
        개발 중에는 mock 데이터 반환.
        """
        # Try to get access token
        token = await self._get_access_token()

        if not token:
            # Return mock data if no token available
            return {
                "ticker": ticker,
                "name": self._get_stock_name(ticker),
                "price": 75000.0,  # mock
                "change_pct": 2.5,  # mock
                "volume": 1000000,  # mock
                "high": 76000.0,  # mock
                "low": 74000.0,  # mock
                "market": "KR",
                "timestamp": datetime.now()
            }

        try:
            url = f"{self.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": self.kis_config.kis_app_key,
                "appsecret": self.kis_config.kis_app_secret,
                "tr_id": "FHKST01010100",
                "content-type": "application/json",
            }

            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": ticker,
            }

            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, params=params, timeout=10.0)
                resp.raise_for_status()
                result = resp.json()

                if result.get("rt_cd") != "0":
                    print(f"KIS API error: {result.get('msg1')}")
                    return None

                output = result.get("output", {})
                if not output:
                    return None

                return {
                    "ticker": ticker,
                    "name": self._get_stock_name(ticker),
                    "price": int(output.get("stck_prpr", 0)),
                    "change_pct": float(output.get("prdy_ctrt", 0)),
                    "volume": int(output.get("acml_vol", 0)),
                    "high": int(output.get("stck_hgpr", 0)),
                    "low": int(output.get("stck_lwpr", 0)),
                    "market": "KR",
                    "timestamp": datetime.now()
                }

        except Exception as e:
            print(f"Error fetching KIS stock {ticker}: {e}")
            # Return mock data on error
            return {
                "ticker": ticker,
                "name": self._get_stock_name(ticker),
                "price": 75000.0,  # mock
                "change_pct": 2.5,  # mock
                "volume": 1000000,  # mock
                "high": 76000.0,  # mock
                "low": 74000.0,  # mock
                "market": "KR",
                "timestamp": datetime.now()
            }

    async def fetch_us_stock(self, ticker: str) -> Optional[dict]:
        """Yahoo Finance로 미국 주식 조회 (무료)"""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {"interval": "1d", "range": "5d"}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                result = resp.json()

                if not result.get("chart", {}).get("result"):
                    return None

                meta = result["chart"]["result"][0]["meta"]
                prev_close = meta.get("chartPreviousClose", meta.get("previousClose"))
                current_price = meta.get("regularMarketPrice")

                if not current_price or not prev_close:
                    return None

                change_pct = round(
                    (current_price - prev_close) / prev_close * 100, 2
                )

                return {
                    "ticker": ticker,
                    "name": ticker,  # Yahoo에서 이름을 가져올 수 있음
                    "price": current_price,
                    "change_pct": change_pct,
                    "volume": meta.get("regularMarketVolume"),
                    "high": meta.get("regularMarketDayHigh"),
                    "low": meta.get("regularMarketDayLow"),
                    "market": "US",
                    "timestamp": datetime.now()
                }
        except Exception as e:
            print(f"Error fetching US stock {ticker}: {e}")
            return None

    def _get_stock_name(self, ticker: str) -> str:
        """티커에서 종목명 조회"""
        # watchlist에서 찾기
        for stock in self.watchlist.get("portfolio", {}).get("korean", []):
            if stock["ticker"] == ticker:
                return stock["name"]
        for stock in self.watchlist.get("watchlist", {}).get("korean", []):
            if stock["ticker"] == ticker:
                return stock["name"]
        return ticker

    async def track_portfolio(self, session: Session) -> list[dict]:
        """전체 포트폴리오 추적"""
        results = []

        # 한국 주식
        for stock in self.watchlist.get("portfolio", {}).get("korean", []):
            data = await self.fetch_korean_stock(stock["ticker"])
            if data:
                results.append(data)

        # 미국 주식
        for stock in self.watchlist.get("portfolio", {}).get("us", []):
            data = await self.fetch_us_stock(stock["ticker"])
            if data:
                results.append(data)

        # DB 저장
        for r in results:
            price = StockPrice(**r)
            session.add(price)
        session.commit()

        return results

    async def track_watchlist(self, session: Session) -> list[dict]:
        """관심종목 추적"""
        results = []

        # 한국 관심종목
        for stock in self.watchlist.get("watchlist", {}).get("korean", []):
            data = await self.fetch_korean_stock(stock["ticker"])
            if data:
                results.append(data)

        # 미국 관심종목
        for stock in self.watchlist.get("watchlist", {}).get("us", []):
            data = await self.fetch_us_stock(stock["ticker"])
            if data:
                results.append(data)

        # DB 저장
        for r in results:
            price = StockPrice(**r)
            session.add(price)
        session.commit()

        return results

    async def get_price(self, ticker: str) -> Optional[dict]:
        """단일 종목 가격 조회"""
        # 한국 주식인지 확인 (6자리 숫자)
        if ticker.isdigit() and len(ticker) == 6:
            return await self.fetch_korean_stock(ticker)
        else:
            return await self.fetch_us_stock(ticker)


# ──── Convenience Functions ────
async def fetch_all_prices() -> dict:
    """모든 주식 가격 수집"""
    tracker = StockTracker()
    from storage.db import get_session

    with next(get_session()) as session:
        portfolio = await tracker.track_portfolio(session)
        watchlist = await tracker.track_watchlist(session)

        return {
            "portfolio": portfolio,
            "watchlist": watchlist,
            "timestamp": datetime.now().isoformat()
        }
