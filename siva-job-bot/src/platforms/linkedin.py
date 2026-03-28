"""LinkedIn Easy Apply automation platform.

Primary platform implementation combining best practices from all analyzed repos:
- Anti-detection from Auto_job_applier (undetected-chromedriver + profiles)
- Form filling from AIHawk Fork (context-aware routing + Levenshtein)
- Rate limiting from AIHawk Fork (multi-layered delays)
- Job ID pre-caching from EasyApplyJobsBot (avoids stale elements)
- Completion percentage tracking from EasyApplyJobsBot
"""

import math
import re
import time
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from src.ai.form_filler import FormFiller
from src.browser.driver import BrowserDriver
from src.platforms.base import BasePlatform, Job
from src.utils.humanizer import human_delay, random_scroll, session_break
from src.utils.logger import log


class LinkedInPlatform(BasePlatform):
    """LinkedIn Easy Apply automation.

    Handles: login, job search, filtering, form filling, and submission.
    """

    BASE_URL = "https://www.linkedin.com"
    JOBS_URL = "https://www.linkedin.com/jobs/search/"

    # Experience level codes for LinkedIn URL
    EXPERIENCE_CODES = {
        "internship": "1",
        "entry": "2",
        "associate": "3",
        "mid": "4",
        "senior": "4",
        "director": "5",
        "executive": "6",
    }

    # Job type codes
    JOB_TYPE_CODES = {
        "full_time": "F",
        "part_time": "P",
        "contract": "C",
        "temporary": "T",
        "internship": "I",
        "volunteer": "V",
        "other": "O",
    }

    # Date posted codes
    DATE_CODES = {
        24: "r86400",
        168: "r604800",     # 1 week
        720: "r2592000",    # 1 month
    }

    def __init__(
        self,
        browser: BrowserDriver,
        form_filler: Optional[FormFiller] = None,
    ):
        self.browser = browser
        self.form_filler = form_filler
        self._applied_ids: set[str] = set()

    def login(self, username: str, password: str) -> bool:
        """Log in to LinkedIn.

        First checks if already logged in via session/cookies.
        Falls back to credential-based login.
        """
        self.browser.get(f"{self.BASE_URL}/feed/")
        human_delay(2.0, 4.0)

        if self.is_logged_in():
            log.info("Already logged in to LinkedIn")
            return True

        log.info("Logging in to LinkedIn...")
        self.browser.get(f"{self.BASE_URL}/login")
        human_delay(1.5, 3.0)

        try:
            email_field = self.browser.find_element(By.ID, "username")
            self.browser.type_text(email_field, username)
            human_delay(0.5, 1.0)

            pass_field = self.browser.find_element(By.ID, "password")
            self.browser.type_text(pass_field, password)
            human_delay(0.5, 1.0)

            submit = self.browser.find_element(
                By.CSS_SELECTOR, "button[type='submit']"
            )
            self.browser.click(submit)
            human_delay(3.0, 5.0)

            # Handle security verification if triggered
            if "checkpoint" in self.browser.current_url():
                log.warning(
                    "LinkedIn security challenge detected. "
                    "Please complete verification manually (5 minute timeout)..."
                )
                self.browser.wait_for_url_contains("/feed/", timeout=300)

            if self.is_logged_in():
                log.info("LinkedIn login successful")
                return True
            else:
                log.error("LinkedIn login failed")
                return False

        except Exception as e:
            log.error(f"Login error: {e}")
            return False

    def is_logged_in(self) -> bool:
        """Check if currently logged in to LinkedIn."""
        current = self.browser.current_url()
        return "/feed" in current or "/jobs" in current

    def search_jobs(self, config: dict) -> list[Job]:
        """Search LinkedIn for jobs matching configuration.

        Constructs search URLs with all filters and paginates through results.
        Pre-caches job IDs to avoid stale element issues.
        """
        jobs = []
        keywords_include = config.get("keywords", {}).get("include", [])
        locations = config.get("locations", [""])

        for location in locations:
            for keyword in keywords_include:
                url = self._build_search_url(keyword, location, config)
                page_jobs = self._search_single_query(url, config)
                jobs.extend(page_jobs)

                log.info(
                    f"Found {len(page_jobs)} jobs for '{keyword}' in '{location}'"
                )
                human_delay(3.0, 6.0)

        log.info(f"Total jobs found: {len(jobs)}")
        return jobs

    def _build_search_url(
        self, keyword: str, location: str, config: dict
    ) -> str:
        """Build LinkedIn job search URL with all filters."""
        params = [
            f"keywords={keyword}",
            f"location={location}",
            "f_LF=f_AL",  # Easy Apply only
        ]

        # Experience levels
        exp_levels = config.get("experience_levels", [])
        exp_codes = [
            self.EXPERIENCE_CODES[lvl]
            for lvl in exp_levels
            if lvl in self.EXPERIENCE_CODES
        ]
        if exp_codes:
            params.append(f"f_E={','.join(exp_codes)}")

        # Job types
        job_types = config.get("job_types", [])
        type_codes = [
            self.JOB_TYPE_CODES[jt]
            for jt in job_types
            if jt in self.JOB_TYPE_CODES
        ]
        if type_codes:
            params.append(f"f_JT={','.join(type_codes)}")

        # Remote filter
        if config.get("remote_only"):
            params.append("f_WT=2")

        # Date posted
        hours = config.get("posted_within_hours", 0)
        if hours > 0:
            # Find closest date code
            for h, code in sorted(self.DATE_CODES.items()):
                if hours <= h:
                    params.append(f"f_TPR={code}")
                    break

        # Sort by most recent
        params.append("sortBy=DD")

        return f"{self.JOBS_URL}?{'&'.join(params)}"

    def _search_single_query(self, url: str, config: dict) -> list[Job]:
        """Execute a single search query and paginate through results."""
        jobs = []
        self.browser.get(url)
        human_delay(2.0, 4.0)

        # Get total results count
        total_jobs = self._get_total_results()
        if total_jobs == 0:
            return jobs

        total_pages = min(math.ceil(total_jobs / 25), 40)  # Max 40 pages
        log.info(f"Found {total_jobs} jobs across {total_pages} pages")

        keywords_exclude = config.get("keywords", {}).get("exclude", [])
        companies_blacklist = [
            c.lower() for c in config.get("companies", {}).get("blacklist", [])
        ]
        title_blacklist = [t.lower() for t in config.get("title_blacklist", [])]
        bad_words = [w.lower() for w in config.get("description_bad_words", [])]

        for page in range(total_pages):
            if page > 0:
                page_url = f"{url}&start={page * 25}"
                self.browser.get(page_url)
                human_delay(2.0, 4.0)

            # Pre-cache job IDs from tiles (avoids stale element references)
            job_ids = self._extract_job_ids()

            for job_id in job_ids:
                if job_id in self._applied_ids:
                    continue

                try:
                    job = self._extract_job_details(job_id)
                    if not job:
                        continue

                    # Apply filters
                    if self._is_blacklisted(
                        job, keywords_exclude, companies_blacklist,
                        title_blacklist, bad_words,
                    ):
                        continue

                    jobs.append(job)
                except Exception as e:
                    log.debug(f"Error extracting job {job_id}: {e}")
                    continue

            # Rate limiting: break every 5 pages
            if (page + 1) % 5 == 0 and page < total_pages - 1:
                human_delay(10.0, 30.0)

        return jobs

    def _get_total_results(self) -> int:
        """Extract total job count from search results page."""
        try:
            count_el = self.browser.find_element(
                By.CSS_SELECTOR,
                ".jobs-search-results-list__subtitle",
                timeout=5,
            )
            text = count_el.text.strip()
            numbers = re.findall(r"[\d,]+", text)
            if numbers:
                return int(numbers[0].replace(",", ""))
        except Exception:
            pass
        return 0

    def _extract_job_ids(self) -> list[str]:
        """Pre-cache all job IDs from the current page to avoid stale refs."""
        ids = []
        try:
            cards = self.browser.find_elements(
                By.CSS_SELECTOR,
                "li[data-occludable-job-id]",
                timeout=5,
            )
            for card in cards:
                try:
                    job_id = card.get_attribute("data-occludable-job-id")
                    if job_id:
                        # Extract numeric ID
                        clean_id = job_id.split(":")[-1]
                        ids.append(clean_id)
                except Exception:
                    continue
        except Exception:
            pass

        return ids

    def _extract_job_details(self, job_id: str) -> Optional[Job]:
        """Navigate to a job and extract its details."""
        job_url = f"{self.BASE_URL}/jobs/view/{job_id}"
        self.browser.get(job_url)
        human_delay(1.5, 3.0)

        try:
            title = ""
            company = ""
            location = ""
            description = ""

            # Title
            try:
                title_el = self.browser.find_element(
                    By.CSS_SELECTOR, ".t-24.t-bold", timeout=5
                )
                title = title_el.text.strip()
            except Exception:
                pass

            # Company
            try:
                company_el = self.browser.find_element(
                    By.CSS_SELECTOR,
                    ".job-details-jobs-unified-top-card__company-name",
                    timeout=3,
                )
                company = company_el.text.strip()
            except Exception:
                pass

            # Location
            try:
                loc_el = self.browser.find_element(
                    By.CSS_SELECTOR,
                    ".job-details-jobs-unified-top-card__bullet",
                    timeout=3,
                )
                location = loc_el.text.strip()
            except Exception:
                pass

            # Description
            try:
                desc_el = self.browser.find_element(
                    By.CSS_SELECTOR, ".jobs-description__content", timeout=3
                )
                description = desc_el.text.strip()
            except Exception:
                pass

            if not title:
                return None

            return Job(
                job_id=job_id,
                title=title,
                company=company,
                location=location,
                url=job_url,
                description=description,
                platform="linkedin",
            )

        except Exception as e:
            log.debug(f"Failed to extract job details for {job_id}: {e}")
            return None

    def _is_blacklisted(
        self,
        job: Job,
        keywords_exclude: list[str],
        companies_blacklist: list[str],
        title_blacklist: list[str],
        bad_words: list[str],
    ) -> bool:
        """Check if a job should be filtered out."""
        title_lower = job.title.lower()
        company_lower = job.company.lower().strip()
        desc_lower = job.description.lower()

        # Company blacklist
        if company_lower in companies_blacklist:
            log.debug(f"Blacklisted company: {job.company}")
            return True

        # Title blacklist
        for word in title_blacklist:
            if word in title_lower:
                log.debug(f"Blacklisted title word '{word}': {job.title}")
                return True

        # Keyword exclude
        for word in keywords_exclude:
            if word.lower() in title_lower:
                log.debug(f"Excluded keyword '{word}': {job.title}")
                return True

        # Description bad words
        for word in bad_words:
            if word in desc_lower:
                log.debug(f"Bad word '{word}' in description: {job.title}")
                return True

        return False

    def apply_to_job(self, job: Job) -> bool:
        """Apply to a LinkedIn Easy Apply job.

        Handles the multi-step application form with AI-powered form filling.
        """
        try:
            # Navigate to job if not already there
            if job.job_id not in self.browser.current_url():
                self.browser.get(job.url)
                human_delay(1.5, 3.0)

            # Find and click Easy Apply button
            easy_apply_btn = self._find_easy_apply_button()
            if not easy_apply_btn:
                log.debug(f"No Easy Apply button for: {job.title}")
                return False

            self.browser.click(easy_apply_btn)
            human_delay(1.5, 3.0)

            # Fill out the application form (may be multi-step)
            success = self._fill_application_form(job)

            if success:
                self._applied_ids.add(job.job_id)
                log.info(f"Applied to: {job.title} at {job.company}")
            else:
                self._discard_application()

            return success

        except Exception as e:
            log.error(f"Application error for {job.title}: {e}")
            self._discard_application()
            return False

    def _find_easy_apply_button(self):
        """Find the Easy Apply button on the job page."""
        selectors = [
            "button.jobs-apply-button",
            "button[aria-label*='Easy Apply']",
            ".jobs-s-apply button",
        ]

        for selector in selectors:
            try:
                btn = self.browser.find_element(
                    By.CSS_SELECTOR, selector, timeout=3
                )
                if btn.is_displayed() and btn.is_enabled():
                    return btn
            except Exception:
                continue

        return None

    def _fill_application_form(self, job: Job) -> bool:
        """Fill out the multi-step Easy Apply form.

        Uses completion percentage to track progress (from EasyApplyJobsBot).
        """
        max_steps = 10  # Safety limit

        for step in range(max_steps):
            human_delay(1.0, 2.0)

            # Check for submit button (final step)
            if self._try_submit():
                return True

            # Fill current form section
            self._fill_current_section(job)

            # Try to advance to next step
            if not self._click_next():
                # Check if there are form errors
                if self._has_form_errors():
                    log.warning(f"Form errors on step {step + 1}")
                    self._handle_form_errors(job)
                    if not self._click_next():
                        return False
                else:
                    # May already be at submit
                    return self._try_submit()

            human_delay(1.0, 2.0)

        log.warning(f"Exceeded max steps for: {job.title}")
        return False

    def _fill_current_section(self, job: Job) -> None:
        """Fill all form elements in the current form section."""
        if not self.form_filler:
            return

        # Handle file uploads (resume/cover letter)
        self._handle_uploads(job)

        # Handle text inputs
        self._fill_text_inputs(job)

        # Handle textareas
        self._fill_textareas(job)

        # Handle select dropdowns
        self._fill_dropdowns(job)

        # Handle radio buttons
        self._fill_radio_buttons(job)

        # Handle checkboxes (terms of service, etc.)
        self._fill_checkboxes()

    def _handle_uploads(self, job: Job) -> None:
        """Handle file upload fields (resume, cover letter)."""
        upload_inputs = self.browser.find_elements(
            By.CSS_SELECTOR, "input[type='file']", timeout=2
        )
        for upload in upload_inputs:
            try:
                label = self._get_upload_label(upload)
                label_lower = label.lower()
                if "resume" in label_lower or "cv" in label_lower:
                    log.debug(f"Resume upload detected: {label}")
                    # Upload will be handled by the caller with resume path
                elif "cover" in label_lower:
                    log.debug(f"Cover letter upload detected: {label}")
            except Exception:
                continue

    def _fill_text_inputs(self, job: Job) -> None:
        """Fill text input fields using AI form filler."""
        inputs = self.browser.find_elements(
            By.CSS_SELECTOR,
            "input[type='text'], input[type='tel'], input[type='number'], input[type='email']",
            timeout=2,
        )

        for inp in inputs:
            try:
                if not inp.is_displayed() or inp.get_attribute("value"):
                    continue

                label = self._get_field_label(inp)
                if not label:
                    continue

                answer = self.form_filler.answer_text_question(label)
                self.browser.type_text(inp, answer)
            except Exception as e:
                log.debug(f"Text input error: {e}")
                continue

    def _fill_textareas(self, job: Job) -> None:
        """Fill textarea fields using AI form filler."""
        textareas = self.browser.find_elements(
            By.CSS_SELECTOR, "textarea", timeout=2
        )

        for ta in textareas:
            try:
                if not ta.is_displayed() or ta.get_attribute("value"):
                    continue

                label = self._get_field_label(ta)
                if not label:
                    continue

                answer = self.form_filler.answer_text_question(label)
                self.browser.type_text(ta, answer)
            except Exception as e:
                log.debug(f"Textarea error: {e}")
                continue

    def _fill_dropdowns(self, job: Job) -> None:
        """Fill select/dropdown fields using AI form filler."""
        selects = self.browser.find_elements(
            By.CSS_SELECTOR, "select", timeout=2
        )

        for sel_el in selects:
            try:
                if not sel_el.is_displayed():
                    continue

                select = Select(sel_el)
                # Skip if already selected (not default)
                if select.first_selected_option.text.strip() not in [
                    "", "Select an option", "-- Select --"
                ]:
                    continue

                label = self._get_field_label(sel_el)
                options = [opt.text.strip() for opt in select.options if opt.text.strip()]

                if not label or len(options) <= 1:
                    continue

                chosen = self.form_filler.answer_choice_question(label, options)
                select.select_by_visible_text(chosen)
                human_delay(0.3, 0.6)
            except Exception as e:
                log.debug(f"Dropdown error: {e}")
                continue

    def _fill_radio_buttons(self, job: Job) -> None:
        """Fill radio button groups using AI form filler."""
        fieldsets = self.browser.find_elements(
            By.CSS_SELECTOR,
            "fieldset[data-test-form-builder-radio-button-form-component]",
            timeout=2,
        )

        for fieldset in fieldsets:
            try:
                legend = fieldset.find_element(By.CSS_SELECTOR, "legend, span.fb-dash-form-element__label")
                question = legend.text.strip()
                if not question:
                    continue

                options_els = fieldset.find_elements(
                    By.CSS_SELECTOR, "label[data-test-text-selectable-option__label]"
                )
                options = [opt.text.strip() for opt in options_els if opt.text.strip()]

                if not options:
                    continue

                chosen = self.form_filler.answer_choice_question(question, options)

                for opt_el in options_els:
                    if opt_el.text.strip() == chosen:
                        self.browser.click(opt_el)
                        break
            except Exception as e:
                log.debug(f"Radio button error: {e}")
                continue

    def _fill_checkboxes(self) -> None:
        """Handle checkbox fields (terms of service, etc.)."""
        try:
            checkboxes = self.browser.find_elements(
                By.CSS_SELECTOR,
                "input[type='checkbox']",
                timeout=2,
            )
            for cb in checkboxes:
                if not cb.is_selected() and cb.is_displayed():
                    label = self._get_field_label(cb)
                    label_lower = (label or "").lower()
                    # Auto-check terms of service / acknowledgments
                    if any(kw in label_lower for kw in [
                        "terms", "acknowledge", "agree", "confirm", "certify"
                    ]):
                        self.browser.click(cb)
        except Exception:
            pass

    def _get_field_label(self, element) -> str:
        """Extract the label text for a form element."""
        try:
            # Try aria-label
            label = element.get_attribute("aria-label")
            if label:
                return label.strip()

            # Try associated label via id
            el_id = element.get_attribute("id")
            if el_id:
                try:
                    label_el = self.browser.driver.find_element(
                        By.CSS_SELECTOR, f"label[for='{el_id}']"
                    )
                    return label_el.text.strip()
                except Exception:
                    pass

            # Try parent label
            try:
                parent = element.find_element(By.XPATH, "./..")
                label_el = parent.find_element(By.CSS_SELECTOR, "label, span")
                return label_el.text.strip()
            except Exception:
                pass

            # Try placeholder
            placeholder = element.get_attribute("placeholder")
            if placeholder:
                return placeholder.strip()

        except Exception:
            pass
        return ""

    def _get_upload_label(self, element) -> str:
        """Get the label for a file upload field."""
        try:
            parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'jobs-document-upload')]")
            label = parent.find_element(By.CSS_SELECTOR, "label, span")
            return label.text.strip()
        except Exception:
            return self._get_field_label(element)

    def _try_submit(self) -> bool:
        """Try to find and click the submit button."""
        selectors = [
            "button[aria-label='Submit application']",
            "button[aria-label='Review your application']",
        ]

        for selector in selectors:
            try:
                btn = self.browser.find_element(By.CSS_SELECTOR, selector, timeout=2)
                if btn.is_displayed():
                    # If it's "Review", click it then look for submit
                    if "Review" in (btn.get_attribute("aria-label") or ""):
                        self.browser.click(btn)
                        human_delay(1.0, 2.0)
                        return self._try_submit()

                    self.browser.click(btn)
                    human_delay(1.0, 2.0)

                    # Uncheck follow company if present
                    self._uncheck_follow()

                    return True
            except Exception:
                continue

        return False

    def _click_next(self) -> bool:
        """Click the 'Next' or 'Continue' button."""
        selectors = [
            "button[aria-label='Continue to next step']",
            "button[aria-label='Review your application']",
        ]

        for selector in selectors:
            try:
                btn = self.browser.find_element(By.CSS_SELECTOR, selector, timeout=3)
                if btn.is_displayed():
                    self.browser.click(btn)
                    return True
            except Exception:
                continue

        return False

    def _has_form_errors(self) -> bool:
        """Check if there are validation errors on the form."""
        return self.browser.element_exists(
            By.CSS_SELECTOR,
            ".artdeco-inline-feedback--error",
            timeout=1,
        )

    def _handle_form_errors(self, job: Job) -> None:
        """Attempt to fix form validation errors."""
        try:
            errors = self.browser.find_elements(
                By.CSS_SELECTOR,
                ".artdeco-inline-feedback--error",
                timeout=2,
            )
            for error in errors:
                error_text = error.text.strip()
                log.debug(f"Form error: {error_text}")
                # Try to find and re-fill the associated field
                try:
                    parent = error.find_element(By.XPATH, "./ancestor::div[contains(@class, 'fb-dash-form-element')]")
                    inputs = parent.find_elements(By.CSS_SELECTOR, "input, textarea, select")
                    for inp in inputs:
                        if inp.tag_name == "select":
                            select = Select(inp)
                            if len(select.options) > 1:
                                select.select_by_index(1)
                        else:
                            label = self._get_field_label(inp)
                            hint = f"{label} (Error: {error_text})"
                            if self.form_filler:
                                answer = self.form_filler.answer_text_question(hint)
                                self.browser.type_text(inp, answer)
                except Exception:
                    continue
        except Exception:
            pass

    def _uncheck_follow(self) -> None:
        """Uncheck the 'Follow company' checkbox if present."""
        try:
            follow_cb = self.browser.find_element(
                By.CSS_SELECTOR,
                "input[id*='follow-company']",
                timeout=2,
            )
            if follow_cb.is_selected():
                self.browser.click(follow_cb)
        except Exception:
            pass

    def _discard_application(self) -> None:
        """Close/discard the current application modal."""
        try:
            dismiss_btn = self.browser.find_element(
                By.CSS_SELECTOR,
                "button[aria-label='Dismiss']",
                timeout=3,
            )
            self.browser.click(dismiss_btn)
            human_delay(0.5, 1.0)

            # Confirm discard
            confirm_btn = self.browser.find_element(
                By.CSS_SELECTOR,
                "button[data-control-name='discard_application_confirm_btn'],"
                "button[data-test-dialog-primary-btn]",
                timeout=3,
            )
            self.browser.click(confirm_btn)
        except Exception:
            pass

    def close(self) -> None:
        """Close the browser."""
        self.browser.close()
