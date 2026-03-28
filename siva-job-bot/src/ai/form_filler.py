"""AI-powered form filling using DeepSeek for intelligent question answering."""

import json
import re
from typing import Optional

from Levenshtein import distance as levenshtein_distance

from src.ai.deepseek_client import DeepSeekClient
from src.ai.prompts import (
    FORM_FILL_CHOICE_PROMPT,
    FORM_FILL_TEXT_PROMPT,
    QUESTION_CLASSIFY_PROMPT,
)
from src.utils.logger import log


class FormFiller:
    """AI-powered form filling with answer caching and fuzzy matching.

    Combines:
    - Manual Q&A overrides (highest priority)
    - Cached answers from previous runs (SQLite)
    - AI-generated answers (DeepSeek V3)
    - Levenshtein fuzzy matching for multiple-choice options
    """

    def __init__(
        self,
        client: DeepSeekClient,
        model: str,
        resume: str,
        qa_overrides: dict[str, str],
        db_path: str = "data/applications.db",
    ):
        self.client = client
        self.model = model
        self.resume = resume
        self.qa_overrides = qa_overrides
        self._answer_history: list[dict] = []
        self._init_qa_cache(db_path)

    def _init_qa_cache(self, db_path: str) -> None:
        """Initialize the Q&A cache table in SQLite."""
        import sqlite3
        from pathlib import Path

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path)
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

        Priority: overrides -> cache -> AI.
        """
        # 1. Check manual overrides
        override = self._check_overrides(question)
        if override is not None:
            self._store_in_cache(question, override, "override")
            return override

        # 2. Check cache
        cached = self._check_cache(question)
        if cached is not None:
            return cached

        # 3. Ask AI
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
