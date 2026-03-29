"""Tests for form validation and submission verification (Fix 3)."""

import os
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.browser.form_validator import (
    verify_submission_success,
    find_form_errors,
    take_screenshot,
    SUCCESS_PATTERNS,
)


class TestVerifySubmissionSuccess:
    """Test post-submission success detection (Fix 3)."""

    def test_linkedin_success_via_element(self):
        driver = MagicMock()
        driver.current_url = "https://linkedin.com/jobs"
        mock_el = MagicMock()
        mock_el.is_displayed.return_value = True
        driver.find_elements.side_effect = lambda by, css: (
            [mock_el] if "application was sent" in css else []
        )
        assert verify_submission_success(driver, "linkedin") is True

    def test_linkedin_no_success_indicators(self):
        driver = MagicMock()
        driver.current_url = "https://linkedin.com/jobs/view/123"
        driver.find_elements.return_value = []
        body = MagicMock()
        body.text = "Some random page text"
        driver.find_element.return_value = body
        assert verify_submission_success(driver, "linkedin") is False

    def test_workday_success_via_url(self):
        driver = MagicMock()
        driver.current_url = "https://company.wd5.myworkdayjobs.com/successfullyApplied"
        assert verify_submission_success(driver, "workday") is True

    def test_workday_success_via_text(self):
        driver = MagicMock()
        driver.current_url = "https://company.wd5.myworkdayjobs.com/form"
        driver.find_elements.return_value = []
        body = MagicMock()
        body.text = "Congratulations! Thank you for applying to this position."
        driver.find_element.return_value = body
        assert verify_submission_success(driver, "workday") is True

    def test_lever_success_via_url(self):
        driver = MagicMock()
        driver.current_url = "https://jobs.lever.co/company/abc123/thanks"
        assert verify_submission_success(driver, "lever") is True

    def test_unknown_platform_returns_false(self):
        driver = MagicMock()
        driver.current_url = "https://unknown.com/form"
        assert verify_submission_success(driver, "unknown_platform") is False


class TestSuccessPatterns:
    """Test that all major platforms have success patterns."""

    def test_linkedin_patterns_exist(self):
        assert "linkedin" in SUCCESS_PATTERNS

    def test_workday_patterns_exist(self):
        assert "workday" in SUCCESS_PATTERNS

    def test_greenhouse_patterns_exist(self):
        assert "greenhouse" in SUCCESS_PATTERNS

    def test_indeed_patterns_exist(self):
        assert "indeed" in SUCCESS_PATTERNS

    def test_lever_patterns_exist(self):
        assert "lever" in SUCCESS_PATTERNS


class TestFindFormErrors:
    """Test form error detection."""

    def test_no_errors(self):
        driver = MagicMock()
        driver.find_elements.return_value = []
        errors = find_form_errors(driver)
        assert errors == []

    def test_detects_linkedin_errors(self):
        driver = MagicMock()
        error_el = MagicMock()
        error_el.is_displayed.return_value = True
        error_el.text = "This field is required"
        driver.find_elements.side_effect = lambda by, css: (
            [error_el] if "artdeco-inline-feedback--error" in css else []
        )
        errors = find_form_errors(driver)
        assert "This field is required" in errors


class TestTakeScreenshot:
    """Test screenshot capture."""

    def test_take_screenshot_success(self, tmp_path):
        driver = MagicMock()
        driver.save_screenshot.return_value = True
        with patch("src.browser.form_validator.Path") as mock_path:
            mock_path.return_value = tmp_path / "screenshots"
            result = take_screenshot(driver, "job123", "success")
        assert driver.save_screenshot.called

    def test_take_screenshot_failure(self):
        driver = MagicMock()
        driver.save_screenshot.side_effect = Exception("No browser")
        result = take_screenshot(driver, "job123", "failed")
        assert result == ""
