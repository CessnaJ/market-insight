"""
Telegram Bot for Market Insight

This is the main interface for the investment intelligence system.
Provides mobile access, push notifications, and quick thought logging.
"""

import asyncio
import json
import logging
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from storage.db import (
    get_portfolio_holdings,
    get_latest_stock_price,
    get_latest_daily_report,
)
from storage.vector_store import VectorStore
from storage.models import Thought
from storage.db import add_thought
from sqlmodel import Session
from storage.db import engine
from analyzer.llm_router import route_llm
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class InvestmentBot:
    """
    Telegram Bot이 메인 인터페이스인 이유:
    1. 모바일에서 즉시 접근 가능
    2. 푸시 알림
    3. 빠른 메모 입력
    4. 어디서든 접근
    """

    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("portfolio", self.cmd_portfolio))
        self.application.add_handler(CommandHandler("think", self.cmd_think))
        self.application.add_handler(CommandHandler("recall", self.cmd_recall))
        self.application.add_handler(CommandHandler("report", self.cmd_report))
        self.application.add_handler(CommandHandler("ask", self.cmd_ask))
        self.application.add_handler(CommandHandler("help", self.cmd_help))

        # Handle non-command messages as thoughts
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - welcome message"""
        welcome_msg = """
👋 *Market Insight 봇에 오신 것을 환영합니다!*

이 봇은 개인 투자 인텔리전스 시스템의 메인 인터페이스입니다.

📋 *사용 가능한 명령어:*
`/portfolio` - 포트폴리오 현황
`/think [내용]` - 생각 기록
`/recall [주제]` - 과거 생각 검색
`/report` - 최신 리포트
`/ask [질문]` - 자유 질문
`/help` - 도움말

💡 *팁:* 텍스트를 보내면 자동으로 생각으로 기록됩니다!
        """
        await update.message.reply_text(welcome_msg, parse_mode="Markdown")

    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """포트폴리오 현황"""
        with Session(engine) as session:
            holdings = get_portfolio_holdings(session)

            if not holdings:
                await update.message.reply_text("📊 포트폴리오가 비어있습니다.")
                return

            total_value = 0.0
            total_invested = 0.0
            holdings_list = []

            for holding in holdings:
                latest_price = get_latest_stock_price(session, holding.ticker)
                current_price = latest_price.price if latest_price else holding.avg_price

                current_value = holding.shares * current_price
                invested_value = holding.shares * holding.avg_price
                pnl = current_value - invested_value
                pnl_pct = (pnl / invested_value * 100) if invested_value > 0 else 0.0

                total_value += current_value
                total_invested += invested_value

                holdings_list.append({
                    "name": holding.name,
                    "ticker": holding.ticker,
                    "shares": holding.shares,
                    "pnl_pct": pnl_pct,
                    "current_value": current_value,
                })

            total_pnl = total_value - total_invested
            total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

            msg = "📊 *포트폴리오 현황*\n\n"
            msg += f"💰 총 평가액: ₩{total_value:,.0f}\n"
            msg += f"📈 총 수익률: {total_pnl_pct:+.1f}%\n"
            msg += f"💵 총 손익: ₩{total_pnl:+,.0f}\n\n"

            msg += "*종목별:*\n"
            for h in holdings_list:
                emoji = "🟢" if h['pnl_pct'] >= 0 else "🔴"
                msg += f"{emoji} {h['name']} ({h['ticker']}): {h['pnl_pct']:+.1f}% (₩{h['current_value']:,.0f})\n"

            await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_think(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """생각 기록 - /think [내용]"""
        thought_text = " ".join(context.args) if context.args else ""

        if not thought_text:
            await update.message.reply_text(
                "❌ 사용법: `/think [생각 내용]`\n\n"
                "예: `/think 삼성전자 실적이 좋아서 추가 매수 고려 중`"
            )
            return

        # LLM으로 자동 분류
        try:
            classification = await route_llm(
                task="classify_thought",
                content=thought_text,
                require_quality="low"
            )
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            classification = {
                "type": "general",
                "tags": [],
                "tickers": []
            }

        with Session(engine) as session:
            thought_id = str(uuid.uuid4())
            thought = Thought(
                id=thought_id,
                content=thought_text,
                thought_type=classification.get("type", "general"),
                tags=json.dumps(classification.get("tags", [])),
                related_tickers=json.dumps(classification.get("tickers", [])),
                confidence=None,
                outcome=None,
            )
            add_thought(session, thought)

            # Add to vector store
            vector_store = VectorStore()
            vector_store.add_thought(
                thought_id=thought_id,
                content=thought_text,
                metadata={
                    "type": classification.get("type", "general"),
                    "tickers": classification.get("tickers", []),
                    "tags": classification.get("tags", []),
                    "created_at": datetime.now().isoformat(),
                }
            )

        await update.message.reply_text(
            f"✅ 기록완료\n"
            f"분류: {classification.get('type', 'general')}\n"
            f"태그: {', '.join(classification.get('tags', []))}\n"
            f"관련종목: {', '.join(classification.get('tickers', []))}"
        )

    async def cmd_recall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """과거 생각 검색 - /recall [주제]"""
        query = " ".join(context.args) if context.args else ""

        if not query:
            await update.message.reply_text(
                "❌ 사용법: `/recall [검색어]`\n\n"
                "예: `/recall 반도체`"
            )
            return

        vector_store = VectorStore()
        results = vector_store.search_similar_thoughts(query, n=5)

        if not results:
            await update.message.reply_text(f"🔍 '{query}' 관련 기록이 없습니다.")
            return

        msg = f"🔍 *'{query}' 관련 과거 기록:*\n\n"
        for result in results[:3]:  # Show top 3
            metadata = result.get("metadata", {})
            created_at = metadata.get("created_at", "")
            if created_at:
                created_at = created_at[:10]
            content = result.get("content", "")[:200]
            msg += f"📅 {created_at}\n"
            msg += f"   {content}...\n\n"

        await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """최신 리포트 조회"""
        with Session(engine) as session:
            report = get_latest_daily_report(session)

            if not report:
                await update.message.reply_text("📄 리포트가 아직 생성되지 않았습니다.")
                return

            msg = f"📄 *{report.date} 일일 리포트*\n\n"
            msg += report.report_markdown[:1000]  # Limit to 1000 chars

            if len(report.report_markdown) > 1000:
                msg += "\n\n... (내용이 길어서 일부만 표시)"

            await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_ask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """자유 질문 - /ask [질문]"""
        question = " ".join(context.args) if context.args else ""

        if not question:
            await update.message.reply_text(
                "❌ 사용법: `/ask [질문]`\n\n"
                "예: `/ask 지금 반도체 섹터 비중 늘려야 할까?`"
            )
            return

        # 관련 컨텍스트 수집
        vector_store = VectorStore()
        related_thoughts = vector_store.search_similar_thoughts(question, 3)
        related_content = vector_store.search_related_content(question, 3)

        context_text = f"""
질문: {question}

관련 과거 생각: {json.dumps([r.get('content', '')[:100] for r in related_thoughts], ensure_ascii=False)}
관련 콘텐츠: {json.dumps([r.get('content', '')[:100] for r in related_content], ensure_ascii=False)}
"""

        try:
            answer = await route_llm(
                task="answer_question",
                content=context_text,
                require_quality="normal"
            )

            # Limit response length
            if len(answer) > 1000:
                answer = answer[:1000] + "\n\n... (답변이 길어서 일부만 표시)"

            await update.message.reply_text(answer)
        except Exception as e:
            logger.error(f"LLM answer failed: {e}")
            await update.message.reply_text(
                "❌ 답변 생성 중 오류가 발생했습니다. 나중에 다시 시도해주세요."
            )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        help_msg = """
📋 *사용 가능한 명령어:*

`/portfolio` - 포트폴리오 현황
`/think [내용]` - 생각 기록
`/recall [주제]` - 과거 생각 검색
`/report` - 최신 리포트
`/ask [질문]` - 자유 질문
`/help` - 도움말

💡 *팁:* 텍스트를 보내면 자동으로 생각으로 기록됩니다!
        """
        await update.message.reply_text(help_msg, parse_mode="Markdown")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """텍스트 메시지는 자동으로 생각으로 기록"""
        thought_text = update.message.text

        if not thought_text:
            return

        # Use think command logic
        context.args = thought_text.split()
        await self.cmd_think(update, context)

    def run(self):
        """Run the bot"""
        logger.info("Starting Telegram bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def create_bot(token: str) -> InvestmentBot:
    """Create bot instance"""
    return InvestmentBot(token)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        exit(1)

    bot = create_bot(token)
    bot.run()
