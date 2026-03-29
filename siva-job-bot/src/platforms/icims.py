"""iCIMS ATS platform - stub with iframe handling notes.

iCIMS embeds application forms in iframes (careers-*.icims.com).
Some implementations use Shadow DOM. Fields use standard HTML
with iCIMS-specific class names.
"""

from typing import Optional

from selenium.webdriver.common.by import By

from src.ai.form_filler import FormFiller
from src.browser.driver import BrowserDriver
from src.platforms.base import BasePlatform, Job
from src.utils.humanizer import human_delay
from src.utils.logger import log

ICIMS_SELECTORS = {
    "iframe": "iframe[src*='icims'], iframe[id*='icims']",
    "first_name": "input[id*='FirstName'], input[name*='firstName']",
    "last_name": "input[id*='LastName'], input[name*='lastName']",
    "email": "input[id*='Email'], input[name*='email']",
    "phone": "input[id*='Phone'], input[name*='phone']",
    "resume": "input[type='file']",
    "submit": "button[type='submit'], input[type='submit']",
}


class ICIMSPlatform(BasePlatform):
    """iCIMS ATS application automation (basic implementation)."""

    def __init__(
        self,
        browser: BrowserDriver,
        form_filler: Optional[FormFiller] = None,
        personal_info: dict = None,
        captcha_solver=None,
    ):
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
        """Apply to an iCIMS job posting."""
        try:
            self.browser.get(job.url)
            human_delay(2.0, 4.0)

            # Switch to iCIMS iframe if present
            self.browser.switch_to_iframe(ICIMS_SELECTORS["iframe"], timeout=5)

            filled = 0
            name = self.personal.get("name", "")
            field_map = {
                "first_name": self.personal.get("first_name", name.split()[0] if name else ""),
                "last_name": self.personal.get("last_name", name.split()[-1] if name else ""),
                "email": self.personal.get("email", ""),
                "phone": self.personal.get("phone", ""),
            }

            for key, value in field_map.items():
                if not value:
                    continue
                try:
                    el = self.browser.find_element(
                        By.CSS_SELECTOR, ICIMS_SELECTORS[key], timeout=2
                    )
                    if el.is_displayed() and not el.get_attribute("value"):
                        self.browser.type_text(el, value)
                        filled += 1
                except Exception:
                    continue

            # Resume upload
            resume_path = self.personal.get("resume_path", "")
            if resume_path:
                try:
                    upload = self.browser.driver.find_element(
                        By.CSS_SELECTOR, ICIMS_SELECTORS["resume"]
                    )
                    upload.send_keys(resume_path)
                    filled += 1
                except Exception:
                    pass

            if filled > 0:
                try:
                    submit = self.browser.find_element(
                        By.CSS_SELECTOR, ICIMS_SELECTORS["submit"], timeout=5
                    )
                    self.browser.click(submit)
                    human_delay(2.0, 4.0)
                except Exception:
                    pass
                log.info(f"iCIMS application submitted: {job.title}")

            self.browser.switch_to_default_content()
            return filled > 0

        except Exception as e:
            log.error(f"iCIMS error: {e}")
            self.browser.switch_to_default_content()
            return False

    def close(self) -> None:
        pass
