"""Indeed job platform implementation.

Indeed uses nested iframes for its application flow:
1. Parent page contains a modal iframe
2. Inside modal iframe, a 'resumeapply' iframe contains the actual form
3. Form fields use 'ia-' and 'ifl-' prefixed selectors

Requires careful iframe switching to interact with form elements.
"""

from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from src.ai.form_filler import FormFiller
from src.browser.driver import BrowserDriver
from src.platforms.base import BasePlatform, Job
from src.utils.humanizer import human_delay
from src.utils.logger import log

# Indeed selectors
INDEED_SELECTORS = {
    # Apply button on job page
    "apply_button": "#indeedApplyButton, button[id*='indeedApply'], .ia-IndeedApplyButton",
    # Modal and iframe
    "modal_iframe": "iframe[id*='indeedapply'], iframe[src*='indeedapply']",
    "resume_iframe": "iframe[src*='resumeapply'], iframe[name*='resumeapply']",
    # Form fields (inside iframe)
    "name": "#ia-FirstAndLastName, input[id*='ia-FirstAndLastName'], input[name='applicant.name']",
    "email": "#ia-EmailAddress, input[id*='ia-EmailAddress'], input[name='applicant.email']",
    "phone": "#ia-PhoneNumber, input[id*='ia-PhoneNumber'], input[name='applicant.phoneNumber']",
    "resume_upload": "input[type='file'][id*='resume'], input[type='file'][name*='resume']",
    "cover_letter": "textarea[id*='cover-letter'], textarea[name*='coverLetter']",
    # Location fields
    "city": "#ia-city, input[id*='ia-city']",
    "state": "#ia-state, select[id*='ia-state']",
    # Navigation
    "continue_button": "button[id*='ia-continue'], button.ia-continueButton, a.ia-continueButton",
    "submit_button": "button[id*='ia-submit'], button.ia-submitButton",
    # Questions
    "question_container": ".ia-Questions, .ifl-Questions, div[id*='questions']",
    "question_text_input": "input[id^='ia-'][type='text'], input[id^='ifl-'][type='text']",
    "question_textarea": "textarea[id^='ia-'], textarea[id^='ifl-']",
    "question_select": "select[id^='ia-'], select[id^='ifl-']",
    "question_radio": "input[id^='ia-'][type='radio'], input[id^='ifl-'][type='radio']",
}


class IndeedPlatform(BasePlatform):
    """Indeed job application automation.

    Handles Indeed's nested-iframe application flow with ia-/ifl- prefixed selectors.
    """

    BASE_URL = "https://www.indeed.com"

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
        """Login to Indeed."""
        self.browser.get(f"{self.BASE_URL}/account/login")
        human_delay(2.0, 4.0)

        try:
            email = self.browser.find_element(
                By.CSS_SELECTOR, "input[type='email'], #login-email-input", timeout=5
            )
            self.browser.type_text(email, username)
            human_delay(0.5, 1.0)

            # Indeed may show password on next page
            submit = self.browser.find_element(
                By.CSS_SELECTOR, "button[type='submit']", timeout=3
            )
            self.browser.click(submit)
            human_delay(2.0, 4.0)

            # Password page
            try:
                pass_field = self.browser.find_element(
                    By.CSS_SELECTOR, "input[type='password'], #login-password-input", timeout=5
                )
                self.browser.type_text(pass_field, password)
                submit = self.browser.find_element(
                    By.CSS_SELECTOR, "button[type='submit']", timeout=3
                )
                self.browser.click(submit)
                human_delay(3.0, 5.0)
            except Exception:
                pass  # May use alternative auth

            log.info("Indeed login attempted")
            return True
        except Exception as e:
            log.error(f"Indeed login error: {e}")
            return False

    def is_logged_in(self) -> bool:
        try:
            return "indeed.com" in self.browser.current_url()
        except Exception:
            return False

    def search_jobs(self, config: dict) -> list[Job]:
        """Search Indeed for jobs."""
        jobs = []
        keywords = config.get("keywords", {}).get("include", [])
        locations = config.get("locations", [""])

        for location in locations:
            for keyword in keywords:
                query_url = (
                    f"{self.BASE_URL}/jobs?"
                    f"q={keyword.replace(' ', '+')}"
                    f"&l={location.replace(' ', '+')}"
                )

                posted_hours = config.get("posted_within_hours", 0)
                if posted_hours <= 24:
                    query_url += "&fromage=1"
                elif posted_hours <= 72:
                    query_url += "&fromage=3"
                elif posted_hours <= 168:
                    query_url += "&fromage=7"

                page_jobs = self._search_page(query_url)
                jobs.extend(page_jobs)
                log.info(f"Indeed: found {len(page_jobs)} jobs for '{keyword}' in '{location}'")
                human_delay(2.0, 4.0)

        return jobs

    def _search_page(self, url: str) -> list[Job]:
        """Extract jobs from a single Indeed search results page."""
        jobs = []
        self.browser.get(url)
        human_delay(2.0, 4.0)

        try:
            cards = self.browser.find_elements(
                By.CSS_SELECTOR,
                ".job_seen_beacon, .jobsearch-ResultsList > li, div[data-jk]",
                timeout=5,
            )

            for card in cards:
                try:
                    job_id = card.get_attribute("data-jk") or ""
                    if not job_id:
                        link = card.find_element(By.CSS_SELECTOR, "a[data-jk]")
                        job_id = link.get_attribute("data-jk") or ""
                    if not job_id:
                        continue

                    title_el = card.find_element(
                        By.CSS_SELECTOR, ".jobTitle a, h2.jobTitle span"
                    )
                    title = title_el.text.strip()

                    company = ""
                    try:
                        company_el = card.find_element(
                            By.CSS_SELECTOR, ".companyName, [data-testid='company-name']"
                        )
                        company = company_el.text.strip()
                    except Exception:
                        pass

                    location = ""
                    try:
                        loc_el = card.find_element(
                            By.CSS_SELECTOR, ".companyLocation, [data-testid='text-location']"
                        )
                        location = loc_el.text.strip()
                    except Exception:
                        pass

                    job_url = f"{self.BASE_URL}/viewjob?jk={job_id}"
                    jobs.append(Job(
                        job_id=job_id,
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        platform="indeed",
                    ))
                except Exception:
                    continue
        except Exception:
            pass

        return jobs

    def apply_to_job(self, job: Job) -> bool:
        """Apply to an Indeed job with nested iframe handling."""
        try:
            self.browser.get(job.url)
            human_delay(2.0, 4.0)

            # Click Apply Now button
            try:
                apply_btn = self.browser.find_element(
                    By.CSS_SELECTOR, INDEED_SELECTORS["apply_button"], timeout=5
                )
                self.browser.click(apply_btn)
                human_delay(2.0, 4.0)
            except Exception:
                log.debug("No Indeed Apply button found")
                return False

            # Switch into the Indeed Apply iframe(s)
            if not self._switch_to_apply_iframe():
                log.warning("Could not switch to Indeed apply iframe")
                return False

            # Fill multi-step form
            max_steps = 8
            for step in range(max_steps):
                human_delay(1.0, 2.0)

                self._fill_current_step()

                # Check for submit
                if self._try_submit():
                    self.browser.switch_to_default_content()
                    log.info(f"Indeed application submitted: {job.title}")
                    return True

                # Try continue/next
                if not self._click_continue():
                    break

                human_delay(1.0, 2.0)

            self.browser.switch_to_default_content()
            log.warning(f"Indeed form incomplete for: {job.title}")
            return False

        except Exception as e:
            log.error(f"Indeed application error: {e}")
            self.browser.switch_to_default_content()
            return False

    def _switch_to_apply_iframe(self) -> bool:
        """Switch into the nested Indeed Apply iframes.

        Indeed nests: page → modal iframe → resumeapply iframe.
        """
        # Try modal iframe first
        if self.browser.switch_to_iframe(INDEED_SELECTORS["modal_iframe"], timeout=5):
            # Try nested resume apply iframe
            if self.browser.switch_to_iframe(INDEED_SELECTORS["resume_iframe"], timeout=3):
                return True
            # May already be in the right frame
            return True

        # Try direct resume apply iframe
        if self.browser.switch_to_iframe(INDEED_SELECTORS["resume_iframe"], timeout=5):
            return True

        # Check if form is directly on page (no iframe)
        try:
            self.browser.find_element(
                By.CSS_SELECTOR, INDEED_SELECTORS["name"], timeout=3
            )
            return True
        except Exception:
            pass

        return False

    def _fill_current_step(self) -> None:
        """Fill all fields on the current Indeed form step."""
        self._fill_personal_info()
        self._upload_resume()
        self._fill_questions()

    def _fill_personal_info(self) -> None:
        """Fill name, email, phone fields."""
        name = self.personal.get("name", "")
        field_map = {
            "name": name,
            "email": self.personal.get("email", ""),
            "phone": self.personal.get("phone", ""),
            "city": self.personal.get("city", ""),
        }

        for field_key, value in field_map.items():
            if not value:
                continue
            selector = INDEED_SELECTORS.get(field_key, "")
            try:
                el = self.browser.find_element(By.CSS_SELECTOR, selector, timeout=2)
                if el.is_displayed() and not el.get_attribute("value"):
                    self.browser.type_text(el, value)
                    human_delay(0.2, 0.5)
            except Exception:
                continue

    def _upload_resume(self) -> None:
        """Upload resume file."""
        resume_path = self.personal.get("resume_path", "")
        if not resume_path:
            return

        try:
            upload = self.browser.driver.find_element(
                By.CSS_SELECTOR, INDEED_SELECTORS["resume_upload"]
            )
            upload.send_keys(resume_path)
            human_delay(1.5, 3.0)
        except Exception:
            pass

    def _fill_questions(self) -> None:
        """Fill custom screening questions using AI form filler."""
        if not self.form_filler:
            return

        # Text inputs
        try:
            inputs = self.browser.driver.find_elements(
                By.CSS_SELECTOR, INDEED_SELECTORS["question_text_input"]
            )
            for inp in inputs:
                try:
                    if not inp.is_displayed() or inp.get_attribute("value"):
                        continue
                    label = self._get_field_label(inp)
                    if label:
                        answer = self.form_filler.answer_text_question(label)
                        self.browser.type_text(inp, answer)
                except Exception:
                    continue
        except Exception:
            pass

        # Textareas
        try:
            textareas = self.browser.driver.find_elements(
                By.CSS_SELECTOR, INDEED_SELECTORS["question_textarea"]
            )
            for ta in textareas:
                try:
                    if not ta.is_displayed() or ta.get_attribute("value"):
                        continue
                    label = self._get_field_label(ta)
                    if label:
                        answer = self.form_filler.answer_text_question(label)
                        self.browser.type_text(ta, answer)
                except Exception:
                    continue
        except Exception:
            pass

        # Selects
        try:
            selects = self.browser.driver.find_elements(
                By.CSS_SELECTOR, INDEED_SELECTORS["question_select"]
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
                except Exception:
                    continue
        except Exception:
            pass

        # Radio buttons
        try:
            radio_groups = {}
            radios = self.browser.driver.find_elements(
                By.CSS_SELECTOR, INDEED_SELECTORS["question_radio"]
            )
            for radio in radios:
                name = radio.get_attribute("name") or ""
                if name not in radio_groups:
                    radio_groups[name] = []
                radio_groups[name].append(radio)

            for name, group_radios in radio_groups.items():
                if any(r.is_selected() for r in group_radios):
                    continue  # Already answered
                label = self._get_field_label(group_radios[0])
                options = []
                for r in group_radios:
                    try:
                        opt_label = r.find_element(By.XPATH, "./following-sibling::label | ../label")
                        options.append(opt_label.text.strip())
                    except Exception:
                        options.append(r.get_attribute("value") or "")

                if label and options and self.form_filler:
                    chosen = self.form_filler.answer_choice_question(label, options)
                    for i, opt in enumerate(options):
                        if opt == chosen:
                            self.browser.click(group_radios[i])
                            break
        except Exception:
            pass

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
            parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'question') or contains(@class, 'field')][1]")
            label = parent.find_element(By.CSS_SELECTOR, "label, span.label, .ia-question-text")
            if label.text.strip():
                return label.text.strip()
        except Exception:
            pass

        try:
            aria = element.get_attribute("aria-label")
            if aria:
                return aria.strip()
        except Exception:
            pass

        return ""

    def _try_submit(self) -> bool:
        """Try to find and click the submit button."""
        try:
            btn = self.browser.find_element(
                By.CSS_SELECTOR, INDEED_SELECTORS["submit_button"], timeout=2
            )
            if btn.is_displayed():
                self.browser.click(btn)
                human_delay(2.0, 4.0)
                return True
        except Exception:
            pass
        return False

    def _click_continue(self) -> bool:
        """Click the Continue button."""
        try:
            btn = self.browser.find_element(
                By.CSS_SELECTOR, INDEED_SELECTORS["continue_button"], timeout=3
            )
            if btn.is_displayed():
                self.browser.click(btn)
                human_delay(1.0, 2.0)
                return True
        except Exception:
            pass
        return False

    def close(self) -> None:
        pass
