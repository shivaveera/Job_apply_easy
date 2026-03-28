"""AI-powered job relevance scoring against the applicant's resume."""

import json
from typing import Optional

from src.ai.deepseek_client import DeepSeekClient
from src.ai.prompts import JOB_SCORING_PROMPT
from src.utils.logger import log


class JobScorer:
    """Scores job postings for relevance to the applicant's resume."""

    def __init__(self, client: DeepSeekClient, model: str, resume: str):
        self.client = client
        self.model = model
        self.resume = resume

    def score(
        self,
        job_title: str,
        company: str,
        location: str,
        job_description: str,
    ) -> dict:
        """Score a job posting against the resume.

        Returns:
            Dict with 'score' (0.0-1.0) and 'reasoning' string.
        """
        prompt = JOB_SCORING_PROMPT.format(
            resume=self.resume,
            job_title=job_title,
            company=company,
            location=location,
            job_description=job_description[:3000],  # Truncate for token limits
        )

        try:
            response = self.client.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.1,
                max_tokens=256,
            )

            result = self._parse_response(response)
            log.info(
                f"Job score for '{job_title}' at {company}: "
                f"{result['score']:.2f} - {result['reasoning'][:80]}"
            )
            return result

        except Exception as e:
            log.warning(f"Scoring failed for '{job_title}': {e}. Returning default.")
            return {"score": 0.5, "reasoning": "Scoring failed, using default"}

    def _parse_response(self, response: str) -> dict:
        """Parse the JSON response from the scoring model."""
        try:
            # Handle markdown code blocks
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            data = json.loads(text)
            score = float(data.get("score", 0.5))
            score = max(0.0, min(1.0, score))
            reasoning = str(data.get("reasoning", "No reasoning provided"))
            return {"score": score, "reasoning": reasoning}
        except (json.JSONDecodeError, ValueError, KeyError):
            log.warning(f"Failed to parse scoring response: {response[:200]}")
            return {"score": 0.5, "reasoning": "Parse error, using default"}

    def meets_threshold(
        self,
        job_title: str,
        company: str,
        location: str,
        job_description: str,
        threshold: float = 0.6,
    ) -> tuple[bool, dict]:
        """Check if a job meets the minimum relevance threshold.

        Returns:
            Tuple of (meets_threshold: bool, score_details: dict).
        """
        result = self.score(job_title, company, location, job_description)
        return result["score"] >= threshold, result
