"""Tests for CAPTCHA solver (Fix 2)."""

import pytest
from unittest.mock import MagicMock, patch

from src.browser.captcha import CaptchaSolver


class TestCaptchaSolverInit:
    """Test CaptchaSolver initialization."""

    def test_enabled_with_capsolver_key(self):
        solver = CaptchaSolver({"capsolver_api_key": "test-key"})
        assert solver.enabled is True
        assert solver.capsolver_key == "test-key"

    def test_enabled_with_twocaptcha_key(self):
        solver = CaptchaSolver({"twocaptcha_api_key": "test-key"})
        assert solver.enabled is True
        assert solver.twocaptcha_key == "test-key"

    def test_disabled_without_keys(self):
        solver = CaptchaSolver({})
        assert solver.enabled is False

    def test_disabled_with_empty_config(self):
        solver = CaptchaSolver()
        assert solver.enabled is False


class TestCaptchaDetection:
    """Test CAPTCHA detection on pages."""

    def test_detect_recaptcha(self):
        solver = CaptchaSolver()
        driver = MagicMock()
        driver.page_source = "<html>recaptcha data-sitekey</html>"
        recaptcha_el = MagicMock()
        driver.find_elements.side_effect = lambda by, css: (
            [recaptcha_el] if "data-sitekey" in css and "g-recaptcha" in css else []
        )
        result = solver.detect_captcha(driver)
        assert result == "recaptcha_v2"

    def test_detect_no_captcha(self):
        solver = CaptchaSolver()
        driver = MagicMock()
        driver.page_source = "<html><body>Normal page</body></html>"
        driver.current_url = "https://example.com"
        driver.find_elements.return_value = []
        result = solver.detect_captcha(driver)
        assert result is None

    def test_detect_linkedin_checkpoint(self):
        solver = CaptchaSolver()
        driver = MagicMock()
        driver.page_source = "<html>challenge verification</html>"
        driver.current_url = "https://linkedin.com/checkpoint/challenge"
        driver.find_elements.return_value = []
        result = solver.detect_captcha(driver)
        assert result == "linkedin_checkpoint"


class TestCaptchaSolve:
    """Test CAPTCHA solving flow."""

    def test_solve_returns_true_when_no_captcha(self):
        solver = CaptchaSolver()
        driver = MagicMock()
        driver.page_source = "<html>normal</html>"
        driver.current_url = "https://example.com"
        driver.find_elements.return_value = []
        assert solver.solve(driver) is True

    def test_solve_linkedin_checkpoint_waits(self):
        solver = CaptchaSolver()
        driver = MagicMock()
        # Simulate URL changing after checkpoint (CAPTCHA solved)
        # _wait_for_manual_solve checks current_url changes
        call_count = [0]
        original_url = "https://linkedin.com/checkpoint"
        def get_url():
            call_count[0] += 1
            if call_count[0] > 1:
                return "https://linkedin.com/feed/"
            return original_url
        type(driver).current_url = property(lambda self: get_url())

        with patch("src.browser.captcha.time.sleep"):
            result = solver.solve(driver, "linkedin_checkpoint")
        assert result is True

    @patch("src.browser.captcha.time.sleep")
    def test_solve_manual_timeout(self, mock_sleep):
        solver = CaptchaSolver()
        driver = MagicMock()
        driver.current_url = "https://stuck.com/captcha"
        solver.detect_captcha = MagicMock(return_value="recaptcha_v2")
        # Use a real but very short timeout - mock sleep so it's instant
        result = solver._wait_for_manual_solve(driver, timeout=0)
        assert result is False
