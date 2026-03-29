"""Browser driver management with stealth and lifecycle handling.

Enhanced with:
- React controlled component support (native value setter + synthetic events)
- Shadow DOM penetration for ADP/iCIMS
- Human-like per-character typing
- iframe switching helpers
- ActionChains-based smooth clicking
"""

import random
import time
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
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

    Supports undetected-chromedriver (preferred), SeleniumBase UC Mode,
    and standard Selenium as fallback.
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

    def human_click(self, element) -> None:
        """Click with smooth scroll + ActionChains for more human-like behavior."""
        self.scroll_to(element)
        human_click_delay()
        try:
            actions = ActionChains(self.driver)
            # Add small random offset to click position
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-3, 3)
            actions.move_to_element_with_offset(element, offset_x, offset_y)
            actions.click()
            actions.perform()
        except Exception:
            self.click(element)
        human_delay(0.5, 1.5)

    def type_text(self, element, text: str, clear_first: bool = True) -> None:
        """Type text into an input with human-like timing."""
        if clear_first:
            element.clear()
            human_delay(0.2, 0.4)
        element.send_keys(text)
        human_delay(0.3, 0.8)

    def human_type(self, element, text: str, clear_first: bool = True) -> None:
        """Type text character-by-character with random per-key delays.

        More human-like than send_keys() for anti-detection.
        """
        if clear_first:
            element.click()
            human_delay(0.1, 0.2)
            element.send_keys(Keys.CONTROL + "a")
            human_delay(0.05, 0.1)
            element.send_keys(Keys.DELETE)
            human_delay(0.2, 0.4)

        for char in text:
            element.send_keys(char)
            # Random per-character delay (50-150ms, occasionally longer)
            delay = random.gauss(0.08, 0.03)
            if random.random() < 0.05:  # 5% chance of a longer pause
                delay += random.uniform(0.2, 0.5)
            time.sleep(max(0.03, delay))

        human_delay(0.2, 0.5)

    def set_react_value(self, element, value: str) -> None:
        """Set value on a React controlled input using native setter.

        React overrides the value setter, so element.value = 'x' won't trigger
        state updates. This uses the native HTMLInputElement setter + synthetic
        input event to properly trigger React's onChange handler.
        """
        self.driver.execute_script("""
            const el = arguments[0];
            const value = arguments[1];
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(el, value);
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, element, value)
        human_delay(0.2, 0.5)

    def set_react_textarea_value(self, element, value: str) -> None:
        """Set value on a React controlled textarea using native setter."""
        self.driver.execute_script("""
            const el = arguments[0];
            const value = arguments[1];
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            ).set;
            nativeTextAreaValueSetter.call(el, value);
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, element, value)
        human_delay(0.2, 0.5)

    def pierce_shadow_dom(self, host_selector: str, inner_selector: str):
        """Find an element inside a Shadow DOM.

        Args:
            host_selector: CSS selector for the shadow host element.
            inner_selector: CSS selector for the target element inside the shadow root.

        Returns:
            The element inside the shadow DOM, or None.
        """
        try:
            return self.driver.execute_script("""
                const host = document.querySelector(arguments[0]);
                if (!host || !host.shadowRoot) return null;
                return host.shadowRoot.querySelector(arguments[1]);
            """, host_selector, inner_selector)
        except Exception as e:
            log.debug(f"Shadow DOM pierce failed: {e}")
            return None

    def pierce_shadow_dom_chain(self, selectors: list[str]):
        """Pierce through nested Shadow DOMs.

        Args:
            selectors: List of CSS selectors, alternating between host and inner.
                       e.g. ["shadow-host-1", "shadow-host-2", "target-element"]
        """
        try:
            js_parts = ["let el = document"]
            for i, sel in enumerate(selectors):
                if i < len(selectors) - 1:
                    js_parts.append(f"el = el.querySelector('{sel}')")
                    js_parts.append("if (!el) return null")
                    js_parts.append("el = el.shadowRoot")
                    js_parts.append("if (!el) return null")
                else:
                    js_parts.append(f"return el.querySelector('{sel}')")
            script = ";\n".join(js_parts)
            return self.driver.execute_script(script)
        except Exception as e:
            log.debug(f"Shadow DOM chain pierce failed: {e}")
            return None

    def switch_to_iframe(self, selector: str, timeout: float = 10) -> bool:
        """Switch to an iframe by CSS selector.

        Returns True if switch was successful.
        """
        try:
            iframe = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            self.driver.switch_to.frame(iframe)
            human_delay(0.5, 1.0)
            return True
        except Exception as e:
            log.debug(f"Failed to switch to iframe '{selector}': {e}")
            return False

    def switch_to_parent_frame(self) -> None:
        """Switch back to parent frame."""
        self.driver.switch_to.parent_frame()

    def switch_to_default_content(self) -> None:
        """Switch back to main page content from any iframe."""
        self.driver.switch_to.default_content()

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

    def wait_for_clickable(self, by: By, value: str, timeout: float = 10):
        """Wait for element to be clickable."""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

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

    def execute_script(self, script: str, *args):
        """Execute JavaScript in the browser."""
        return self.driver.execute_script(script, *args)

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
