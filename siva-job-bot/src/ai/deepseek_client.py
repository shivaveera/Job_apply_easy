"""Centralized DeepSeek API client using OpenAI-compatible SDK.

All AI modules import from this single client wrapper.
Includes response caching to avoid redundant API calls.
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI

from src.utils.logger import log


class DeepSeekClient:
    """Wrapper around DeepSeek API via OpenAI-compatible SDK.

    Features:
    - Single client instance for all AI operations
    - SQLite-based response caching (hash prompt -> cached result)
    - Automatic retry with exponential backoff
    - Token usage and cost tracking
    """

    # DeepSeek pricing (per million tokens)
    PRICING = {
        "deepseek-chat": {"input": 0.27, "output": 1.10},
        "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    }

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        cache_enabled: bool = True,
        cache_db_path: str = "data/ai_cache.db",
        max_retries: int = 3,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.cache_enabled = cache_enabled
        self.max_retries = max_retries
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.total_requests = 0

        if cache_enabled:
            Path(cache_db_path).parent.mkdir(parents=True, exist_ok=True)
            self._cache_db = sqlite3.connect(cache_db_path)
            self._init_cache_table()
        else:
            self._cache_db = None

    def _init_cache_table(self) -> None:
        """Create the response cache table if it doesn't exist."""
        self._cache_db.execute("""
            CREATE TABLE IF NOT EXISTS response_cache (
                prompt_hash TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                response TEXT NOT NULL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._cache_db.commit()

    def _hash_prompt(self, model: str, messages: list[dict]) -> str:
        """Create a deterministic hash of the prompt for caching."""
        content = json.dumps({"model": model, "messages": messages}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cached(self, prompt_hash: str) -> Optional[str]:
        """Retrieve a cached response by prompt hash."""
        if not self._cache_db:
            return None
        row = self._cache_db.execute(
            "SELECT response FROM response_cache WHERE prompt_hash = ?",
            (prompt_hash,),
        ).fetchone()
        return row[0] if row else None

    def _store_cache(
        self,
        prompt_hash: str,
        model: str,
        response: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Store a response in the cache."""
        if not self._cache_db:
            return
        self._cache_db.execute(
            """INSERT OR REPLACE INTO response_cache
               (prompt_hash, model, response, input_tokens, output_tokens)
               VALUES (?, ?, ?, ?, ?)""",
            (prompt_hash, model, response, input_tokens, output_tokens),
        )
        self._cache_db.commit()

    def _track_usage(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """Track cumulative token usage and cost."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_requests += 1

        pricing = self.PRICING.get(model, self.PRICING["deepseek-chat"])
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        self.total_cost += cost

    def chat(
        self,
        messages: list[dict],
        model: str = "deepseek-chat",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        use_cache: bool = True,
    ) -> str:
        """Send a chat completion request to DeepSeek.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model name ('deepseek-chat' or 'deepseek-reasoner').
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum response tokens.
            use_cache: Whether to use response caching.

        Returns:
            The assistant's response text.
        """
        # Check cache first
        if self.cache_enabled and use_cache:
            prompt_hash = self._hash_prompt(model, messages)
            cached = self._get_cached(prompt_hash)
            if cached:
                log.debug(f"Cache hit for {model} request")
                return cached
        else:
            prompt_hash = None

        # Retry with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                result = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens if response.usage else 0
                output_tokens = response.usage.completion_tokens if response.usage else 0

                self._track_usage(model, input_tokens, output_tokens)

                # Cache the response
                if prompt_hash:
                    self._store_cache(
                        prompt_hash, model, result, input_tokens, output_tokens
                    )

                log.debug(
                    f"DeepSeek {model}: {input_tokens} in / {output_tokens} out tokens"
                )
                return result

            except Exception as e:
                last_error = e
                wait_time = 2 ** (attempt + 1)
                log.warning(
                    f"DeepSeek API error (attempt {attempt + 1}/{self.max_retries}): "
                    f"{e}. Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)

        log.error(f"DeepSeek API failed after {self.max_retries} attempts: {last_error}")
        raise last_error

    def get_usage_summary(self) -> dict:
        """Return cumulative usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 4),
        }

    def close(self) -> None:
        """Close the cache database connection."""
        if self._cache_db:
            self._cache_db.close()
