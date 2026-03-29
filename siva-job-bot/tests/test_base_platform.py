"""Tests for base platform interface."""

import pytest
from src.platforms.base import BasePlatform, Job


class TestJob:
    """Tests for the Job dataclass."""

    def test_job_creation_minimal(self):
        job = Job(job_id="1", title="Dev", company="Acme")
        assert job.job_id == "1"
        assert job.title == "Dev"
        assert job.company == "Acme"
        assert job.url == ""
        assert job.platform == ""

    def test_job_creation_full(self):
        job = Job(
            job_id="123",
            title="SWE",
            company="Google",
            location="Remote",
            url="https://example.com/123",
            description="A job",
            work_type="remote",
            salary_info="100k",
            posted_date="2026-01-01",
            apply_method="easy_apply",
            recruiter_name="Alice",
            recruiter_url="https://linkedin.com/in/alice",
            platform="linkedin",
        )
        assert job.location == "Remote"
        assert job.salary_info == "100k"
        assert job.platform == "linkedin"


class TestBasePlatformSignature:
    """Tests that BasePlatform.apply_to_job accepts resume and cover letter paths."""

    def test_apply_to_job_signature(self):
        """Verify the abstract method accepts resume_path and cover_letter_path."""
        import inspect
        sig = inspect.signature(BasePlatform.apply_to_job)
        params = list(sig.parameters.keys())
        assert "resume_path" in params
        assert "cover_letter_path" in params

    def test_apply_to_job_defaults(self):
        """Verify default values for file paths are empty strings."""
        import inspect
        sig = inspect.signature(BasePlatform.apply_to_job)
        assert sig.parameters["resume_path"].default == ""
        assert sig.parameters["cover_letter_path"].default == ""
