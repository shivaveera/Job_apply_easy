# Deep Analysis Report: 6 Job Application Bot Repositories

**Date:** 2026-03-28
**Purpose:** Comprehensive analysis of open-source job application automation tools to inform the design of a superior unified bot.

---

## Table of Contents

1. [AIHawk (Jobs_Applier_AI_Agent_AIHawk)](#1-aihawk)
2. [Auto_job_applier_linkedIn](#2-auto_job_applier_linkedin)
3. [JobHuntr / job-application-bot-by-ollama-ai](#3-jobhuntr)
4. [linkedin-easyapply-using-AI](#4-linkedin-easyapply-using-ai)
5. [EasyApplyJobsBot](#5-easyapplyjobsbot)
6. [linkedIn_auto_jobs_applier_with_AI (AIHawk Fork)](#6-aihawk-fork)
7. [Cross-Cutting Insights](#7-cross-cutting-insights)

---

## 1. AIHawk (Jobs_Applier_AI_Agent_AIHawk)

**GitHub:** feder-cr/Jobs_Applier_AI_Agent_AIHawk
**Stars:** Most popular of the 6
**Status:** Core job application logic REMOVED (copyright reasons); now primarily a resume/cover letter generator

### Architecture & Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.x |
| Browser Automation | Selenium 4.9.1 (undetected-chromedriver in requirements but unused) |
| AI/LLM | LangChain abstraction supporting 6 providers: OpenAI, Claude, Gemini, Ollama, HuggingFace, Perplexity |
| Storage | YAML configs, JSON logs, filesystem for generated PDFs |
| Config | YAML (secrets, work preferences, resume) with Pydantic validation |
| Logging | Loguru with file rotation (10MB, 1-week retention, ZIP compression) |
| CLI | Click + Inquirer for interactive prompts |

### Core Features

- **Job Search & Filtering:** Framework exists (Job dataclass, config supports keywords, blacklists, experience levels, date filters, distance radius) but actual scraping code REMOVED
- **Form Filling:** `GPTAnswerer` class with methods for text, numeric, and multiple-choice questions — but implementation removed
- **Resume Generation:** PRIMARY FOCUS — full pipeline: YAML → Pydantic Resume → LLM-tailored HTML sections → CDP-based PDF via Selenium
- **Cover Letter:** Specialized `LLMCoverLetterJobDescription` class generates HTML cover letters with job context
- **Job-Specific Tailoring:** `LLMResumeJobDescription` re-writes each resume section to match job description
- **RAG-Based Job Parsing:** FAISS vector store + OpenAI embeddings for intelligent job description extraction (TokenTextSplitter: 500 tokens, 50 overlap)
- **Job Suitability Scoring:** LLM scores jobs 1-10 against resume; configurable threshold (default: 7)

### Anti-Detection

- Basic Chrome options (incognito, disable-web-security, disable-extensions)
- CDP-based PDF generation (less detectable than screenshots)
- Rate limiting: 30-60 second waits, exponential backoff for 429s
- **Missing:** No proxy rotation, no user agent rotation, no behavioral delays, no mouse movement simulation

### Code Quality: 7/10

- **Strengths:** Clean design patterns (Adapter, Facade, Strategy, Template Method, Factory), Pydantic validation, multi-LLM abstraction, comprehensive logging with cost tracking
- **Weaknesses:** Monolithic main.py (565 lines), removed core functionality, hardcoded token prices, global config object

### Unique/Clever Features

1. **RAG-based job parsing** with FAISS — more sophisticated than regex
2. **Multi-LLM abstraction** — single codebase supports 6 LLM providers
3. **CSS-based resume style system** — pluggable styles with metadata extraction
4. **LLM cost tracking** — logs every API call with token counts and estimated costs
5. **Prompt template abstraction** — prompts in separate module files, loaded dynamically

---

## 2. Auto_job_applier_linkedIn

**GitHub:** GodsScion/Auto_job_applier_linkedIn
**Status:** Active, feature-rich, production-grade

### Architecture & Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Browser Automation | Selenium + undetected-chromedriver (stealth mode toggle) |
| AI/LLM | OpenAI, DeepSeek, Gemini (3 providers with OpenAI-compatible abstraction) |
| Storage | CSV files for tracking, Python config files |
| Config | Python files (secrets.py, settings.py, search.py, questions.py, personals.py) |
| Logging | Custom dual-output (console + file) |
| UI | Flask web dashboard for tracking applied jobs |

### Core Features

- **Job Search & Filtering:** Most comprehensive filtering — experience level, job type, work style, salary range, companies (whitelist/blacklist with exceptions), bad words in descriptions, security clearance filter, master's degree filter, experience threshold
- **Form Filling:** Sophisticated type detection — dropdowns (bidirectional fuzzy matching), radio buttons, text inputs (smart label analysis for salary/notice/location/name), textareas, checkboxes, address fields
- **Smart Salary Handling:** Auto-detects currency format (lakhs, monthly, annual) and converts accordingly
- **Notice Period Conversion:** Auto-converts days → weeks/months based on question label
- **Resume:** Default resume upload with fallback; AI-based customization in development
- **Anti-Detection:** undetected-chromedriver, real Chrome profile usage, randomized click intervals (0.6-3.0s), smooth scrolling, screen keep-awake, multi-tab support, visible window mode
- **Tracking:** CSV with 18+ fields, Flask web UI dashboard, session summaries
- **Rate Limiting:** Daily Easy Apply limit detection, configurable switch_number per search term, randomized click gaps

### Anti-Detection: Best-in-Class

1. Undetected ChromeDriver with auto-patching
2. Real Chrome profile persistence (cross-platform detection)
3. Randomized timing via `buffer()` function (non-uniform distribution)
4. Human-like smooth scrolling
5. PyAutoGUI for native OS-level input simulation
6. Screen keep-awake (prevents screensaver)
7. Multi-tab support (reduces "always applying" pattern)
8. Session persistence across runs
9. No fixed delay patterns

### Code Quality: 7.5/10

- **Strengths:** Clean modular architecture, comprehensive config validation framework, contributor guidelines with documentation standards, type hints, cross-platform support
- **Weaknesses:** Main file still large (1267 lines), credentials in plaintext config files
- **Notable:** Contributor attestation system with format requirements

### Unique/Clever Features

1. **Bidirectional fuzzy matching** for dropdown options
2. **Smart salary/notice period formatting** based on label context
3. **Company whitelist/blacklist with exceptions** (good words override bad words)
4. **Daily Easy Apply limit detection** (auto-stops when LinkedIn cap hit)
5. **Questions memory system** — tracks randomly answered questions for user review
6. **Flask web dashboard** for application tracking
7. **Multi-LLM with local model support** (Ollama, LM Studio via OpenAI-compatible endpoint)
8. **Cross-platform Chrome profile detection** (Windows/Linux/macOS)

---

## 3. JobHuntr (job-application-bot-by-ollama-ai)

**GitHub:** lookr-fyi/job-application-bot-by-ollama-ai
**Status:** CLOSED-SOURCE commercial product (documentation only in repo)

### Architecture (Inferred from Docs)

| Component | Technology |
|-----------|-----------|
| Platform | Desktop app (macOS .dmg, Windows .exe) |
| AI | Free: Local Ollama (4B+ models); Premium: GPT-4o + Claude 3 Sonnet |
| Browser | Embedded Chromium riding user's Chrome profile |
| Storage | Local + cloud sync (premium) |

### Core Features (from Documentation)

- **Multi-Platform:** LinkedIn, Indeed, ZipRecruiter, Glassdoor, Dice, ANY company career page (universal as of v3.0.0)
- **Smart Filtering:** Semantic AI matching (not keyword-based)
- **ATS Resume Optimization:** Per-application resume tailoring
- **Cover Letter:** Personalized per job
- **Outreach Automation:** UNIQUE — automated messaging to hiring managers, peers, recruiters
- **D.A.M.N Mode:** Headless/daemon mode (runs without browser window)
- **Infinite Hunt:** 24/7 continuous operation with auto-tuning
- **Community Job Board:** Crowdsourced job discovery
- **Rate Limiting:** 25/day (free), 35-45/day (premium)

### Anti-Detection Philosophy

- "Respectful automation" — own IP, user's Chrome profile, no mass scraping
- Human-like delays, rate limiting, duplicate prevention
- Open communication with platforms (PLATFORM_LETTER.md)
- Explicitly contrasts with "risky" tools

### Code Quality: N/A (Closed Source)

### Unique/Clever Features

1. **Universal career page support** — applies on ANY website
2. **Hiring manager outreach automation** — exclusive feature
3. **Community job board** — crowdsourced discovery
4. **AI reasoning transparency** — shows decision process with references
5. **Free tier with local Ollama** — no API costs

---

## 4. linkedin-easyapply-using-AI

**GitHub:** srikar-kodakandla/linkedin-easyapply-using-AI
**Status:** Active but monolithic

### Architecture & Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3 |
| Browser Automation | undetected-chromedriver |
| AI/LLM | GPT-4 (via gpt4_openai web wrapper) + Google Gemini (API fallback) |
| Storage | Pickle files for applied job tracking |
| Config | JSON per user ({email_prefix}.json) |
| Notifications | Telegram bot integration |

### Core Features

- **Job Search:** Multi-keyword, multi-location, remote/hybrid filters, 40-page pagination limit
- **Form Filling:** Three types: text inputs, radio buttons, dropdowns. **Two-pass LLM strategy** — Pass 1: detailed reasoning with resume context, Pass 2: constrained output extraction
- **Lenient JSON Parsing:** Uses demjson3 for tolerant parsing of LLM output (handles markdown blocks, malformed JSON)
- **Dual LLM Backend:** ChatGPT (primary) with Gemini fallback for cost savings
- **Role Filtering:** Keyword whitelist/blacklist with case-insensitive matching
- **Telegram Notifications:** Real-time updates on applications, errors, runtime stats
- **Progressive Completion Logic:** Adjusts strategy based on form completion percentage

### Anti-Detection

- undetected-chromedriver (primary defense)
- Random delays: 4-6s page nav, 5-10s job views, fixed 8s form fills
- Scroll simulation with ActionChains
- LinkedIn verification detection (drops to debugger for manual CAPTCHA)
- **Missing:** No proxy rotation, no user agent rotation, predictable fixed delays

### Code Quality: 4/10

- **Critical Issues:** Monolithic single file (783 lines), 50+ bare `except: pass` blocks, global variable injection from JSON, hardcoded XPath selectors, credentials in plaintext JSON, no docstrings, no type hints
- **Strengths:** Functional, Telegram integration works, dual-LLM fallback

### Unique/Clever Features

1. **Two-pass LLM form filling** — reasoning first, then extraction (reduces hallucination)
2. **Lenient JSON parsing** with demjson3 (handles LLM output quirks)
3. **Date-aware resume injection** — appends today's date for availability questions
4. **Error message-driven form filling** — reads validation errors and includes in prompt
5. **Progressive completion logic** — adjusts retry strategy based on form % complete

---

## 5. EasyApplyJobsBot

**GitHub:** wodsuz/EasyApplyJobsBot (rebranded as "Apllie")
**Status:** Active, lean codebase

### Architecture & Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| Browser Automation | Selenium 4.0+ with selenium-stealth |
| AI/LLM | None (template-based answers from YAML) |
| Storage | Text files for daily logs, pickle for cookies |
| Config | Python config file + YAML for form answers |
| Deployment | Docker support (Dockerfile + docker-compose) |

### Core Features

- **Job Search:** Keywords, location (with geoId mapping for continents), experience levels, date posted, job type, remote/hybrid, salary range, sort order
- **Form Filling:** NO AI — pre-filled answers from `additionalQuestions.yaml` (96+ fields covering skills, languages, salary, education). Phone number fuzzy matching with 7 CSS + 4 XPath fallback selectors
- **Multi-Step Navigation:** Reverse-engineers step count from LinkedIn's completion percentage
- **Applied Status Detection:** Checks for "Applied" label without clicking each job
- **Dry-Run Mode:** Navigate and log without submitting
- **Cookie Persistence:** MD5-hashed email → pickle file
- **Docker Deployment:** Full containerization with volume mounts

### Anti-Detection

1. **selenium-stealth** — spoofs navigator properties (languages, vendor, platform, WebGL)
2. Chrome options hardening (disable-blink-features=AutomationControlled, excludeSwitches, useAutomationExtension=False)
3. Randomized delays (uniform 1-5s based on configurable botSpeed)
4. Chrome profile support (inherits real browsing history)
5. Cookie persistence across sessions

### Code Quality: 6/10

- **Strengths:** Clean 4-file structure (~1000 lines total), clear separation of concerns, dry-run mode, Docker support
- **Weaknesses:** No AI integration, limited class hierarchy, generic exception catching, credentials in config.py

### Unique/Clever Features

1. **Job ID pre-caching** — extracts data-attributes to avoid StaleElementReferenceException
2. **Completion percentage math** — reverse-engineers form steps from LinkedIn's progress bar
3. **Continent-level geoId mapping** — "Europe" → `geoId=100506914`
4. **Phone field fuzzy matching** — 11 different selector strategies
5. **Docker deployment** — only bot with full containerization
6. **No AI dependency** — works offline with pre-configured answers

---

## 6. linkedIn_auto_jobs_applier_with_AI (AIHawk Fork)

**GitHub:** jomacs/linkedIn_auto_jobs_applier_with_AI
**Status:** Active, cleaner fork of AIHawk

### Architecture & Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Browser Automation | Selenium 4.9.1 with webdriver-manager |
| AI/LLM | OpenAI GPT-4o-mini via LangChain |
| Storage | JSON files (answers cache, success/failed/skipped logs, LLM call logs) |
| Config | YAML (secrets, config, plain_text_resume) |
| Resume Gen | External lib_resume_builder_AIHawk library |

### Core Features

- **Job Search:** Multi-position × multi-location cross-product, Easy Apply filter, experience/job type/date filters, company/title blacklists
- **Form Filling:** Comprehensive type routing — radio buttons, text inputs, textareas, date pickers, dropdowns, file uploads, terms of service checkboxes. Answer caching with text sanitization
- **Levenshtein fuzzy matching** for option selection (handles LLM creative responses)
- **Context-aware resume section routing** — meta-prompt classifies question → selects relevant resume section → generates targeted answer
- **Dynamic PDF resume per job** — generates unique tailored resume for each application
- **Cover Letter:** Generated via GPT, rendered to PDF with reportlab

### Anti-Detection

1. Chrome options (excludeSwitches, disable automation flags)
2. Chrome profile persistence (`chrome_profile/linkedin_profile`)
3. Image/CSS blocking (reduces bandwidth + detection surface)
4. **Multi-layered rate limiting:**
   - Click/type: 1.5-2.5s random
   - Page scroll: 1.0-2.6s random per step
   - Form submission: 3-5s random
   - Per-page minimum: 15 minutes
   - Every 5 pages: 5-34 minute random sleep
   - Every 5 location cycles: 50-90 minute random sleep
5. Manual security challenge handling (5-minute window for CAPTCHA)

### Code Quality: 8/10 (Best of the 6)

- **Strengths:** Clean 10-file architecture (~1,900 lines), explicit state management (LinkedInBotState), Facade pattern for orchestration, ConfigValidator with strict YAML validation, environment variable support (SKIP_APPLY, DISABLE_DESCRIPTION_FILTER), type hints in dataclasses
- **Weaknesses:** No inline docstrings, LinkedIn-only, requires manual CAPTCHA solving

### Unique/Clever Features

1. **Levenshtein distance matching** for fuzzy option selection
2. **Context-aware resume section routing** (13 section types)
3. **Answer caching with text sanitization** (deduplication across runs)
4. **Multi-layered rate limiting** (most sophisticated of all 6)
5. **State machine pattern** for initialization order enforcement
6. **Decorator pattern for LLM logging** (wraps ChatOpenAI transparently)
7. **Dynamic per-job resume generation** via external library

---

## 7. Cross-Cutting Insights

### Best Approaches by Category

| Category | Winner | Why |
|----------|--------|-----|
| **Anti-Detection** | Auto_job_applier | undetected-chromedriver + real profiles + native input + randomized timing |
| **Form Filling** | AIHawk Fork | Context-aware routing + Levenshtein matching + answer caching |
| **LLM Integration** | AIHawk (original) | 6-provider abstraction via LangChain |
| **Resume Tailoring** | AIHawk + Fork | Per-job LLM-tailored HTML → PDF pipeline |
| **Job Filtering** | Auto_job_applier | Most filters + smart salary/experience logic |
| **Code Architecture** | AIHawk Fork | Cleanest separation, state machine, facade pattern |
| **Tracking** | Auto_job_applier | CSV + Flask web dashboard |
| **Multi-Platform** | JobHuntr (closed) | LinkedIn + Indeed + ZipRecruiter + Glassdoor + Dice + any career page |
| **Docker/Deploy** | EasyApplyJobsBot | Only one with full Docker support |
| **Notifications** | linkedin-easyapply-using-AI | Telegram bot with real-time updates |
| **Cost Efficiency** | EasyApplyJobsBot | No AI needed (template answers) |

### Common Weaknesses Across All

1. **LinkedIn-only** (open-source ones) — no Indeed, Glassdoor, Greenhouse support
2. **No response caching** — redundant LLM calls for identical questions
3. **Plaintext credentials** — no vault/encryption support
4. **No headless anti-detection** — most need visible browser
5. **Single-threaded** — no concurrent processing
6. **No notification diversity** — at most Telegram; no email/Slack/Discord
7. **Manual CAPTCHA** — all require human intervention for verification

### Key Design Decisions for Our Bot

Based on this analysis, the optimal bot should combine:

1. **From Auto_job_applier:** Anti-detection stack (undetected-chromedriver + real profiles + native input), smart salary/notice formatting, company whitelist/blacklist with exceptions, daily limit detection
2. **From AIHawk Fork:** Clean architecture (Facade + State Machine), answer caching with sanitization, Levenshtein fuzzy matching, multi-layered rate limiting, context-aware form routing
3. **From AIHawk Original:** Multi-LLM abstraction, RAG-based job parsing, per-job resume tailoring pipeline, LLM cost tracking
4. **From linkedin-easyapply-using-AI:** Two-pass LLM prompting, Telegram notifications, error-message-driven form filling
5. **From EasyApplyJobsBot:** Docker support, dry-run mode, job ID pre-caching, completion percentage math
6. **From JobHuntr (concept):** Multi-platform support, semantic job matching, hiring manager outreach
