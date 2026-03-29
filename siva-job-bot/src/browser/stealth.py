"""Anti-detection and stealth browser configuration.

2025-2026 stealth stack:
- SeleniumBase UC Mode (preferred) / undetected-chromedriver (fallback)
- selenium-stealth fingerprint spoofing
- Canvas/WebGL/AudioContext fingerprint noise injection
- Chrome profile persistence with lock file repair
- Automation flag removal via CDP
- Proxy support for IP rotation
"""

import json
import os
import platform
import random
from pathlib import Path
from typing import Optional

from src.utils.logger import log

# User agent rotation pool (Chrome 131-134, 2025)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
]

# Fingerprint evasion script injected via CDP before any page loads
FINGERPRINT_EVASION_JS = """
// Canvas fingerprint noise
const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    const ctx = this.getContext('2d');
    if (ctx) {
        try {
            const d = ctx.getImageData(0, 0, Math.min(this.width, 16), Math.min(this.height, 16));
            for (let i = 0; i < d.data.length; i += 4) {
                d.data[i] += Math.floor(Math.random() * 3) - 1;
            }
            ctx.putImageData(d, 0, 0);
        } catch(e) {}
    }
    return origToDataURL.apply(this, arguments);
};

// WebGL vendor/renderer spoof
const getParam = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(p) {
    if (p === 37445) return 'Google Inc. (Intel)';
    if (p === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)';
    return getParam.call(this, p);
};
// Also patch WebGL2
if (typeof WebGL2RenderingContext !== 'undefined') {
    const getParam2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(p) {
        if (p === 37445) return 'Google Inc. (Intel)';
        if (p === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)';
        return getParam2.call(this, p);
    };
}

// AudioContext fingerprint noise
const origGetFloatFrequencyData = AnalyserNode.prototype.getFloatFrequencyData;
AnalyserNode.prototype.getFloatFrequencyData = function(array) {
    origGetFloatFrequencyData.call(this, array);
    for (let i = 0; i < array.length; i++) {
        array[i] += (Math.random() - 0.5) * 0.01;
    }
};

// Webdriver flag removal
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// Plugins spoof (realistic count)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const p = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {name: 'Native Client', filename: 'internal-nacl-plugin'}
        ];
        p.length = 3;
        return p;
    }
});

// Languages
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});

// Hardware concurrency (realistic value)
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});

// Device memory (realistic value)
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});

// Connection (realistic)
if (navigator.connection) {
    Object.defineProperty(navigator.connection, 'rtt', {get: () => 50});
}
"""


def get_bot_profile_dir(platform_name: str = "default") -> str:
    """Get or create a persistent bot Chrome profile directory.

    Each platform gets its own profile to maintain separate sessions.
    """
    profile_dir = Path.home() / ".siva-job-bot" / "profiles" / platform_name
    profile_dir.mkdir(parents=True, exist_ok=True)
    return str(profile_dir)


def repair_chrome_profile(profile_dir: str) -> None:
    """Repair Chrome profile after unclean shutdown.

    Removes lock files and fixes exit_type to prevent
    'Chrome didn't shut down correctly' prompts.
    """
    for lock_file in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        lock_path = os.path.join(profile_dir, lock_file)
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except OSError:
                pass

    prefs_path = os.path.join(profile_dir, "Default", "Preferences")
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("profile", {})["exit_type"] = "Normal"
            data["profile"]["exited_cleanly"] = True
            with open(prefs_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except (json.JSONDecodeError, KeyError, OSError):
            pass


def get_stealth_chrome_options(
    headless: bool = False,
    use_profile: bool = True,
    profile_dir: Optional[str] = None,
    proxy: Optional[str] = None,
) -> "ChromeOptions":
    """Configure Chrome options with anti-detection measures."""
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
        if not profile_dir:
            profile_dir = get_bot_profile_dir()
        repair_chrome_profile(profile_dir)
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--profile-directory=Default")
        log.info(f"Using Chrome profile: {profile_dir}")

    # Proxy support
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
        log.info(f"Using proxy: {proxy[:30]}...")

    # Headless mode
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)

    return options


def apply_stealth(driver) -> None:
    """Apply selenium-stealth patches to mask automation fingerprints."""
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
        log.debug("selenium-stealth not installed, skipping")
    except Exception as e:
        log.warning(f"Failed to apply stealth: {e}")


def inject_stealth_scripts(driver) -> None:
    """Execute JavaScript to mask automation detection."""
    try:
        driver.execute_script(FINGERPRINT_EVASION_JS)
    except Exception:
        pass


def inject_fingerprint_evasion_cdp(driver) -> None:
    """Inject fingerprint evasion via CDP (runs before any page loads).

    This is the most reliable method - injects scripts that execute
    before the page's own JavaScript can detect automation.
    """
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": FINGERPRINT_EVASION_JS},
        )
        log.debug("CDP fingerprint evasion injected")
    except Exception as e:
        log.debug(f"CDP injection not available: {e}")
        inject_stealth_scripts(driver)
