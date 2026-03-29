"""API-based job discovery for Greenhouse and Lever.

These platforms have public JSON APIs that don't require Selenium:
- Greenhouse: boards-api.greenhouse.io/v1/boards/{token}/jobs
- Lever: api.lever.co/v0/postings/{company}

This is faster and more reliable than scraping for job discovery.
"""

import re
from typing import Optional
from urllib.parse import quote

import requests

from src.platforms.base import Job
from src.utils.logger import log


def discover_greenhouse_jobs(
    board_token: str,
    keywords: list[str] = None,
    location: str = "",
) -> list[Job]:
    """Discover jobs from a Greenhouse board via public API.

    Args:
        board_token: The company's Greenhouse board token
                     (from boards.greenhouse.io/{token})
        keywords: Optional keyword filter
        location: Optional location filter

    Returns:
        List of Job objects with application URLs
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    jobs = []

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("jobs", []):
            title = item.get("title", "")
            loc = item.get("location", {}).get("name", "")
            job_id = str(item.get("id", ""))
            content = item.get("content", "")

            # Keyword filter
            if keywords:
                combined = f"{title} {content}".lower()
                if not any(kw.lower() in combined for kw in keywords):
                    continue

            # Location filter
            if location and location.lower() not in loc.lower():
                if "remote" not in loc.lower():
                    continue

            apply_url = item.get("absolute_url", "")
            if not apply_url:
                apply_url = f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"

            jobs.append(Job(
                job_id=f"gh_{job_id}",
                title=title,
                company=board_token,
                location=loc,
                url=apply_url,
                description=_strip_html(content),
                platform="greenhouse",
            ))

        log.info(f"Greenhouse [{board_token}]: found {len(jobs)} jobs")

    except requests.RequestException as e:
        log.error(f"Greenhouse API error for {board_token}: {e}")
    except (ValueError, KeyError) as e:
        log.error(f"Greenhouse response parse error: {e}")

    return jobs


def discover_lever_jobs(
    company: str,
    keywords: list[str] = None,
    team: str = "",
    location: str = "",
    commitment: str = "",
) -> list[Job]:
    """Discover jobs from a Lever board via public API.

    Args:
        company: The company slug (from jobs.lever.co/{company})
        keywords: Optional keyword filter
        team: Filter by team (e.g., "Engineering")
        location: Filter by location
        commitment: Filter by commitment (e.g., "Full-time")

    Returns:
        List of Job objects with application URLs
    """
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    if team:
        url += f"&team={quote(team)}"
    if location:
        url += f"&location={quote(location)}"
    if commitment:
        url += f"&commitment={quote(commitment)}"

    jobs = []

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for item in data:
            title = item.get("text", "")
            loc = item.get("categories", {}).get("location", "")
            team_name = item.get("categories", {}).get("team", "")
            job_id = item.get("id", "")
            description = item.get("descriptionPlain", "") or item.get("description", "")

            # Keyword filter
            if keywords:
                combined = f"{title} {description} {team_name}".lower()
                if not any(kw.lower() in combined for kw in keywords):
                    continue

            apply_url = item.get("applyUrl", "") or item.get("hostedUrl", "")
            if not apply_url:
                apply_url = f"https://jobs.lever.co/{company}/{job_id}/apply"

            salary_range = ""
            sr = item.get("salaryRange", {})
            if sr:
                salary_range = f"{sr.get('min', '')} - {sr.get('max', '')} {sr.get('currency', 'USD')}"

            jobs.append(Job(
                job_id=f"lever_{job_id}",
                title=title,
                company=company,
                location=loc,
                url=apply_url,
                description=_strip_html(description),
                salary_info=salary_range,
                platform="lever",
            ))

        log.info(f"Lever [{company}]: found {len(jobs)} jobs")

    except requests.RequestException as e:
        log.error(f"Lever API error for {company}: {e}")
    except (ValueError, KeyError) as e:
        log.error(f"Lever response parse error: {e}")

    return jobs


def discover_jobs_from_company_boards(
    companies: list[dict],
    keywords: list[str] = None,
    location: str = "",
) -> list[Job]:
    """Discover jobs from multiple company career boards.

    Args:
        companies: List of dicts with 'platform' and 'token' keys.
                   e.g., [{"platform": "greenhouse", "token": "airbnb"},
                          {"platform": "lever", "token": "stripe"}]
        keywords: Keyword filter applied across all boards
        location: Location filter

    Returns:
        Combined list of jobs from all boards
    """
    all_jobs = []

    for company in companies:
        platform = company.get("platform", "").lower()
        token = company.get("token", "")

        if not token:
            continue

        if platform == "greenhouse":
            jobs = discover_greenhouse_jobs(token, keywords, location)
            all_jobs.extend(jobs)
        elif platform == "lever":
            jobs = discover_lever_jobs(
                token, keywords,
                team=company.get("team", ""),
                location=location,
            )
            all_jobs.extend(jobs)
        else:
            log.debug(f"Unknown board platform: {platform}")

    log.info(f"Total jobs discovered from boards: {len(all_jobs)}")
    return all_jobs


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()[:5000]
