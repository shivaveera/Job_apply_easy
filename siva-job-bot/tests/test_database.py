"""Tests for application database with WAL mode (Fix 6)."""

import pytest
import sqlite3

from src.tracking.database import ApplicationDatabase


class TestDatabaseWAL:
    """Test that WAL mode is enabled (Fix 6)."""

    def test_wal_mode_enabled(self, tmp_db_path):
        db = ApplicationDatabase(db_path=tmp_db_path)
        row = db.conn.execute("PRAGMA journal_mode").fetchone()
        assert row[0] == "wal"
        db.close()


class TestDatabaseOperations:
    """Test core database operations."""

    def test_save_and_retrieve_application(self, tmp_db_path):
        db = ApplicationDatabase(db_path=tmp_db_path)
        app_id = db.save_application(
            job_id="test_123",
            job_title="Python Developer",
            company="TestCo",
            location="Remote",
            job_url="https://example.com/job/123",
            status="applied",
            ai_score=0.85,
        )
        assert app_id > 0
        assert db.is_already_applied("test_123") is True
        assert db.is_already_applied("nonexistent") is False
        db.close()

    def test_save_application_with_resume_path(self, tmp_db_path):
        db = ApplicationDatabase(db_path=tmp_db_path)
        db.save_application(
            job_id="test_456",
            job_title="SWE",
            company="Acme",
            resume_path="/path/to/resume.pdf",
            cover_letter_path="/path/to/cl.pdf",
        )
        row = db.conn.execute(
            "SELECT resume_path, cover_letter_path FROM applications WHERE job_id = ?",
            ("test_456",),
        ).fetchone()
        assert row["resume_path"] == "/path/to/resume.pdf"
        assert row["cover_letter_path"] == "/path/to/cl.pdf"
        db.close()

    def test_get_today_count(self, tmp_db_path):
        db = ApplicationDatabase(db_path=tmp_db_path)
        db.update_daily_stats(applied=5)
        assert db.get_today_count() == 5
        db.close()

    def test_update_daily_stats_accumulates(self, tmp_db_path):
        db = ApplicationDatabase(db_path=tmp_db_path)
        db.update_daily_stats(applied=3, skipped=1)
        db.update_daily_stats(applied=2, failed=1)
        count = db.get_today_count()
        assert count == 5  # 3 + 2
        db.close()

    def test_get_stats(self, tmp_db_path):
        db = ApplicationDatabase(db_path=tmp_db_path)
        db.save_application(job_id="j1", job_title="Dev", company="A", status="applied")
        db.save_application(job_id="j2", job_title="SWE", company="B", status="applied")
        db.save_application(job_id="j3", job_title="MLE", company="A", status="failed")
        stats = db.get_stats()
        assert stats["total_applied"] == 2
        assert "applied" in stats["by_status"]
        assert "failed" in stats["by_status"]
        db.close()

    def test_save_answers(self, tmp_db_path):
        db = ApplicationDatabase(db_path=tmp_db_path)
        app_id = db.save_application(job_id="j1", job_title="Dev", company="A")
        db.save_answers(app_id, [
            {"question": "Experience?", "answer": "3 years", "source": "profile"},
            {"question": "Location?", "answer": "Remote", "source": "ai"},
        ])
        rows = db.conn.execute(
            "SELECT question, answer FROM application_answers WHERE application_id = ?",
            (app_id,),
        ).fetchall()
        assert len(rows) == 2
        db.close()

    def test_export_csv(self, tmp_path, tmp_db_path):
        db = ApplicationDatabase(db_path=tmp_db_path)
        db.save_application(job_id="j1", job_title="Dev", company="A")
        csv_path = str(tmp_path / "export.csv")
        result = db.export_csv(output_path=csv_path)
        assert result == csv_path
        with open(csv_path) as f:
            content = f.read()
        assert "Dev" in content
        db.close()

    def test_export_csv_empty(self, tmp_db_path):
        db = ApplicationDatabase(db_path=tmp_db_path)
        result = db.export_csv(output_path="data/empty.csv")
        assert result == ""
        db.close()
