"""Human-like behavior simulation for browser automation.

Uses gaussian (normal) distribution for delays instead of uniform random,
creating more natural-looking timing patterns.
"""

import random
import time
from typing import Optional

from src.utils.logger import log


def human_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
    """Sleep for a gaussian-distributed random duration.

    The delay clusters around the midpoint with natural variance,
    mimicking human reaction times.
    """
    mean = (min_sec + max_sec) / 2
    std_dev = (max_sec - min_sec) / 4  # 95% within range
    delay = max(min_sec, min(max_sec, random.gauss(mean, std_dev)))
    time.sleep(delay)


def human_typing_delay() -> None:
    """Brief delay between keystrokes (50-150ms)."""
    time.sleep(random.gauss(0.1, 0.025))


def human_click_delay() -> None:
    """Delay before a click action (0.3-1.2s)."""
    human_delay(0.3, 1.2)


def session_break(min_minutes: float = 5, max_minutes: float = 15) -> None:
    """Take a human-like break between application sessions."""
    minutes = random.gauss(
        (min_minutes + max_minutes) / 2,
        (max_minutes - min_minutes) / 4,
    )
    minutes = max(min_minutes, min(max_minutes, minutes))
    log.info(f"Taking a {minutes:.1f} minute break...")
    time.sleep(minutes * 60)


def is_within_active_hours(
    active_start: str = "08:00", active_end: str = "22:00"
) -> bool:
    """Check if current time is within configured active hours."""
    from datetime import datetime

    now = datetime.now()
    start_h, start_m = map(int, active_start.split(":"))
    end_h, end_m = map(int, active_end.split(":"))

    start_minutes = start_h * 60 + start_m
    end_minutes = end_h * 60 + end_m
    now_minutes = now.hour * 60 + now.minute

    return start_minutes <= now_minutes <= end_minutes


def random_scroll(driver, element=None, direction: str = "down") -> None:
    """Perform a human-like scroll action on the page or element."""
    pixels = random.randint(200, 600)
    if direction == "up":
        pixels = -pixels

    if element:
        driver.execute_script(
            "arguments[0].scrollTop += arguments[1]", element, pixels
        )
    else:
        driver.execute_script(f"window.scrollBy(0, {pixels})")

    human_delay(0.5, 1.5)


def random_mouse_offset() -> tuple[int, int]:
    """Generate small random mouse offset to avoid pixel-perfect clicks."""
    return (random.randint(-3, 3), random.randint(-3, 3))


def should_take_break(
    apps_count: int,
    break_after: int = 15,
) -> bool:
    """Determine if a session break is needed based on application count."""
    return apps_count > 0 and apps_count % break_after == 0


def wait_for_active_hours(active_start: str, active_end: str) -> None:
    """Sleep until active hours begin if currently outside them."""
    import datetime

    if is_within_active_hours(active_start, active_end):
        return

    start_h, start_m = map(int, active_start.split(":"))
    now = datetime.datetime.now()
    target = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)

    if target <= now:
        target += datetime.timedelta(days=1)

    wait_seconds = (target - now).total_seconds()
    log.info(
        f"Outside active hours. Sleeping until {active_start} "
        f"({wait_seconds / 3600:.1f} hours)"
    )
    time.sleep(wait_seconds)
