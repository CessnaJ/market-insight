"""CLI Interface for Market Insight"""

import click
import json
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from storage.db import get_session
from storage.models import DailyReport
from collector.thought_logger import ThoughtLogger, ThoughtType, log_thought, search_thoughts
from collector.stock_tracker import StockTracker

console = Console()


# ──── Portfolio Commands ────
@click.group()
def cli():
    """Market Insight CLI - Personal Investment Intelligence System"""
    pass


@cli.command()
def portfolio():
    """포트폴리오 현황 조회"""
    from storage.db import get_portfolio_holdings, get_latest_stock_price

    with next(get_session()) as session:
        holdings = get_portfolio_holdings(session)

        if not holdings:
            console.print("[yellow]보유 종목이 없습니다.[/yellow]")
            return

        # 테이블 생성
        table = Table(title="📊 포트폴리오 현황")
        table.add_column("종목", style="cyan")
        table.add_column("티커", style="magenta")
        table.add_column("보유수량", justify="right")
        table.add_column("평단가", justify="right")
        table.add_column("현재가", justify="right")
        table.add_column("수익률", justify="right")

        total_value = 0.0
        total_invested = 0.0

        for holding in holdings:
            latest_price = get_latest_stock_price(session, holding.ticker)
            current_price = latest_price.price if latest_price else holding.avg_price

            current_value = current_price * holding.shares
            invested_value = holding.avg_price * holding.shares

            total_value += current_value
            total_invested += invested_value

            pnl_pct = ((current_price - holding.avg_price) / holding.avg_price * 100) if holding.avg_price > 0 else 0

            # 색상 지정
            pnl_color = "green" if pnl_pct >= 0 else "red"
            pnl_str = f"{pnl_pct:+.2f}%"

            table.add_row(
                holding.name,
                holding.ticker,
                f"{holding.shares:.2f}",
                f"{holding.avg_price:,.0f}",
                f"{current_price:,.0f}",
                f"[{pnl_color}]{pnl_str}[/{pnl_color}]"
            )

        console.print(table)

        # 총합
        total_pnl = total_value - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        total_color = "green" if total_pnl >= 0 else "red"

        console.print(Panel(
            f"총 평가액: {total_value:,.0f}원\n"
            f"총 투자원금: {total_invested:,.0f}원\n"
            f"총 손익: [{total_color}]{total_pnl:+,.0f}원 ({total_pnl_pct:+.2f}%)[/{total_color}]",
            title="💰 총합",
            style="bold"
        ))


@cli.command()
@click.argument("ticker")
def price(ticker: str):
    """특정 종목의 현재가 조회"""
    tracker = StockTracker()
    import asyncio

    async def fetch():
        data = await tracker.get_price(ticker)
        if data:
            console.print(Panel(
                f"종목: {data.get('name', ticker)}\n"
                f"현재가: {data['price']:,.0f}\n"
                f"변동률: {data['change_pct']:+.2f}%\n"
                f"시장: {data['market']}",
                title=f"📈 {ticker}"
            ))
        else:
            console.print(f"[red]종목 {ticker}의 가격을 찾을 수 없습니다.[/red]")

    asyncio.run(fetch())


# ──── Thought Commands ────
@cli.command()
@click.argument("content", nargs=-1)
@click.option("--type", "-t", default="general", help="생각 유형 (market_view, stock_idea, risk_concern, ai_insight, content_note, general)")
@click.option("--tickers", "-k", multiple=True, help="관련 종목코드")
@click.option("--confidence", "-c", type=int, help="확신도 (1-10)")
def think(content: tuple, type: str, tickers: tuple, confidence: Optional[int]):
    """
    생각 기록

    예: inv think "삼성전자 반도체 수요 증가로 상승 예상" -t stock_idea -k 005930 -c 7
    """
    if not content:
        console.print("[red]내용을 입력해주세요.[/red]")
        return

    thought_text = " ".join(content)
    ticker_list = list(tickers) if tickers else None

    try:
        thought = log_thought(
            content=thought_text,
            thought_type=type,
            related_tickers=ticker_list,
            confidence=confidence
        )

        console.print(f"[green]✅ 기록완료[/green]")
        console.print(f"ID: {thought.id}")
        console.print(f"유형: {thought.thought_type}")
        console.print(f"내용: {thought.content[:100]}...")
        if ticker_list:
            console.print(f"관련종목: {', '.join(ticker_list)}")
    except Exception as e:
        console.print(f"[red]기록 실패: {e}[/red]")


@cli.command()
@click.argument("query", nargs=-1)
@click.option("--limit", "-n", default=5, help="반환할 결과 수")
def recall(query: tuple, limit: int):
    """
    과거 생각 검색

    예: inv recall "반도체" -n 10
    """
    if not query:
        console.print("[red]검색어를 입력해주세요.[/red]")
        return

    search_query = " ".join(query)
    results = search_thoughts(query=search_query, limit=limit)

    if not results:
        console.print(f"[yellow]'{search_query}' 관련 기록이 없습니다.[/yellow]")
        return

    console.print(f"🔍 '{search_query}' 관련 기록 ({len(results)}개):\n")

    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        console.print(f"[cyan]{i}.[/cyan] {result['content'][:200]}...")
        console.print(f"   [dim]유형: {metadata.get('type', 'N/A')} | "
                     f"날짜: {metadata.get('created_at', 'N/A')[:10]}[/dim]\n")


@cli.command()
@click.option("--limit", "-n", default=10, help="반환할 개수")
def thoughts(limit: int):
    """최근 생각 목록 조회"""
    logger = ThoughtLogger()
    recent = logger.get_recent_thoughts(limit)

    if not recent:
        console.print("[yellow]기록된 생각이 없습니다.[/yellow]")
        return

    table = Table(title="📝 최근 생각")
    table.add_column("유형", style="cyan")
    table.add_column("내용", style="white")
    table.add_column("날짜", style="dim")

    for thought in recent:
        table.add_row(
            thought.thought_type,
            thought.content[:50] + "..." if len(thought.content) > 50 else thought.content,
            thought.created_at.strftime("%Y-%m-%d %H:%M")
        )

    console.print(table)


# ──── Utility Commands ────
@cli.command()
def init():
    """데이터베이스 초기화"""
    from storage.db import init_database
    init_database()
    console.print("[green]✅ 데이터베이스 초기화 완료[/green]")


@cli.command()
def collect():
    """주식 가격 수집"""
    import asyncio
    from collector.stock_tracker import fetch_all_prices

    console.print("주식 가격 수집 중...")

    async def run():
        result = await fetch_all_prices()
        console.print(f"[green]✅ 수집 완료[/green]")
        console.print(f"포트폴리오: {len(result['portfolio'])}개")
        console.print(f"관심종목: {len(result['watchlist'])}개")

    asyncio.run(run())


# ──── Content Collection Commands ────
@cli.group()
def content():
    """콘텐츠 수집 관련 명령어"""
    pass


@content.command()
def youtube():
    """YouTube 채널에서 콘텐츠 수집"""
    from collector.youtube_collector import YouTubeCollector

    console.print("YouTube 콘텐츠 수집 중...")

    collector = YouTubeCollector()
    results = collector.collect_all()

    total = sum(len(items) for items in results.values())
    console.print(f"[green]✅ 수집 완료[/green]")
    console.print(f"채널: {len(results)}개")
    console.print(f"동영상: {total}개")

    for channel, items in results.items():
        console.print(f"  - {channel}: {len(items)}개")


@content.command()
def naver():
    """네이버 블로그에서 콘텐츠 수집"""
    from collector.naver_blog_collector import NaverBlogCollector

    console.print("네이버 블로그 콘텐츠 수집 중...")

    collector = NaverBlogCollector()
    results = collector.collect_all()

    total = sum(len(items) for items in results.values())
    console.print(f"[green]✅ 수집 완료[/green]")
    console.print(f"블로그: {len(results)}개")
    console.print(f"게시글: {total}개")

    for blog, items in results.items():
        console.print(f"  - {blog}: {len(items)}개")


@content.command()
@click.option("--limit", "-n", default=10, help="반환할 개수")
def list(limit: int):
    """최근 수집된 콘텐츠 목록"""
    from storage.db import get_recent_contents

    with next(get_session()) as session:
        contents = get_recent_contents(session, limit)

    if not contents:
        console.print("[yellow]수집된 콘텐츠가 없습니다.[/yellow]")
        return

    table = Table(title="📰 최근 콘텐츠")
    table.add_column("출처", style="cyan")
    table.add_column("제목", style="white")
    table.add_column("날짜", style="dim")

    for content in contents:
        source_name = content.source_name or content.source_type
        table.add_row(
            source_name,
            content.title[:40] + "..." if len(content.title) > 40 else content.title,
            content.collected_at.strftime("%Y-%m-%d %H:%M")
        )

    console.print(table)


# ──── Report Commands ────
@cli.group()
def report():
    """리포트 생성 관련 명령어"""
    pass


@report.command()
@click.option("--date", "-d", help="대상 날짜 (YYYY-MM-DD)")
def daily(date: Optional[str]):
    """일일 리포트 생성"""
    from datetime import datetime
    from analyzer.report_builder import generate_daily_report

    target_date = None
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()

    console.print("일일 리포트 생성 중...")

    report = generate_daily_report(target_date)

    console.print(f"[green]✅ 리포트 생성 완료[/green]")
    console.print(f"날짜: {report.date}")

    # Display report
    console.print(Panel(report.report_markdown, title=f"📊 일일 리포트 ({report.date})"))


@report.command()
@click.option("--date", "-d", help="대상 날짜 (YYYY-MM-DD)")
def weekly(date: Optional[str]):
    """주간 리포트 생성"""
    from datetime import datetime
    from analyzer.report_builder import generate_weekly_report

    target_date = None
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()

    console.print("주간 리포트 생성 중...")

    report = generate_weekly_report(target_date)

    console.print(f"[green]✅ 리포트 생성 완료[/green]")
    console.print(f"날짜: {report.date}")

    # Display report
    console.print(Panel(report.report_markdown, title=f"📊 주간 리포트"))


@report.command()
@click.option("--limit", "-n", default=5, help="반환할 개수")
def list_reports(limit: int):
    """최근 리포트 목록"""
    from storage.db import get_latest_daily_report
    from sqlmodel import select

    with next(get_session()) as session:
        reports = session.exec(
            select(DailyReport)
            .order_by(DailyReport.date.desc())
            .limit(limit)
        ).all()

    if not reports:
        console.print("[yellow]생성된 리포트가 없습니다.[/yellow]")
        return

    table = Table(title="📊 최근 리포트")
    table.add_column("날짜", style="cyan")
    table.add_column("요약", style="white")

    for report in reports:
        summary = report.report_markdown[:50] + "..." if len(report.report_markdown) > 50 else report.report_markdown
        table.add_row(str(report.date), summary)

    console.print(table)


# ──── Scheduler Commands ────
@cli.group()
def scheduler():
    """스케줄러 관련 명령어"""
    pass


@scheduler.command()
def start():
    """스케줄러 시작"""
    from scheduler.daily_jobs import start_scheduler

    console.print("스케줄러 시작 중...")
    console.print("[yellow]Ctrl+C로 종료[/yellow]")

    try:
        start_scheduler()
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]스케줄러 종료[/yellow]")


@scheduler.command()
def jobs():
    """예약된 작업 목록"""
    from scheduler.daily_jobs import list_jobs

    console.print("예약된 작업:")
    list_jobs()


@scheduler.command()
@click.argument("job_id")
def run(job_id: str):
    """작업 즉시 실행"""
    from scheduler.daily_jobs import run_job

    console.print(f"작업 실행 중: {job_id}")
    run_job(job_id)
    console.print(f"[green]✅ 작업 완료[/green]")


if __name__ == "__main__":
    cli()
