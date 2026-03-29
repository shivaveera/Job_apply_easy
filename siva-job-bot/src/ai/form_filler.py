"""AI-powered form filling using DeepSeek for intelligent question answering.

Enhanced with:
- Answer profile (single source of truth for factual answers)
- Question classification → profile lookup → AI fallback
- Semantic caching with fuzzy question matching
- JSON mode for structured LLM responses
- Answer consistency cross-checking
"""

import json
import re
from pathlib import Path
from typing import Optional

import yaml
from Levenshtein import distance as levenshtein_distance

from src.ai.deepseek_client import DeepSeekClient
from src.ai.prompts import (
    FORM_FILL_CHOICE_PROMPT,
    FORM_FILL_TEXT_PROMPT,
    QUESTION_CLASSIFY_PROMPT,
)
from src.utils.logger import log

# Question patterns that map to answer profile fields (no AI needed)
PROFILE_PATTERNS = {
    # Work authorization
    r"authorized.*(us|united states|work)": ("work_authorization", "authorized_us"),
    r"(require|need).*(sponsor|visa)": ("work_authorization", "require_sponsorship"),
    r"(us|u\.s\.).*citizen": ("work_authorization", "us_citizen"),
    r"green.?card": ("work_authorization", "green_card"),
    # Experience
    r"(years?|yrs?).*(experience|exp)": ("experience_years", "total"),
    r"(years?|yrs?).*(python)": ("experience_years", "python"),
    r"(years?|yrs?).*(java\b)": ("experience_years", "java"),
    r"(years?|yrs?).*(javascript|js\b)": ("experience_years", "javascript"),
    r"(years?|yrs?).*(react)": ("experience_years", "react"),
    r"(years?|yrs?).*(sql)": ("experience_years", "sql"),
    r"(years?|yrs?).*(aws|cloud)": ("experience_years", "aws"),
    # Education
    r"(highest|level).*(degree|education)": ("education", "highest_degree"),
    r"(field|major|area).*(study|concentration)": ("education", "field_of_study"),
    r"(gpa|grade point)": ("education", "gpa"),
    # Salary
    r"(salary|compensation|pay).*(expect|desired|minimum|range)": ("salary", "desired"),
    r"(minimum|min).*(salary|compensation|pay)": ("salary", "minimum"),
    # Availability
    r"(start|begin|available).*(date|when)": ("availability", "start_date"),
    r"notice.?period": ("availability", "notice_period"),
    r"(relocat|move)": ("availability", "willing_to_relocate"),
    r"(remote|hybrid|onsite|on.?site|work.*type|work.*arrangement)": ("availability", "preferred_work_type"),
    r"(travel|commute)": ("availability", "willing_to_travel"),
    # Demographics
    r"gender": ("demographics", "gender"),
    r"(race|ethnic)": ("demographics", "ethnicity"),
    r"veteran": ("demographics", "veteran_status"),
    r"disabilit": ("demographics", "disability_status"),
    # Common
    r"background.?check": ("common_answers", "background_check"),
    r"drug.?(test|screen)": ("common_answers", "drug_test"),
    r"(18|eighteen).*years?.*(old|age)": ("common_answers", "over_18"),
    r"(felon|convict)": ("common_answers", "convicted_of_felony"),
    r"(how|where).*(hear|find|learn).*about": ("source", None),
}


class FormFiller:
    """AI-powered form filling with answer profile and caching.

    Priority chain:
    1. Manual Q&A overrides (config/qa_overrides.yaml)
    2. Answer profile pattern match (config/answer_profile.yaml)
    3. SQLite cache (exact question hash)
    4. AI-generated answer (DeepSeek V3 with JSON mode)
    5. Levenshtein fuzzy matching for multiple-choice
    """

    def __init__(
        self,
        client: DeepSeekClient,
        model: str,
        resume: str,
        qa_overrides: dict[str, str],
        db_path: str = "data/applications.db",
        answer_profile_path: str = "config/answer_profile.yaml",
    ):
        self.client = client
        self.model = model
        self.resume = resume
        self.qa_overrides = qa_overrides
        self._answer_history: list[dict] = []
        self._answer_profile = self._load_answer_profile(answer_profile_path)
        self._init_qa_cache(db_path)

    def _load_answer_profile(self, path: str) -> dict:
        """Load the answer profile YAML (single source of truth)."""
        profile_path = Path(path)
        if not profile_path.exists():
            log.debug(f"Answer profile not found at {path}")
            return {}
        try:
            with open(profile_path, encoding="utf-8") as f:
                profile = yaml.safe_load(f) or {}
            log.info(f"Answer profile loaded from {path}")
            return profile
        except Exception as e:
            log.warning(f"Failed to load answer profile: {e}")
            return {}

    def _check_answer_profile(self, question: str) -> Optional[str]:
        """Check if the question matches an answer profile pattern.

        Uses regex patterns to map questions to profile fields,
        avoiding LLM calls for common factual questions.
        """
        if not self._answer_profile:
            return None

        q_lower = question.lower().strip()

        for pattern, (section, field) in PROFILE_PATTERNS.items():
            if re.search(pattern, q_lower):
                if field is None:
                    # Direct value (e.g., "source")
                    value = self._answer_profile.get(section, "")
                else:
                    section_data = self._answer_profile.get(section, {})
                    if isinstance(section_data, dict):
                        value = section_data.get(field, "")
                    else:
                        value = str(section_data)

                if value:
                    log.debug(f"Profile match: '{question[:50]}' -> [{section}.{field}] = '{value}'")
                    return str(value)

        return None

    def _init_qa_cache(self, db_path: str) -> None:
        """Initialize the Q&A cache table in SQLite."""
        import sqlite3
        from pathlib import Path

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS qa_cache (
                question_hash TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.commit()

    def _normalize_question(self, question: str) -> str:
        """Normalize question text for matching."""
        return re.sub(r"[^a-z0-9\s]", "", question.lower().strip())

    def _check_overrides(self, question: str) -> Optional[str]:
        """Check if the question matches any manual Q&A override."""
        q_lower = question.lower().strip()
        for pattern, answer in self.qa_overrides.items():
            if pattern.lower() in q_lower:
                log.debug(f"Override match: '{pattern}' -> '{answer}'")
                return answer
        return None

    def _check_cache(self, question: str) -> Optional[str]:
        """Check the SQLite cache for a previously answered question."""
        import hashlib

        q_hash = hashlib.sha256(self._normalize_question(question).encode()).hexdigest()
        row = self._db.execute(
            "SELECT answer FROM qa_cache WHERE question_hash = ?", (q_hash,)
        ).fetchone()
        if row:
            log.debug(f"Cache hit for question: {question[:60]}")
            return row[0]
        return None

    def _store_in_cache(self, question: str, answer: str, source: str) -> None:
        """Store a Q&A pair in the cache."""
        import hashlib

        q_hash = hashlib.sha256(self._normalize_question(question).encode()).hexdigest()
        self._db.execute(
            """INSERT OR REPLACE INTO qa_cache (question_hash, question, answer, source)
               VALUES (?, ?, ?, ?)""",
            (q_hash, question[:500], answer[:1000], source),
        )
        self._db.commit()

    def answer_text_question(
        self,
        question: str,
        format_hint: str = "",
    ) -> str:
        """Answer a text-based form question.

        Priority: overrides -> profile -> cache -> AI.
        """
        # 1. Check manual overrides
        override = self._check_overrides(question)
        if override is not None:
            self._store_in_cache(question, override, "override")
            return override

        # 2. Check answer profile (factual questions)
        profile_answer = self._check_answer_profile(question)
        if profile_answer is not None:
            self._store_in_cache(question, profile_answer, "profile")
            return profile_answer

        # 3. Check cache
        cached = self._check_cache(question)
        if cached is not None:
            return cached

        # 4. Ask AI
        previous = "\n".join(
            f"Q: {h['question'][:60]} -> A: {h['answer'][:60]}"
            for h in self._answer_history[-5:]
        )

        prompt = FORM_FILL_TEXT_PROMPT.format(
            resume=self.resume[:3000],
            previous_answers=previous or "None yet",
            question=question,
            format_hint=f"Expected format: {format_hint}" if format_hint else "",
        )

        answer = self.client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.2,
            max_tokens=512,
        ).strip()

        self._store_in_cache(question, answer, "ai")
        self._answer_history.append({"question": question, "answer": answer})
        log.info(f"AI answered: '{question[:60]}' -> '{answer[:60]}'")
        return answer

    def answer_choice_question(
        self,
        question: str,
        options: list[str],
    ) -> str:
        """Select the best option for a multiple-choice question.

        Uses AI + Levenshtein fuzzy matching for robust option selection.
        """
        # Check overrides first
        override = self._check_overrides(question)
        if override is not None:
            return self._fuzzy_match_option(override, options)

        # Check cache
        cached = self._check_cache(question)
        if cached is not None:
            return self._fuzzy_match_option(cached, options)

        # Ask AI
        options_text = "\n".join(f"- {opt}" for opt in options)
        prompt = FORM_FILL_CHOICE_PROMPT.format(
            resume=self.resume[:3000],
            question=question,
            options=options_text,
        )

        ai_answer = self.client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.1,
            max_tokens=128,
        ).strip()

        selected = self._fuzzy_match_option(ai_answer, options)
        self._store_in_cache(question, selected, "ai")
        self._answer_history.append({"question": question, "answer": selected})
        log.info(f"AI selected: '{question[:60]}' -> '{selected}'")
        return selected

    def _fuzzy_match_option(self, text: str, options: list[str]) -> str:
        """Find the closest matching option using Levenshtein distance.

        Also checks for substring matches before falling back to edit distance.
        """
        text_lower = text.lower().strip()

        # Exact match
        for opt in options:
            if opt.lower().strip() == text_lower:
                return opt

        # Substring match (bidirectional)
        for opt in options:
            opt_lower = opt.lower().strip()
            if text_lower in opt_lower or opt_lower in text_lower:
                return opt

        # Levenshtein distance
        distances = [
            (opt, levenshtein_distance(text_lower, opt.lower().strip()))
            for opt in options
        ]
        best = min(distances, key=lambda x: x[1])
        log.debug(f"Fuzzy match: '{text}' -> '{best[0]}' (distance: {best[1]})")
        return best[0]

    def classify_question(self, question: str) -> str:
        """Classify a question to determine which resume section is relevant."""
        prompt = QUESTION_CLASSIFY_PROMPT.format(question=question)
        category = self.client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.0,
            max_tokens=32,
        ).strip().lower()

        valid_categories = {
            "personal_info", "work_authorization", "experience", "education",
            "skills", "availability", "salary", "preferences", "demographics",
            "cover_letter", "other",
        }
        return category if category in valid_categories else "other"

    def close(self) -> None:
        """Close the database connection."""
        if self._db:
            self._db.close()
