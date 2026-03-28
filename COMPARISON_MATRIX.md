# Comparison Matrix: 6 Job Application Bot Repositories

**Date:** 2026-03-28
**Rating Key:** ✅ Full support | 🟡 Partial | ❌ Missing | 🔥 Best-in-class

---

## Tech Stack

| Feature | AIHawk | Auto_job_applier | JobHuntr | EasyApply_AI | EasyApplyBot | AIHawk_fork |
|---------|--------|------------------|----------|--------------|--------------|-------------|
| **Language** | Python 3.x | Python 3.10+ | Closed source | Python 3 | Python 3.11 | Python 3.10+ |
| **Browser Automation** | Selenium 4.9.1 | 🔥 Selenium + undetected-chromedriver | Embedded Chromium | undetected-chromedriver | Selenium + selenium-stealth | Selenium 4.9.1 |
| **AI/LLM Integration** | 🔥 6 providers (LangChain) | ✅ 3 providers (OpenAI/DeepSeek/Gemini) | ✅ Ollama + GPT-4o + Claude | 🟡 GPT-4 + Gemini | ❌ None | 🟡 OpenAI only |
| **Config Format** | ✅ YAML + Pydantic | 🟡 Python files | N/A | 🟡 JSON | 🟡 Python + YAML | ✅ YAML + validation |
| **Database/Storage** | JSON files | CSV files | Local + Cloud | Pickle files | Text files + Pickle | JSON files |
| **Docker Support** | ❌ | ❌ | N/A | ❌ | 🔥 Full (Dockerfile + compose) | ❌ |
| **Web UI** | ❌ | 🔥 Flask dashboard | ✅ Desktop app | ❌ | ❌ | ❌ |

---

## Job Search & Filtering

| Feature | AIHawk | Auto_job_applier | JobHuntr | EasyApply_AI | EasyApplyBot | AIHawk_fork |
|---------|--------|------------------|----------|--------------|--------------|-------------|
| **Keyword Search** | ✅ | 🔥 Multiple terms | ✅ | ✅ Multiple terms | ✅ Multiple terms | ✅ Multiple terms |
| **Location Filter** | ✅ | ✅ | ✅ 4 countries | ✅ Multiple | 🔥 Continent geoIds | ✅ Multiple |
| **Experience Level** | ✅ 6 levels | ✅ 6 levels | ✅ | ❌ | ✅ 6 levels | ✅ 6 levels |
| **Salary Range** | ❌ | 🔥 $40K-$200K+ tiers | ✅ | ❌ | ✅ $40K-$200K+ | ❌ |
| **Remote/Hybrid/Onsite** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Date Posted** | ✅ 4 options | ✅ 4 options | ❌ | ❌ | ✅ 4 options | ✅ 4 options |
| **Company Blacklist** | ✅ | 🔥 With exceptions | ❌ | ❌ | ✅ | ✅ |
| **Title Blacklist** | ✅ | ✅ | ❌ | ✅ Whitelist+Blacklist | ✅ | ✅ |
| **Job Description Bad Words** | ❌ | 🔥 Keywords + clearance | ❌ | ❌ | ❌ | ❌ |
| **Experience Threshold** | ❌ | 🔥 Auto-skip by years | ❌ | ❌ | ❌ | ❌ |
| **AI Job Scoring** | ✅ 1-10 scale | 🟡 AI skill extraction | ✅ Semantic | ❌ | ❌ | ❌ |
| **Easy Apply Only** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Duplicate Prevention** | ✅ | ✅ CSV check | ✅ | ✅ Pickle | ✅ Applied label | ✅ JSON check |
| **Daily Limit Detection** | ❌ | 🔥 Auto-detect | ❌ | ❌ | ✅ Max per run | ❌ |

---

## Application Form Filling

| Feature | AIHawk | Auto_job_applier | JobHuntr | EasyApply_AI | EasyApplyBot | AIHawk_fork |
|---------|--------|------------------|----------|--------------|--------------|-------------|
| **Text Input** | ✅ AI | 🔥 Smart label detection | ✅ AI | ✅ AI (2-pass) | 🟡 Phone only | ✅ AI |
| **Dropdown/Select** | ✅ AI | 🔥 Bidirectional fuzzy | ✅ AI | ✅ AI | ❌ | ✅ AI + Levenshtein |
| **Radio Buttons** | ✅ AI | ✅ Pattern matching | ✅ AI | ✅ AI | ❌ | ✅ AI |
| **Checkboxes** | ❌ | ✅ EEO handling | ✅ | ❌ | ❌ | ✅ Terms of service |
| **Date Pickers** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **File Upload** | ✅ | ✅ Default resume | ✅ | ❌ | ✅ Resume select | 🔥 Dynamic per-job |
| **Answer Caching** | ❌ | 🟡 Questions memory | ✅ FAQ tracking | ❌ | 🟡 YAML templates | 🔥 JSON with sanitization |
| **Multi-Step Forms** | ❌ (removed) | ✅ | ✅ | ✅ % tracking | 🔥 % reverse-engineer | ✅ |
| **Salary Auto-Format** | ❌ | 🔥 Lakhs/monthly/annual | ❌ | ❌ | ❌ | ❌ |
| **Error-Driven Filling** | ❌ | ❌ | ❌ | 🔥 Reads validation errors | ❌ | ✅ Error detection |
| **Fuzzy Option Matching** | ❌ | 🔥 Bidirectional | ✅ | ❌ | ❌ | 🔥 Levenshtein distance |
| **Context-Aware Routing** | ❌ | ❌ | ✅ | ❌ | ❌ | 🔥 13 resume sections |

---

## Resume & Cover Letter

| Feature | AIHawk | Auto_job_applier | JobHuntr | EasyApply_AI | EasyApplyBot | AIHawk_fork |
|---------|--------|------------------|----------|--------------|--------------|-------------|
| **Per-Job Resume Tailoring** | 🔥 LLM re-writes sections | 🟡 In development | ✅ ATS optimized | ❌ Static resume | ❌ Static resume | 🔥 Dynamic PDF per job |
| **Resume Format** | HTML → PDF (CDP) | DOCX + PDF | ❌ N/A | Plain text | PDF upload | HTML → PDF |
| **Multiple Styles** | 🔥 CSS style system | ❌ | ❌ | ❌ | ❌ | ✅ Via external lib |
| **ATS Optimization** | ✅ LLM-driven | 🟡 Planned | ✅ | ❌ | ❌ | ✅ LLM-driven |
| **Cover Letter Gen** | ✅ Job-aware | 🟡 Template-based | ✅ Personalized | ❌ | ❌ | ✅ GPT + reportlab PDF |
| **Markdown Resume** | ❌ (YAML) | ❌ (Python config) | ❌ | ❌ (TXT) | ❌ | ❌ (YAML) |

---

## Anti-Detection & Safety

| Feature | AIHawk | Auto_job_applier | JobHuntr | EasyApply_AI | EasyApplyBot | AIHawk_fork |
|---------|--------|------------------|----------|--------------|--------------|-------------|
| **Undetected ChromeDriver** | 🟡 In requirements, unused | 🔥 Active + auto-patch | N/A | ✅ Active | ❌ | ❌ |
| **Selenium Stealth** | ❌ | ❌ | N/A | ❌ | 🔥 Full fingerprint spoof | ❌ |
| **Chrome Profile Reuse** | ❌ (incognito) | 🔥 Cross-platform detect | ✅ Embedded | ❌ | ✅ | ✅ |
| **Randomized Delays** | 🟡 Fixed 30-60s | 🔥 Non-uniform buffer() | ✅ | 🟡 Partial random | 🟡 Uniform random | 🔥 Multi-layered |
| **Mouse Movement** | ❌ | 🟡 ActionChains | ✅ | 🟡 Scroll only | ❌ | 🟡 ActionChains |
| **Native Input (PyAutoGUI)** | ❌ | 🔥 OS-level keypresses | N/A | ❌ | ❌ | ❌ |
| **User Agent Rotation** | ❌ | ❌ | N/A | ❌ | 🟡 Spoofed once | ❌ |
| **Proxy Support** | ❌ | ❌ | N/A | ❌ | ❌ | ❌ |
| **Session Breaks** | ❌ | 🟡 Switch number | ✅ | ❌ | ❌ | 🔥 5-34 min every 5 pages |
| **Active Hours Restriction** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **CAPTCHA Handling** | ❌ | 🟡 Manual prompt | N/A | 🟡 Debugger pause | ❌ | 🟡 5-min manual window |
| **Cookie Persistence** | ❌ | ✅ Profile-based | ✅ | ❌ | ✅ Pickle cookies | ✅ Profile-based |
| **Image/CSS Blocking** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Reduces fingerprint |
| **Headless Mode** | ❌ | ✅ (toggle) | ✅ D.A.M.N mode | ❌ | ✅ | ✅ |
| **Dry-Run Mode** | ❌ | ✅ Pause options | ❌ | ❌ | 🔥 Full dry-run | ❌ SKIP_APPLY env |
| **Screen Keep-Awake** | ❌ | 🔥 ShiftRight press | N/A | ❌ | ❌ | ❌ |
| **Max Apps/Day Limit** | 🟡 JOB_MAX_APPLICATIONS=5 | ✅ Daily limit detect | ✅ 25-45/day | ❌ | ✅ maxApplicationsPerRun | ❌ |

---

## Tracking & Notifications

| Feature | AIHawk | Auto_job_applier | JobHuntr | EasyApply_AI | EasyApplyBot | AIHawk_fork |
|---------|--------|------------------|----------|--------------|--------------|-------------|
| **Application Logging** | ✅ JSON + filesystem | 🔥 CSV (18+ fields) | ✅ Full history | 🟡 Pickle IDs only | ✅ Daily text files | ✅ JSON (success/fail/skip) |
| **LLM Cost Tracking** | 🔥 Token + cost logs | ❌ | ❌ | ❌ | N/A | ✅ Token + cost logs |
| **Web Dashboard** | ❌ | 🔥 Flask UI | ✅ Desktop app | ❌ | ❌ | ❌ |
| **CLI Stats** | ❌ | ✅ Session summary | ❌ | ✅ Category stats | 🔥 Emoji summary | ❌ |
| **CSV Export** | ❌ | ✅ Native CSV | ❌ | ❌ | ❌ | ❌ |
| **Telegram Notifications** | ❌ | ❌ | ❌ | 🔥 Real-time | ❌ | ❌ |
| **Email Notifications** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Session Summary** | ❌ | ✅ End-of-run stats | ❌ | ✅ Runtime + counts | ✅ Applied/skipped/failed | ❌ |

---

## Platform Support

| Platform | AIHawk | Auto_job_applier | JobHuntr | EasyApply_AI | EasyApplyBot | AIHawk_fork |
|----------|--------|------------------|----------|--------------|--------------|-------------|
| **LinkedIn Easy Apply** | ❌ (removed) | 🔥 Primary | ✅ | ✅ | ✅ | ✅ |
| **Indeed** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Glassdoor** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **ZipRecruiter** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Dice** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Greenhouse** | ❌ | ❌ | 🟡 Via universal | ❌ | ❌ | ❌ |
| **Lever** | ❌ | ❌ | 🟡 Via universal | ❌ | ❌ | ❌ |
| **Company Career Pages** | ❌ | 🟡 External detect | 🔥 Universal | ❌ | ❌ | ❌ |

---

## Code Quality & Architecture

| Metric | AIHawk | Auto_job_applier | JobHuntr | EasyApply_AI | EasyApplyBot | AIHawk_fork |
|--------|--------|------------------|----------|--------------|--------------|-------------|
| **Overall Score** | 7/10 | 7.5/10 | N/A | 4/10 | 6/10 | 🔥 8/10 |
| **Modularity** | ✅ Good patterns | ✅ Clean modules | N/A | ❌ Single file | 🟡 4 files | 🔥 10 focused files |
| **Type Hints** | ✅ Pydantic | ✅ Required | N/A | ❌ None | ❌ None | ✅ Dataclasses |
| **Error Handling** | 🟡 Mixed | ✅ Validation framework | N/A | ❌ 50+ bare except | 🟡 Try-except-pass | ✅ Specific exceptions |
| **Config Validation** | ✅ Pydantic + custom | 🔥 Full validator module | N/A | ❌ None | ❌ None | ✅ ConfigValidator |
| **Documentation** | 🟡 Partial docstrings | ✅ Contributor guidelines | N/A | ❌ Minimal | 🟡 README only | 🟡 README good, no docstrings |
| **Design Patterns** | 🔥 Adapter/Facade/Strategy/Factory | ✅ Clean separation | N/A | ❌ Monolith | 🟡 Basic OOP | ✅ Facade/State/Decorator |
| **Testability** | 🟡 | 🟡 Env var overrides | N/A | ❌ | ✅ Dry-run mode | 🟡 SKIP_APPLY env |
| **Total Lines** | ~3000+ | ~2000+ | N/A | 783 | ~1000 | ~1900 |

---

## Summary: Best-in-Class by Feature

| Feature Area | 🔥 Winner | Runner-Up |
|-------------|-----------|-----------|
| **Anti-Detection** | Auto_job_applier | AIHawk Fork |
| **Form Filling Intelligence** | AIHawk Fork | Auto_job_applier |
| **LLM Provider Support** | AIHawk (6 providers) | Auto_job_applier (3 providers) |
| **Resume Tailoring** | AIHawk + Fork | JobHuntr (closed) |
| **Job Filtering Depth** | Auto_job_applier | EasyApplyBot |
| **Code Architecture** | AIHawk Fork | AIHawk |
| **Deployment/DevOps** | EasyApplyJobsBot (Docker) | Auto_job_applier (Flask) |
| **Notifications** | linkedin-easyapply-using-AI (Telegram) | Auto_job_applier (dashboard) |
| **Multi-Platform** | JobHuntr (closed) | None (all LinkedIn-only) |
| **Cost Efficiency** | EasyApplyJobsBot (no AI) | Auto_job_applier (local LLMs) |
| **Overall Best Open-Source** | Auto_job_applier | AIHawk Fork |
