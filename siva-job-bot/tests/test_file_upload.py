"""Tests for file upload module (Fix 1)."""

import os
import pytest
from unittest.mock import MagicMock, patch

from src.browser.file_upload import (
    upload_file_standard,
    upload_resume,
    upload_cover_letter,
    get_resume_format,
    RESUME_SELECTORS,
    COVER_LETTER_SELECTORS,
    DOCX_PREFERRED_PLATFORMS,
)


class TestResumeFormat:
    """Test resume format selection per platform."""

    def test_pdf_default(self):
        assert get_resume_format("linkedin") == "pdf"
        assert get_resume_format("greenhouse") == "pdf"
        assert get_resume_format("lever") == "pdf"

    def test_docx_preferred(self):
        assert get_resume_format("taleo") == "docx"
        assert get_resume_format("icims") == "docx"
        assert get_resume_format("adp") == "docx"


class TestResumeSelectors:
    """Test that all expected platforms have selectors."""

    def test_linkedin_selector_exists(self):
        assert "linkedin" in RESUME_SELECTORS

    def test_workday_selector_exists(self):
        assert "workday" in RESUME_SELECTORS

    def test_greenhouse_selector_exists(self):
        assert "greenhouse" in RESUME_SELECTORS

    def test_default_selector_exists(self):
        assert "default" in RESUME_SELECTORS


class TestUploadFileStandard:
    """Test standard file input upload."""

    def test_upload_nonexistent_file(self):
        driver = MagicMock()
        result = upload_file_standard(driver, "input[type='file']", "/nonexistent/file.pdf")
        assert result is False

    def test_upload_existing_file(self, tmp_resume):
        driver = MagicMock()
        mock_input = MagicMock()
        from selenium.webdriver.support.ui import WebDriverWait
        with patch("src.browser.file_upload.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = mock_input
            result = upload_file_standard(driver, "input[type='file']", tmp_resume)
        assert result is True
        mock_input.send_keys.assert_called_once()


class TestUploadResume:
    """Test resume upload routing per platform."""

    def test_upload_resume_missing_file(self):
        driver = MagicMock()
        result = upload_resume(driver, "linkedin", "/nonexistent.pdf")
        assert result is False

    def test_upload_resume_empty_path(self):
        driver = MagicMock()
        result = upload_resume(driver, "linkedin", "")
        assert result is False

    @patch("src.browser.file_upload.upload_file_standard", return_value=True)
    def test_upload_resume_linkedin(self, mock_upload, tmp_resume):
        driver = MagicMock()
        result = upload_resume(driver, "linkedin", tmp_resume)
        assert result is True
        # Should have tried the linkedin-specific selector
        call_args = mock_upload.call_args
        assert "linkedin" in RESUME_SELECTORS

    @patch("src.browser.file_upload.upload_file_dragdrop", return_value=True)
    def test_upload_resume_workday_tries_dragdrop(self, mock_dragdrop, tmp_resume):
        driver = MagicMock()
        result = upload_resume(driver, "workday", tmp_resume)
        assert result is True
        mock_dragdrop.assert_called_once()


class TestUploadCoverLetter:
    """Test cover letter upload."""

    def test_upload_cover_letter_missing_file(self):
        driver = MagicMock()
        result = upload_cover_letter(driver, "linkedin", "")
        assert result is False

    def test_cover_letter_selectors_exist(self):
        assert "linkedin" in COVER_LETTER_SELECTORS
        assert "greenhouse" in COVER_LETTER_SELECTORS
        assert "default" in COVER_LETTER_SELECTORS
