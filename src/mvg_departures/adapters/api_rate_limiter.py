"""Rate limiter for outgoing API requests.

Provides per-adapter rate limiting to be nice to external APIs.
Uses a simple time-based approach with minimum delay between requests.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import ClassVar

logger = logging.getLogger(__name__)


class ApiRateLimiter:
    """Rate limiter for outgoing API requests.

    Ensures a minimum delay between requests to a specific API.
    Thread-safe and async-safe using asyncio.Lock.
    """

    # Class-level registry of rate limiters by API name
    _instances: ClassVar[dict[str, ApiRateLimiter]] = {}
    _registry_lock: ClassVar[asyncio.Lock | None] = None

    def __init__(self, api_name: str, min_delay_seconds: float = 1.0) -> None:
        """Initialize the rate limiter.

        Args:
            api_name: Name of the API (for logging).
            min_delay_seconds: Minimum delay between requests in seconds.
        """
        self.api_name = api_name
        self.min_delay_seconds = min_delay_seconds
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, api_name: str, min_delay_seconds: float = 1.0) -> ApiRateLimiter:
        """Get or create a rate limiter instance for an API.

        This ensures all calls to the same API share the same rate limiter.

        Args:
            api_name: Name of the API.
            min_delay_seconds: Minimum delay between requests in seconds.

        Returns:
            Shared ApiRateLimiter instance for the API.
        """
        # Lazy init the registry lock
        if cls._registry_lock is None:
            cls._registry_lock = asyncio.Lock()

        async with cls._registry_lock:
            if api_name not in cls._instances:
                cls._instances[api_name] = cls(api_name, min_delay_seconds)
                logger.info(
                    f"Created rate limiter for {api_name} with {min_delay_seconds}s minimum delay"
                )
            return cls._instances[api_name]

    async def acquire(self) -> None:
        """Acquire permission to make a request.

        Blocks until enough time has passed since the last request.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            wait_time = self.min_delay_seconds - elapsed

            if wait_time > 0:
                logger.debug(f"{self.api_name}: waiting {wait_time:.2f}s before next request")
                await asyncio.sleep(wait_time)

            self._last_request_time = time.monotonic()

    async def __aenter__(self) -> ApiRateLimiter:
        """Context manager entry - acquire rate limit."""
        await self.acquire()
        return self

    async def __aexit__(
        self, _exc_type: type | None, _exc_val: Exception | None, _exc_tb: object
    ) -> None:
        """Context manager exit - nothing to do."""
