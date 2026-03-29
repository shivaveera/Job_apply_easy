"""Retry and crash recovery utilities.

Provides:
- retry_on_stale: Decorator for handling StaleElementReferenceException
- retry_with_backoff: Generic exponential backoff retry
- SessionCheckpoint: SQLite-based checkpoint for crash recovery
"""

import functools
import sqlite3
import time
from typing import Optional

from src.utils.logger import log


def retry_on_stale(max_retries: int = 3, delay: float = 1.0):
    """Decorator: retry on StaleElementReferenceException with backoff.

    Handles the most common Selenium failure mode in dynamic SPAs.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from selenium.common.exceptions import (
                NoSuchElementException,
                StaleElementReferenceException,
                ElementNotInteractableException,
            )
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (StaleElementReferenceException, NoSuchElementException,
                        ElementNotInteractableException) as e:
                    if attempt == max_retries - 1:
                        log.warning(f"Retry exhausted for {func.__name__}: {e}")
                        raise
                    wait = delay * (2 ** attempt)
                    log.debug(f"Retry {attempt + 1}/{max_retries} for {func.__name__} in {wait:.1f}s")
                    time.sleep(wait)
        return wrapper
    return decorator


def retry_with_backoff(max_retries: int = 3, base_delay: float = 2.0, exceptions=(Exception,)):
    """Decorator: generic exponential backoff retry."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    wait = base_delay * (2 ** attempt)
                    log.debug(f"Retry {attempt + 1}/{max_retries} for {func.__name__} in {wait:.1f}s: {e}")
                    time.sleep(wait)
        return wrapper
    return decorator


class SessionCheckpoint:
    """SQLite-based session checkpoint for crash recovery.

    Tracks which jobs have been processed in the current session
    so the bot can resume after crashes without re-processing.
    """

    def __init__(self, db_path: str = "data/session_checkpoint.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()
        self.session_id = self._new_session()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT DEFAULT (datetime('now')),
                ended_at TEXT,
                status TEXT DEFAULT 'running',
                total_processed INTEGER DEFAULT 0,
                total_applied INTEGER DEFAULT 0,
                total_failed INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS processed_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                job_url TEXT NOT NULL,
                job_id TEXT,
                platform TEXT,
                status TEXT DEFAULT 'processing',
                step TEXT DEFAULT 'discovered',
                error TEXT,
                processed_at TEXT DEFAULT (datetime('now')),
                UNIQUE(session_id, job_url)
            );
            CREATE INDEX IF NOT EXISTS idx_processed_session
                ON processed_jobs(session_id, status);
        """)
        self.conn.commit()

    def _new_session(self) -> int:
        cursor = self.conn.execute("INSERT INTO sessions DEFAULT VALUES")
        self.conn.commit()
        return cursor.lastrowid

    def is_processed(self, job_url: str) -> bool:
        """Check if a job was already processed in THIS session."""
        row = self.conn.execute(
            "SELECT status FROM processed_jobs WHERE session_id = ? AND job_url = ?",
            (self.session_id, job_url),
        ).fetchone()
        return row is not None and row[0] in ("applied", "skipped")

    def mark_processing(self, job_url: str, job_id: str = "", platform: str = "") -> None:
        """Mark a job as currently being processed."""
        self.conn.execute(
            """INSERT OR REPLACE INTO processed_jobs
               (session_id, job_url, job_id, platform, status, step)
               VALUES (?, ?, ?, ?, 'processing', 'started')""",
            (self.session_id, job_url, job_id, platform),
        )
        self.conn.commit()

    def update_step(self, job_url: str, step: str) -> None:
        """Update the current step for a job (for resume on crash)."""
        self.conn.execute(
            "UPDATE processed_jobs SET step = ? WHERE session_id = ? AND job_url = ?",
            (step, self.session_id, job_url),
        )
        self.conn.commit()

    def mark_applied(self, job_url: str) -> None:
        self.conn.execute(
            "UPDATE processed_jobs SET status = 'applied' WHERE session_id = ? AND job_url = ?",
            (self.session_id, job_url),
        )
        self.conn.commit()

    def mark_failed(self, job_url: str, error: str = "") -> None:
        self.conn.execute(
            "UPDATE processed_jobs SET status = 'failed', error = ? WHERE session_id = ? AND job_url = ?",
            (error, self.session_id, job_url),
        )
        self.conn.commit()

    def mark_skipped(self, job_url: str) -> None:
        self.conn.execute(
            "UPDATE processed_jobs SET status = 'skipped' WHERE session_id = ? AND job_url = ?",
            (self.session_id, job_url),
        )
        self.conn.commit()

    def get_incomplete_jobs(self) -> list[dict]:
        """Get jobs that were being processed when the last session crashed."""
        rows = self.conn.execute(
            """SELECT job_url, job_id, platform, step FROM processed_jobs
               WHERE status = 'processing' AND session_id = (
                   SELECT id FROM sessions WHERE status = 'running'
                   ORDER BY id DESC LIMIT 1 OFFSET 1
               )""",
        ).fetchall()
        return [
            {"job_url": r[0], "job_id": r[1], "platform": r[2], "step": r[3]}
            for r in rows
        ]

    def end_session(self) -> None:
        """Mark the current session as completed."""
        stats = self.conn.execute(
            """SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status='applied' THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
               FROM processed_jobs WHERE session_id = ?""",
            (self.session_id,),
        ).fetchone()
        self.conn.execute(
            """UPDATE sessions SET ended_at = datetime('now'), status = 'completed',
               total_processed = ?, total_applied = ?, total_failed = ?
               WHERE id = ?""",
            (stats[0], stats[1], stats[2], self.session_id),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
