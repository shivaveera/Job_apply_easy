"""SQLite database for application tracking and history."""

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.logger import log


class ApplicationDatabase:
    """SQLite-based tracking of all job applications.

    Tracks: job details, application status, resume used,
    answers given, timestamps, and AI scoring.
    """

    def __init__(self, db_path: str = "data/applications.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """Create application tracking tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE,
                job_title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                job_url TEXT,
                platform TEXT DEFAULT 'linkedin',
                status TEXT DEFAULT 'applied',
                ai_score REAL,
                ai_reasoning TEXT,
                resume_path TEXT,
                cover_letter_path TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                job_description TEXT,
                work_type TEXT,
                salary_info TEXT,
                recruiter_name TEXT,
                recruiter_url TEXT,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS application_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT DEFAULT 'ai',
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES applications(id)
            );

            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                applied INTEGER DEFAULT 0,
                skipped INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                blacklisted INTEGER DEFAULT 0,
                total_ai_cost REAL DEFAULT 0.0
            );

            CREATE INDEX IF NOT EXISTS idx_applications_company
                ON applications(company);
            CREATE INDEX IF NOT EXISTS idx_applications_status
                ON applications(status);
            CREATE INDEX IF NOT EXISTS idx_applications_date
                ON applications(applied_at);
        """)
        self.conn.commit()

    def is_already_applied(self, job_id: str) -> bool:
        """Check if we've already applied to this job."""
        row = self.conn.execute(
            "SELECT 1 FROM applications WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None

    def save_application(
        self,
        job_id: str,
        job_title: str,
        company: str,
        location: str = "",
        job_url: str = "",
        platform: str = "linkedin",
        status: str = "applied",
        ai_score: Optional[float] = None,
        ai_reasoning: str = "",
        resume_path: str = "",
        cover_letter_path: str = "",
        job_description: str = "",
        work_type: str = "",
        salary_info: str = "",
        recruiter_name: str = "",
        recruiter_url: str = "",
        notes: str = "",
    ) -> int:
        """Save a new application record. Returns the application ID."""
        cursor = self.conn.execute(
            """INSERT OR REPLACE INTO applications
               (job_id, job_title, company, location, job_url, platform,
                status, ai_score, ai_reasoning, resume_path, cover_letter_path,
                job_description, work_type, salary_info, recruiter_name,
                recruiter_url, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id, job_title, company, location, job_url, platform,
                status, ai_score, ai_reasoning, resume_path, cover_letter_path,
                job_description[:5000], work_type, salary_info, recruiter_name,
                recruiter_url, notes,
            ),
        )
        self.conn.commit()
        log.info(f"Saved application: {job_title} at {company} [{status}]")
        return cursor.lastrowid

    def save_answers(
        self,
        application_id: int,
        answers: list[dict],
    ) -> None:
        """Save Q&A pairs for an application."""
        for qa in answers:
            self.conn.execute(
                """INSERT INTO application_answers
                   (application_id, question, answer, source)
                   VALUES (?, ?, ?, ?)""",
                (
                    application_id,
                    qa.get("question", "")[:500],
                    qa.get("answer", "")[:1000],
                    qa.get("source", "ai"),
                ),
            )
        self.conn.commit()

    def update_daily_stats(
        self,
        applied: int = 0,
        skipped: int = 0,
        failed: int = 0,
        blacklisted: int = 0,
        ai_cost: float = 0.0,
    ) -> None:
        """Update daily statistics counters."""
        today = datetime.now().strftime("%Y-%m-%d")
        self.conn.execute(
            """INSERT INTO daily_stats (date, applied, skipped, failed, blacklisted, total_ai_cost)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET
                   applied = applied + excluded.applied,
                   skipped = skipped + excluded.skipped,
                   failed = failed + excluded.failed,
                   blacklisted = blacklisted + excluded.blacklisted,
                   total_ai_cost = total_ai_cost + excluded.total_ai_cost""",
            (today, applied, skipped, failed, blacklisted, ai_cost),
        )
        self.conn.commit()

    def get_today_count(self) -> int:
        """Get the number of applications submitted today."""
        today = datetime.now().strftime("%Y-%m-%d")
        row = self.conn.execute(
            "SELECT applied FROM daily_stats WHERE date = ?", (today,)
        ).fetchone()
        return row["applied"] if row else 0

    def get_stats(self) -> dict:
        """Get comprehensive application statistics."""
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = datetime.now().strftime("%Y-%m-%d")

        stats = {}

        # Total counts
        row = self.conn.execute(
            "SELECT COUNT(*) as total FROM applications WHERE status = 'applied'"
        ).fetchone()
        stats["total_applied"] = row["total"]

        # Today's count
        row = self.conn.execute(
            "SELECT COUNT(*) as today FROM applications WHERE date(applied_at) = ?",
            (today,),
        ).fetchone()
        stats["today_applied"] = row["today"]

        # This week
        row = self.conn.execute(
            "SELECT COUNT(*) as week FROM applications WHERE applied_at >= datetime('now', '-7 days')"
        ).fetchone()
        stats["week_applied"] = row["week"]

        # By platform
        rows = self.conn.execute(
            "SELECT platform, COUNT(*) as count FROM applications GROUP BY platform"
        ).fetchall()
        stats["by_platform"] = {row["platform"]: row["count"] for row in rows}

        # By status
        rows = self.conn.execute(
            "SELECT status, COUNT(*) as count FROM applications GROUP BY status"
        ).fetchall()
        stats["by_status"] = {row["status"]: row["count"] for row in rows}

        # Top companies
        rows = self.conn.execute(
            "SELECT company, COUNT(*) as count FROM applications GROUP BY company ORDER BY count DESC LIMIT 10"
        ).fetchall()
        stats["top_companies"] = {row["company"]: row["count"] for row in rows}

        # Average AI score
        row = self.conn.execute(
            "SELECT AVG(ai_score) as avg_score FROM applications WHERE ai_score IS NOT NULL"
        ).fetchone()
        stats["avg_ai_score"] = round(row["avg_score"], 2) if row["avg_score"] else None

        # Total AI cost
        row = self.conn.execute(
            "SELECT SUM(total_ai_cost) as total_cost FROM daily_stats"
        ).fetchone()
        stats["total_ai_cost"] = round(row["total_cost"], 4) if row["total_cost"] else 0.0

        return stats

    def export_csv(self, output_path: str = "data/applications_export.csv") -> str:
        """Export all applications to CSV."""
        rows = self.conn.execute(
            "SELECT * FROM applications ORDER BY applied_at DESC"
        ).fetchall()

        if not rows:
            log.warning("No applications to export")
            return ""

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow(tuple(row))

        log.info(f"Exported {len(rows)} applications to {output_path}")
        return output_path

    def get_applications_needing_followup(self, days_since: int = 7) -> list[dict]:
        """Get applications that may need manual follow-up."""
        rows = self.conn.execute(
            """SELECT job_title, company, job_url, applied_at
               FROM applications
               WHERE status = 'applied'
               AND applied_at <= datetime('now', ?)
               ORDER BY applied_at ASC""",
            (f"-{days_since} days",),
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
