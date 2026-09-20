"""Base ProviderAdapter interface with rate limiting, circuit breaker, and health tracking."""
import asyncio
import hashlib
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import httpx

from packages.common.config import settings
from packages.common.logging import get_logger
from packages.schemas.source import SourceHealthRead, SourceItemBase

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, fast reject
    HALF_OPEN = "HALF_OPEN"# Testing recovery


class CircuitBreaker:
    """Protects downstream sources and our worker from cascading failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time: Optional[float] = None

    def record_success(self):
        self.consecutive_failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        if self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker tripped to OPEN after {self.consecutive_failures} failures.")

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (time.time() - self.last_failure_time > self.recovery_timeout_seconds):
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN probe.")
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False


class RateLimiter:
    """Token bucket / delay rate limiter per adapter."""

    def __init__(self, requests_per_minute: int = 20):
        self.min_interval = 60.0 / max(1, requests_per_minute)
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                await asyncio.sleep(wait_time)
            self.last_request_time = time.time()


class ProviderAdapter(ABC):
    """Abstract base class for all exchange, government, and news data sources."""

    def __init__(
        self,
        source_id: str,
        name: str,
        base_url: str,
        requests_per_minute: int = 20,
        timeout_seconds: int = 15,
        max_retries: int = 3,
    ):
        self.source_id = source_id
        self.name = name
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(requests_per_minute)
        self.circuit_breaker = CircuitBreaker()
        self.last_poll_at: Optional[datetime] = None
        self.last_success_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.last_error_at: Optional[datetime] = None
        self.expected_cadence_seconds: int = 300
        self.last_latency_ms: int = 0
        self.total_requests_24h: int = 0
        self.successful_requests_24h: int = 0

    @abstractmethod
    async def fetch(self, **kwargs) -> List[SourceItemBase]:
        """Fetch raw items from upstream source."""
        pass

    async def _execute_http_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
    ) -> httpx.Response:
        """Executes HTTP request with rate-limiting, retries, jitter, and circuit breaking."""
        if not self.circuit_breaker.can_attempt():
            self.last_error = f"Circuit breaker OPEN for source {self.source_id}"
            self.last_error_at = datetime.now(timezone.utc)
            raise RuntimeError(f"Circuit breaker for source '{self.source_id}' is OPEN. Aborting request.")

        await self.rate_limiter.acquire()

        req_headers = {
            "User-Agent": settings.COLLECTOR_USER_AGENT,
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            req_headers.update(headers)

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            start_time = time.time()
            self.total_requests_24h += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=req_headers,
                        params=params,
                        json=json_body,
                    )
                    response.raise_for_status()
                    self.last_latency_ms = int((time.time() - start_time) * 1000)
                    self.last_success_at = datetime.now(timezone.utc)
                    self.last_error = None
                    self.successful_requests_24h += 1
                    self.circuit_breaker.record_success()
                    return response
            except Exception as e:
                last_exc = e
                self.last_error = str(e)
                self.last_error_at = datetime.now(timezone.utc)
                self.circuit_breaker.record_failure()
                if attempt < self.max_retries:
                    # Exponential backoff with jitter
                    backoff = (2 ** attempt) + random.uniform(0.1, 1.0)
                    logger.warning(
                        f"Attempt {attempt}/{self.max_retries} failed for {url}: {e}. Retrying in {backoff:.2f}s"
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for {url}: {e}")

        raise last_exc or RuntimeError(f"Unknown network failure fetching {url}")

    def compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content for provenance and deduplication."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_health(self) -> Dict[str, Any]:
        """Returns comprehensive health diagnostic dictionary with status classification."""
        success_rate = (
            (self.successful_requests_24h / self.total_requests_24h * 100.0)
            if self.total_requests_24h > 0
            else 100.0
        )
        
        now = datetime.now(timezone.utc)
        is_stale = False
        if self.last_success_at:
            delta_seconds = (now - self.last_success_at).total_seconds()
            if delta_seconds > self.expected_cadence_seconds * 3:
                is_stale = True

        # Classify status: healthy, degraded, rate-limited, failed, stale
        if self.circuit_breaker.state == CircuitState.OPEN:
            status = "failed"
            rate_status = "BLOCKED"
        elif self.last_error and "429" in self.last_error:
            status = "rate-limited"
            rate_status = "THROTTLED"
        elif is_stale:
            status = "stale"
            rate_status = "OK"
        elif self.circuit_breaker.consecutive_failures > 0 or success_rate < 90.0:
            status = "degraded"
            rate_status = "OK"
        else:
            status = "healthy"
            rate_status = "OK"

        return {
            "source_id": self.source_id,
            "name": self.name,
            "status": status,
            "last_poll_at": self.last_poll_at,
            "last_success_at": self.last_success_at,
            "consecutive_failures": self.circuit_breaker.consecutive_failures,
            "success_rate_24h": round(success_rate, 2),
            "latency_ms": self.last_latency_ms,
            "rate_limit_status": rate_status,
            "notes": self.last_error,
        }
