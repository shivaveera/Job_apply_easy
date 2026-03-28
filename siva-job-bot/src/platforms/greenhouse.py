"""Greenhouse ATS platform - stub implementation for future development."""

from src.platforms.base import BasePlatform, Job
from src.utils.logger import log


class GreenhousePlatform(BasePlatform):
    """Greenhouse ATS application automation (stub).

    TODO: Implement Greenhouse-specific application logic.
    Greenhouse uses a standardized application form across many companies.
    """

    def __init__(self, browser, form_filler=None):
        self.browser = browser
        self.form_filler = form_filler

    def login(self, username: str, password: str) -> bool:
        log.warning("Greenhouse platform not yet implemented")
        return False

    def is_logged_in(self) -> bool:
        return False

    def search_jobs(self, config: dict) -> list[Job]:
        log.warning("Greenhouse search not yet implemented")
        return []

    def apply_to_job(self, job: Job) -> bool:
        log.warning("Greenhouse apply not yet implemented")
        return False

    def close(self) -> None:
        pass
