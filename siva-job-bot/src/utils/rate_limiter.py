"""Per-platform rate limiting with safe thresholds.

Based on research:
- LinkedIn: 25-30/day, 4-5/hr max (hard limit 50/24h)
- Indeed: 15-25/day, 2-3/hr (Cloudflare detection)
- Workday: No known global limit but per-employer
- Greenhouse/Lever: Moderate (API rate limited)

Uses gaussian-distributed delays for human-like timing.
"""

import random
import time
from datetime import datetime, timedelta

from src.utils.logger import log

# Safe rate limits per platform (applications per period)
PLATFORM_LIMITS = {
    "linkedin": {"per_hour": 5, "per_day": 30, "min_delay": 45, "max_delay": 180},
    "indeed": {"per_hour": 3, "per_day": 20, "min_delay": 60, "max_delay": 240},
    "workday": {"per_hour": 6, "per_day": 40, "min_delay": 30, "max_delay": 120},
    "greenhouse": {"per_hour": 8, "per_day": 50, "min_delay": 20, "max_delay": 90},
    "lever": {"per_hour": 8, "per_day": 50, "min_delay": 20, "max_delay": 90},
    "smartrecruiters": {"per_hour": 6, "per_day": 40, "min_delay": 30, "max_delay": 120},
    "icims": {"per_hour": 5, "per_day": 30, "min_delay": 30, "max_delay": 120},
    "taleo": {"per_hour": 4, "per_day": 25, "min_delay": 45, "max_delay": 180},
    "adp": {"per_hour": 5, "per_day": 30, "min_delay": 30, "max_delay": 120},
    "ashby": {"per_hour": 8, "per_day": 50, "min_delay": 20, "max_delay": 90},
    "default": {"per_hour": 5, "per_day": 30, "min_delay": 30, "max_delay": 120},
}

# Break probability: 10% chance of 5-10 minute break after each application
BREAK_PROBABILITY = 0.10
BREAK_MIN_MINUTES = 5
BREAK_MAX_MINUTES = 10


class RateLimiter:
    """Track and enforce per-platform application rate limits."""

    def __init__(self, config_overrides: dict = None):
        self._timestamps: dict[str, list[datetime]] = {}
        self._overrides = config_overrides or {}

    def _get_limits(self, platform: str) -> dict:
        """Get rate limits for a platform, with config overrides."""
        base = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["default"]).copy()
        if platform in self._overrides:
            base.update(self._overrides[platform])
        return base

    def can_apply(self, platform: str) -> bool:
        """Check if we're within rate limits for a platform."""
        limits = self._get_limits(platform)
        now = datetime.now()
        timestamps = self._timestamps.get(platform, [])

        # Clean old timestamps
        cutoff_day = now - timedelta(hours=24)
        timestamps = [ts for ts in timestamps if ts > cutoff_day]
        self._timestamps[platform] = timestamps

        # Check daily limit
        if len(timestamps) >= limits["per_day"]:
            log.warning(f"Daily limit reached for {platform}: {len(timestamps)}/{limits['per_day']}")
            return False

        # Check hourly limit
        cutoff_hour = now - timedelta(hours=1)
        hourly_count = sum(1 for ts in timestamps if ts > cutoff_hour)
        if hourly_count >= limits["per_hour"]:
            log.warning(f"Hourly limit reached for {platform}: {hourly_count}/{limits['per_hour']}")
            return False

        return True

    def record_application(self, platform: str) -> None:
        """Record that an application was submitted."""
        if platform not in self._timestamps:
            self._timestamps[platform] = []
        self._timestamps[platform].append(datetime.now())

    def wait_between_applications(self, platform: str) -> None:
        """Wait a human-like delay between applications.

        Uses gaussian distribution for natural timing.
        Includes 10% chance of a longer break.
        """
        limits = self._get_limits(platform)
        min_delay = limits["min_delay"]
        max_delay = limits["max_delay"]

        # Gaussian delay
        mean = (min_delay + max_delay) / 2
        std = (max_delay - min_delay) / 4
        delay = max(min_delay, min(max_delay, random.gauss(mean, std)))

        # Random long break
        if random.random() < BREAK_PROBABILITY:
            break_minutes = random.uniform(BREAK_MIN_MINUTES, BREAK_MAX_MINUTES)
            log.info(f"Taking a {break_minutes:.1f}m random break (anti-detection)")
            time.sleep(break_minutes * 60)
            return

        log.debug(f"Rate limit delay: {delay:.0f}s for {platform}")
        time.sleep(delay)

    def time_until_available(self, platform: str) -> float:
        """Get seconds until next application is allowed."""
        limits = self._get_limits(platform)
        timestamps = self._timestamps.get(platform, [])
        now = datetime.now()

        # Check hourly
        cutoff_hour = now - timedelta(hours=1)
        hourly = [ts for ts in timestamps if ts > cutoff_hour]
        if len(hourly) >= limits["per_hour"]:
            oldest = min(hourly)
            return (oldest + timedelta(hours=1) - now).total_seconds()

        return 0

    def get_stats(self) -> dict:
        """Get current rate limit stats per platform."""
        now = datetime.now()
        stats = {}
        for platform, timestamps in self._timestamps.items():
            cutoff_day = now - timedelta(hours=24)
            cutoff_hour = now - timedelta(hours=1)
            day_count = sum(1 for ts in timestamps if ts > cutoff_day)
            hour_count = sum(1 for ts in timestamps if ts > cutoff_hour)
            limits = self._get_limits(platform)
            stats[platform] = {
                "today": day_count,
                "this_hour": hour_count,
                "daily_limit": limits["per_day"],
                "hourly_limit": limits["per_hour"],
            }
        return stats
