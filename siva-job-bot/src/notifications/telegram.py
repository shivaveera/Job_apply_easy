"""Telegram bot notifications for real-time application updates."""

import json
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from src.utils.logger import log


class TelegramNotifier:
    """Send notifications via Telegram bot.

    Supports: application confirmations, errors, daily digests.
    """

    API_BASE = "https://api.telegram.org/bot{token}"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = self.API_BASE.format(token=bot_token)

    def send(self, message: str, silent: bool = False) -> bool:
        """Send a text message via Telegram.

        Args:
            message: The message text (supports Markdown).
            silent: If True, send without notification sound.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.bot_token or not self.chat_id:
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message[:4096],  # Telegram limit
            "parse_mode": "Markdown",
            "disable_notification": silent,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except URLError as e:
            log.warning(f"Telegram send failed: {e}")
            return False
        except Exception as e:
            log.warning(f"Telegram error: {e}")
            return False

    def notify_applied(self, job_title: str, company: str, score: Optional[float] = None) -> bool:
        """Send notification for a successful application."""
        score_text = f" (Score: {score:.2f})" if score is not None else ""
        return self.send(f"Applied: *{job_title}* at _{company}_{score_text}")

    def notify_error(self, message: str) -> bool:
        """Send error notification."""
        return self.send(f"Error: {message}")

    def notify_session_summary(
        self,
        applied: int,
        skipped: int,
        failed: int,
        duration_minutes: float,
    ) -> bool:
        """Send end-of-session summary."""
        return self.send(
            f"*Session Complete*\n"
            f"Applied: {applied}\n"
            f"Skipped: {skipped}\n"
            f"Failed: {failed}\n"
            f"Duration: {duration_minutes:.1f}m"
        )

    def notify_daily_digest(self, stats: dict) -> bool:
        """Send daily statistics digest."""
        return self.send(
            f"*Daily Digest*\n"
            f"Today: {stats.get('today_applied', 0)} applications\n"
            f"This Week: {stats.get('week_applied', 0)}\n"
            f"Total: {stats.get('total_applied', 0)}\n"
            f"AI Cost: ${stats.get('total_ai_cost', 0):.4f}"
        )

    def notify_needs_input(self, question: str) -> bool:
        """Send notification when manual input is needed."""
        return self.send(f"Manual input needed:\n_{question}_")
