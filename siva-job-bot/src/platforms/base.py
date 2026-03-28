"""Abstract base class for all job platform implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    """Represents a job posting."""

    job_id: str
    title: str
    company: str
    location: str = ""
    url: str = ""
    description: str = ""
    work_type: str = ""  # remote, hybrid, onsite
    salary_info: str = ""
    posted_date: str = ""
    apply_method: str = ""  # easy_apply, external, etc.
    recruiter_name: str = ""
    recruiter_url: str = ""
    platform: str = ""


class BasePlatform(ABC):
    """Abstract base class for job platform automation.

    All platform implementations (LinkedIn, Indeed, Greenhouse, etc.)
    must implement these methods.
    """

    @abstractmethod
    def login(self, username: str, password: str) -> bool:
        """Authenticate with the platform.

        Returns:
            True if login successful.
        """

    @abstractmethod
    def search_jobs(self, config: dict) -> list[Job]:
        """Search for jobs matching the configuration.

        Args:
            config: Search configuration dict with keywords, location, filters.

        Returns:
            List of Job objects matching the search criteria.
        """

    @abstractmethod
    def apply_to_job(self, job: Job) -> bool:
        """Submit an application for a job.

        Args:
            job: The Job to apply to.

        Returns:
            True if application submitted successfully.
        """

    @abstractmethod
    def is_logged_in(self) -> bool:
        """Check if currently authenticated with the platform."""

    @abstractmethod
    def close(self) -> None:
        """Clean up resources."""
