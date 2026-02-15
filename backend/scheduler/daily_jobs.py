"""Daily Jobs Scheduler

Schedules automated tasks for content collection and report generation.
Uses APScheduler for job scheduling.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from collector.youtube_collector import YouTubeCollector
from collector.naver_blog_collector import NaverBlogCollector
from collector.stock_tracker import track_portfolio, track_watchlist
from analyzer.report_builder import ReportBuilder
from storage.db import get_session
from storage.models import DailySnapshot


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DailyJobsScheduler:
    """
    Scheduler for daily automated tasks

    Usage:
        scheduler = DailyJobsScheduler()
        scheduler.start()
        scheduler.stop()
    """

    def __init__(self):
        """Initialize scheduler"""
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Setup scheduled jobs"""
        # YouTube content collection - Every 6 hours
        self.scheduler.add_job(
            self._collect_youtube,
            trigger=CronTrigger(hour="*/6"),
            id="collect_youtube",
            name="Collect YouTube content",
            replace_existing=True,
        )

        # Naver blog collection - Every 12 hours
        self.scheduler.add_job(
            self._collect_naver_blog,
            trigger=CronTrigger(hour="*/12"),
            id="collect_naver_blog",
            name="Collect Naver blog content",
            replace_existing=True,
        )

        # Stock price tracking - Every hour during market hours
        self.scheduler.add_job(
            self._track_stocks,
            trigger=CronTrigger(hour="9-15", minute="0"),
            id="track_stocks",
            name="Track stock prices",
            replace_existing=True,
        )

        # Daily report generation - Every day at 8 PM
        self.scheduler.add_job(
            self._generate_daily_report,
            trigger=CronTrigger(hour=20, minute=0),
            id="daily_report",
            name="Generate daily report",
            replace_existing=True,
        )

        # Weekly report generation - Every Sunday at 9 PM
        self.scheduler.add_job(
            self._generate_weekly_report,
            trigger=CronTrigger(day_of_week="sun", hour=21, minute=0),
            id="weekly_report",
            name="Generate weekly report",
            replace_existing=True,
        )

        # Daily snapshot creation - Every day at 6 PM
        self.scheduler.add_job(
            self._create_daily_snapshot,
            trigger=CronTrigger(hour=18, minute=0),
            id="daily_snapshot",
            name="Create daily snapshot",
            replace_existing=True,
        )

    def _collect_youtube(self):
        """Collect YouTube content"""
        logger.info("Starting YouTube content collection...")

        try:
            collector = YouTubeCollector()
            results = collector.collect_all()

            total = sum(len(items) for items in results.values())
            logger.info(f"Collected {total} YouTube videos from {len(results)} channels")

        except Exception as e:
            logger.error(f"Error collecting YouTube content: {e}")

    def _collect_naver_blog(self):
        """Collect Naver blog content"""
        logger.info("Starting Naver blog collection...")

        try:
            collector = NaverBlogCollector()
            results = collector.collect_all()

            total = sum(len(items) for items in results.values())
            logger.info(f"Collected {total} Naver blog posts from {len(results)} blogs")

        except Exception as e:
            logger.error(f"Error collecting Naver blog content: {e}")

    def _track_stocks(self):
        """Track stock prices"""
        logger.info("Starting stock price tracking...")

        try:
            # Track portfolio
            portfolio_result = track_portfolio()
            logger.info(f"Portfolio tracking: {portfolio_result}")

            # Track watchlist
            watchlist_result = track_watchlist()
            logger.info(f"Watchlist tracking: {watchlist_result}")

        except Exception as e:
            logger.error(f"Error tracking stock prices: {e}")

    def _generate_daily_report(self):
        """Generate daily report"""
        logger.info("Starting daily report generation...")

        try:
            builder = ReportBuilder()
            report = builder.generate_daily_report()

            logger.info(f"Generated daily report for {report.date}")

        except Exception as e:
            logger.error(f"Error generating daily report: {e}")

    def _generate_weekly_report(self):
        """Generate weekly report"""
        logger.info("Starting weekly report generation...")

        try:
            builder = ReportBuilder()
            report = builder.generate_weekly_report()

            logger.info(f"Generated weekly report for {report.date}")

        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")

    def _create_daily_snapshot(self):
        """Create daily portfolio snapshot"""
        logger.info("Creating daily snapshot...")

        try:
            with next(get_session()) as session:
                # Get portfolio summary
                holdings = session.exec(select(PortfolioHolding)).all()

                if not holdings:
                    logger.warning("No holdings found, skipping snapshot")
                    return

                # Calculate portfolio value
                total_value = 0.0
                total_invested = 0.0
                cash_balance = 1000000.0  # Default cash balance

                holdings_json = []
                top_gainer = None
                top_loser = None
                max_gain = -float("inf")
                max_loss = float("inf")

                for holding in holdings:
                    invested = holding.shares * holding.avg_price
                    total_invested += invested

                    # Get latest price
                    from storage.db import get_latest_stock_price
                    latest_price = get_latest_stock_price(session, holding.ticker)

                    if latest_price:
                        current_value = holding.shares * latest_price.price
                        total_value += current_value

                        # Calculate P&L
                        pnl_pct = latest_price.change_pct

                        # Track top gainer/loser
                        if pnl_pct > max_gain:
                            max_gain = pnl_pct
                            top_gainer = holding.ticker
                        if pnl_pct < max_loss:
                            max_loss = pnl_pct
                            top_loser = holding.ticker

                        holdings_json.append({
                            "ticker": holding.ticker,
                            "name": holding.name,
                            "shares": holding.shares,
                            "avg_price": holding.avg_price,
                            "current_price": latest_price.price,
                            "current_value": current_value,
                            "invested": invested,
                            "pnl_pct": pnl_pct,
                        })
                    else:
                        total_invested += invested

                total_pnl = total_value - total_invested
                total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

                # Create snapshot
                snapshot = DailySnapshot(
                    date=datetime.now().date(),
                    total_value=total_value + cash_balance,
                    total_invested=total_invested,
                    total_pnl=total_pnl,
                    total_pnl_pct=total_pnl_pct,
                    cash_balance=cash_balance,
                    top_gainer=top_gainer,
                    top_loser=top_loser,
                    holdings_json=str(holdings_json),
                )

                from storage.db import add_daily_snapshot
                add_daily_snapshot(session, snapshot)

                logger.info(
                    f"Created snapshot: Value={total_value + cash_balance:,.0f}, "
                    f"PnL={total_pnl:,.0f} ({total_pnl_pct:+.2f}%)"
                )

        except Exception as e:
            logger.error(f"Error creating daily snapshot: {e}")

    def start(self):
        """Start the scheduler"""
        logger.info("Starting daily jobs scheduler...")
        self.scheduler.start()

    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping daily jobs scheduler...")
        self.scheduler.shutdown()

    def run_job_now(self, job_id: str):
        """Run a specific job immediately"""
        logger.info(f"Running job immediately: {job_id}")

        job_map = {
            "collect_youtube": self._collect_youtube,
            "collect_naver_blog": self._collect_naver_blog,
            "track_stocks": self._track_stocks,
            "daily_report": self._generate_daily_report,
            "weekly_report": self._generate_weekly_report,
            "daily_snapshot": self._create_daily_snapshot,
        }

        if job_id in job_map:
            job_map[job_id]()
        else:
            logger.error(f"Unknown job ID: {job_id}")

    def list_jobs(self):
        """List all scheduled jobs"""
        jobs = self.scheduler.get_jobs()

        logger.info("Scheduled jobs:")
        for job in jobs:
            logger.info(f"  - {job.id}: {job.name} (next run: {job.next_run_time})")

        return jobs


# ──── Global Scheduler Instance ────
_scheduler_instance = None


def get_scheduler() -> DailyJobsScheduler:
    """Get global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DailyJobsScheduler()
    return _scheduler_instance


# ──── Convenience Functions ────
def start_scheduler():
    """Start the global scheduler"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the global scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()


def run_job(job_id: str):
    """Run a specific job immediately"""
    scheduler = get_scheduler()
    scheduler.run_job_now(job_id)


def list_jobs():
    """List all scheduled jobs"""
    scheduler = get_scheduler()
    return scheduler.list_jobs()
