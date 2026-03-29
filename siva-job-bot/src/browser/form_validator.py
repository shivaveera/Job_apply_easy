"""Form validation, required field detection, and submission verification.

Handles:
- Required field detection (HTML5 required, aria-required, asterisk labels)
- Pre-submit validation (ensure all required fields are filled)
- Post-submit success verification per ATS platform
- Screenshot capture on submit for audit trail
- Error detection and retry loop
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from selenium.webdriver.common.by import By

from src.utils.logger import log


def find_required_fields(driver) -> list:
    """Find all required fields on the current page.

    Uses four detection strategies layered together:
    1. HTML5 required attribute
    2. aria-required="true"
    3. data-required="true"
    4. Asterisk (*) in associated label
    """
    required = set()

    # HTML5 required, aria-required, data-required
    for selector in ['[required]', '[aria-required="true"]', '[data-required="true"]']:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed():
                    required.add(el)
        except Exception:
            pass

    # Asterisk in labels
    try:
        labels = driver.find_elements(By.CSS_SELECTOR, "label")
        for label in labels:
            text = label.text.strip()
            if "*" in text:
                field_for = label.get_attribute("for")
                if field_for:
                    try:
                        field = driver.find_element(By.ID, field_for)
                        if field.is_displayed():
                            required.add(field)
                    except Exception:
                        pass
            # Also check for .required or .asterisk child elements
            try:
                if label.find_elements(By.CSS_SELECTOR, ".asterisk, .required, .text-danger"):
                    field_for = label.get_attribute("for")
                    if field_for:
                        field = driver.find_element(By.ID, field_for)
                        if field.is_displayed():
                            required.add(field)
            except Exception:
                pass
    except Exception:
        pass

    return list(required)


def find_empty_required_fields(driver) -> list:
    """Find required fields that are still empty."""
    required = find_required_fields(driver)
    empty = []
    for field in required:
        try:
            tag = field.tag_name.lower()
            if tag in ("input", "textarea"):
                value = field.get_attribute("value") or ""
                if not value.strip():
                    empty.append(field)
            elif tag == "select":
                from selenium.webdriver.support.ui import Select
                selected = Select(field).first_selected_option.text.strip()
                if not selected or selected in ("", "Select", "-- Select --", "Choose..."):
                    empty.append(field)
        except Exception:
            continue
    return empty


def find_form_errors(driver) -> list[str]:
    """Detect form validation error messages on the current page."""
    errors = []
    error_selectors = [
        ".artdeco-inline-feedback--error",  # LinkedIn
        "[role='alert']",
        ".error-message",
        ".field-error",
        ".form-error",
        ".validation-error",
        ".invalid-feedback",
        "[data-automation-id='errorMessage']",  # Workday
        ".ia-error",  # Indeed
    ]

    for selector in error_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed() and el.text.strip():
                    errors.append(el.text.strip())
        except Exception:
            continue

    return errors


# Per-platform success detection patterns
SUCCESS_PATTERNS = {
    "linkedin": {
        "url_contains": [],
        "element_selectors": [
            "[aria-label*='application was sent']",
            ".artdeco-modal__content .t-bold",
        ],
        "text_contains": ["application was sent", "your application has been submitted"],
    },
    "workday": {
        "url_contains": ["successfullyApplied"],
        "element_selectors": [
            "[data-automation-id='congratulationsMessage']",
            "[data-automation-id='congratulationsLabel']",
        ],
        "text_contains": ["thank you for applying", "application has been submitted", "congratulations"],
    },
    "greenhouse": {
        "url_contains": [],
        "element_selectors": [
            ".application-confirmation",
            "#application_confirmation",
        ],
        "text_contains": ["application has been submitted", "thank you for applying", "we have received your application"],
    },
    "indeed": {
        "url_contains": [],
        "element_selectors": [
            ".ia-PostApply",
            "[data-testid='post-apply']",
        ],
        "text_contains": ["application has been submitted", "your application was sent"],
    },
    "lever": {
        "url_contains": ["/thanks"],
        "element_selectors": [
            ".application-confirmation",
            ".posting-confirmation",
        ],
        "text_contains": ["application has been submitted", "thank you for applying"],
    },
    "smartrecruiters": {
        "url_contains": ["confirmation", "thank"],
        "element_selectors": [".confirmation-message"],
        "text_contains": ["application has been submitted", "thank you"],
    },
}


def verify_submission_success(driver, platform: str) -> bool:
    """Verify that an application was successfully submitted.

    Uses platform-specific URL patterns, element selectors, and text matching.
    """
    patterns = SUCCESS_PATTERNS.get(platform, {})

    # Check URL
    current_url = driver.current_url.lower()
    for url_pattern in patterns.get("url_contains", []):
        if url_pattern.lower() in current_url:
            log.info(f"Success verified via URL pattern: {url_pattern}")
            return True

    # Check for success elements
    for selector in patterns.get("element_selectors", []):
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if any(el.is_displayed() for el in elements):
                log.info(f"Success verified via element: {selector}")
                return True
        except Exception:
            continue

    # Check page text
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        for text in patterns.get("text_contains", []):
            if text.lower() in page_text:
                log.info(f"Success verified via text: '{text}'")
                return True
    except Exception:
        pass

    return False


def take_screenshot(driver, job_id: str, status: str = "submit") -> str:
    """Take a screenshot for audit trail.

    Returns the screenshot file path.
    """
    screenshot_dir = Path("data/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{status}_{job_id}_{timestamp}.png"
    filepath = screenshot_dir / filename

    try:
        driver.save_screenshot(str(filepath))
        log.debug(f"Screenshot saved: {filepath}")
        return str(filepath)
    except Exception as e:
        log.debug(f"Screenshot failed: {e}")
        return ""


def fill_and_submit_with_retry(
    driver,
    fill_fn,
    submit_fn,
    platform: str,
    max_retries: int = 2,
) -> bool:
    """Fill form, attempt submit, check errors, re-fill, retry.

    Args:
        driver: Selenium WebDriver
        fill_fn: Callable that fills the current form page
        submit_fn: Callable that clicks submit/next
        platform: Platform name for success verification
        max_retries: Max retry attempts on validation error
    """
    for attempt in range(max_retries + 1):
        # Fill the form
        fill_fn()

        # Check for empty required fields before submitting
        empty = find_empty_required_fields(driver)
        if empty:
            log.warning(f"Found {len(empty)} empty required fields on attempt {attempt + 1}")
            # Try to fill them again
            fill_fn()

        # Attempt submit
        submit_fn()
        time.sleep(2)

        # Check for errors
        errors = find_form_errors(driver)
        if not errors:
            return True

        log.warning(f"Form errors on attempt {attempt + 1}: {errors}")
        if attempt < max_retries:
            log.info("Retrying form fill...")
            time.sleep(1)

    return False
