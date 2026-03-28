"""Email notifications for daily digest summaries."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from src.utils.logger import log


class EmailNotifier:
    """Send email notifications and daily digests."""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipient_email: str,
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email

    def send(self, subject: str, body: str, html: bool = False) -> bool:
        """Send an email.

        Args:
            subject: Email subject line.
            body: Email body content.
            html: If True, send as HTML email.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not all([self.smtp_server, self.sender_email, self.recipient_email]):
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = self.recipient_email

        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            log.info(f"Email sent: {subject}")
            return True
        except Exception as e:
            log.warning(f"Email send failed: {e}")
            return False

    def send_daily_digest(self, stats: dict) -> bool:
        """Send a daily application digest email."""
        subject = f"Job Bot Daily Digest - {stats.get('today_applied', 0)} Applications"
        body = f"""
        <html><body>
        <h2>Siva Job Bot - Daily Digest</h2>
        <table border="1" cellpadding="8" cellspacing="0">
            <tr><td><b>Today</b></td><td>{stats.get('today_applied', 0)}</td></tr>
            <tr><td><b>This Week</b></td><td>{stats.get('week_applied', 0)}</td></tr>
            <tr><td><b>Total</b></td><td>{stats.get('total_applied', 0)}</td></tr>
            <tr><td><b>Avg AI Score</b></td><td>{stats.get('avg_ai_score', 'N/A')}</td></tr>
            <tr><td><b>AI Cost</b></td><td>${stats.get('total_ai_cost', 0):.4f}</td></tr>
        </table>
        </body></html>
        """
        return self.send(subject, body, html=True)
