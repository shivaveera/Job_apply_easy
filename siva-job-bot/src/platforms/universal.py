"""Universal form filler for unknown/unsupported ATS platforms.

Uses multi-signal heuristic field classification to identify form fields
by name, id, placeholder, aria-label, autocomplete, and associated label text.
Falls back to LLM for unrecognized custom questions.
"""

from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from src.ai.form_filler import FormFiller
from src.platforms.base import BasePlatform, Job
from src.utils.humanizer import human_delay
from src.utils.logger import log

# Multi-signal heuristic field patterns
FIELD_PATTERNS: dict[str, list[str]] = {
    "first_name": [
        "first name", "first_name", "firstname", "given name", "fname",
        "givenname", "legal_first",
    ],
    "last_name": [
        "last name", "last_name", "lastname", "surname", "family name",
        "lname", "familyname", "legal_last",
    ],
    "full_name": [
        "full name", "full_name", "fullname", "your name", "candidate name",
    ],
    "email": [
        "email", "e-mail", "email_address", "emailaddress", "e_mail",
    ],
    "phone": [
        "phone", "telephone", "mobile", "cell", "phone_number",
        "phonenumber", "tel", "contact number",
    ],
    "address": [
        "address", "street", "address_line", "addressline", "street_address",
    ],
    "city": ["city", "town", "municipality"],
    "state": [
        "state", "province", "region", "state_province",
    ],
    "zip_code": [
        "zip", "postal", "zip_code", "zipcode", "postal_code", "postalcode",
    ],
    "country": ["country", "nation"],
    "resume": [
        "resume", "cv", "curriculum vitae", "upload resume", "attach resume",
    ],
    "cover_letter": [
        "cover letter", "cover_letter", "coverletter", "covering letter",
    ],
    "linkedin_url": [
        "linkedin", "linkedin url", "linkedin profile",
    ],
    "website": [
        "website", "portfolio", "personal site", "url", "homepage",
    ],
    "github": ["github", "github url", "github profile"],
    "salary": [
        "salary", "compensation", "desired salary", "expected salary",
        "salary expectation", "pay",
    ],
    "start_date": [
        "start date", "available date", "availability", "when can you start",
        "earliest start",
    ],
    "experience_years": [
        "years of experience", "years experience", "experience years",
        "how many years", "total experience",
    ],
    "work_authorization": [
        "authorized to work", "work authorization", "legally authorized",
        "right to work", "eligible to work",
    ],
    "sponsorship": [
        "sponsorship", "visa sponsor", "require sponsorship",
        "need sponsorship", "immigration",
    ],
    "referral": [
        "how did you hear", "referral", "source", "where did you hear",
        "how did you find",
    ],
    "gender": ["gender", "sex"],
    "race": ["race", "ethnicity", "racial"],
    "veteran": ["veteran", "military", "armed forces"],
    "disability": ["disability", "disabled", "handicap"],
}


def classify_field(element) -> str:
    """Classify a form field using multi-signal heuristic matching.

    Examines: name, id, placeholder, aria-label, autocomplete,
    and associated label text to determine field purpose.
    """
    signals = []
    for attr in ["name", "id", "placeholder", "aria-label", "autocomplete"]:
        try:
            val = element.get_attribute(attr)
            if val:
                signals.append(val)
        except Exception:
            pass

    # Try to get associated label text
    try:
        el_id = element.get_attribute("id")
        if el_id:
            labels = element.find_elements(
                By.XPATH, f"//label[@for='{el_id}']"
            )
            for lbl in labels:
                signals.append(lbl.text)
    except Exception:
        pass

    # Try parent label
    try:
        parent = element.find_element(By.XPATH, "./..")
        for tag in ["label", "span", "legend", "div"]:
            try:
                lbl = parent.find_element(By.TAG_NAME, tag)
                if lbl.text.strip():
                    signals.append(lbl.text)
            except Exception:
                pass
    except Exception:
        pass

    combined = " ".join(filter(None, signals)).lower()

    for field_type, patterns in FIELD_PATTERNS.items():
        if any(p in combined for p in patterns):
            return field_type

    return "unknown"


def get_field_label(element) -> str:
    """Extract the human-readable label for a form element."""
    # aria-label
    try:
        label = element.get_attribute("aria-label")
        if label:
            return label.strip()
    except Exception:
        pass

    # Associated label
    try:
        el_id = element.get_attribute("id")
        if el_id:
            labels = element.find_elements(By.XPATH, f"//label[@for='{el_id}']")
            if labels:
                return labels[0].text.strip()
    except Exception:
        pass

    # Parent label
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

    # Placeholder
    try:
        ph = element.get_attribute("placeholder")
        if ph:
            return ph.strip()
    except Exception:
        pass

    return ""


class UniversalFormFiller(BasePlatform):
    """Universal form filler for unknown/unsupported ATS platforms.

    Uses heuristic field classification + LLM fallback to fill any web form.
    """

    def __init__(self, browser, form_filler: Optional[FormFiller] = None, personal_info: dict = None):
        self.browser = browser
        self.form_filler = form_filler
        self.personal = personal_info or {}

    def login(self, username: str, password: str) -> bool:
        return True  # No login needed for career pages

    def is_logged_in(self) -> bool:
        return True

    def search_jobs(self, config: dict) -> list[Job]:
        return []  # Universal filler doesn't search — it fills forms at given URLs

    def fill_form_at_url(self, url: str, job: Optional[Job] = None) -> bool:
        """Navigate to a URL and fill all detected form fields.

        Args:
            url: The career page / application form URL.
            job: Optional Job context for AI-powered answers.

        Returns:
            True if form was filled successfully.
        """
        self.browser.get(url)
        human_delay(2.0, 4.0)

        filled_count = 0

        # Fill text inputs
        filled_count += self._fill_text_inputs()

        # Fill textareas
        filled_count += self._fill_textareas()

        # Fill dropdowns
        filled_count += self._fill_selects()

        # Fill file uploads
        filled_count += self._fill_file_uploads()

        # Fill checkboxes
        filled_count += self._fill_checkboxes()

        log.info(f"Universal filler: filled {filled_count} fields at {url}")
        return filled_count > 0

    def _fill_text_inputs(self) -> int:
        """Fill all text-type input fields on the page."""
        filled = 0
        inputs = self.browser.find_elements(
            By.CSS_SELECTOR,
            "input[type='text'], input[type='email'], input[type='tel'], "
            "input[type='number'], input[type='url'], input:not([type])",
            timeout=3,
        )

        for inp in inputs:
            try:
                if not inp.is_displayed() or inp.get_attribute("value"):
                    continue

                field_type = classify_field(inp)
                answer = self._get_answer_for_field(field_type, inp)

                if answer:
                    self.browser.type_text(inp, answer)
                    filled += 1
            except Exception as e:
                log.debug(f"Text input fill error: {e}")

        return filled

    def _fill_textareas(self) -> int:
        """Fill all textarea fields."""
        filled = 0
        textareas = self.browser.find_elements(By.TAG_NAME, "textarea", timeout=3)

        for ta in textareas:
            try:
                if not ta.is_displayed() or ta.get_attribute("value"):
                    continue

                field_type = classify_field(ta)
                label = get_field_label(ta)

                if field_type == "cover_letter" and self.form_filler:
                    answer = self.form_filler.answer_text_question(
                        f"Write a cover letter for: {label}"
                    )
                elif self.form_filler:
                    answer = self.form_filler.answer_text_question(label or "Additional information")
                else:
                    continue

                self.browser.type_text(ta, answer)
                filled += 1
            except Exception as e:
                log.debug(f"Textarea fill error: {e}")

        return filled

    def _fill_selects(self) -> int:
        """Fill all dropdown/select fields."""
        filled = 0
        selects = self.browser.find_elements(By.TAG_NAME, "select", timeout=3)

        for sel_el in selects:
            try:
                if not sel_el.is_displayed():
                    continue

                select = Select(sel_el)
                current = select.first_selected_option.text.strip()
                if current and current not in ["", "Select an option", "-- Select --", "Choose..."]:
                    continue

                label = get_field_label(sel_el)
                options = [opt.text.strip() for opt in select.options if opt.text.strip()]

                if not options or len(options) <= 1:
                    continue

                if self.form_filler:
                    chosen = self.form_filler.answer_choice_question(
                        label or "Select an option", options
                    )
                    select.select_by_visible_text(chosen)
                    filled += 1
                else:
                    # Default: select first non-empty option
                    for opt in select.options:
                        if opt.text.strip() and opt.text.strip() not in [
                            "Select an option", "-- Select --", "Choose..."
                        ]:
                            select.select_by_visible_text(opt.text.strip())
                            filled += 1
                            break
            except Exception as e:
                log.debug(f"Select fill error: {e}")

        return filled

    def _fill_file_uploads(self) -> int:
        """Fill file upload fields (resume, cover letter)."""
        filled = 0
        uploads = self.browser.find_elements(
            By.CSS_SELECTOR, "input[type='file']", timeout=3
        )

        for upload in uploads:
            try:
                field_type = classify_field(upload)
                if field_type == "resume":
                    resume_path = self.personal.get("resume_path", "")
                    if resume_path:
                        upload.send_keys(resume_path)
                        filled += 1
                elif field_type == "cover_letter":
                    cl_path = self.personal.get("cover_letter_path", "")
                    if cl_path:
                        upload.send_keys(cl_path)
                        filled += 1
            except Exception as e:
                log.debug(f"File upload error: {e}")

        return filled

    def _fill_checkboxes(self) -> int:
        """Fill checkbox fields (terms, acknowledgments)."""
        filled = 0
        checkboxes = self.browser.find_elements(
            By.CSS_SELECTOR, "input[type='checkbox']", timeout=3
        )

        for cb in checkboxes:
            try:
                if not cb.is_displayed() or cb.is_selected():
                    continue

                label = get_field_label(cb)
                label_lower = (label or "").lower()

                # Auto-check terms/acknowledgments
                if any(kw in label_lower for kw in [
                    "terms", "acknowledge", "agree", "confirm", "certify",
                    "consent", "accept", "i understand",
                ]):
                    self.browser.click(cb)
                    filled += 1
            except Exception:
                pass

        return filled

    def _get_answer_for_field(self, field_type: str, element) -> Optional[str]:
        """Get the answer for a classified field type."""
        personal = self.personal

        # Direct mapping from personal info
        direct_map = {
            "first_name": personal.get("first_name", personal.get("name", "").split()[0] if personal.get("name") else ""),
            "last_name": personal.get("last_name", personal.get("name", "").split()[-1] if personal.get("name") else ""),
            "full_name": personal.get("name", ""),
            "email": personal.get("email", ""),
            "phone": personal.get("phone", ""),
            "address": personal.get("address", ""),
            "city": personal.get("city", personal.get("location", "").split(",")[0].strip() if personal.get("location") else ""),
            "state": personal.get("state", ""),
            "zip_code": personal.get("zip_code", ""),
            "country": personal.get("country", "United States"),
            "linkedin_url": personal.get("linkedin_url", ""),
            "website": personal.get("website", ""),
            "github": personal.get("github_url", ""),
        }

        if field_type in direct_map and direct_map[field_type]:
            return direct_map[field_type]

        # For unknown fields, use AI
        if field_type == "unknown" and self.form_filler:
            label = get_field_label(element)
            if label:
                return self.form_filler.answer_text_question(label)

        # For classified but unmapped fields, use AI
        if self.form_filler:
            label = get_field_label(element)
            if label:
                return self.form_filler.answer_text_question(label)

        return None

    def apply_to_job(self, job: Job) -> bool:
        return self.fill_form_at_url(job.url, job)

    def close(self) -> None:
        pass
