"""Tests for rate limiter (Fix 4)."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.utils.rate_limiter import RateLimiter, PLATFORM_LIMITS


class TestRateLimiterCanApply:
    """Test can_apply rate limit checks."""

    def test_can_apply_initially_true(self):
        rl = RateLimiter()
        assert rl.can_apply("linkedin") is True

    def test_can_apply_under_hourly_limit(self):
        rl = RateLimiter()
        for _ in range(4):  # LinkedIn hourly limit is 5
            rl.record_application("linkedin")
        assert rl.can_apply("linkedin") is True

    def test_can_apply_at_hourly_limit(self):
        rl = RateLimiter()
        for _ in range(5):  # LinkedIn hourly limit is 5
            rl.record_application("linkedin")
        assert rl.can_apply("linkedin") is False

    def test_can_apply_at_daily_limit(self):
        rl = RateLimiter()
        # Simulate 30 applications spread across the last 24 hours
        now = datetime.now()
        rl._timestamps["linkedin"] = [
            now - timedelta(minutes=i * 30) for i in range(30)
        ]
        assert rl.can_apply("linkedin") is False

    def test_can_apply_after_old_timestamps_expire(self):
        rl = RateLimiter()
        # All timestamps older than 24h
        old = datetime.now() - timedelta(hours=25)
        rl._timestamps["linkedin"] = [old] * 30
        assert rl.can_apply("linkedin") is True

    def test_can_apply_unknown_platform_uses_default(self):
        rl = RateLimiter()
        assert rl.can_apply("nonexistent_platform") is True


class TestRateLimiterRecord:
    """Test recording applications."""

    def test_record_application_adds_timestamp(self):
        rl = RateLimiter()
        rl.record_application("linkedin")
        assert len(rl._timestamps["linkedin"]) == 1

    def test_record_multiple_applications(self):
        rl = RateLimiter()
        for _ in range(5):
            rl.record_application("linkedin")
        assert len(rl._timestamps["linkedin"]) == 5


class TestRateLimiterStats:
    """Test stats reporting."""

    def test_get_stats_empty(self):
        rl = RateLimiter()
        assert rl.get_stats() == {}

    def test_get_stats_after_applications(self):
        rl = RateLimiter()
        rl.record_application("linkedin")
        rl.record_application("linkedin")
        rl.record_application("greenhouse")
        stats = rl.get_stats()
        assert "linkedin" in stats
        assert "greenhouse" in stats
        assert stats["linkedin"]["today"] == 2
        assert stats["linkedin"]["this_hour"] == 2
        assert stats["greenhouse"]["today"] == 1


class TestRateLimiterWait:
    """Test wait_between_applications timing."""

    @patch("src.utils.rate_limiter.time.sleep")
    @patch("src.utils.rate_limiter.random.random", return_value=0.5)  # No break
    @patch("src.utils.rate_limiter.random.gauss", return_value=100.0)
    def test_wait_calls_sleep(self, mock_gauss, mock_random, mock_sleep):
        rl = RateLimiter()
        rl.wait_between_applications("linkedin")
        mock_sleep.assert_called_once_with(100.0)

    @patch("src.utils.rate_limiter.time.sleep")
    @patch("src.utils.rate_limiter.random.random", return_value=0.05)  # Trigger break
    @patch("src.utils.rate_limiter.random.uniform", return_value=7.0)
    def test_wait_takes_break(self, mock_uniform, mock_random, mock_sleep):
        rl = RateLimiter()
        rl.wait_between_applications("linkedin")
        # Should sleep for 7 minutes = 420 seconds
        mock_sleep.assert_called_once_with(420.0)


class TestRateLimiterOverrides:
    """Test config overrides."""

    def test_override_limits(self):
        rl = RateLimiter(config_overrides={"linkedin": {"per_hour": 100, "per_day": 1000}})
        for _ in range(50):
            rl.record_application("linkedin")
        assert rl.can_apply("linkedin") is True

    def test_time_until_available_zero_when_allowed(self):
        rl = RateLimiter()
        assert rl.time_until_available("linkedin") == 0

    def test_time_until_available_positive_when_limited(self):
        rl = RateLimiter()
        for _ in range(5):
            rl.record_application("linkedin")
        wait = rl.time_until_available("linkedin")
        assert wait > 0


class TestPlatformLimits:
    """Test that all expected platforms have limits defined."""

    def test_linkedin_limits_exist(self):
        assert "linkedin" in PLATFORM_LIMITS
        assert PLATFORM_LIMITS["linkedin"]["per_hour"] == 5
        assert PLATFORM_LIMITS["linkedin"]["per_day"] == 30

    def test_indeed_limits_exist(self):
        assert "indeed" in PLATFORM_LIMITS

    def test_workday_limits_exist(self):
        assert "workday" in PLATFORM_LIMITS

    def test_default_limits_exist(self):
        assert "default" in PLATFORM_LIMITS
