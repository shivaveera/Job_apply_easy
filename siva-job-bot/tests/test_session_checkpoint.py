"""Tests for session checkpoint / crash recovery (Fix 5)."""

import pytest
import sqlite3

from src.utils.retry import SessionCheckpoint, retry_on_stale, retry_with_backoff


class TestSessionCheckpoint:
    """Test SessionCheckpoint SQLite-based crash recovery."""

    def test_init_creates_db(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        assert cp.session_id is not None
        assert cp.session_id > 0
        cp.close()

    def test_wal_mode_enabled(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        row = cp.conn.execute("PRAGMA journal_mode").fetchone()
        assert row[0] == "wal"
        cp.close()

    def test_mark_processing(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        cp.mark_processing("https://example.com/job1", "job1", "linkedin")
        row = cp.conn.execute(
            "SELECT status, platform FROM processed_jobs WHERE job_url = ?",
            ("https://example.com/job1",),
        ).fetchone()
        assert row[0] == "processing"
        assert row[1] == "linkedin"
        cp.close()

    def test_mark_applied(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        cp.mark_processing("https://example.com/job1", "job1", "linkedin")
        cp.mark_applied("https://example.com/job1")
        row = cp.conn.execute(
            "SELECT status FROM processed_jobs WHERE job_url = ?",
            ("https://example.com/job1",),
        ).fetchone()
        assert row[0] == "applied"
        cp.close()

    def test_mark_failed(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        cp.mark_processing("https://example.com/job1", "job1", "linkedin")
        cp.mark_failed("https://example.com/job1", "timeout error")
        row = cp.conn.execute(
            "SELECT status, error FROM processed_jobs WHERE job_url = ?",
            ("https://example.com/job1",),
        ).fetchone()
        assert row[0] == "failed"
        assert row[1] == "timeout error"
        cp.close()

    def test_is_processed_true_for_applied(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        cp.mark_processing("https://example.com/job1", "job1", "linkedin")
        cp.mark_applied("https://example.com/job1")
        assert cp.is_processed("https://example.com/job1") is True
        cp.close()

    def test_is_processed_false_for_processing(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        cp.mark_processing("https://example.com/job1", "job1", "linkedin")
        assert cp.is_processed("https://example.com/job1") is False
        cp.close()

    def test_is_processed_false_for_unknown(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        assert cp.is_processed("https://example.com/unknown") is False
        cp.close()

    def test_update_step(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        cp.mark_processing("https://example.com/job1", "job1", "linkedin")
        cp.update_step("https://example.com/job1", "form_filling")
        row = cp.conn.execute(
            "SELECT step FROM processed_jobs WHERE job_url = ?",
            ("https://example.com/job1",),
        ).fetchone()
        assert row[0] == "form_filling"
        cp.close()

    def test_end_session(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        cp.mark_processing("https://example.com/j1", "j1", "linkedin")
        cp.mark_applied("https://example.com/j1")
        cp.mark_processing("https://example.com/j2", "j2", "linkedin")
        cp.mark_failed("https://example.com/j2")
        cp.end_session()

        row = cp.conn.execute(
            "SELECT status, total_applied, total_failed FROM sessions WHERE id = ?",
            (cp.session_id,),
        ).fetchone()
        assert row[0] == "completed"
        assert row[1] == 1  # 1 applied
        assert row[2] == 1  # 1 failed
        cp.close()

    def test_mark_skipped(self, tmp_db_path):
        cp = SessionCheckpoint(db_path=tmp_db_path)
        cp.mark_processing("https://example.com/job1", "job1", "linkedin")
        cp.mark_skipped("https://example.com/job1")
        assert cp.is_processed("https://example.com/job1") is True
        cp.close()


class TestRetryOnStale:
    """Test the retry_on_stale decorator."""

    def test_success_no_retry(self):
        call_count = 0

        @retry_on_stale(max_retries=3, delay=0.01)
        def succeeds():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeeds() == "ok"
        assert call_count == 1

    def test_retries_on_stale_element(self):
        from selenium.common.exceptions import StaleElementReferenceException
        call_count = 0

        @retry_on_stale(max_retries=3, delay=0.01)
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise StaleElementReferenceException("stale")
            return "ok"

        assert fails_then_succeeds() == "ok"
        assert call_count == 3

    def test_raises_after_exhausted_retries(self):
        from selenium.common.exceptions import StaleElementReferenceException

        @retry_on_stale(max_retries=2, delay=0.01)
        def always_fails():
            raise StaleElementReferenceException("stale")

        with pytest.raises(StaleElementReferenceException):
            always_fails()


class TestRetryWithBackoff:
    """Test the retry_with_backoff decorator."""

    def test_success_no_retry(self):
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def succeeds():
            return 42

        assert succeeds() == 42

    def test_retries_specified_exceptions(self):
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "done"

        assert fails_twice() == "done"
        assert call_count == 3
