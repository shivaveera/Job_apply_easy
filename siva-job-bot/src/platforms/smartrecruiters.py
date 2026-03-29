"""SmartRecruiters ATS platform implementation.

SmartRecruiters uses standard HTML forms at jobs.smartrecruiters.com.
Forms include standard fields plus custom screening questions.
"""

from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from src.ai.form_filler import FormFiller
from src.browser.driver import BrowserDriver
from src.platforms.base import BasePlatform, Job
from src.utils.humanizer import human_delay
from src.utils.logger import log

SR_SELECTORS = {
    "first_name": "input[name='firstName'], #firstName",
    "last_name": "input[name='lastName'], #lastName",
    "email": "input[name='email'], #email",
    "phone": "input[name='phoneNumber'], #phoneNumber",
    "resume": "input[type='file']",
    "location": "input[name='location'], #location",
    "linkedin": "input[name='web.linkedin'], input[name*='linkedin']",
    "submit": "button[type='submit'], .apply-btn",
    "apply_button": "a.apply-btn, button.apply-btn, a[href*='/apply']",
    "consent_checkbox": "input[name='consent'], input[type='checkbox'][name*='consent']",
}


class SmartRecruitersPlatform(BasePlatform):
    """SmartRecruiters ATS application automation."""

    def __init__(
        self,
        browser: BrowserDriver,
        form_filler: Optional[FormFiller] = None,
        personal_info: dict = None,
    ):
        self.browser = browser
        self.form_filler = form_filler
        self.personal = personal_info or {}

    def login(self, username: str, password: str) -> bool:
        return True

    def is_logged_in(self) -> bool:
        return True

    def search_jobs(self, config: dict) -> list[Job]:
        return []

    def apply_to_job(self, job: Job) -> bool:
        """Fill and submit a SmartRecruiters application."""
        try:
            self.browser.get(job.url)
            human_delay(2.0, 4.0)

            # Click Apply if on job detail page
            try:
                btn = self.browser.find_element(
                    By.CSS_SELECTOR, SR_SELECTORS["apply_button"], timeout=3
                )
                self.browser.click(btn)
                human_delay(1.5, 3.0)
            except Exception:
                pass

            filled = 0
            name = self.personal.get("name", "")

            # Standard fields
            field_map = {
                "first_name": self.personal.get("first_name", name.split()[0] if name else ""),
                "last_name": self.personal.get("last_name", name.split()[-1] if name else ""),
                "email": self.personal.get("email", ""),
                "phone": self.personal.get("phone", ""),
                "location": self.personal.get("location", ""),
                "linkedin": self.personal.get("linkedin_url", ""),
            }

            for key, value in field_map.items():
                if not value:
                    continue
                try:
                    el = self.browser.find_element(
                        By.CSS_SELECTOR, SR_SELECTORS[key], timeout=2
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
                        By.CSS_SELECTOR, SR_SELECTORS["resume"]
                    )
                    upload.send_keys(resume_path)
                    filled += 1
                    human_delay(1.0, 2.0)
                except Exception:
                    pass

            # Consent checkbox
            try:
                cb = self.browser.driver.find_element(
                    By.CSS_SELECTOR, SR_SELECTORS["consent_checkbox"]
                )
                if not cb.is_selected():
                    self.browser.click(cb)
            except Exception:
                pass

            # Custom questions via form filler
            if self.form_filler:
                filled += self._fill_custom_questions()

            if filled > 0:
                try:
                    submit = self.browser.find_element(
                        By.CSS_SELECTOR, SR_SELECTORS["submit"], timeout=5
                    )
                    self.browser.click(submit)
                    human_delay(2.0, 4.0)
                except Exception:
                    pass
                log.info(f"SmartRecruiters application submitted: {job.title}")
                return True

            return False

        except Exception as e:
            log.error(f"SmartRecruiters error: {e}")
            return False

    def _fill_custom_questions(self) -> int:
        """Fill custom screening questions."""
        filled = 0
        try:
            inputs = self.browser.driver.find_elements(
                By.CSS_SELECTOR,
                "input[type='text']:not([name='firstName']):not([name='lastName'])"
                ":not([name='email']):not([name='phoneNumber'])"
            )
            for inp in inputs:
                try:
                    if not inp.is_displayed() or inp.get_attribute("value"):
                        continue
                    label = self._get_label(inp)
                    if label:
                        answer = self.form_filler.answer_text_question(label)
                        self.browser.type_text(inp, answer)
                        filled += 1
                except Exception:
                    continue
        except Exception:
            pass
        return filled

    def _get_label(self, element) -> str:
        try:
            el_id = element.get_attribute("id")
            if el_id:
                labels = self.browser.driver.find_elements(
                    By.CSS_SELECTOR, f"label[for='{el_id}']"
                )
                if labels:
                    return labels[0].text.strip()
        except Exception:
            pass
        try:
            parent = element.find_element(By.XPATH, "./..")
            lbl = parent.find_element(By.TAG_NAME, "label")
            return lbl.text.strip()
        except Exception:
            pass
        return ""

    def close(self) -> None:
        pass
