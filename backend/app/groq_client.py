"""
Thin wrapper around the Groq SDK used by (a) the semantic prompt-injection
detector, (b) TrustReport narrative generation, and (c) the Agent Sandbox's
own "brain".

Design per build spec §7.5/§7.6:
- If GROQ_API_KEY is missing/invalid, `enabled` is False and every caller
  must fall back to a structured/non-LLM path instead of crashing.
- Retries with exponential backoff on 429.
- A simple circuit breaker: after N consecutive failures, stop calling Groq
  for a cooldown window and report degraded=True instead of hammering the API.
"""
import asyncio
import time
from dataclasses import dataclass, field

from app.config import get_settings

settings = get_settings()

try:
    from groq import Groq, RateLimitError
except ImportError:  # groq package not installed yet in this environment
    Groq = None
    class RateLimitError(Exception):
        pass


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    _failures: int = field(default=0, init=False)
    _open_until: float = field(default=0.0, init=False)

    def is_open(self) -> bool:
        return time.monotonic() < self._open_until

    def record_success(self) -> None:
        self._failures = 0
        self._open_until = 0.0

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._open_until = time.monotonic() + self.cooldown_seconds


class GroqClient:
    def __init__(self) -> None:
        self.enabled = settings.groq_enabled and Groq is not None
        self._client = Groq(api_key=settings.groq_api_key) if self.enabled else None
        self.breaker = CircuitBreaker()
        self._cache: dict[str, str] = {}  # tiny in-memory LRU-ish cache

    @property
    def degraded(self) -> bool:
        """True when Groq should not be called right now (disabled or breaker open)."""
        return (not self.enabled) or self.breaker.is_open()

    async def complete(
        self,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 400,
        max_retries: int = 2,
    ) -> tuple[str | None, bool]:
        """
        Returns (text, degraded). `degraded=True` means the caller should use
        its non-LLM fallback — this function never raises.
        """
        if self.degraded:
            return None, True

        cache_key = f"{model}:{hash(system)}:{hash(user)}"
        if cache_key in self._cache:
            return self._cache[cache_key], False

        delay = 1.0
        for attempt in range(max_retries + 1):
            try:
                resp = await asyncio.to_thread(
                    self._client.chat.completions.create,
                    model=model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                text = resp.choices[0].message.content
                self.breaker.record_success()
                if len(self._cache) > 200:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[cache_key] = text
                return text, False
            except RateLimitError:
                self.breaker.record_failure()
                if attempt < max_retries and not self.breaker.is_open():
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                return None, True
            except Exception:
                self.breaker.record_failure()
                return None, True
        return None, True


groq_client = GroqClient()
