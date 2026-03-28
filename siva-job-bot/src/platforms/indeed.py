"""Indeed job platform - stub implementation for future development."""

from src.platforms.base import BasePlatform, Job
from src.utils.logger import log


class IndeedPlatform(BasePlatform):
    """Indeed job application automation (stub).

    TODO: Implement Indeed-specific job search and application logic.
    """

    def __init__(self, browser, form_filler=None):
        self.browser = browser
        self.form_filler = form_filler

    def login(self, username: str, password: str) -> bool:
        log.warning("Indeed platform not yet implemented")
        return False

    def is_logged_in(self) -> bool:
        return False

    def search_jobs(self, config: dict) -> list[Job]:
        log.warning("Indeed search not yet implemented")
        return []

    def apply_to_job(self, job: Job) -> bool:
        log.warning("Indeed apply not yet implemented")
        return False

    def close(self) -> None:
        pass
