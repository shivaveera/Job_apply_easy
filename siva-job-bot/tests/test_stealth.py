"""Tests for stealth and CDP injection (Fix 7)."""

import pytest
from unittest.mock import MagicMock, patch

from src.browser.stealth import (
    FINGERPRINT_EVASION_JS,
    inject_fingerprint_evasion_cdp,
    inject_stealth_scripts,
    get_bot_profile_dir,
    repair_chrome_profile,
)


class TestCDPInjection:
    """Test that CDP injection is used (Fix 7)."""

    def test_cdp_injection_calls_execute_cdp_cmd(self):
        driver = MagicMock()
        inject_fingerprint_evasion_cdp(driver)
        driver.execute_cdp_cmd.assert_called_once_with(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": FINGERPRINT_EVASION_JS},
        )

    def test_cdp_injection_falls_back_to_runtime(self):
        driver = MagicMock()
        driver.execute_cdp_cmd.side_effect = Exception("CDP not available")
        inject_fingerprint_evasion_cdp(driver)
        # Should fall back to runtime injection
        driver.execute_script.assert_called_once_with(FINGERPRINT_EVASION_JS)

    def test_runtime_injection_directly(self):
        driver = MagicMock()
        inject_stealth_scripts(driver)
        driver.execute_script.assert_called_once_with(FINGERPRINT_EVASION_JS)


class TestFingerprintEvasionJS:
    """Test that the JS contains all expected evasions."""

    def test_canvas_fingerprint(self):
        assert "toDataURL" in FINGERPRINT_EVASION_JS

    def test_webgl_vendor_spoof(self):
        assert "37445" in FINGERPRINT_EVASION_JS  # UNMASKED_VENDOR
        assert "37446" in FINGERPRINT_EVASION_JS  # UNMASKED_RENDERER

    def test_audio_context_noise(self):
        assert "AnalyserNode" in FINGERPRINT_EVASION_JS

    def test_webdriver_flag_removal(self):
        assert "webdriver" in FINGERPRINT_EVASION_JS

    def test_plugins_spoof(self):
        assert "plugins" in FINGERPRINT_EVASION_JS

    def test_hardware_concurrency(self):
        assert "hardwareConcurrency" in FINGERPRINT_EVASION_JS


class TestBotProfileDir:
    """Test Chrome profile directory management."""

    def test_get_bot_profile_dir_default(self, tmp_path):
        with patch("src.browser.stealth.Path.home", return_value=tmp_path):
            path = get_bot_profile_dir("default")
        assert "default" in path
        assert ".siva-job-bot" in path

    def test_get_bot_profile_dir_platform_specific(self, tmp_path):
        with patch("src.browser.stealth.Path.home", return_value=tmp_path):
            path = get_bot_profile_dir("linkedin")
        assert "linkedin" in path


class TestRepairChromeProfile:
    """Test Chrome profile repair."""

    def test_repair_removes_lock_files(self, tmp_path):
        profile_dir = str(tmp_path)
        # Create lock files
        for lock in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
            (tmp_path / lock).write_text("locked")
        repair_chrome_profile(profile_dir)
        for lock in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
            assert not (tmp_path / lock).exists()

    def test_repair_fixes_exit_type(self, tmp_path):
        import json
        profile_dir = str(tmp_path)
        prefs_dir = tmp_path / "Default"
        prefs_dir.mkdir()
        prefs_file = prefs_dir / "Preferences"
        prefs_file.write_text(json.dumps({"profile": {"exit_type": "Crashed"}}))

        repair_chrome_profile(profile_dir)

        with open(prefs_file) as f:
            data = json.load(f)
        assert data["profile"]["exit_type"] == "Normal"
        assert data["profile"]["exited_cleanly"] is True
