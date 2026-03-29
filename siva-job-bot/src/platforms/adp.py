"""ADP Workforce Now ATS platform - stub with Shadow DOM notes.

ADP career pages may use Shadow DOM and Web Components.
The browser driver's pierce_shadow_dom() method can penetrate these.
"""

from src.ai.form_filler import FormFiller
from src.browser.driver import BrowserDriver
from src.platforms.base import BasePlatform, Job
from src.utils.logger import log


class ADPPlatform(BasePlatform):
    """ADP Workforce Now application automation (stub)."""

    def __init__(self, browser: BrowserDriver, form_filler: FormFiller = None, personal_info: dict = None):
        self.browser = browser
        self.form_filler = form_filler
        self.personal = personal_info or {}

    def login(self, username: str, password: str) -> bool:
        log.info("ADP: basic implementation - login not fully supported")
        return True

    def is_logged_in(self) -> bool:
        return True

    def search_jobs(self, config: dict) -> list[Job]:
        return []

    def apply_to_job(self, job: Job) -> bool:
        log.info(f"ADP: would apply to {job.title} - routing to universal filler")
        return False

    def close(self) -> None:
        pass
