"""Browser driver management with stealth and lifecycle handling."""

from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.browser.stealth import (
    apply_stealth,
    get_stealth_chrome_options,
    inject_stealth_scripts,
)
from src.utils.humanizer import human_click_delay, human_delay, random_scroll
from src.utils.logger import log


class BrowserDriver:
    """Manages the browser lifecycle with anti-detection features.

    Supports both undetected-chromedriver (preferred) and standard Selenium.
    """

    def __init__(
        self,
        headless: bool = False,
        use_profile: bool = True,
        profile_dir: Optional[str] = None,
        stealth_mode: bool = True,
    ):
        self.headless = headless
        self.use_profile = use_profile
        self.profile_dir = profile_dir
        self.stealth_mode = stealth_mode
        self.driver = None

    def start(self) -> None:
        """Initialize and start the browser with stealth configuration."""
        options = get_stealth_chrome_options(
            headless=self.headless,
            use_profile=self.use_profile,
            profile_dir=self.profile_dir,
        )

        # Try undetected-chromedriver first
        if self.stealth_mode:
            try:
                import undetected_chromedriver as uc

                self.driver = uc.Chrome(options=options)
                log.info("Browser started with undetected-chromedriver")
            except ImportError:
                log.warning(
                    "undetected-chromedriver not installed. "
                    "Install with: pip install undetected-chromedriver"
                )
                self._start_standard(options)
            except Exception as e:
                log.warning(f"undetected-chromedriver failed: {e}. Falling back.")
                self._start_standard(options)
        else:
            self._start_standard(options)

        # Apply stealth patches
        apply_stealth(self.driver)
        inject_stealth_scripts(self.driver)

        # Set page load timeout
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(5)

    def _start_standard(self, options) -> None:
        """Start browser with standard Selenium ChromeDriver."""
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        log.info("Browser started with standard Selenium")

    def get(self, url: str) -> None:
        """Navigate to URL with human-like delay."""
        self.driver.get(url)
        human_delay(1.0, 3.0)
        inject_stealth_scripts(self.driver)

    def find_element(self, by: By, value: str, timeout: float = 10):
        """Find element with explicit wait."""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def find_elements(self, by: By, value: str, timeout: float = 10) -> list:
        """Find multiple elements with explicit wait."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_elements(by, value)
        except Exception:
            return []

    def click(self, element) -> None:
        """Click an element with human-like delay."""
        human_click_delay()
        try:
            element.click()
        except Exception:
            # Fallback: JavaScript click
            self.driver.execute_script("arguments[0].click();", element)
        human_delay(0.5, 1.5)

    def type_text(self, element, text: str, clear_first: bool = True) -> None:
        """Type text into an input with human-like timing."""
        if clear_first:
            element.clear()
            human_delay(0.2, 0.4)
        element.send_keys(text)
        human_delay(0.3, 0.8)

    def scroll_to(self, element) -> None:
        """Scroll to an element with smooth behavior."""
        self.driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element,
        )
        human_delay(0.5, 1.0)

    def wait_for_url_contains(self, text: str, timeout: float = 60) -> bool:
        """Wait until URL contains the specified text."""
        try:
            WebDriverWait(self.driver, timeout).until(EC.url_contains(text))
            return True
        except Exception:
            return False

    def element_exists(self, by: By, value: str, timeout: float = 3) -> bool:
        """Check if an element exists on the page."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except Exception:
            return False

    def get_page_source(self) -> str:
        """Get the current page HTML source."""
        return self.driver.page_source

    def current_url(self) -> str:
        """Get the current page URL."""
        return self.driver.current_url

    def close(self) -> None:
        """Close the browser gracefully."""
        if self.driver:
            try:
                self.driver.quit()
                log.info("Browser closed")
            except Exception as e:
                log.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None
