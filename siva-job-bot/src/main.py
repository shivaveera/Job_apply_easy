"""Main orchestrator for the Siva Job Bot.

Coordinates all components: config loading, browser management,
AI client initialization, platform automation, tracking, and
multi-ATS platform routing.
"""

import sys
import time
from pathlib import Path
from typing import Optional

import yaml

from src.ai.cover_letter import CoverLetterGenerator
from src.ai.deepseek_client import DeepSeekClient
from src.ai.form_filler import FormFiller
from src.ai.job_scorer import JobScorer
from src.ai.resume_gen import ResumeGenerator
from src.browser.driver import BrowserDriver
from src.platforms.adp import ADPPlatform
from src.platforms.ashby import AshbyPlatform
from src.platforms.ats_detector import detect_ats, detect_ats_from_driver, get_platform_display_name
from src.platforms.base import BasePlatform, Job
from src.platforms.greenhouse import GreenhousePlatform
from src.platforms.icims import ICIMSPlatform
from src.platforms.indeed import IndeedPlatform
from src.platforms.lever import LeverPlatform
from src.platforms.linkedin import LinkedInPlatform
from src.platforms.smartrecruiters import SmartRecruitersPlatform
from src.platforms.taleo import TaleoPlatform
from src.platforms.universal import UniversalFormFiller
from src.platforms.workday import WorkdayPlatform
from src.tracking.dashboard import print_dashboard, print_session_summary
from src.tracking.database import ApplicationDatabase
from src.utils.humanizer import (
    human_delay,
    is_within_active_hours,
    session_break,
    should_take_break,
    wait_for_active_hours,
)
from src.utils.logger import log


class JobBot:
    """Main job application bot orchestrator.

    Manages the full application pipeline:
    1. Load config and initialize components
    2. Login to platforms
    3. Search for jobs
    4. Score and filter jobs
    5. Apply with AI-powered form filling
    6. Track results and notify
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.db: Optional[ApplicationDatabase] = None
        self.ai_client: Optional[DeepSeekClient] = None
        self.browser: Optional[BrowserDriver] = None
        self.job_scorer: Optional[JobScorer] = None
        self.form_filler: Optional[FormFiller] = None
        self.resume_gen: Optional[ResumeGenerator] = None
        self.cover_letter_gen: Optional[CoverLetterGenerator] = None
        self.notifier = None

        # Session counters
        self.applied = 0
        self.skipped = 0
        self.failed = 0
        self.blacklisted = 0

    def _load_config(self, config_path: str) -> dict:
        """Load and validate the YAML configuration."""
        path = Path(config_path)
        if not path.exists():
            log.error(f"Config file not found: {config_path}")
            sys.exit(1)

        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self._validate_config(config)
        log.info(f"Configuration loaded from {config_path}")
        return config

    def _validate_config(self, config: dict) -> None:
        """Validate required configuration fields."""
        required_sections = ["personal", "search", "platforms", "ai", "safety", "database"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")

        # Validate AI key is set (unless dry run)
        if not config["safety"].get("dry_run"):
            api_key = config["ai"].get("deepseek_api_key", "")
            if not api_key:
                log.warning(
                    "DeepSeek API key not set. AI features will be disabled. "
                    "Set ai.deepseek_api_key in config.yaml or use --dry-run mode."
                )

    def initialize(self) -> None:
        """Initialize all bot components."""
        log.info("Initializing Siva Job Bot...")

        # Database
        db_path = self.config["database"]["path"]
        self.db = ApplicationDatabase(db_path)

        # AI Client
        ai_config = self.config["ai"]
        api_key = ai_config.get("deepseek_api_key", "")

        if api_key:
            self.ai_client = DeepSeekClient(
                api_key=api_key,
                base_url=ai_config.get("deepseek_base_url", "https://api.deepseek.com/v1"),
                cache_enabled=ai_config.get("cache_responses", True),
                cache_db_path="data/ai_cache.db",
                max_retries=ai_config.get("max_retries", 3),
            )

            # Load resume
            resume_path = "config/resume_base.md"
            resume_text = Path(resume_path).read_text(encoding="utf-8") if Path(resume_path).exists() else ""

            models = ai_config.get("models", {})

            # Job Scorer
            self.job_scorer = JobScorer(
                client=self.ai_client,
                model=models.get("scoring", "deepseek-chat"),
                resume=resume_text,
            )

            # Form Filler
            qa_overrides = self._load_qa_overrides()
            self.form_filler = FormFiller(
                client=self.ai_client,
                model=models.get("form_filling", "deepseek-chat"),
                resume=resume_text,
                qa_overrides=qa_overrides,
                db_path=db_path,
            )

            # Resume Generator
            if ai_config.get("resume_tailoring", True):
                self.resume_gen = ResumeGenerator(
                    client=self.ai_client,
                    model=models.get("resume", "deepseek-chat"),
                    base_resume_path=resume_path,
                )

            # Cover Letter Generator
            if ai_config.get("cover_letter", True):
                self.cover_letter_gen = CoverLetterGenerator(
                    client=self.ai_client,
                    model=models.get("cover_letter", "deepseek-chat"),
                    resume=resume_text,
                )

            log.info("AI components initialized")
        else:
            log.warning("Running without AI - form filling will be limited")

        # Notifications
        self._init_notifications()

        # Browser
        safety = self.config["safety"]
        self.browser = BrowserDriver(
            headless=False,
            use_profile=True,
            stealth_mode=safety.get("conservative_mode", True),
        )

        log.info("All components initialized")

    def _load_qa_overrides(self) -> dict[str, str]:
        """Load Q&A overrides from YAML file."""
        override_path = Path("config/qa_overrides.yaml")
        if not override_path.exists():
            return {}

        with open(override_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        overrides = data.get("overrides", {})
        # Inject personal info
        personal = self.config.get("personal", {})
        if personal.get("linkedin_url"):
            overrides["linkedin"] = personal["linkedin_url"]
        if personal.get("github_url"):
            overrides["github"] = personal["github_url"]
        if personal.get("website"):
            overrides["website"] = personal["website"]
            overrides["portfolio"] = personal["website"]

        return overrides

    def _init_notifications(self) -> None:
        """Initialize notification services."""
        notif_config = self.config.get("notifications", {})

        # Telegram
        tg = notif_config.get("telegram", {})
        if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
            from src.notifications.telegram import TelegramNotifier
            self.notifier = TelegramNotifier(
                bot_token=tg["bot_token"],
                chat_id=str(tg["chat_id"]),
            )
            log.info("Telegram notifications enabled")

    def run(self, dry_run: bool = False) -> None:
        """Execute the main job application loop.

        Args:
            dry_run: If True, search and score jobs but don't actually apply.
        """
        if dry_run:
            self.config["safety"]["dry_run"] = True
            log.info("DRY RUN MODE - No applications will be submitted")

        start_time = time.time()

        try:
            self.initialize()

            # Show current stats
            print_dashboard(self.db)

            # Start browser
            self.browser.start()

            # Run platform-specific automation
            self._run_linkedin()

            # Run multi-ATS URL-based applications
            self._run_url_applications()

        except KeyboardInterrupt:
            log.info("Bot stopped by user")
        except Exception as e:
            log.error(f"Bot error: {e}", exc_info=True)
            if self.notifier:
                self.notifier.notify_error(str(e))
        finally:
            self._cleanup(start_time)

    def _run_linkedin(self) -> None:
        """Run the LinkedIn automation pipeline."""
        li_config = self.config["platforms"].get("linkedin", {})
        if not li_config.get("enabled", False):
            log.info("LinkedIn is disabled in config")
            return

        platform = LinkedInPlatform(
            browser=self.browser,
            form_filler=self.form_filler,
        )

        # Login
        username = li_config.get("username", "")
        password = li_config.get("password", "")

        if not platform.login(username, password):
            log.error("LinkedIn login failed. Please check credentials.")
            return

        # Search for jobs
        search_config = self.config["search"]
        jobs = platform.search_jobs(search_config)

        if not jobs:
            log.info("No jobs found matching your criteria")
            return

        log.info(f"Processing {len(jobs)} jobs...")
        safety = self.config["safety"]
        max_daily = safety.get("max_applications_per_day", 50)
        scoring_threshold = self.config["ai"].get("job_scoring_threshold", 0.6)
        is_dry_run = safety.get("dry_run", False)

        for i, job in enumerate(jobs):
            # Check daily limit
            today_count = self.db.get_today_count()
            if today_count >= max_daily:
                log.info(f"Daily application limit reached ({max_daily})")
                break

            # Check active hours
            active_hours = safety.get("active_hours", ["08:00", "22:00"])
            if not is_within_active_hours(active_hours[0], active_hours[1]):
                wait_for_active_hours(active_hours[0], active_hours[1])

            # Check if already applied
            if self.db.is_already_applied(job.job_id):
                self.skipped += 1
                continue

            # AI scoring
            if self.job_scorer and job.description:
                meets, score_result = self.job_scorer.meets_threshold(
                    job.title, job.company, job.location,
                    job.description, scoring_threshold,
                )
                if not meets:
                    log.info(
                        f"Skipping (score {score_result['score']:.2f} < {scoring_threshold}): "
                        f"{job.title} at {job.company}"
                    )
                    self.db.save_application(
                        job_id=job.job_id,
                        job_title=job.title,
                        company=job.company,
                        location=job.location,
                        job_url=job.url,
                        status="skipped_low_score",
                        ai_score=score_result["score"],
                        ai_reasoning=score_result["reasoning"],
                        job_description=job.description,
                    )
                    self.skipped += 1
                    continue
            else:
                score_result = {"score": None, "reasoning": ""}

            # Generate tailored resume if enabled
            resume_path = ""
            if self.resume_gen and job.description:
                try:
                    _, pdf_path = self.resume_gen.generate_for_job(
                        job.title, job.company, job.description, job.job_id
                    )
                    resume_path = str(pdf_path) if pdf_path else ""
                except Exception as e:
                    log.warning(f"Resume generation failed: {e}")

            # Generate cover letter if enabled
            cover_letter_path = ""
            if self.cover_letter_gen and job.description:
                try:
                    _, cl_path = self.cover_letter_gen.generate_for_job(
                        job.title, job.company, job.description, job.job_id
                    )
                    cover_letter_path = str(cl_path) if cl_path else ""
                except Exception as e:
                    log.warning(f"Cover letter generation failed: {e}")

            # Apply
            if is_dry_run:
                log.info(f"[DRY RUN] Would apply to: {job.title} at {job.company}")
                self.db.save_application(
                    job_id=job.job_id,
                    job_title=job.title,
                    company=job.company,
                    location=job.location,
                    job_url=job.url,
                    status="dry_run",
                    ai_score=score_result.get("score"),
                    ai_reasoning=score_result.get("reasoning", ""),
                    resume_path=resume_path,
                    cover_letter_path=cover_letter_path,
                    job_description=job.description,
                )
                self.applied += 1
            else:
                # Pause before submit if configured
                if safety.get("pause_before_submit"):
                    input(
                        f"\nReady to apply to: {job.title} at {job.company}. "
                        f"Press Enter to continue or Ctrl+C to skip..."
                    )

                success = platform.apply_to_job(job)

                if success:
                    app_id = self.db.save_application(
                        job_id=job.job_id,
                        job_title=job.title,
                        company=job.company,
                        location=job.location,
                        job_url=job.url,
                        status="applied",
                        ai_score=score_result.get("score"),
                        ai_reasoning=score_result.get("reasoning", ""),
                        resume_path=resume_path,
                        cover_letter_path=cover_letter_path,
                        job_description=job.description,
                    )
                    self.applied += 1

                    if self.notifier:
                        self.notifier.notify_applied(
                            job.title, job.company, score_result.get("score")
                        )
                else:
                    self.db.save_application(
                        job_id=job.job_id,
                        job_title=job.title,
                        company=job.company,
                        location=job.location,
                        job_url=job.url,
                        status="failed",
                        job_description=job.description,
                    )
                    self.failed += 1

            # Human-like delay between applications
            delay_range = safety.get("delay_between_apps_seconds", [30, 90])
            human_delay(delay_range[0], delay_range[1])

            # Session break
            break_after = safety.get("session_break_after", 15)
            if should_take_break(self.applied, break_after):
                break_range = safety.get("session_break_minutes", [5, 15])
                session_break(break_range[0], break_range[1])

        platform.close()

    def _get_platform_for_ats(self, ats_key: str) -> Optional[BasePlatform]:
        """Get the platform implementation for a detected ATS.

        Routes to the correct platform module based on ATS detection.
        Falls back to UniversalFormFiller for unknown platforms.
        """
        personal = self.config.get("personal", {})

        platform_map = {
            "greenhouse": lambda: GreenhousePlatform(self.browser, self.form_filler, personal),
            "lever": lambda: LeverPlatform(self.browser, self.form_filler, personal),
            "workday": lambda: WorkdayPlatform(self.browser, self.form_filler, personal),
            "indeed": lambda: IndeedPlatform(self.browser, self.form_filler, personal),
            "smartrecruiters": lambda: SmartRecruitersPlatform(self.browser, self.form_filler, personal),
            "icims": lambda: ICIMSPlatform(self.browser, self.form_filler, personal),
            "taleo": lambda: TaleoPlatform(self.browser, self.form_filler, personal),
            "adp": lambda: ADPPlatform(self.browser, self.form_filler, personal),
            "ashby": lambda: AshbyPlatform(self.browser, self.form_filler, personal),
        }

        if ats_key in platform_map:
            return platform_map[ats_key]()

        # Fallback: universal form filler
        return UniversalFormFiller(self.browser, self.form_filler, personal)

    def _run_url_applications(self) -> None:
        """Apply to jobs from a list of URLs with automatic ATS detection.

        Reads URLs from config 'application_urls' list. For each URL:
        1. Detect the ATS platform
        2. Route to the correct platform module
        3. Fill and submit the application
        """
        urls = self.config.get("application_urls", [])
        if not urls:
            return

        log.info(f"Processing {len(urls)} application URLs...")
        safety = self.config["safety"]
        is_dry_run = safety.get("dry_run", False)
        max_daily = safety.get("max_applications_per_day", 50)

        for url in urls:
            # Check daily limit
            today_count = self.db.get_today_count()
            if today_count >= max_daily:
                log.info(f"Daily limit reached ({max_daily})")
                break

            # Detect ATS
            ats_key = detect_ats(url)
            ats_name = get_platform_display_name(ats_key)
            log.info(f"Detected ATS: {ats_name} for {url}")

            # If detection was inconclusive, try with page source
            if ats_key == "unknown":
                self.browser.get(url)
                human_delay(2.0, 4.0)
                ats_key = detect_ats_from_driver(self.browser.driver)
                ats_name = get_platform_display_name(ats_key)
                if ats_key != "unknown":
                    log.info(f"ATS re-detected via DOM: {ats_name}")

            job = Job(
                job_id=url,
                title=f"Application at {ats_name}",
                company=ats_name,
                url=url,
                platform=ats_key,
            )

            if self.db.is_already_applied(job.job_id):
                log.debug(f"Already applied: {url}")
                continue

            if is_dry_run:
                log.info(f"[DRY RUN] Would apply via {ats_name}: {url}")
                self.db.save_application(
                    job_id=job.job_id, job_title=job.title,
                    company=job.company, location="", job_url=url,
                    status="dry_run",
                )
                self.applied += 1
                continue

            platform = self._get_platform_for_ats(ats_key)

            try:
                success = platform.apply_to_job(job)
                status = "applied" if success else "failed"
                self.db.save_application(
                    job_id=job.job_id, job_title=job.title,
                    company=job.company, location="", job_url=url,
                    status=status,
                )
                if success:
                    self.applied += 1
                    if self.notifier:
                        self.notifier.notify_applied(job.title, job.company, None)
                else:
                    self.failed += 1
            except Exception as e:
                log.error(f"URL application failed for {url}: {e}")
                self.failed += 1

            # Delay between applications
            delay_range = safety.get("delay_between_apps_seconds", [30, 90])
            human_delay(delay_range[0], delay_range[1])

            # Session break check
            break_after = safety.get("session_break_after", 15)
            if should_take_break(self.applied, break_after):
                break_range = safety.get("session_break_minutes", [5, 15])
                session_break(break_range[0], break_range[1])

    def _cleanup(self, start_time: float) -> None:
        """Clean up resources and show session summary."""
        duration = (time.time() - start_time) / 60

        # Update daily stats
        ai_cost = self.ai_client.get_usage_summary()["total_cost_usd"] if self.ai_client else 0
        if self.db:
            self.db.update_daily_stats(
                applied=self.applied,
                skipped=self.skipped,
                failed=self.failed,
                blacklisted=self.blacklisted,
                ai_cost=ai_cost,
            )

        # Print session summary
        print_session_summary(
            self.applied, self.skipped, self.failed,
            self.blacklisted, duration, ai_cost,
        )

        # Export CSV if configured
        if self.db and self.config["database"].get("export_csv"):
            self.db.export_csv()

        # Send session notification
        if self.notifier:
            self.notifier.notify_session_summary(
                self.applied, self.skipped, self.failed, duration,
            )

        # Show final dashboard
        if self.db:
            print_dashboard(self.db)

        # Show AI usage
        if self.ai_client:
            usage = self.ai_client.get_usage_summary()
            log.info(f"AI Usage: {usage}")

        # Close all resources
        if self.browser:
            self.browser.close()
        if self.ai_client:
            self.ai_client.close()
        if self.form_filler:
            self.form_filler.close()
        if self.db:
            self.db.close()

        log.info("Bot shutdown complete")
