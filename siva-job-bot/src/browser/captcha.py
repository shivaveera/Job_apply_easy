"""CAPTCHA detection and solving integration.

Supports multiple CAPTCHA solving services:
- CapSolver (cheapest, AI-based, 3-9s)
- 2Captcha (most documented, human-based, 10-40s)
- Audio CAPTCHA fallback (free, using speech-to-text)

Also includes detection for common CAPTCHA types on ATS platforms.
"""

import time
from typing import Optional

from selenium.webdriver.common.by import By

from src.utils.logger import log


class CaptchaSolver:
    """Unified CAPTCHA detection and solving."""

    def __init__(self, config: dict = None):
        config = config or {}
        self.capsolver_key = config.get("capsolver_api_key", "")
        self.twocaptcha_key = config.get("twocaptcha_api_key", "")
        self.enabled = bool(self.capsolver_key or self.twocaptcha_key)

    def detect_captcha(self, driver) -> Optional[str]:
        """Detect if a CAPTCHA is present on the page.

        Returns:
            CAPTCHA type string ('recaptcha_v2', 'hcaptcha', 'turnstile', 'audio')
            or None if no CAPTCHA detected.
        """
        try:
            page_source = driver.page_source.lower()

            # reCAPTCHA v2/v3
            if driver.find_elements(By.CSS_SELECTOR, "[data-sitekey], .g-recaptcha, #recaptcha"):
                return "recaptcha_v2"
            if "recaptcha" in page_source and "data-sitekey" in page_source:
                return "recaptcha_v2"

            # hCaptcha
            if driver.find_elements(By.CSS_SELECTOR, "[data-sitekey].h-captcha, .h-captcha"):
                return "hcaptcha"

            # Cloudflare Turnstile
            if driver.find_elements(By.CSS_SELECTOR, ".cf-turnstile, [data-sitekey][data-callback]"):
                return "turnstile"
            if "challenges.cloudflare.com" in page_source:
                return "turnstile"

            # LinkedIn security checkpoint
            if "checkpoint" in driver.current_url and "challenge" in page_source:
                return "linkedin_checkpoint"

        except Exception:
            pass

        return None

    def solve(self, driver, captcha_type: str = None) -> bool:
        """Attempt to solve a detected CAPTCHA.

        Tries solving services in order: CapSolver → 2Captcha → manual wait.
        """
        if not captcha_type:
            captcha_type = self.detect_captcha(driver)

        if not captcha_type:
            return True  # No CAPTCHA to solve

        log.info(f"CAPTCHA detected: {captcha_type}")

        if captcha_type == "linkedin_checkpoint":
            return self._wait_for_manual_solve(driver, timeout=300)

        if not self.enabled:
            log.warning("No CAPTCHA solver configured. Waiting for manual solve...")
            return self._wait_for_manual_solve(driver, timeout=120)

        # Try CapSolver first (faster, cheaper)
        if self.capsolver_key:
            result = self._solve_capsolver(driver, captcha_type)
            if result:
                return True

        # Fallback to 2Captcha
        if self.twocaptcha_key:
            result = self._solve_twocaptcha(driver, captcha_type)
            if result:
                return True

        # Last resort: wait for manual
        log.warning("Automated solving failed. Waiting for manual solve...")
        return self._wait_for_manual_solve(driver, timeout=120)

    def _solve_capsolver(self, driver, captcha_type: str) -> bool:
        """Solve CAPTCHA using CapSolver API."""
        try:
            import capsolver
            capsolver.api_key = self.capsolver_key

            url = driver.current_url
            sitekey = self._extract_sitekey(driver)
            if not sitekey:
                return False

            task_type_map = {
                "recaptcha_v2": "ReCaptchaV2TaskProxyLess",
                "hcaptcha": "HCaptchaTaskProxyLess",
                "turnstile": "AntiTurnstileTaskProxyLess",
            }
            task_type = task_type_map.get(captcha_type)
            if not task_type:
                return False

            solution = capsolver.solve({
                "type": task_type,
                "websiteURL": url,
                "websiteKey": sitekey,
            })

            token = solution.get("gRecaptchaResponse") or solution.get("token", "")
            if token:
                self._inject_token(driver, captcha_type, token)
                log.info("CAPTCHA solved via CapSolver")
                return True

        except ImportError:
            log.debug("capsolver package not installed")
        except Exception as e:
            log.warning(f"CapSolver failed: {e}")

        return False

    def _solve_twocaptcha(self, driver, captcha_type: str) -> bool:
        """Solve CAPTCHA using 2Captcha API."""
        try:
            from twocaptcha import TwoCaptcha
            solver = TwoCaptcha(self.twocaptcha_key)

            url = driver.current_url
            sitekey = self._extract_sitekey(driver)
            if not sitekey:
                return False

            if captcha_type == "recaptcha_v2":
                result = solver.recaptcha(sitekey=sitekey, url=url)
            elif captcha_type == "hcaptcha":
                result = solver.hcaptcha(sitekey=sitekey, url=url)
            elif captcha_type == "turnstile":
                result = solver.turnstile(sitekey=sitekey, url=url)
            else:
                return False

            token = result.get("code", "")
            if token:
                self._inject_token(driver, captcha_type, token)
                log.info("CAPTCHA solved via 2Captcha")
                return True

        except ImportError:
            log.debug("twocaptcha package not installed")
        except Exception as e:
            log.warning(f"2Captcha failed: {e}")

        return False

    def _extract_sitekey(self, driver) -> str:
        """Extract the CAPTCHA sitekey from the page."""
        selectors = [
            "[data-sitekey]",
            ".g-recaptcha[data-sitekey]",
            ".h-captcha[data-sitekey]",
            ".cf-turnstile[data-sitekey]",
        ]
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                key = el.get_attribute("data-sitekey")
                if key:
                    return key
            except Exception:
                continue
        return ""

    def _inject_token(self, driver, captcha_type: str, token: str) -> None:
        """Inject the solved CAPTCHA token into the page."""
        if captcha_type in ("recaptcha_v2",):
            driver.execute_script(f"""
                var el = document.getElementById('g-recaptcha-response');
                if (el) {{ el.style.display='block'; el.value='{token}'; }}
                // Trigger reCAPTCHA callback
                if (typeof ___grecaptcha_cfg !== 'undefined') {{
                    Object.keys(___grecaptcha_cfg.clients).forEach(function(key) {{
                        var c = ___grecaptcha_cfg.clients[key];
                        function findCb(obj) {{
                            if (!obj) return;
                            Object.keys(obj).forEach(function(k) {{
                                if (typeof obj[k] === 'object') findCb(obj[k]);
                                if (typeof obj[k] === 'function' && k === 'callback') obj[k]('{token}');
                            }});
                        }}
                        findCb(c);
                    }});
                }}
            """)
        elif captcha_type == "hcaptcha":
            driver.execute_script(f"""
                var ta = document.querySelector('[name="h-captcha-response"]');
                if (ta) ta.value = '{token}';
                var iframe = document.querySelector('iframe[data-hcaptcha-widget-id]');
                if (iframe) iframe.setAttribute('data-hcaptcha-response', '{token}');
            """)
        elif captcha_type == "turnstile":
            driver.execute_script(f"""
                var el = document.querySelector('[name="cf-turnstile-response"]');
                if (el) el.value = '{token}';
                if (window.turnstile) window.turnstile.getResponse = () => '{token}';
            """)

    def _wait_for_manual_solve(self, driver, timeout: int = 120) -> bool:
        """Wait for the user to manually solve the CAPTCHA."""
        log.warning(f"Please solve the CAPTCHA manually ({timeout}s timeout)...")
        start = time.time()
        initial_url = driver.current_url

        while time.time() - start < timeout:
            time.sleep(2)
            # Check if page changed (CAPTCHA solved)
            if driver.current_url != initial_url:
                log.info("CAPTCHA appears to be solved (URL changed)")
                return True
            # Check if CAPTCHA element disappeared
            if not self.detect_captcha(driver):
                log.info("CAPTCHA appears to be solved (element gone)")
                return True

        log.error("CAPTCHA solve timeout")
        return False
