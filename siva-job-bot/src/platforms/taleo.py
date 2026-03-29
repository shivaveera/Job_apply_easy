"""Oracle Taleo ATS platform - stub implementation.

Taleo (tbe.taleo.net / oracle.taleo.net) uses complex multi-page forms
with proprietary JavaScript. Forms load in iframes with legacy DOM structures.
"""

from src.ai.form_filler import FormFiller
from src.browser.driver import BrowserDriver
from src.platforms.base import BasePlatform, Job
from src.utils.logger import log


class TaleoPlatform(BasePlatform):
    """Oracle Taleo ATS application automation (stub)."""

    def __init__(self, browser: BrowserDriver, form_filler: FormFiller = None, personal_info: dict = None):
        self.browser = browser
        self.form_filler = form_filler
        self.personal = personal_info or {}

    def login(self, username: str, password: str) -> bool:
        log.info("Taleo: basic implementation - login not fully supported")
        return True

    def is_logged_in(self) -> bool:
        return True

    def search_jobs(self, config: dict) -> list[Job]:
        return []

    def apply_to_job(self, job: Job) -> bool:
        log.info(f"Taleo: would apply to {job.title} - routing to universal filler")
        return False

    def close(self) -> None:
        pass
