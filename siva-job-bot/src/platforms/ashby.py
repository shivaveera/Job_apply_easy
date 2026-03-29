"""Ashby ATS platform - stub implementation.

Ashby (jobs.ashbyhq.com) uses modern React-based forms.
Similar to Greenhouse in structure but with React controlled components.
"""

from src.ai.form_filler import FormFiller
from src.browser.driver import BrowserDriver
from src.platforms.base import BasePlatform, Job
from src.utils.logger import log


class AshbyPlatform(BasePlatform):
    """Ashby ATS application automation (stub)."""

    def __init__(self, browser: BrowserDriver, form_filler: FormFiller = None, personal_info: dict = None, captcha_solver=None):
        self.browser = browser
        self.form_filler = form_filler
        self.personal = personal_info or {}
        self.captcha_solver = captcha_solver

    def login(self, username: str, password: str) -> bool:
        return True

    def is_logged_in(self) -> bool:
        return True

    def search_jobs(self, config: dict) -> list[Job]:
        return []

    def apply_to_job(self, job: Job) -> bool:
        log.info(f"Ashby: would apply to {job.title} - routing to universal filler")
        return False

    def close(self) -> None:
        pass
