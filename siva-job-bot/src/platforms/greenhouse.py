"""Greenhouse ATS platform implementation.

Greenhouse uses standard HTML forms with name-attribute selectors.
Forms are predictable: first_name, last_name, email, phone, resume,
cover_letter, and custom questions with question_{id} naming.
"""

from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from src.ai.form_filler import FormFiller
from src.browser.driver import BrowserDriver
from src.platforms.base import BasePlatform, Job
from src.utils.humanizer import human_delay
from src.utils.logger import log

# Greenhouse standard field selectors (name attributes)
GH_SELECTORS = {
    "first_name": "input[name='first_name'], #first_name",
    "last_name": "input[name='last_name'], #last_name",
    "email": "input[name='email'], #email",
    "phone": "input[name='phone'], #phone",
    "resume": "input[name='resume'], input[type='file'][id*='resume']",
    "cover_letter": "textarea[name='cover_letter'], #cover_letter_text",
    "linkedin": "input[name='urls[LinkedIn]'], input[name*='linkedin']",
    "website": "input[name='urls[Portfolio]'], input[name*='website'], input[name*='portfolio']",
    "github": "input[name='urls[GitHub]'], input[name*='github']",
    "location": "input[name='location'], #candidate_location",
    "submit": "input[type='submit'], button[type='submit'], #submit_app",
    "application_form": "#application_form, #greenhouse_application, form.application-form",
}

# Greenhouse custom question patterns
GH_QUESTION_SELECTOR = "[id^='question_'], [name^='question_'], .field"


class GreenhousePlatform(BasePlatform):
    """Greenhouse ATS application automation.

    Handles Greenhouse's standardized application forms with name-based selectors.
    """

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
        return True  # Greenhouse doesn't require login

    def is_logged_in(self) -> bool:
        return True

    def search_jobs(self, config: dict) -> list[Job]:
        return []  # Applied via direct URL

    def apply_to_job(self, job: Job) -> bool:
        """Fill and submit a Greenhouse application form."""
        try:
            self.browser.get(job.url)
            human_delay(2.0, 4.0)

            # Verify we're on a Greenhouse form
            if not self.browser.element_exists(
                By.CSS_SELECTOR, GH_SELECTORS["application_form"], timeout=5
            ):
                log.warning("Greenhouse application form not found")
                return False

            filled = 0

            # Fill standard fields
            filled += self._fill_personal_info()

            # Upload resume
            filled += self._upload_resume()

            # Fill cover letter
            filled += self._fill_cover_letter(job)

            # Fill URL fields (LinkedIn, GitHub, etc.)
            filled += self._fill_urls()

            # Fill custom questions
            filled += self._fill_custom_questions()

            # Fill select dropdowns
            filled += self._fill_selects()

            # Submit
            if filled > 0:
                self._submit()
                log.info(f"Greenhouse application submitted: {job.title}")
                return True

            log.warning("No fields filled on Greenhouse form")
            return False

        except Exception as e:
            log.error(f"Greenhouse application error: {e}")
            return False

    def _fill_personal_info(self) -> int:
        """Fill standard personal info fields."""
        filled = 0
        name = self.personal.get("name", "")
        field_map = {
            "first_name": self.personal.get("first_name", name.split()[0] if name else ""),
            "last_name": self.personal.get("last_name", name.split()[-1] if name else ""),
            "email": self.personal.get("email", ""),
            "phone": self.personal.get("phone", ""),
            "location": self.personal.get("location", ""),
        }

        for field_key, value in field_map.items():
            if not value:
                continue
            selector = GH_SELECTORS.get(field_key, "")
            if not selector:
                continue
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
                By.CSS_SELECTOR, GH_SELECTORS["resume"]
            )
            upload.send_keys(resume_path)
            human_delay(1.0, 2.0)
            log.debug("Greenhouse resume uploaded")
            return 1
        except Exception:
            return 0

    def _fill_cover_letter(self, job: Job) -> int:
        """Fill cover letter textarea."""
        try:
            cl_el = self.browser.find_element(
                By.CSS_SELECTOR, GH_SELECTORS["cover_letter"], timeout=2
            )
            if not cl_el.is_displayed() or cl_el.get_attribute("value"):
                return 0

            if self.form_filler:
                answer = self.form_filler.answer_text_question(
                    f"Write a brief cover letter for {job.title} at {job.company}"
                )
                self.browser.type_text(cl_el, answer)
                return 1
        except Exception:
            pass
        return 0

    def _fill_urls(self) -> int:
        """Fill LinkedIn, GitHub, website URL fields."""
        filled = 0
        url_map = {
            "linkedin": self.personal.get("linkedin_url", ""),
            "github": self.personal.get("github_url", ""),
            "website": self.personal.get("website", ""),
        }

        for field_key, value in url_map.items():
            if not value:
                continue
            selector = GH_SELECTORS.get(field_key, "")
            if not selector:
                continue
            try:
                el = self.browser.find_element(By.CSS_SELECTOR, selector, timeout=2)
                if el.is_displayed() and not el.get_attribute("value"):
                    self.browser.type_text(el, value)
                    filled += 1
            except Exception:
                continue

        return filled

    def _fill_custom_questions(self) -> int:
        """Fill Greenhouse custom questions using AI form filler."""
        if not self.form_filler:
            return 0

        filled = 0

        # Text inputs with question_ prefix
        try:
            inputs = self.browser.driver.find_elements(
                By.CSS_SELECTOR,
                "input[id^='question_'][type='text'], input[name^='question_']"
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

        # Textareas with question_ prefix
        try:
            textareas = self.browser.driver.find_elements(
                By.CSS_SELECTOR,
                "textarea[id^='question_'], textarea[name^='question_']"
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

        return filled

    def _fill_selects(self) -> int:
        """Fill dropdown/select fields."""
        filled = 0
        try:
            selects = self.browser.driver.find_elements(By.TAG_NAME, "select")
            for sel_el in selects:
                try:
                    if not sel_el.is_displayed():
                        continue
                    select = Select(sel_el)
                    current = select.first_selected_option.text.strip()
                    if current and current not in ["", "Select", "-- Select --", "Choose..."]:
                        continue

                    label = self._get_field_label(sel_el)
                    options = [opt.text.strip() for opt in select.options if opt.text.strip()]

                    if len(options) <= 1:
                        continue

                    if self.form_filler and label:
                        chosen = self.form_filler.answer_choice_question(label, options)
                        select.select_by_visible_text(chosen)
                        filled += 1
                    else:
                        for opt in select.options:
                            if opt.text.strip() and opt.text.strip() not in [
                                "Select", "-- Select --", "Choose..."
                            ]:
                                select.select_by_visible_text(opt.text.strip())
                                filled += 1
                                break
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
            parent = element.find_element(By.XPATH, "./..")
            for tag in ["label", "span", "legend"]:
                try:
                    lbl = parent.find_element(By.TAG_NAME, tag)
                    if lbl.text.strip():
                        return lbl.text.strip()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            placeholder = element.get_attribute("placeholder")
            if placeholder:
                return placeholder.strip()
        except Exception:
            pass

        return ""

    def _submit(self) -> None:
        """Click the submit button."""
        try:
            btn = self.browser.find_element(
                By.CSS_SELECTOR, GH_SELECTORS["submit"], timeout=5
            )
            self.browser.click(btn)
            human_delay(2.0, 4.0)
        except Exception as e:
            log.debug(f"Greenhouse submit button not found: {e}")

    def close(self) -> None:
        pass
