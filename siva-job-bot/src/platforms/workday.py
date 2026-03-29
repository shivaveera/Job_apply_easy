"""Workday ATS platform implementation.

Workday uses React controlled components with data-automation-id attributes
as primary selectors. Custom dropdowns (not native <select>) require
click-open → wait-for-listbox → click-option pattern.
"""

from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.ai.form_filler import FormFiller
from src.browser.driver import BrowserDriver
from src.platforms.base import BasePlatform, Job
from src.utils.humanizer import human_delay
from src.utils.logger import log

# Workday selectors keyed by data-automation-id
WORKDAY_SELECTORS = {
    # Application form fields
    "first_name": "[data-automation-id='legalNameSection_firstName']",
    "last_name": "[data-automation-id='legalNameSection_lastName']",
    "email": "[data-automation-id='email']",
    "phone_device_type": "[data-automation-id='phone-device-type']",
    "phone_number": "[data-automation-id='phone-number']",
    "address_line1": "[data-automation-id='addressSection_addressLine1']",
    "city": "[data-automation-id='addressSection_city']",
    "state": "[data-automation-id='addressSection_countryRegion']",
    "zip_code": "[data-automation-id='addressSection_postalCode']",
    "country": "[data-automation-id='addressSection_country']",
    # Resume upload
    "resume_upload": "[data-automation-id='file-upload-input-ref']",
    "resume_drop": "[data-automation-id='dragDropRegion']",
    # Source / how did you hear
    "source": "[data-automation-id='source']",
    "source_dropdown": "[data-automation-id='sourceSection'] [data-automation-id='multiselectInputContainer']",
    # Navigation
    "apply_button": "[data-automation-id='applyButton']",
    "next_button": "[data-automation-id='bottom-navigation-next-button']",
    "submit_button": "[data-automation-id='submit']",
    "previous_button": "[data-automation-id='bottom-navigation-previous-button']",
    # Account
    "create_account_email": "[data-automation-id='createAccountEmail']",
    "create_account_password": "[data-automation-id='createAccountPassword']",
    "sign_in_email": "[data-automation-id='signInEmailAddress']",
    "sign_in_password": "[data-automation-id='signInPassword']",
    "sign_in_button": "[data-automation-id='signInSubmitButton']",
    "create_account_submit": "[data-automation-id='createAccountSubmitButton']",
    # Work experience
    "add_work_experience": "[data-automation-id='Add Work Experience']",
    "job_title": "[data-automation-id='jobTitle']",
    "company_name": "[data-automation-id='company']",
    "work_from": "[data-automation-id='formField-startDate']",
    "work_to": "[data-automation-id='formField-endDate']",
    "role_description": "[data-automation-id='description']",
    # Education
    "add_education": "[data-automation-id='Add Education']",
    "school_name": "[data-automation-id='school']",
    "degree": "[data-automation-id='degree']",
    "field_of_study": "[data-automation-id='field-of-study']",
    "gpa": "[data-automation-id='gpa']",
    # EEO / voluntary disclosure
    "gender": "[data-automation-id='gender']",
    "ethnicity": "[data-automation-id='ethnicityDropdown']",
    "veteran_status": "[data-automation-id='veteranStatus']",
    "disability_status": "[data-automation-id='disabilityStatus']",
    # Custom questions container
    "questionnaire": "[data-automation-id='questionnaire']",
}

# Workday custom dropdown: not a <select>, uses listbox pattern
WORKDAY_DROPDOWN_LISTBOX = "[data-automation-id='selectWidget'] [role='listbox']"
WORKDAY_DROPDOWN_OPTION = "[role='option']"


class WorkdayPlatform(BasePlatform):
    """Workday ATS application automation.

    Handles Workday's React-based forms using data-automation-id attributes,
    custom dropdowns, and multi-step application flow.
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
        """Login or create account on Workday career site."""
        # Try sign-in first
        try:
            email_el = self.browser.find_element(
                By.CSS_SELECTOR, WORKDAY_SELECTORS["sign_in_email"], timeout=5
            )
            self.browser.set_react_value(email_el, username)
            human_delay(0.3, 0.6)

            pass_el = self.browser.find_element(
                By.CSS_SELECTOR, WORKDAY_SELECTORS["sign_in_password"], timeout=3
            )
            self.browser.set_react_value(pass_el, password)
            human_delay(0.3, 0.6)

            sign_in = self.browser.find_element(
                By.CSS_SELECTOR, WORKDAY_SELECTORS["sign_in_button"], timeout=3
            )
            self.browser.click(sign_in)
            human_delay(3.0, 5.0)

            log.info("Workday sign-in attempted")
            return True
        except Exception:
            log.debug("Workday sign-in form not found, may not require login")
            return True

    def is_logged_in(self) -> bool:
        return True

    def search_jobs(self, config: dict) -> list[Job]:
        return []  # Workday jobs are applied via direct URL

    def apply_to_job(self, job: Job) -> bool:
        """Apply to a Workday job posting."""
        try:
            self.browser.get(job.url)
            human_delay(2.0, 4.0)

            # Click Apply button if present
            self._click_apply_button()

            # Fill application form (multi-step)
            max_steps = 10
            for step in range(max_steps):
                human_delay(1.0, 2.0)

                # Fill current page fields
                self._fill_current_page()

                # Check for submit
                if self._try_submit():
                    log.info(f"Workday application submitted: {job.title}")
                    return True

                # Try next
                if not self._click_next():
                    break

                human_delay(1.5, 3.0)

            log.warning(f"Workday form completion unclear for: {job.title}")
            return False

        except Exception as e:
            log.error(f"Workday application error: {e}")
            return False

    def _click_apply_button(self) -> None:
        """Click the initial Apply button on the job posting page."""
        try:
            btn = self.browser.find_element(
                By.CSS_SELECTOR, WORKDAY_SELECTORS["apply_button"], timeout=5
            )
            self.browser.click(btn)
            human_delay(2.0, 4.0)
        except Exception:
            log.debug("No Workday Apply button found (may already be in form)")

    def _fill_current_page(self) -> None:
        """Fill all fields on the current Workday form page."""
        self._fill_personal_info()
        self._fill_resume_upload()
        self._fill_work_experience()
        self._fill_education()
        self._fill_questionnaire()
        self._fill_eeo()

    def _fill_personal_info(self) -> None:
        """Fill personal information fields."""
        field_map = {
            "first_name": self.personal.get("first_name", self.personal.get("name", "").split()[0] if self.personal.get("name") else ""),
            "last_name": self.personal.get("last_name", self.personal.get("name", "").split()[-1] if self.personal.get("name") else ""),
            "email": self.personal.get("email", ""),
            "phone_number": self.personal.get("phone", ""),
            "address_line1": self.personal.get("address", ""),
            "city": self.personal.get("city", ""),
            "zip_code": self.personal.get("zip_code", ""),
        }

        for field_key, value in field_map.items():
            if not value:
                continue
            selector = WORKDAY_SELECTORS.get(field_key, "")
            if not selector:
                continue
            try:
                el = self.browser.driver.find_element(By.CSS_SELECTOR, selector)
                if el.is_displayed() and not el.get_attribute("value"):
                    self.browser.set_react_value(el, value)
                    human_delay(0.2, 0.5)
            except Exception:
                continue

        # Country dropdown (custom Workday dropdown)
        country = self.personal.get("country", "United States")
        if country:
            self._select_workday_dropdown(
                WORKDAY_SELECTORS["country"], country
            )

    def _fill_resume_upload(self) -> None:
        """Upload resume via file input."""
        resume_path = self.personal.get("resume_path", "")
        if not resume_path:
            return

        try:
            upload = self.browser.driver.find_element(
                By.CSS_SELECTOR, WORKDAY_SELECTORS["resume_upload"]
            )
            upload.send_keys(resume_path)
            human_delay(2.0, 4.0)
            log.debug("Workday resume uploaded")
        except Exception:
            log.debug("No Workday resume upload field on this page")

    def _set_workday_field(self, field_key: str, value: str) -> None:
        """Set a Workday form field by its selector key."""
        selector = WORKDAY_SELECTORS.get(field_key, "")
        if not selector or not value:
            return
        try:
            el = self.browser.driver.find_element(By.CSS_SELECTOR, selector)
            if el.is_displayed():
                self.browser.set_react_value(el, value)
                human_delay(0.2, 0.5)
        except Exception:
            pass

    def _fill_work_experience(self) -> None:
        """Fill work experience section if present using AI form filler."""
        try:
            add_btn = self.browser.driver.find_element(
                By.CSS_SELECTOR, WORKDAY_SELECTORS["add_work_experience"]
            )
        except Exception:
            return

        # Check if work experience already exists
        existing = self.browser.driver.find_elements(
            By.CSS_SELECTOR, WORKDAY_SELECTORS["job_title"]
        )
        if existing and any(el.get_attribute("value") for el in existing):
            log.debug("Work experience already populated, skipping")
            return

        if not self.form_filler:
            log.debug("No form filler available for work experience")
            return

        try:
            self.browser.click(add_btn)
            human_delay(1.0, 2.0)

            job_title = self.form_filler.answer_text_question("What is your most recent job title?")
            self._set_workday_field("job_title", job_title)

            company = self.form_filler.answer_text_question("What is your most recent employer/company name?")
            self._set_workday_field("company_name", company)

            try:
                desc_el = self.browser.driver.find_element(
                    By.CSS_SELECTOR, WORKDAY_SELECTORS["role_description"]
                )
                if desc_el.is_displayed():
                    description = self.form_filler.answer_text_question(
                        "Briefly describe your responsibilities in your most recent role"
                    )
                    self.browser.set_react_textarea_value(desc_el, description)
            except Exception:
                pass

            log.info("Workday work experience filled")
        except Exception as e:
            log.warning(f"Failed to fill work experience: {e}")

    def _fill_education(self) -> None:
        """Fill education section if present using answer profile data."""
        try:
            add_btn = self.browser.driver.find_element(
                By.CSS_SELECTOR, WORKDAY_SELECTORS["add_education"]
            )
        except Exception:
            return

        # Check if education already exists
        existing = self.browser.driver.find_elements(
            By.CSS_SELECTOR, WORKDAY_SELECTORS["school_name"]
        )
        if existing and any(el.get_attribute("value") for el in existing):
            log.debug("Education already populated, skipping")
            return

        if not self.form_filler:
            return

        try:
            self.browser.click(add_btn)
            human_delay(1.0, 2.0)

            school = self.form_filler.answer_text_question("What school/university did you attend?")
            self._set_workday_field("school_name", school)

            # Degree dropdown
            degree = self.form_filler.answer_text_question("What is your highest degree? (e.g., Bachelor's)")
            self._select_workday_dropdown(WORKDAY_SELECTORS["degree"], degree)

            field_of_study = self.form_filler.answer_text_question("What was your field of study/major?")
            self._set_workday_field("field_of_study", field_of_study)

            gpa = self.form_filler.answer_text_question("What was your GPA?")
            if gpa:
                self._set_workday_field("gpa", gpa)

            log.info("Workday education filled")
        except Exception as e:
            log.warning(f"Failed to fill education: {e}")

    def _fill_questionnaire(self) -> None:
        """Fill custom questionnaire fields using AI form filler."""
        try:
            questionnaire = self.browser.driver.find_element(
                By.CSS_SELECTOR, WORKDAY_SELECTORS["questionnaire"]
            )
        except Exception:
            return

        if not self.form_filler:
            return

        # Text inputs in questionnaire
        inputs = questionnaire.find_elements(By.CSS_SELECTOR, "input[type='text']")
        for inp in inputs:
            try:
                if not inp.is_displayed() or inp.get_attribute("value"):
                    continue
                label = self._get_workday_field_label(inp)
                if label:
                    answer = self.form_filler.answer_text_question(label)
                    self.browser.set_react_value(inp, answer)
                    human_delay(0.2, 0.5)
            except Exception:
                continue

        # Textareas in questionnaire
        textareas = questionnaire.find_elements(By.TAG_NAME, "textarea")
        for ta in textareas:
            try:
                if not ta.is_displayed() or ta.get_attribute("value"):
                    continue
                label = self._get_workday_field_label(ta)
                if label:
                    answer = self.form_filler.answer_text_question(label)
                    self.browser.set_react_textarea_value(ta, answer)
                    human_delay(0.2, 0.5)
            except Exception:
                continue

        # Dropdowns (custom Workday selects) in questionnaire
        dropdowns = questionnaire.find_elements(
            By.CSS_SELECTOR, "[data-automation-id='multiselectInputContainer']"
        )
        for dd in dropdowns:
            try:
                if not dd.is_displayed():
                    continue
                label = self._get_workday_field_label(dd)
                if label:
                    self._handle_workday_questionnaire_dropdown(dd, label)
            except Exception:
                continue

    def _fill_eeo(self) -> None:
        """Fill EEO / voluntary disclosure fields with 'Decline to self-identify'."""
        eeo_fields = {
            "gender": "Decline to Self Identify",
            "ethnicity": "Decline to Self Identify",
            "veteran_status": "I don't wish to answer",
            "disability_status": "I don't wish to answer",
        }

        for field_key, default_value in eeo_fields.items():
            selector = WORKDAY_SELECTORS.get(field_key, "")
            if selector:
                self._select_workday_dropdown(selector, default_value)

    def _select_workday_dropdown(self, trigger_selector: str, target_text: str) -> bool:
        """Select an option from a Workday custom dropdown.

        Pattern: click trigger → wait for listbox → find option → click option.
        """
        try:
            trigger = self.browser.driver.find_element(
                By.CSS_SELECTOR, trigger_selector
            )
            if not trigger.is_displayed():
                return False

            self.browser.click(trigger)
            human_delay(0.5, 1.0)

            # Wait for listbox to appear
            WebDriverWait(self.browser.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='listbox']"))
            )

            options = self.browser.driver.find_elements(
                By.CSS_SELECTOR, "[role='listbox'] [role='option']"
            )

            target_lower = target_text.lower()
            for opt in options:
                if target_lower in opt.text.strip().lower():
                    self.browser.click(opt)
                    human_delay(0.3, 0.6)
                    return True

            # If exact match not found, try partial match
            for opt in options:
                opt_text = opt.text.strip().lower()
                if any(word in opt_text for word in target_lower.split()):
                    self.browser.click(opt)
                    human_delay(0.3, 0.6)
                    return True

            # Close dropdown if no match
            trigger.send_keys("\x1b")  # Escape
            return False

        except Exception as e:
            log.debug(f"Workday dropdown selection failed: {e}")
            return False

    def _handle_workday_questionnaire_dropdown(self, dropdown_el, label: str) -> None:
        """Handle a dropdown in the questionnaire section using AI."""
        try:
            self.browser.click(dropdown_el)
            human_delay(0.5, 1.0)

            WebDriverWait(self.browser.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='listbox']"))
            )

            options_els = self.browser.driver.find_elements(
                By.CSS_SELECTOR, "[role='listbox'] [role='option']"
            )
            options = [opt.text.strip() for opt in options_els if opt.text.strip()]

            if options and self.form_filler:
                chosen = self.form_filler.answer_choice_question(label, options)
                for opt_el in options_els:
                    if opt_el.text.strip() == chosen:
                        self.browser.click(opt_el)
                        return

            dropdown_el.send_keys("\x1b")
        except Exception as e:
            log.debug(f"Workday questionnaire dropdown error: {e}")

    def _get_workday_field_label(self, element) -> str:
        """Extract the label for a Workday form field."""
        try:
            # Try data-automation-id based label
            parent = element.find_element(By.XPATH, "./ancestor::*[@data-automation-id][1]")
            label_el = parent.find_element(By.CSS_SELECTOR, "label")
            if label_el.text.strip():
                return label_el.text.strip()
        except Exception:
            pass

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

        return ""

    def _try_submit(self) -> bool:
        """Try to find and click the Workday submit button."""
        try:
            submit = self.browser.find_element(
                By.CSS_SELECTOR, WORKDAY_SELECTORS["submit_button"], timeout=2
            )
            if submit.is_displayed():
                self.browser.click(submit)
                human_delay(2.0, 4.0)
                return True
        except Exception:
            pass
        return False

    def _click_next(self) -> bool:
        """Click the Next button on the Workday form."""
        try:
            btn = self.browser.find_element(
                By.CSS_SELECTOR, WORKDAY_SELECTORS["next_button"], timeout=3
            )
            if btn.is_displayed():
                self.browser.click(btn)
                human_delay(1.5, 3.0)
                return True
        except Exception:
            pass
        return False

    def close(self) -> None:
        pass
