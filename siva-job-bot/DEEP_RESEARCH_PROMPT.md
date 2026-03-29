# Deep Research Prompt: Making Siva-Job-Bot Fully Autonomous

> Copy this entire prompt into DeepResearch / ChatGPT Deep Research / Perplexity Pro / Claude Research.
> Goal: Get back actionable code patterns, selectors, and strategies to make every piece production-ready.

---

## Context

I have built an automated job application bot called **siva-job-bot** with:
- **Selenium + undetected-chromedriver** for browser automation
- **DeepSeek V3** as the LLM (OpenAI-compatible Python SDK)
- **SQLite** for application tracking + AI response caching
- **YAML** config for all settings
- **13+ ATS platform modules**: LinkedIn, Indeed, Workday, Greenhouse, Lever, SmartRecruiters, iCIMS, Taleo, ADP, Ashby, + universal form filler
- **ATS auto-detection** via URL patterns, HTML signatures, and DOM inspection
- **Anti-detection**: undetected-chromedriver, selenium-stealth, Chrome profile persistence, gaussian-distribution delays, per-character human typing

The bot currently works for LinkedIn Easy Apply but has gaps across other platforms and in the autonomous pipeline. I need research to make it **100% autonomous** - zero human intervention from launch to application submission across ALL major ATS platforms.

---

## RESEARCH AREA 1: Resume Upload Automation (CRITICAL)

The bot generates tailored PDFs per job but **never actually uploads them** to forms. I need:

1. **How to reliably upload files via Selenium `input[type='file']`** across different ATS platforms:
   - LinkedIn Easy Apply file upload (the `jobs-document-upload-file-input` class)
   - Greenhouse file upload (standard `input[name='resume']`)
   - Workday drag-drop upload region (`data-automation-id='dragDropRegion'`) - how to handle drag-drop uploads in Selenium when there's no `<input type="file">`?
   - Indeed nested iframe file upload - how to send_keys to a file input inside a nested iframe?
   - Lever file upload

2. **Drag-and-drop file upload fallback** - some ATS platforms (Workday, some iCIMS) don't expose `<input type="file">`. Research:
   - JavaScript-based file injection via `DataTransfer` and `DragEvent` simulation
   - Using `pyautogui` as last resort for native OS file dialog
   - Any Selenium 4+ native drag-and-drop file methods

3. **Resume format handling**: When should we upload PDF vs DOCX? Do any ATS platforms reject PDFs? Which ones prefer DOCX for parsing?

---

## RESEARCH AREA 2: CAPTCHA and Bot Detection Bypass (2025-2026)

1. **Current state of bot detection** on each major platform:
   - LinkedIn: what triggers their bot detection? Rate limits? IP-based? Browser fingerprint?
   - Indeed: what is their current anti-bot system? Do they use Cloudflare/DataDome/PerimeterX?
   - Workday: do they have bot detection? What triggers it?
   - Greenhouse/Lever: any anti-bot measures?

2. **CAPTCHA handling strategies**:
   - **2Captcha / Anti-Captcha / CapSolver API integration** - how to integrate these services with Selenium for reCAPTCHA v2, v3, hCaptcha, and Turnstile
   - Provide Python code examples for each CAPTCHA service
   - Cost per solve and speed comparison
   - **Audio CAPTCHA solving** as free alternative - using speech-to-text APIs

3. **SeleniumBase UC Mode** (recommended for 2025-2026):
   - Exact setup code for SeleniumBase with UC Mode enabled
   - How does it compare to undetected-chromedriver for LinkedIn, Indeed?
   - Can it coexist with selenium-stealth?

4. **Residential proxy rotation** for IP-based detection:
   - Best residential proxy services for job bot use cases
   - How to rotate proxies per-session or per-application in Selenium
   - SOCKS5 vs HTTP proxy setup in Chrome options

5. **Browser fingerprint evasion**:
   - Canvas fingerprint spoofing (2025 techniques)
   - WebGL renderer spoofing
   - AudioContext fingerprint masking
   - Font enumeration blocking
   - Screen resolution randomization
   - Timezone/locale matching with proxy location

---

## RESEARCH AREA 3: Multi-Step Form Navigation & Validation

The bot currently fills forms but doesn't verify success. I need:

1. **Form submission verification patterns**:
   - How to detect "Application submitted successfully" across each ATS:
     - LinkedIn: what URL/element appears after successful Easy Apply?
     - Workday: what confirmation page/element appears?
     - Greenhouse: confirmation page patterns?
     - Indeed: confirmation patterns inside the iframe?
   - Screenshot-on-submit implementation for audit trail

2. **Required field detection**:
   - How to detect which fields are required before submission (aria-required, asterisk in label, HTML5 required attribute, custom validation)
   - How to re-scan after a failed submit and find error messages
   - Pattern for "fill required fields → attempt submit → check errors → re-fill → retry"

3. **Multi-page form progression**:
   - Workday: How many steps does a typical application have? What are the page names/identifiers?
   - LinkedIn Easy Apply: How to detect current step number and total steps (progress bar)?
   - Indeed: How many screens in a typical Indeed Apply flow? How to detect current screen?

4. **Conditional/dynamic fields**:
   - How to handle fields that appear based on previous answers (e.g., "If Yes, please explain")
   - How to handle dynamic dropdowns that load options via AJAX
   - How to wait for React state updates before reading new fields

---

## RESEARCH AREA 4: ATS-Specific Deep Selectors (2025 Current)

For each ATS, I need the **exact current CSS selectors and XPaths** that work as of 2025. The ones I have may be outdated.

### LinkedIn (2025 selectors needed):
- Easy Apply modal container selector
- Each form step's container
- Progress bar / step indicator
- "Follow company" checkbox (to uncheck)
- "Submit application" final button (exact aria-label)
- Error message container
- Salary expectation field (when present)
- "How did you hear about this job?" dropdown

### Workday (2025 selectors needed):
- Full list of `data-automation-id` values for ALL common form fields
- Country/State/City cascading dropdown pattern
- Date picker interaction (month/year selectors)
- "How did you hear about us?" field handling
- Voluntary self-identification (EEO) page selectors
- "I agree to terms" checkbox pattern
- Multi-select question handling

### Indeed (2025 selectors needed):
- Current iframe nesting structure (has it changed?)
- Updated `ia-` and `ifl-` prefix selectors
- "Qualifications" screening question patterns
- Salary expectation field
- "Are you willing to commute?" question
- Assessment/screening test detection (to skip or handle)

### Greenhouse (2025 selectors needed):
- Current `#application_form` structure
- Custom question field naming convention (`question_{id}` - still current?)
- Demographic/EEO question handling
- Multi-file upload support
- GDPR consent checkbox patterns

### SmartRecruiters (2025 selectors needed):
- Current application form structure at `jobs.smartrecruiters.com`
- Screening question field patterns
- Resume parsing confirmation handling
- GDPR/privacy consent flows

---

## RESEARCH AREA 5: Session Persistence & Recovery

1. **Chrome profile session persistence**:
   - Best practice for `--user-data-dir` to maintain login sessions across runs
   - How to detect expired sessions and auto-re-login
   - Cookie-based session validation before starting a run

2. **Crash recovery**:
   - How to checkpoint progress (save which jobs were already processed)
   - How to resume from last successful application after a crash
   - How to handle "stale element" exceptions mid-form without losing progress

3. **Rate limiting and throttling**:
   - LinkedIn: what's the safe application rate? How many per hour/day before flagging?
   - Indeed: application rate limits?
   - Workday: any rate limits per career site?
   - What are the signs that you're being rate-limited vs. banned?

---

## RESEARCH AREA 6: LLM-Powered Form Intelligence

1. **Smart question answering patterns**:
   - How to classify form questions into types: personal info, work authorization, salary, availability, experience years, etc.
   - How to build a question-answer cache that works across different ATS platforms (same question phrased differently)
   - Fuzzy matching threshold for recognizing "similar enough" questions

2. **Cover letter personalization**:
   - What fields from a job posting should be extracted for cover letter generation?
   - Best prompt structure for generating ATS-friendly cover letters
   - Should cover letters be different lengths for different platforms?

3. **Job description parsing**:
   - How to extract: required skills, preferred skills, years of experience, salary range, visa sponsorship, remote/hybrid/onsite from unstructured job descriptions
   - Best prompt for extracting structured data from job postings

4. **Answer consistency**:
   - How to ensure the bot gives consistent answers across applications (e.g., always says "5 years Python experience" not sometimes "4" and sometimes "6")
   - How to maintain an "answer profile" that the LLM references

---

## RESEARCH AREA 7: Job Discovery Beyond LinkedIn/Indeed

1. **Greenhouse job board scraping**:
   - How to discover ALL open jobs on a company's Greenhouse board (boards.greenhouse.io/company)
   - API endpoint for listing jobs (if available)
   - Pagination patterns

2. **Lever job board scraping**:
   - How to list all jobs at jobs.lever.co/company
   - JSON API endpoint for job listings

3. **Workday job search**:
   - How to search within a company's Workday career site
   - Common URL patterns for Workday job search
   - Pagination and filtering

4. **Aggregator sites**:
   - Can the bot scrape jobs from Glassdoor, ZipRecruiter, or Google Jobs and then apply via the original ATS?
   - How to extract the actual application URL from aggregator listings

5. **Company career page crawling**:
   - Strategy for discovering which ATS a company uses from their careers page
   - Common career page URL patterns (/careers, /jobs, /openings)

---

## RESEARCH AREA 8: Application Tracking & Analytics

1. **Post-application monitoring**:
   - How to check application status on LinkedIn (Applied → Viewed → Interview?)
   - Can we scrape application status from Workday/Greenhouse portals?
   - Email parsing for application responses (regex patterns for rejection/interview emails)

2. **Analytics dashboard**:
   - What metrics matter: apply rate, response rate, interview rate, by platform, by job type
   - How to calculate "best time to apply" from historical data
   - How to identify which keywords get more responses

---

## RESEARCH AREA 9: Anti-Detection Advanced Techniques (2025-2026)

1. **Browser fingerprint rotation**:
   - How to generate consistent but unique fingerprints per session
   - Tools: FingerprintSwitcher, puppeteer-extra-plugin-stealth equivalents for Selenium
   - Canvas/WebGL/AudioContext noise injection code

2. **Human behavior simulation** beyond delays:
   - Mouse movement patterns (Bezier curves vs linear)
   - Scroll behavior patterns (read-then-scroll vs continuous)
   - Tab switching / window focus patterns
   - Typo simulation and correction
   - Random page visits between applications (checking email, browsing news)

3. **Detection test sites**:
   - List of sites to test bot detection: bot.sannysoft.com, browserleaks.com, pixelscan.net
   - What should pass for each test
   - How to automate detection testing before starting applications

---

## RESEARCH AREA 10: Legal & Ethical Considerations

1. **Terms of Service**: Which platforms explicitly prohibit automated applications? What are the actual risks?
2. **Rate limits**: What are the documented API/usage limits for LinkedIn, Indeed?
3. **GDPR/CCPA**: Any data handling requirements when storing application data?
4. **Best practices**: How to use automation ethically (not spam-applying to every job)

---

## OUTPUT FORMAT REQUESTED

For each research area, provide:
1. **Findings**: What you discovered
2. **Code Examples**: Python/Selenium code snippets that can be directly integrated
3. **Selectors**: Exact CSS selectors / XPaths tested as of 2025
4. **Warnings**: What to avoid, what breaks, what gets you banned
5. **Priority**: Rate each item as P0 (must fix), P1 (should fix), P2 (nice to have)

Focus on **actionable, copy-paste-ready code** over theory. I want to integrate findings directly into the codebase.
