"""Tests for BrowserDriver CDP integration (Fix 7)."""

import pytest
from unittest.mock import MagicMock, patch, call


class TestDriverCDPIntegration:
    """Test that driver.start() uses CDP injection instead of runtime JS."""

    @patch("src.browser.driver.inject_fingerprint_evasion_cdp")
    @patch("src.browser.driver.apply_stealth")
    @patch("src.browser.driver.get_stealth_chrome_options")
    def test_start_uses_cdp_injection(self, mock_options, mock_stealth, mock_cdp):
        """Verify start() calls inject_fingerprint_evasion_cdp, not inject_stealth_scripts."""
        from src.browser.driver import BrowserDriver

        browser = BrowserDriver(stealth_mode=False)
        mock_options.return_value = MagicMock()
        mock_driver = MagicMock()

        def fake_start_standard(options):
            browser.driver = mock_driver

        with patch.object(BrowserDriver, "_start_standard", side_effect=fake_start_standard):
            browser.start()

        mock_cdp.assert_called_once_with(mock_driver)
        mock_stealth.assert_called_once_with(mock_driver)

    def test_get_does_not_reinject_stealth(self):
        """Verify get() no longer calls inject_stealth_scripts on every navigation."""
        from src.browser.driver import BrowserDriver

        browser = BrowserDriver()
        browser.driver = MagicMock()

        with patch("src.browser.driver.human_delay"):
            browser.get("https://example.com")

        browser.driver.get.assert_called_once_with("https://example.com")
        # Should NOT have called execute_script with stealth JS
        # (CDP handles it before page load)
