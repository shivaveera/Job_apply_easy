"""ATS (Applicant Tracking System) detection module.

Identifies which ATS platform powers a career page using URL patterns,
HTML signatures, and DOM inspection. Routes to the correct platform
module for form filling.
"""

import re
from typing import Optional

from src.utils.logger import log

# URL pattern matching (highest confidence)
ATS_URL_PATTERNS: dict[str, list[str]] = {
    "greenhouse": [r"boards\.greenhouse\.io", r"job-boards\.greenhouse\.io"],
    "lever": [r"jobs\.lever\.co", r"jobs\.eu\.lever\.co"],
    "workday": [r"\.wd\d+\.myworkdayjobs\.com", r"myworkdayjobs\.com"],
    "icims": [r"\.icims\.com", r"careers-.*\.icims\.com"],
    "taleo": [r"\.taleo\.net", r"tbe\.taleo\.net", r"oracle\.taleo\.net"],
    "successfactors": [
        r"\.successfactors\.com",
        r"performancemanager\d*\.successfactors",
    ],
    "adp": [r"workforcenow\.adp\.com", r"recruiting\.adp\.com"],
    "smartrecruiters": [r"jobs\.smartrecruiters\.com"],
    "bamboohr": [r"\.bamboohr\.com/careers", r"\.bamboohr\.com/hiring"],
    "jobvite": [r"jobs\.jobvite\.com", r"app\.jobvite\.com"],
    "ashby": [r"jobs\.ashbyhq\.com"],
    "jazzhr": [r"\.applytojob\.com"],
    "breezyhr": [r"\.breezy\.hr"],
    "paylocity": [r"recruiting\.paylocity\.com"],
    "linkedin": [r"linkedin\.com/jobs"],
    "indeed": [r"indeed\.com/viewjob", r"indeed\.com/applystart"],
}

# HTML source signatures (medium confidence)
ATS_HTML_SIGNATURES: dict[str, list[str]] = {
    "workday": ["data-automation-id", "myworkdayjobs", "workday"],
    "greenhouse": ["boards.greenhouse.io", "greenhouse.io", "gh_jid"],
    "lever": ["jobs.lever.co", "lever.co", "lever-jobs"],
    "icims": ["icims.com", "iCIMS", "icims"],
    "taleo": ["taleo.net", "oracle.taleo"],
    "smartrecruiters": ["smartrecruiters.com", "smartrecruiters"],
    "ashby": ["ashbyhq.com", "ashby"],
    "adp": ["recruitment-current-openings", "adp.com"],
    "bamboohr": ["bamboohr.com"],
    "jobvite": ["jobvite.com"],
    "successfactors": ["successfactors.com"],
}

# DOM element signatures (highest confidence, requires page load)
ATS_DOM_SIGNATURES: dict[str, list[str]] = {
    "workday": [
        "[data-automation-id]",
        "[data-automation-id='applyButton']",
    ],
    "greenhouse": [
        "input[name='first_name']",
        "#greenhouse_application",
    ],
    "lever": [
        ".posting-apply",
        "input[name='urls[LinkedIn]']",
    ],
    "adp": [
        "recruitment-current-openings",
    ],
    "icims": [
        "iframe[src*='icims']",
    ],
}


def detect_ats(url: str, page_source: str = "") -> str:
    """Detect which ATS platform powers the given URL.

    Uses a multi-signal approach:
    1. URL pattern matching (highest confidence)
    2. HTML source signatures (medium confidence)
    3. Falls back to 'unknown' for universal form filler

    Args:
        url: The career page URL.
        page_source: Optional HTML source of the page.

    Returns:
        ATS platform name string (e.g., 'greenhouse', 'workday', 'unknown').
    """
    # 1. URL pattern matching
    for ats, patterns in ATS_URL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                log.info(f"ATS detected via URL: {ats}")
                return ats

    # 2. HTML source scanning
    if page_source:
        src_lower = page_source.lower()
        for ats, signatures in ATS_HTML_SIGNATURES.items():
            if any(sig.lower() in src_lower for sig in signatures):
                log.info(f"ATS detected via HTML signature: {ats}")
                return ats

    log.info("ATS not detected, will use universal form filler")
    return "unknown"


def detect_ats_from_driver(driver) -> str:
    """Detect ATS using a live Selenium driver (checks DOM elements).

    Args:
        driver: Selenium WebDriver instance.

    Returns:
        ATS platform name string.
    """
    url = driver.current_url
    page_source = driver.page_source

    # Try URL + HTML first
    result = detect_ats(url, page_source)
    if result != "unknown":
        return result

    # Try DOM element signatures
    for ats, selectors in ATS_DOM_SIGNATURES.items():
        for selector in selectors:
            try:
                elements = driver.find_elements("css selector", selector)
                if elements:
                    log.info(f"ATS detected via DOM element: {ats}")
                    return ats
            except Exception:
                continue

    return "unknown"


# Platform registry for routing
PLATFORM_NAMES: dict[str, str] = {
    "linkedin": "LinkedIn",
    "indeed": "Indeed",
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "workday": "Workday",
    "icims": "iCIMS",
    "taleo": "Oracle Taleo",
    "successfactors": "SAP SuccessFactors",
    "adp": "ADP Workforce Now",
    "smartrecruiters": "SmartRecruiters",
    "bamboohr": "BambooHR",
    "jobvite": "Jobvite",
    "ashby": "Ashby",
    "jazzhr": "JazzHR",
    "breezyhr": "BreezyHR",
    "paylocity": "Paylocity",
    "unknown": "Unknown (Universal Filler)",
}


def get_platform_display_name(ats_key: str) -> str:
    """Get the human-readable name for an ATS platform."""
    return PLATFORM_NAMES.get(ats_key, ats_key.title())
