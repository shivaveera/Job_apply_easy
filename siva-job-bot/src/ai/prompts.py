"""Centralized prompt templates for all AI operations.

All prompts are defined here as template strings for easy tuning.
Use .format() or f-strings to fill in variables.
"""

# --- Job Scoring ---

JOB_SCORING_PROMPT = """You are a job relevance scoring assistant. Given a candidate's resume and a job posting, rate how well the candidate matches the job on a scale of 0.0 to 1.0.

Consider:
- Skills match (technical skills, tools, languages)
- Experience level alignment
- Industry relevance
- Location compatibility
- Overall fit

RESUME:
{resume}

JOB POSTING:
Title: {job_title}
Company: {company}
Location: {location}
Description: {job_description}

Respond ONLY with a JSON object:
{{"score": <float 0.0-1.0>, "reasoning": "<brief explanation>"}}
"""

# --- Form Filling ---

FORM_FILL_TEXT_PROMPT = """You are helping a job applicant fill out an application form. Answer the following question based on the applicant's information.

APPLICANT INFO:
{resume}

PREVIOUS ANSWERS (for context):
{previous_answers}

QUESTION: {question}
{format_hint}

Rules:
- Answer concisely and professionally
- If the question asks for a number, respond with only the number
- If you're unsure, provide the most reasonable answer based on the resume
- Never say "I don't know" - always provide a best-effort answer
- Match the expected format exactly

YOUR ANSWER (just the answer, no explanation):"""

FORM_FILL_CHOICE_PROMPT = """You are helping a job applicant select the best option for an application form question.

APPLICANT INFO:
{resume}

QUESTION: {question}

OPTIONS:
{options}

Rules:
- Select the option that best matches the applicant's profile
- Respond with ONLY the exact text of the chosen option
- If none match perfectly, choose the closest one
- Prefer "Yes" for work authorization and willingness questions
- For demographic questions, prefer "Decline to answer" if available

YOUR CHOICE (exact option text only):"""

# --- Resume Tailoring ---

RESUME_TAILOR_PROMPT = """You are an ATS (Applicant Tracking System) optimization expert. Tailor the following resume to better match the target job posting while keeping all information truthful.

ORIGINAL RESUME (Markdown):
{resume}

TARGET JOB:
Title: {job_title}
Company: {company}
Description: {job_description}

Instructions:
- Reorder bullet points to highlight most relevant experience first
- Incorporate relevant keywords from the job description naturally
- Adjust the summary/objective to align with the role
- Keep all facts truthful - do not fabricate experience
- Maintain professional formatting in Markdown
- Keep it to 1 page worth of content

Return the tailored resume in Markdown format:"""

# --- Cover Letter ---

COVER_LETTER_PROMPT = """Write a professional, personalized cover letter for the following job application.

APPLICANT RESUME:
{resume}

JOB DETAILS:
Title: {job_title}
Company: {company}
Description: {job_description}

TEMPLATE:
{template}

Instructions:
- Fill in all template placeholders naturally
- Highlight 2-3 specific experiences that match the job requirements
- Show genuine interest in the company and role
- Keep it concise (3-4 paragraphs, under 300 words)
- Professional but personable tone
- Do not use cliches like "I am excited to apply"

Return the complete cover letter:"""

# --- Job Description Summary ---

JOB_SUMMARY_PROMPT = """Summarize this job posting concisely, extracting key information.

JOB POSTING:
{job_description}

Return a JSON object:
{{
    "title": "<job title>",
    "company": "<company name>",
    "location": "<location>",
    "remote": <true/false>,
    "experience_years": <number or null>,
    "key_skills": ["<skill1>", "<skill2>", ...],
    "education": "<requirement or null>",
    "salary_range": "<range or null>",
    "summary": "<2-3 sentence summary>"
}}
"""

# --- Skill Extraction ---

SKILL_EXTRACTION_PROMPT = """Extract and categorize skills from this job description.

JOB DESCRIPTION:
{job_description}

Return a JSON object:
{{
    "required_skills": ["<skill1>", "<skill2>", ...],
    "preferred_skills": ["<skill1>", "<skill2>", ...],
    "tools_technologies": ["<tool1>", "<tool2>", ...],
    "soft_skills": ["<skill1>", "<skill2>", ...]
}}
"""

# --- Question Classification ---

QUESTION_CLASSIFY_PROMPT = """Classify this application form question into one of these categories to determine which part of the applicant's resume is most relevant:

Categories:
1. personal_info - Name, contact, location
2. work_authorization - Visa, citizenship, sponsorship
3. experience - Years of experience, past roles
4. education - Degrees, GPA, certifications
5. skills - Technical skills, tools, languages
6. availability - Start date, notice period
7. salary - Compensation expectations
8. preferences - Remote, relocation, travel
9. demographics - Gender, race, veteran, disability
10. cover_letter - Cover letter or free-form writing
11. other - Anything else

QUESTION: {question}

Respond with ONLY the category name:"""
