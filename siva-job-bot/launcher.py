#!/usr/bin/env python3
"""Interactive CLI launcher for Siva Job Bot.

Provides a menu-driven interface to configure and launch the bot:
- Select platforms (LinkedIn, Indeed, Greenhouse, etc.)
- Choose job categories/keywords (CS-focused presets)
- Set experience level (Entry, Mid, Senior)
- Set time filter (24h, 3 days, 1 week, 1 month)
- Add application URLs for direct ATS applications
- Run in normal or dry-run mode

Usage:
    python launcher.py
    python launcher.py --quick   # Skip menus, use saved config
"""

import argparse
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

# ─── ANSI colors ───────────────────────────────────────────────────────────────
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RESET = "\033[0m"
CHECK = f"{GREEN}\u2714{RESET}"
CROSS = f"{RED}\u2718{RESET}"
ARROW = f"{CYAN}\u25b6{RESET}"

CONFIG_PATH = "config/config.yaml"

# ─── CS Job Category Presets ───────────────────────────────────────────────────
CATEGORY_PRESETS = {
    "1": {
        "name": "Software Engineer (General)",
        "keywords": ["software engineer", "software developer", "backend engineer", "full stack developer"],
        "exclude": ["senior staff", "principal", "director", "VP", "lead architect", "staff engineer"],
    },
    "2": {
        "name": "Frontend / Web Development",
        "keywords": ["frontend engineer", "frontend developer", "react developer", "web developer", "UI engineer"],
        "exclude": ["senior staff", "principal", "director", "VP"],
    },
    "3": {
        "name": "Backend / API Development",
        "keywords": ["backend engineer", "backend developer", "API developer", "python developer", "java developer"],
        "exclude": ["senior staff", "principal", "director", "VP"],
    },
    "4": {
        "name": "Data Science / ML / AI",
        "keywords": ["data scientist", "machine learning engineer", "AI engineer", "data engineer", "ML engineer"],
        "exclude": ["senior staff", "principal", "director", "VP"],
    },
    "5": {
        "name": "DevOps / Cloud / SRE",
        "keywords": ["devops engineer", "cloud engineer", "SRE", "site reliability", "platform engineer", "infrastructure engineer"],
        "exclude": ["senior staff", "principal", "director", "VP"],
    },
    "6": {
        "name": "Cybersecurity",
        "keywords": ["security engineer", "cybersecurity analyst", "security analyst", "penetration tester", "SOC analyst"],
        "exclude": ["senior staff", "principal", "CISO", "director"],
    },
    "7": {
        "name": "Mobile Development",
        "keywords": ["mobile developer", "iOS developer", "android developer", "react native developer", "flutter developer"],
        "exclude": ["senior staff", "principal", "director", "VP"],
    },
    "8": {
        "name": "QA / Test Automation",
        "keywords": ["QA engineer", "test automation engineer", "SDET", "quality assurance", "software tester"],
        "exclude": ["senior staff", "principal", "director"],
    },
    "9": {
        "name": "New Grad / Intern (CS)",
        "keywords": ["software engineer new grad", "junior developer", "software intern", "engineering intern", "entry level developer"],
        "exclude": ["senior", "lead", "principal", "staff", "manager", "director"],
    },
}

EXPERIENCE_OPTIONS = {
    "1": {"name": "Internship", "levels": ["internship"]},
    "2": {"name": "Entry Level", "levels": ["entry"]},
    "3": {"name": "Entry + Mid Level", "levels": ["entry", "mid"]},
    "4": {"name": "Mid Level", "levels": ["mid"]},
    "5": {"name": "Mid + Senior", "levels": ["mid", "senior"]},
    "6": {"name": "Senior", "levels": ["senior"]},
    "7": {"name": "All Levels", "levels": ["internship", "entry", "associate", "mid", "senior"]},
}

TIME_OPTIONS = {
    "1": {"name": "Last 24 hours", "hours": 24},
    "2": {"name": "Last 3 days", "hours": 72},
    "3": {"name": "Last week", "hours": 168},
    "4": {"name": "Last month", "hours": 720},
    "5": {"name": "Any time", "hours": 0},
}

PLATFORM_LIST = [
    ("linkedin", "LinkedIn (Easy Apply)"),
    ("indeed", "Indeed"),
    ("greenhouse", "Greenhouse"),
    ("lever", "Lever"),
    ("workday", "Workday"),
    ("smartrecruiters", "SmartRecruiters"),
    ("icims", "iCIMS"),
    ("taleo", "Oracle Taleo"),
    ("adp", "ADP"),
    ("ashby", "Ashby"),
]


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    banner = f"""
{CYAN}{BOLD}  ____  _             _       _       ____        _
 / ___|(_)_   ____ _ ( )___   | | ___ | __ )  ___ | |_
 \\___ \\| \\ \\ / / _` ||// __| _| |/ _ \\|  _ \\ / _ \\| __|
  ___) | |\\ V / (_| |  \\__ \\| | | (_) | |_) | (_) | |_
 |____/|_| \\_/ \\__,_|  |___/ |_|\\___/|____/ \\___/ \\__|{RESET}
{DIM}  AI-Powered Job Application Bot | DeepSeek LLM | 13+ ATS Platforms{RESET}
"""
    print(banner)


def print_header(text):
    width = 60
    print(f"\n{BOLD}{BLUE}{'=' * width}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * width}{RESET}\n")


def prompt_choice(prompt_text, valid_choices, allow_multiple=False):
    """Get user input with validation."""
    while True:
        raw = input(f"{ARROW} {prompt_text}: ").strip()
        if not raw:
            continue

        if allow_multiple:
            choices = [c.strip() for c in raw.replace(",", " ").split()]
            if all(c in valid_choices for c in choices):
                return choices
            invalid = [c for c in choices if c not in valid_choices]
            print(f"  {RED}Invalid: {', '.join(invalid)}. Try again.{RESET}")
        else:
            if raw in valid_choices:
                return raw
            print(f"  {RED}Invalid choice. Options: {', '.join(valid_choices)}{RESET}")


def prompt_yes_no(prompt_text, default="y"):
    """Get yes/no input."""
    suffix = "[Y/n]" if default == "y" else "[y/N]"
    raw = input(f"{ARROW} {prompt_text} {DIM}{suffix}{RESET}: ").strip().lower()
    if not raw:
        return default == "y"
    return raw in ("y", "yes")


def prompt_text(prompt_text, default=""):
    """Get text input with optional default."""
    if default:
        raw = input(f"{ARROW} {prompt_text} {DIM}[{default}]{RESET}: ").strip()
        return raw if raw else default
    while True:
        raw = input(f"{ARROW} {prompt_text}: ").strip()
        if raw:
            return raw


def select_platforms():
    """Interactive platform selection."""
    print_header("Step 1: Select Platforms")
    print(f"  {DIM}Choose which job platforms to search and apply on.{RESET}")
    print(f"  {DIM}Enter numbers separated by spaces (e.g., 1 3 5){RESET}\n")

    for i, (key, name) in enumerate(PLATFORM_LIST, 1):
        print(f"  {BOLD}{i:>2}{RESET}. {name}")
    print(f"\n  {BOLD} 0{RESET}. All platforms")

    valid = [str(i) for i in range(0, len(PLATFORM_LIST) + 1)]
    choices = prompt_choice("Select platforms", valid, allow_multiple=True)

    if "0" in choices:
        selected = [key for key, _ in PLATFORM_LIST]
    else:
        selected = [PLATFORM_LIST[int(c) - 1][0] for c in choices]

    print(f"\n  {CHECK} Selected: {', '.join(selected)}")
    return selected


def select_categories():
    """Interactive job category selection."""
    print_header("Step 2: Job Categories (CS Focused)")
    print(f"  {DIM}Choose job categories to search for.{RESET}")
    print(f"  {DIM}Enter numbers separated by spaces (e.g., 1 3){RESET}\n")

    for key, cat in CATEGORY_PRESETS.items():
        print(f"  {BOLD}{key:>2}{RESET}. {cat['name']}")
        print(f"      {DIM}Keywords: {', '.join(cat['keywords'][:3])}...{RESET}")
    print(f"\n  {BOLD} 0{RESET}. Custom (enter your own keywords)")

    valid = [str(i) for i in range(0, len(CATEGORY_PRESETS) + 1)]
    choices = prompt_choice("Select categories", valid, allow_multiple=True)

    if "0" in choices:
        custom = prompt_text("Enter keywords (comma-separated)")
        keywords = [k.strip() for k in custom.split(",")]
        exclude = ["senior staff", "principal", "director", "VP"]
        print(f"\n  {CHECK} Custom keywords: {', '.join(keywords)}")
        return keywords, exclude

    keywords = []
    exclude = []
    names = []
    for c in choices:
        cat = CATEGORY_PRESETS[c]
        keywords.extend(cat["keywords"])
        exclude.extend(cat["exclude"])
        names.append(cat["name"])

    # Deduplicate
    keywords = list(dict.fromkeys(keywords))
    exclude = list(dict.fromkeys(exclude))

    print(f"\n  {CHECK} Categories: {', '.join(names)}")
    print(f"  {CHECK} {len(keywords)} search keywords configured")
    return keywords, exclude


def select_experience():
    """Interactive experience level selection."""
    print_header("Step 3: Experience Level")
    print(f"  {DIM}Select the experience level(s) for job search.{RESET}\n")

    for key, opt in EXPERIENCE_OPTIONS.items():
        print(f"  {BOLD}{key}{RESET}. {opt['name']}")

    choice = prompt_choice("Select experience level", list(EXPERIENCE_OPTIONS.keys()))
    selected = EXPERIENCE_OPTIONS[choice]

    print(f"\n  {CHECK} Experience: {selected['name']}")
    return selected["levels"]


def select_time_filter():
    """Interactive time filter selection."""
    print_header("Step 4: Time Filter")
    print(f"  {DIM}Only show jobs posted within this time frame.{RESET}\n")

    for key, opt in TIME_OPTIONS.items():
        print(f"  {BOLD}{key}{RESET}. {opt['name']}")

    choice = prompt_choice("Select time filter", list(TIME_OPTIONS.keys()))
    selected = TIME_OPTIONS[choice]

    print(f"\n  {CHECK} Time filter: {selected['name']}")
    return selected["hours"]


def configure_location():
    """Set job search location."""
    print_header("Step 5: Location")
    location = prompt_text("Enter location (city, state or 'Remote')", "Remote")
    locations = [loc.strip() for loc in location.split(",") if loc.strip()]

    remote_only = False
    if any("remote" in loc.lower() for loc in locations):
        remote_only = prompt_yes_no("Search remote-only positions?", "n")

    print(f"\n  {CHECK} Locations: {', '.join(locations)}")
    if remote_only:
        print(f"  {CHECK} Remote-only filter: ON")
    return locations, remote_only


def configure_credentials(platforms):
    """Prompt for platform credentials."""
    print_header("Step 6: Platform Credentials")
    creds = {}

    needs_creds = {"linkedin", "indeed"}
    active_cred_platforms = [p for p in platforms if p in needs_creds]

    if not active_cred_platforms:
        print(f"  {DIM}No selected platforms require login credentials.{RESET}")
        return creds

    for platform in active_cred_platforms:
        name = platform.capitalize()
        print(f"\n  {BOLD}{name} Credentials:{RESET}")
        has_creds = prompt_yes_no(f"Configure {name} login?", "y")
        if has_creds:
            username = prompt_text(f"  {name} email/username")
            password = prompt_text(f"  {name} password")
            creds[platform] = {"username": username, "password": password}
        else:
            print(f"  {DIM}Skipped - will attempt to use saved browser session{RESET}")

    return creds


def configure_ai():
    """Prompt for AI settings."""
    print_header("Step 7: AI Configuration (DeepSeek)")
    print(f"  {DIM}DeepSeek powers resume tailoring, cover letters, and form filling.{RESET}")
    print(f"  {DIM}Get an API key at: https://platform.deepseek.com{RESET}\n")

    api_key = prompt_text("DeepSeek API key (or press Enter to skip)", "")

    if not api_key:
        print(f"\n  {YELLOW}! AI features will be disabled. Bot can still fill forms with config data.{RESET}")
        return {"api_key": "", "threshold": 0.6}

    threshold = prompt_text("Job match score threshold (0.0-1.0)", "0.6")
    try:
        threshold = float(threshold)
    except ValueError:
        threshold = 0.6

    print(f"\n  {CHECK} DeepSeek API configured")
    print(f"  {CHECK} Score threshold: {threshold}")
    return {"api_key": api_key, "threshold": threshold}


def configure_safety():
    """Safety and rate-limiting settings."""
    print_header("Step 8: Safety Settings")

    max_apps = prompt_text("Max applications per day", "50")
    try:
        max_apps = int(max_apps)
    except ValueError:
        max_apps = 50

    dry_run = prompt_yes_no("Start in dry-run mode? (simulates without applying)", "y")
    pause = prompt_yes_no("Pause before each submit for manual review?", "n")

    print(f"\n  {CHECK} Max daily applications: {max_apps}")
    print(f"  {CHECK} Dry run: {'ON' if dry_run else 'OFF'}")
    print(f"  {CHECK} Pause before submit: {'ON' if pause else 'OFF'}")
    return {
        "max_apps": max_apps,
        "dry_run": dry_run,
        "pause_before_submit": pause,
    }


def add_application_urls():
    """Optionally add direct application URLs."""
    print_header("Step 9: Direct Application URLs (Optional)")
    print(f"  {DIM}Paste job application URLs for direct ATS applications.{RESET}")
    print(f"  {DIM}The bot auto-detects the ATS platform (Greenhouse, Lever, Workday, etc.){RESET}")
    print(f"  {DIM}Enter URLs one per line. Type 'done' when finished.{RESET}\n")

    urls = []
    while True:
        url = input(f"  {DIM}URL (or 'done'):{RESET} ").strip()
        if url.lower() in ("done", "d", ""):
            break
        if url.startswith("http"):
            urls.append(url)
            print(f"  {CHECK} Added: {url[:60]}...")
        else:
            print(f"  {RED}Invalid URL. Must start with http:// or https://{RESET}")

    if urls:
        print(f"\n  {CHECK} {len(urls)} application URLs added")
    return urls


def build_config(
    platforms, keywords, exclude, experience, hours,
    locations, remote_only, creds, ai_settings, safety, urls,
):
    """Build the final config dict from user selections."""
    # Load existing config as base
    config_path = Path(CONFIG_PATH)
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # Search
    config.setdefault("search", {})
    config["search"]["keywords"] = {
        "include": keywords,
        "exclude": exclude,
    }
    config["search"]["locations"] = locations
    config["search"]["remote_only"] = remote_only
    config["search"]["experience_levels"] = experience
    config["search"]["posted_within_hours"] = hours
    config["search"].setdefault("job_types", ["full_time", "contract"])

    # Platforms
    config.setdefault("platforms", {})
    for key, _ in PLATFORM_LIST:
        config["platforms"].setdefault(key, {})
        config["platforms"][key]["enabled"] = key in platforms

    # Credentials
    for platform, pcreds in creds.items():
        config["platforms"][platform]["username"] = pcreds["username"]
        config["platforms"][platform]["password"] = pcreds["password"]

    # AI
    config.setdefault("ai", {})
    if ai_settings["api_key"]:
        config["ai"]["deepseek_api_key"] = ai_settings["api_key"]
    config["ai"]["job_scoring_threshold"] = ai_settings["threshold"]

    # Safety
    config.setdefault("safety", {})
    config["safety"]["max_applications_per_day"] = safety["max_apps"]
    config["safety"]["dry_run"] = safety["dry_run"]
    config["safety"]["pause_before_submit"] = safety["pause_before_submit"]

    # URLs
    config["application_urls"] = urls

    return config


def print_summary(config):
    """Print a summary of the configuration before launch."""
    print_header("Launch Summary")

    search = config.get("search", {})
    platforms_cfg = config.get("platforms", {})
    safety = config.get("safety", {})

    active_platforms = [k for k, v in platforms_cfg.items() if v.get("enabled")]
    keywords = search.get("keywords", {}).get("include", [])
    experience = search.get("experience_levels", [])
    locations = search.get("locations", [])
    hours = search.get("posted_within_hours", 0)
    urls = config.get("application_urls", [])

    print(f"  {BOLD}Platforms:{RESET}    {', '.join(active_platforms)}")
    print(f"  {BOLD}Keywords:{RESET}     {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
    print(f"  {BOLD}Experience:{RESET}   {', '.join(experience)}")
    print(f"  {BOLD}Locations:{RESET}    {', '.join(locations)}")

    time_label = "Any time"
    for opt in TIME_OPTIONS.values():
        if opt["hours"] == hours:
            time_label = opt["name"]
            break
    print(f"  {BOLD}Time filter:{RESET}  {time_label}")

    print(f"  {BOLD}Max daily:{RESET}    {safety.get('max_applications_per_day', 50)}")
    print(f"  {BOLD}Dry run:{RESET}      {'YES' if safety.get('dry_run') else 'NO'}")
    print(f"  {BOLD}Direct URLs:{RESET}  {len(urls)}")

    has_ai = bool(config.get("ai", {}).get("deepseek_api_key"))
    print(f"  {BOLD}AI enabled:{RESET}   {'YES' if has_ai else 'NO'}")

    print()


def save_and_run(config):
    """Save config and launch the bot."""
    # Save config
    config_path = Path(CONFIG_PATH)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"  {CHECK} Config saved to {CONFIG_PATH}")

    proceed = prompt_yes_no(f"\n{BOLD}Launch the bot now?{RESET}", "y")
    if not proceed:
        print(f"\n  {DIM}Config saved. Run later with: python run.py{RESET}")
        return

    print(f"\n{GREEN}{BOLD}  Launching Siva Job Bot...{RESET}\n")
    print(f"{'=' * 60}")

    from src.main import JobBot
    bot = JobBot(config_path=str(config_path))
    bot.run(dry_run=config.get("safety", {}).get("dry_run", False))


def run_interactive():
    """Run the full interactive configuration wizard."""
    clear_screen()
    print_banner()

    platforms = select_platforms()
    keywords, exclude = select_categories()
    experience = select_experience()
    hours = select_time_filter()
    locations, remote_only = configure_location()
    creds = configure_credentials(platforms)
    ai_settings = configure_ai()
    safety = configure_safety()
    urls = add_application_urls()

    config = build_config(
        platforms, keywords, exclude, experience, hours,
        locations, remote_only, creds, ai_settings, safety, urls,
    )

    clear_screen()
    print_banner()
    print_summary(config)
    save_and_run(config)


def run_quick():
    """Quick launch using existing config."""
    clear_screen()
    print_banner()

    config_path = Path(CONFIG_PATH)
    if not config_path.exists():
        print(f"  {RED}No config found at {CONFIG_PATH}. Running interactive setup...{RESET}\n")
        run_interactive()
        return

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    print_summary(config)

    dry_run = prompt_yes_no("Run in dry-run mode?", "y")
    config.setdefault("safety", {})["dry_run"] = dry_run

    save_and_run(config)


def main():
    parser = argparse.ArgumentParser(description="Siva Job Bot - Interactive Launcher")
    parser.add_argument("--quick", action="store_true", help="Quick launch with saved config")
    args = parser.parse_args()

    try:
        if args.quick:
            run_quick()
        else:
            run_interactive()
    except KeyboardInterrupt:
        print(f"\n\n  {YELLOW}Cancelled by user.{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
