"""Notification System - Email and Telegram"""

import asyncio
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from pydantic_settings import BaseSettings
import aiosmtplib
from email.message import EmailMessage
from loguru import logger


class NotificationType(str, Enum):
    """Notification types"""
    PORTFOLIO_UPDATE = "portfolio_update"
    PRICE_ALERT = "price_alert"
    NEW_THOUGHT = "new_thought"
    NEW_REPORT = "new_report"
    MARKET_SUMMARY = "market_summary"
    ERROR = "error"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationSettings(BaseSettings):
    """Notification system settings"""
    # Email settings
    email_enabled: bool = False
    email_host: str = "smtp.gmail.com"
    email_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    email_to: List[str] = []

    # Telegram settings
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # General settings
    notification_min_priority: NotificationPriority = NotificationPriority.NORMAL
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 8     # 8 AM

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "NOTIFICATION_"


class Notification:
    """Single notification"""

    def __init__(
        self,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        ticker: Optional[str] = None,
        data: Optional[Dict] = None
    ):
        self.title = title
        self.message = message
        self.notification_type = notification_type
        self.priority = priority
        self.ticker = ticker
        self.data = data or {}
        self.created_at = datetime.now()


class EmailNotifier:
    """Email notification handler"""

    def __init__(self, settings: NotificationSettings):
        self.settings = settings

    async def send(self, notification: Notification) -> bool:
        """Send email notification"""
        if not self.settings.email_enabled:
            return False

        try:
            # Create email message
            msg = EmailMessage()
            msg["From"] = self.settings.email_from
            msg["To"] = ", ".join(self.settings.email_to)
            msg["Subject"] = f"[Market Insight] {notification.title}"

            # Build email body
            body = self._build_email_body(notification)
            msg.set_content(body, subtype="html")

            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.settings.email_host,
                port=self.settings.email_port,
                username=self.settings.email_username,
                password=self.settings.email_password,
                start_tls=True,
            )

            logger.info(f"Email sent: {notification.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _build_email_body(self, notification: Notification) -> str:
        """Build HTML email body"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4F46E5; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                .priority-urgent {{ border-left: 4px solid #EF4444; }}
                .priority-high {{ border-left: 4px solid #F59E0B; }}
                .priority-normal {{ border-left: 4px solid #10B981; }}
                .priority-low {{ border-left: 4px solid #6B7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Market Insight</h2>
                </div>
                <div class="content priority-{notification.priority.value}">
                    <h3>{notification.title}</h3>
                    <p>{notification.message}</p>
                    {self._build_additional_info(notification)}
                </div>
                <div class="footer">
                    <p>Sent at {notification.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>This is an automated notification from Market Insight</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _build_additional_info(self, notification: Notification) -> str:
        """Build additional info section"""
        if not notification.data:
            return ""

        info = "<div style='margin-top: 20px;'><strong>Additional Information:</strong><ul>"
        for key, value in notification.data.items():
            info += f"<li><strong>{key}:</strong> {value}</li>"
        info += "</ul></div>"
        return info


class TelegramNotifier:
    """Telegram notification handler"""

    def __init__(self, settings: NotificationSettings):
        self.settings = settings
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id

    async def send(self, notification: Notification) -> bool:
        """Send Telegram notification"""
        if not self.settings.telegram_enabled:
            return False

        try:
            # Build message
            message = self._build_message(notification)

            # Send via Telegram Bot API
            from httpx import AsyncClient
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

            async with AsyncClient() as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": "HTML",
                    },
                    timeout=10.0
                )
                response.raise_for_status()

            logger.info(f"Telegram sent: {notification.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram: {e}")
            return False

    def _build_message(self, notification: Notification) -> str:
        """Build Telegram message"""
        # Priority emoji
        priority_emoji = {
            NotificationPriority.URGENT: "🔴",
            NotificationPriority.HIGH: "🟠",
            NotificationPriority.NORMAL: "🟢",
            NotificationPriority.LOW: "🔵",
        }

        emoji = priority_emoji.get(notification.priority, "🟢")

        # Type emoji
        type_emoji = {
            NotificationType.PORTFOLIO_UPDATE: "📊",
            NotificationType.PRICE_ALERT: "💰",
            NotificationType.NEW_THOUGHT: "💭",
            NotificationType.NEW_REPORT: "📄",
            NotificationType.MARKET_SUMMARY: "📈",
            NotificationType.ERROR: "⚠️",
        }

        type_icon = type_emoji.get(notification.notification_type, "📌")

        # Build message
        message = f"{emoji} <b>Market Insight</b>\n\n"
        message += f"{type_icon} <b>{notification.title}</b>\n\n"
        message += f"{notification.message}\n"

        # Add ticker if available
        if notification.ticker:
            message += f"\n🏷️ Ticker: {notification.ticker}"

        # Add additional data
        if notification.data:
            message += "\n\n<b>Details:</b>\n"
            for key, value in notification.data.items():
                message += f"• {key}: {value}\n"

        message += f"\n⏰ {notification.created_at.strftime('%Y-%m-%d %H:%M')}"

        return message


class NotificationManager:
    """Main notification manager"""

    def __init__(self, settings: Optional[NotificationSettings] = None):
        self.settings = settings or NotificationSettings()
        self.email_notifier = EmailNotifier(self.settings)
        self.telegram_notifier = TelegramNotifier(self.settings)
        self._notification_queue: List[Notification] = []

    async def send(self, notification: Notification) -> Dict[str, bool]:
        """Send notification via enabled channels"""
        results = {}

        # Check if notification should be sent during quiet hours
        if not self._should_send(notification):
            logger.info(f"Notification skipped due to quiet hours: {notification.title}")
            return {"email": False, "telegram": False, "skipped": True}

        # Check priority
        if not self._meets_priority(notification):
            logger.info(f"Notification skipped due to priority: {notification.title}")
            return {"email": False, "telegram": False, "skipped": True}

        # Send via email
        if self.settings.email_enabled:
            results["email"] = await self.email_notifier.send(notification)

        # Send via Telegram
        if self.settings.telegram_enabled:
            results["telegram"] = await self.telegram_notifier.send(notification)

        return results

    def _should_send(self, notification: Notification) -> bool:
        """Check if notification should be sent based on quiet hours"""
        # Always send urgent notifications
        if notification.priority == NotificationPriority.URGENT:
            return True

        # Check quiet hours
        current_hour = datetime.now().hour
        if self.settings.quiet_hours_end < self.settings.quiet_hours_start:
            # Quiet hours span midnight (e.g., 22:00 - 08:00)
            in_quiet_hours = current_hour >= self.settings.quiet_hours_start or current_hour < self.settings.quiet_hours_end
        else:
            # Normal hours (e.g., 01:00 - 06:00)
            in_quiet_hours = self.settings.quiet_hours_start <= current_hour < self.settings.quiet_hours_end

        return not in_quiet_hours

    def _meets_priority(self, notification: Notification) -> bool:
        """Check if notification meets minimum priority"""
        priority_order = {
            NotificationPriority.LOW: 0,
            NotificationPriority.NORMAL: 1,
            NotificationPriority.HIGH: 2,
            NotificationPriority.URGENT: 3,
        }

        min_priority = priority_order.get(self.settings.notification_min_priority, 1)
        notification_priority = priority_order.get(notification.priority, 1)

        return notification_priority >= min_priority

    async def send_price_alert(
        self,
        ticker: str,
        name: str,
        current_price: float,
        target_price: float,
        alert_type: str = "above"
    ) -> Dict[str, bool]:
        """Send price alert notification"""
        if alert_type == "above":
            title = f"Price Alert: {ticker} ({name})"
            message = f"Price has risen above target price!\n\nCurrent: {current_price:,.2f}\nTarget: {target_price:,.2f}"
        else:
            title = f"Price Alert: {ticker} ({name})"
            message = f"Price has fallen below target price!\n\nCurrent: {current_price:,.2f}\nTarget: {target_price:,.2f}"

        notification = Notification(
            title=title,
            message=message,
            notification_type=NotificationType.PRICE_ALERT,
            priority=NotificationPriority.HIGH,
            ticker=ticker,
            data={
                "current_price": current_price,
                "target_price": target_price,
                "alert_type": alert_type,
            }
        )

        return await self.send(notification)

    async def send_portfolio_summary(
        self,
        total_value: float,
        total_pnl: float,
        total_pnl_pct: float,
        top_gainers: List[Dict],
        top_losers: List[Dict]
    ) -> Dict[str, bool]:
        """Send portfolio summary notification"""
        title = "Portfolio Summary"
        message = f"Total Value: {total_value:,.2f}\n"
        message += f"Total P&L: {total_pnl:,.2f} ({total_pnl_pct:+.2f}%)\n\n"

        if top_gainers:
            message += "📈 Top Gainers:\n"
            for stock in top_gainers[:3]:
                message += f"• {stock.get('ticker')}: {stock.get('pnl_pct', 0):+.2f}%\n"

        if top_losers:
            message += "\n📉 Top Losers:\n"
            for stock in top_losers[:3]:
                message += f"• {stock.get('ticker')}: {stock.get('pnl_pct', 0):+.2f}%\n"

        notification = Notification(
            title=title,
            message=message,
            notification_type=NotificationType.PORTFOLIO_UPDATE,
            priority=NotificationPriority.NORMAL,
            data={
                "total_value": total_value,
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct,
            }
        )

        return await self.send(notification)

    async def send_error_notification(
        self,
        error_message: str,
        context: Optional[Dict] = None
    ) -> Dict[str, bool]:
        """Send error notification"""
        notification = Notification(
            title="Error Occurred",
            message=error_message,
            notification_type=NotificationType.ERROR,
            priority=NotificationPriority.URGENT,
            data=context or {}
        )

        return await self.send(notification)


# Global notification manager instance
notification_manager = NotificationManager()


# Convenience functions
async def send_notification(
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.PORTFOLIO_UPDATE,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    ticker: Optional[str] = None,
    data: Optional[Dict] = None
) -> Dict[str, bool]:
    """Send a notification"""
    notification = Notification(
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        ticker=ticker,
        data=data
    )
    return await notification_manager.send(notification)


async def send_price_alert(
    ticker: str,
    name: str,
    current_price: float,
    target_price: float,
    alert_type: str = "above"
) -> Dict[str, bool]:
    """Send price alert"""
    return await notification_manager.send_price_alert(
        ticker, name, current_price, target_price, alert_type
    )
