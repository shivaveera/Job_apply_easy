"""Lever ATS platform implementation.

Lever uses standard HTML forms with name-based selectors:
name, email, phone, org, urls[LinkedIn], resume, comments, cards[][field0], etc.
"""

from typing import Optional

from selenium.webdriver.common.by import By

from src.ai.form_filler import FormFiller
from src.browser.driver import BrowserDriver
from src.platforms.base import BasePlatform, Job
from src.utils.humanizer import human_delay
from src.utils.logger import log

LEVER_SELECTORS = {
    "name": "input[name='name']",
    "email": "input[name='email']",
    "phone": "input[name='phone']",
    "org": "input[name='org']",
    "linkedin": "input[name='urls[LinkedIn]']",
    "github": "input[name='urls[GitHub]']",
    "portfolio": "input[name='urls[Portfolio]']",
    "other_url": "input[name='urls[Other]']",
    "resume": "input[name='resume'], input[type='file']",
    "comments": "textarea[name='comments']",
    "submit": "button[type='submit'], .postings-btn-submit, .template-btn-submit",
    "apply_form": ".posting-apply, .application-form, form.postings-form",
    # Custom question fields
    "custom_text": "input[name^='cards['][type='text']",
    "custom_textarea": "textarea[name^='cards[']",
    "custom_select": "select[name^='cards[']",
}


class LeverPlatform(BasePlatform):
    """Lever ATS application automation.

    Handles Lever's standardized job application forms.
    """

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
        return True  # Lever doesn't require login

    def is_logged_in(self) -> bool:
        return True

    def search_jobs(self, config: dict) -> list[Job]:
        return []  # Applied via direct URL

    def apply_to_job(self, job: Job) -> bool:
        """Fill and submit a Lever application form."""
        try:
            self.browser.get(job.url)
            human_delay(2.0, 4.0)

            # Navigate to apply page if on job posting page
            self._navigate_to_apply()

            if not self.browser.element_exists(
                By.CSS_SELECTOR, LEVER_SELECTORS["apply_form"], timeout=5
            ):
                log.warning("Lever application form not found")
                return False

            filled = 0
            filled += self._fill_personal_info()
            filled += self._upload_resume()
            filled += self._fill_urls()
            filled += self._fill_comments(job)
            filled += self._fill_custom_questions()

            if filled > 0:
                self._submit()
                log.info(f"Lever application submitted: {job.title}")
                return True

            log.warning("No fields filled on Lever form")
            return False

        except Exception as e:
            log.error(f"Lever application error: {e}")
            return False

    def _navigate_to_apply(self) -> None:
        """Click Apply button if on the job details page."""
        try:
            apply_btn = self.browser.find_element(
                By.CSS_SELECTOR,
                "a.posting-btn-submit, a[href*='/apply'], .postings-btn",
                timeout=3,
            )
            self.browser.click(apply_btn)
            human_delay(1.5, 3.0)
        except Exception:
            pass  # May already be on apply page

    def _fill_personal_info(self) -> int:
        """Fill standard personal info fields."""
        filled = 0
        name = self.personal.get("name", "")
        field_map = {
            "name": name,
            "email": self.personal.get("email", ""),
            "phone": self.personal.get("phone", ""),
            "org": self.personal.get("current_company", ""),
        }

        for field_key, value in field_map.items():
            if not value:
                continue
            selector = LEVER_SELECTORS.get(field_key, "")
            try:
                el = self.browser.find_element(By.CSS_SELECTOR, selector, timeout=2)
                if el.is_displayed() and not el.get_attribute("value"):
                    self.browser.type_text(el, value)
                    filled += 1
                    human_delay(0.2, 0.5)
            except Exception:
                continue

        return filled

    def _upload_resume(self) -> int:
        """Upload resume file."""
        resume_path = self.personal.get("resume_path", "")
        if not resume_path:
            return 0

        try:
            upload = self.browser.driver.find_element(
                By.CSS_SELECTOR, LEVER_SELECTORS["resume"]
            )
            upload.send_keys(resume_path)
            human_delay(1.0, 2.0)
            return 1
        except Exception:
            return 0

    def _fill_urls(self) -> int:
        """Fill URL fields (LinkedIn, GitHub, Portfolio)."""
        filled = 0
        url_map = {
            "linkedin": self.personal.get("linkedin_url", ""),
            "github": self.personal.get("github_url", ""),
            "portfolio": self.personal.get("website", ""),
        }

        for field_key, value in url_map.items():
            if not value:
                continue
            try:
                el = self.browser.find_element(
                    By.CSS_SELECTOR, LEVER_SELECTORS[field_key], timeout=2
                )
                if el.is_displayed() and not el.get_attribute("value"):
                    self.browser.type_text(el, value)
                    filled += 1
            except Exception:
                continue

        return filled

    def _fill_comments(self, job: Job) -> int:
        """Fill the comments/additional info textarea."""
        try:
            ta = self.browser.find_element(
                By.CSS_SELECTOR, LEVER_SELECTORS["comments"], timeout=2
            )
            if not ta.is_displayed() or ta.get_attribute("value"):
                return 0

            if self.form_filler:
                answer = self.form_filler.answer_text_question(
                    f"Additional information or cover note for {job.title} at {job.company}"
                )
                self.browser.type_text(ta, answer)
                return 1
        except Exception:
            pass
        return 0

    def _fill_custom_questions(self) -> int:
        """Fill Lever custom card-based questions using AI."""
        if not self.form_filler:
            return 0

        filled = 0

        # Text inputs
        try:
            inputs = self.browser.driver.find_elements(
                By.CSS_SELECTOR, LEVER_SELECTORS["custom_text"]
            )
            for inp in inputs:
                try:
                    if not inp.is_displayed() or inp.get_attribute("value"):
                        continue
                    label = self._get_field_label(inp)
                    if label:
                        answer = self.form_filler.answer_text_question(label)
                        self.browser.type_text(inp, answer)
                        filled += 1
                except Exception:
                    continue
        except Exception:
            pass

        # Textareas
        try:
            textareas = self.browser.driver.find_elements(
                By.CSS_SELECTOR, LEVER_SELECTORS["custom_textarea"]
            )
            for ta in textareas:
                try:
                    if not ta.is_displayed() or ta.get_attribute("value"):
                        continue
                    label = self._get_field_label(ta)
                    if label:
                        answer = self.form_filler.answer_text_question(label)
                        self.browser.type_text(ta, answer)
                        filled += 1
                except Exception:
                    continue
        except Exception:
            pass

        # Select dropdowns
        try:
            from selenium.webdriver.support.ui import Select
            selects = self.browser.driver.find_elements(
                By.CSS_SELECTOR, LEVER_SELECTORS["custom_select"]
            )
            for sel_el in selects:
                try:
                    if not sel_el.is_displayed():
                        continue
                    select = Select(sel_el)
                    current = select.first_selected_option.text.strip()
                    if current and current not in ["", "Select", "-- Select --"]:
                        continue
                    label = self._get_field_label(sel_el)
                    options = [opt.text.strip() for opt in select.options if opt.text.strip()]
                    if label and len(options) > 1:
                        chosen = self.form_filler.answer_choice_question(label, options)
                        select.select_by_visible_text(chosen)
                        filled += 1
                except Exception:
                    continue
        except Exception:
            pass

        return filled

    def _get_field_label(self, element) -> str:
        """Extract the label for a form element."""
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
            parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'application-question')]")
            label = parent.find_element(By.CSS_SELECTOR, "label, .question-label, div.text")
            if label.text.strip():
                return label.text.strip()
        except Exception:
            pass

        try:
            parent = element.find_element(By.XPATH, "./..")
            for tag in ["label", "span", "legend", "div.text"]:
                try:
                    lbl = parent.find_element(By.CSS_SELECTOR, tag)
                    if lbl.text.strip():
                        return lbl.text.strip()
                except Exception:
                    pass
        except Exception:
            pass

        return ""

    def _submit(self) -> None:
        """Click the submit button."""
        try:
            btn = self.browser.find_element(
                By.CSS_SELECTOR, LEVER_SELECTORS["submit"], timeout=5
            )
            self.browser.click(btn)
            human_delay(2.0, 4.0)
        except Exception as e:
            log.debug(f"Lever submit button not found: {e}")

    def close(self) -> None:
        pass
