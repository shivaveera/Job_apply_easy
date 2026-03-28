# Siva Job Bot

AI-powered automated job application bot that combines the best approaches from 6 analyzed open-source job bots into a single, superior tool.

## Why This Is Better

This bot was built after deep analysis of AIHawk, Auto_job_applier_linkedIn, JobHuntr, linkedin-easyapply-using-AI, EasyApplyJobsBot, and linkedIn_auto_jobs_applier_with_AI. It cherry-picks the best features from each:

| Feature | Source Inspiration | Implementation |
|---------|-------------------|----------------|
| Anti-detection | Auto_job_applier | undetected-chromedriver + real Chrome profiles + native input simulation |
| Form filling | AIHawk Fork | Context-aware question routing + Levenshtein fuzzy matching + answer caching |
| LLM integration | AIHawk | Single DeepSeek client wrapper (cheaper than OpenAI, OpenAI-compatible SDK) |
| Resume tailoring | AIHawk | Per-job ATS-optimized resume generation via AI |
| Job filtering | Auto_job_applier | Smart salary formatting, company whitelist/blacklist, bad word filtering |
| Rate limiting | AIHawk Fork | Multi-layered gaussian delays (not uniform random) |
| Tracking | Auto_job_applier | SQLite database + CLI dashboard + CSV export |
| Notifications | linkedin-easyapply-using-AI | Telegram real-time + email daily digest |
| Dry-run mode | EasyApplyJobsBot | Full simulation without submitting |
| Architecture | AIHawk Fork | Clean modular design with Facade pattern |

## Features

- **Multi-Platform Support:** LinkedIn Easy Apply (primary), Indeed (stub), Greenhouse (stub)
- **DeepSeek AI Only:** Single LLM provider, no scattered API calls, response caching in SQLite
- **Smart Job Filtering:** Keywords, company blacklist/whitelist, salary range, location, experience level, description bad words
- **AI-Powered Form Filling:** Handles text, dropdowns, radio buttons, checkboxes, file uploads with Q&A caching
- **Per-Job Resume Tailoring:** ATS-optimized resume generation from markdown base
- **AI Cover Letters:** Personalized cover letter generation per application
- **Anti-Detection:** Gaussian delays, Chrome profile persistence, user agent rotation, stealth mode
- **Application Tracking:** SQLite database, CLI dashboard, CSV export, follow-up reminders
- **Notifications:** Telegram (real-time) and email (daily digest)
- **Safety:** Dry-run mode, daily limits, session breaks, active hours, pause-before-submit

## Installation

### Prerequisites

- Python 3.12+
- Google Chrome (latest version)
- DeepSeek API key (get from https://platform.deepseek.com)

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd siva-job-bot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure the bot
cp config/config.yaml config/config.yaml.bak  # Backup
# Edit config/config.yaml with your settings (see Configuration Guide below)

# 5. Edit your resume
# Edit config/resume_base.md with your actual resume in Markdown format

# 6. Run the bot
python run.py --dry-run    # Test first!
python run.py              # Live mode
```

### Optional Dependencies

```bash
# For Telegram notifications
pip install pyTelegramBotAPI

# For better PDF generation (recommended)
sudo apt install pandoc texlive-xetex  # Linux
# brew install pandoc mactex            # macOS
```

## Configuration Guide

The main configuration is in `config/config.yaml`. Here are the key sections:

### Personal Info

```yaml
personal:
  name: "Your Name"
  email: "your@email.com"
  phone: "(555) 123-4567"
  location: "Dallas-Fort Worth, TX"
  linkedin_url: "https://linkedin.com/in/yourprofile"
  github_url: "https://github.com/yourusername"
```

### Search Preferences

```yaml
search:
  keywords:
    include: ["software engineer", "developer", "python"]
    exclude: ["senior staff", "principal", "VP"]
  locations: ["Dallas, TX", "Remote"]
  remote_only: false
  experience_levels: ["entry", "mid", "senior"]
  salary_min: 80000
  posted_within_hours: 24
  companies:
    blacklist: ["Bad Company Inc"]
    whitelist: []
  description_bad_words: ["security clearance required"]
```

### AI Settings (DeepSeek)

```yaml
ai:
  deepseek_api_key: "sk-..."  # Required
  deepseek_base_url: "https://api.deepseek.com/v1"
  models:
    scoring: "deepseek-chat"       # V3 for job scoring
    form_filling: "deepseek-chat"  # V3 for answering questions
    resume: "deepseek-chat"        # V3 for resume tailoring
    cover_letter: "deepseek-chat"  # V3 for cover letters
    reasoning: "deepseek-reasoner" # R1 for complex decisions (optional)
  temperature: 0.3
  cache_responses: true            # Saves money on repeated questions
  job_scoring_threshold: 0.6       # 0-1, minimum relevance to apply
```

### Safety Settings

```yaml
safety:
  max_applications_per_day: 50
  delay_between_apps_seconds: [30, 90]  # Gaussian random range
  session_break_after: 15               # Break after N applications
  session_break_minutes: [5, 15]        # Break duration range
  active_hours: ["08:00", "22:00"]      # Don't apply at 3 AM
  dry_run: false
  pause_before_submit: false
  conservative_mode: true               # Slower, more human-like
```

### Q&A Overrides

Edit `config/qa_overrides.yaml` to set manual answers for common questions:

```yaml
overrides:
  "authorized to work": "Yes"
  "require sponsorship": "No"
  "years of experience": "5"
  "desired salary": "80000"
```

These take priority over AI-generated answers.

## Usage Examples

### Dry Run (Recommended First)

```bash
python run.py --dry-run
```

Searches for jobs, scores them with AI, but does NOT submit any applications. Shows what would happen.

### Normal Mode

```bash
python run.py
```

Full automation: search, score, fill forms, submit applications.

### Conservative Mode

Set in `config.yaml`:

```yaml
safety:
  conservative_mode: true
  delay_between_apps_seconds: [60, 180]
  session_break_after: 10
  pause_before_submit: true  # Manual review before each submit
```

### Aggressive Mode

```yaml
safety:
  conservative_mode: false
  delay_between_apps_seconds: [20, 45]
  session_break_after: 25
  max_applications_per_day: 100
```

**Warning:** Aggressive mode increases the risk of account detection.

### View Statistics

```bash
python run.py --stats
```

### Export to CSV

```bash
python run.py --export
```

### Check Follow-ups

```bash
python run.py --followup 7  # Applications older than 7 days
```

## Supported Platforms

| Platform | Status | Features |
|----------|--------|----------|
| **LinkedIn Easy Apply** | Fully Implemented | Login, search, filter, form fill, submit |
| **Indeed** | Stub | Architecture ready, implementation pending |
| **Greenhouse** | Stub | Architecture ready, implementation pending |
| **Lever** | Planned | - |
| **Workday** | Planned | - |

## Project Structure

```
siva-job-bot/
├── config/
│   ├── config.yaml              # Main configuration
│   ├── resume_base.md           # Your resume in Markdown
│   ├── cover_letter_template.md # Cover letter template
│   └── qa_overrides.yaml        # Manual Q&A answers
├── src/
│   ├── main.py                  # Bot orchestrator
│   ├── platforms/
│   │   ├── base.py              # Abstract platform interface
│   │   ├── linkedin.py          # LinkedIn Easy Apply (primary)
│   │   ├── indeed.py            # Indeed (stub)
│   │   └── greenhouse.py        # Greenhouse (stub)
│   ├── ai/
│   │   ├── deepseek_client.py   # DeepSeek API wrapper + caching
│   │   ├── prompts.py           # All prompt templates
│   │   ├── form_filler.py       # AI form filling + Levenshtein matching
│   │   ├── resume_gen.py        # Per-job resume tailoring
│   │   ├── cover_letter.py      # Cover letter generation
│   │   └── job_scorer.py        # Job relevance scoring
│   ├── browser/
│   │   ├── stealth.py           # Anti-detection configuration
│   │   └── driver.py            # Browser lifecycle management
│   ├── tracking/
│   │   ├── database.py          # SQLite application tracking
│   │   └── dashboard.py         # CLI statistics display
│   ├── notifications/
│   │   ├── telegram.py          # Telegram bot notifications
│   │   └── email.py             # Email digest notifications
│   └── utils/
│       ├── logger.py            # Logging configuration
│       └── humanizer.py         # Human-like behavior simulation
├── data/                        # Generated data (gitignored)
│   ├── applications.db          # SQLite database
│   ├── ai_cache.db              # AI response cache
│   ├── resumes/                 # Generated PDFs
│   ├── cover_letters/           # Generated cover letters
│   └── logs/                    # Application logs
├── tests/
├── requirements.txt
├── setup.py
├── run.py                       # Entry point
└── README.md
```

## Anti-Detection Best Practices

1. **Use conservative mode** for the first few runs
2. **Don't exceed 50 applications/day** — LinkedIn tracks application velocity
3. **Use your real Chrome profile** — it has natural browsing history and cookies
4. **Run during normal hours** (8 AM - 10 PM) — configure `active_hours`
5. **Take breaks** — `session_break_after: 15` adds natural pauses
6. **Don't run headless** — visible browser behaves more naturally
7. **Vary your search terms** — don't run the same query repeatedly
8. **Monitor for security challenges** — the bot will pause and wait for manual CAPTCHA completion

## Troubleshooting

### "ChromeDriver not found"

```bash
pip install webdriver-manager
# Or install Chrome and chromedriver manually
```

### "LinkedIn security challenge detected"

The bot will pause for up to 5 minutes. Complete the CAPTCHA manually in the browser window, then the bot continues automatically.

### "DeepSeek API error"

- Check your API key in `config.yaml`
- Verify you have credits at https://platform.deepseek.com
- The bot retries 3 times with exponential backoff

### "No jobs found"

- Broaden your search keywords
- Try different locations
- Increase `posted_within_hours`
- Check that `experience_levels` matches your profile

### Browser crashes

- Ensure Chrome is updated to the latest version
- Try with `conservative_mode: true`
- Disable Chrome profile with `use_profile: false`

## Cost Estimation

DeepSeek V3 pricing (as of 2026):
- Input: $0.27 per million tokens
- Output: $1.10 per million tokens

Estimated cost per application:
- Job scoring: ~$0.001
- Form filling (5 questions): ~$0.003
- Resume tailoring: ~$0.005
- Cover letter: ~$0.003

**Total: ~$0.01-0.02 per application, or ~$0.50-1.00 for 50 applications/day**

With response caching enabled, repeated questions cost nothing.

## Disclaimer

**This tool is for educational and personal use only.** By using this software:

- You acknowledge that automated job applications may violate the Terms of Service of LinkedIn and other platforms
- You accept full responsibility for any consequences, including potential account restrictions or bans
- You understand that aggressive automation increases detection risk
- You will use the tool responsibly with appropriate rate limiting
- The authors are not responsible for any account actions taken by job platforms

**Recommendations:**
- Always start with `--dry-run` to test your configuration
- Use conservative settings initially
- Monitor your account for any warnings
- Keep your application quality high — AI-generated responses should be reviewed periodically

## License

MIT License
