"""Anti-detection and stealth browser configuration.

Combines the best anti-detection techniques from analyzed repos:
- undetected-chromedriver (from Auto_job_applier)
- selenium-stealth fingerprint spoofing (from EasyApplyJobsBot)
- Chrome profile persistence (from Auto_job_applier + AIHawk fork)
- Automation flag removal
"""

import platform
import random
from pathlib import Path
from typing import Optional

from src.utils.logger import log

# User agent rotation pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
]


def get_chrome_profile_dir() -> Optional[str]:
    """Detect the default Chrome profile directory for the current OS."""
    system = platform.system()
    home = Path.home()

    candidates = []
    if system == "Linux":
        candidates = [
            home / ".config" / "google-chrome",
            home / ".config" / "chromium",
        ]
    elif system == "Darwin":
        candidates = [
            home / "Library" / "Application Support" / "Google" / "Chrome",
        ]
    elif system == "Windows":
        import os
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates = [Path(local) / "Google" / "Chrome" / "User Data"]

    for path in candidates:
        if path.exists():
            log.debug(f"Found Chrome profile: {path}")
            return str(path)

    return None


def get_stealth_chrome_options(
    headless: bool = False,
    use_profile: bool = True,
    profile_dir: Optional[str] = None,
) -> "ChromeOptions":
    """Configure Chrome options with anti-detection measures.

    Returns configured ChromeOptions with stealth settings.
    """
    from selenium.webdriver.chrome.options import Options

    options = Options()

    # Core anti-detection flags
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    # Performance & stability
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-animations")
    options.add_argument("--disable-infobars")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-popup-blocking")

    # Random user agent
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"--user-agent={user_agent}")
    log.debug(f"Using user agent: {user_agent[:60]}...")

    # Chrome profile for session persistence
    if use_profile:
        if profile_dir:
            profile_path = profile_dir
        else:
            profile_path = get_chrome_profile_dir()

        if profile_path:
            options.add_argument(f"--user-data-dir={profile_path}")
            options.add_argument("--profile-directory=Default")
            log.info(f"Using Chrome profile: {profile_path}")
        else:
            # Create a persistent bot profile
            bot_profile = Path.home() / ".siva-job-bot" / "chrome-profile"
            bot_profile.mkdir(parents=True, exist_ok=True)
            options.add_argument(f"--user-data-dir={bot_profile}")
            log.info(f"Using bot profile: {bot_profile}")

    # Headless mode
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    # Block images/CSS for performance (reduce detection surface)
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)

    return options


def apply_stealth(driver) -> None:
    """Apply selenium-stealth patches to mask automation fingerprints.

    Spoofs navigator properties: languages, vendor, platform, WebGL.
    """
    try:
        from selenium_stealth import stealth

        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        log.debug("Selenium stealth patches applied")
    except ImportError:
        log.debug("selenium-stealth not installed, skipping stealth patches")
    except Exception as e:
        log.warning(f"Failed to apply stealth: {e}")


def inject_stealth_scripts(driver) -> None:
    """Execute JavaScript to further mask automation detection."""
    scripts = [
        # Remove webdriver property
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
        # Spoof plugins
        "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
        # Spoof languages
        "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})",
    ]

    for script in scripts:
        try:
            driver.execute_script(script)
        except Exception:
            pass
