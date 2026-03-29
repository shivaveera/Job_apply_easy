"""Shared pytest fixtures for siva-job-bot tests."""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def tmp_db_path(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture
def tmp_resume(tmp_path):
    """Create a temporary resume file."""
    resume = tmp_path / "test_resume.pdf"
    resume.write_text("fake resume content")
    return str(resume)


@pytest.fixture
def tmp_cover_letter(tmp_path):
    """Create a temporary cover letter file."""
    cl = tmp_path / "test_cover_letter.pdf"
    cl.write_text("fake cover letter content")
    return str(cl)


@pytest.fixture
def mock_driver():
    """Create a mock Selenium WebDriver."""
    driver = MagicMock()
    driver.current_url = "https://www.linkedin.com/feed/"
    driver.page_source = "<html><body>Mock page</body></html>"
    driver.find_elements.return_value = []
    driver.find_element.return_value = MagicMock()
    return driver


@pytest.fixture
def mock_browser(mock_driver):
    """Create a mock BrowserDriver wrapping a mock Selenium driver."""
    browser = MagicMock()
    browser.driver = mock_driver
    browser.current_url.return_value = "https://www.linkedin.com/feed/"
    browser.find_elements.return_value = []
    browser.find_element.return_value = MagicMock()
    browser.element_exists.return_value = False
    return browser


@pytest.fixture
def mock_form_filler():
    """Create a mock FormFiller."""
    filler = MagicMock()
    filler.answer_text_question.return_value = "Test Answer"
    filler.answer_choice_question.return_value = "Option A"
    return filler


@pytest.fixture
def mock_captcha_solver():
    """Create a mock CaptchaSolver."""
    solver = MagicMock()
    solver.enabled = True
    solver.detect_captcha.return_value = None
    solver.solve.return_value = True
    return solver


@pytest.fixture
def sample_job():
    """Create a sample Job object."""
    from src.platforms.base import Job
    return Job(
        job_id="12345",
        title="Software Engineer",
        company="Test Corp",
        location="Remote",
        url="https://www.linkedin.com/jobs/view/12345",
        description="Test job description",
        platform="linkedin",
    )


@pytest.fixture
def sample_config():
    """Create a sample config dict."""
    return {
        "personal": {
            "name": "Test User",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone": "+1-555-555-5555",
            "location": "Remote",
            "city": "Dallas",
            "state": "TX",
            "zip_code": "75001",
            "country": "United States",
            "linkedin_url": "https://linkedin.com/in/testuser",
            "github_url": "https://github.com/testuser",
            "website": "",
            "current_company": "",
            "resume_path": "",
        },
        "search": {
            "keywords": {"include": ["python developer"], "exclude": ["senior"]},
            "locations": ["Dallas, TX"],
            "experience_levels": ["entry"],
            "job_types": ["full_time"],
        },
        "platforms": {
            "linkedin": {
                "enabled": True,
                "username": "test@example.com",
                "password": "testpass",
            },
        },
        "ai": {
            "deepseek_api_key": "",
            "job_scoring_threshold": 0.6,
            "models": {},
        },
        "safety": {
            "dry_run": True,
            "max_applications_per_day": 50,
            "delay_between_apps_seconds": [1, 2],
            "session_break_after": 15,
            "session_break_minutes": [1, 2],
            "active_hours": ["00:00", "23:59"],
            "conservative_mode": True,
        },
        "database": {
            "path": "data/test_applications.db",
            "export_csv": False,
        },
        "captcha": {},
        "company_boards": [],
        "application_urls": [],
    }
