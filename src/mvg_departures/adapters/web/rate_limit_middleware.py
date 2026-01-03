"""Rate limiting middleware for Starlette using throttled-py."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from throttled import RateLimiterType, Throttled, rate_limiter, store

logger = logging.getLogger(__name__)


def extract_client_ip(request: Request) -> str:
    """Extract client IP address from request, supporting X-Forwarded-For header.

    Handles X-Forwarded-For header which may contain multiple IPs (client, proxy1, proxy2).
    Returns the first (original client) IP in the chain.

    Note: throttled-py does not natively parse X-Forwarded-For, so we handle it here.
    """
    # Check X-Forwarded-For header first (for reverse proxy/load balancer scenarios)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
        # Take the first one (original client IP)
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    # Fallback to direct connection IP
    if request.client and request.client.host:
        return request.client.host

    # Last resort: use a default identifier
    logger.warning("Could not determine client IP, using 'unknown'")
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting per IP address."""

    def __init__(
        self,
        app: Callable,
        requests_per_minute: int = 100,
    ) -> None:
        """Initialize rate limiting middleware.

        Args:
            app: The ASGI application to wrap.
            requests_per_minute: Maximum number of requests allowed per IP per minute.
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        # Store quota and store for creating per-IP throttlers
        # Each IP gets its own Throttled instance with the same quota
        self.quota = rate_limiter.per_min(requests_per_minute, burst=requests_per_minute)
        self.rate_limiter_store = store.MemoryStore()
        logger.info(f"Rate limiting enabled: {requests_per_minute} requests per minute per IP")

    def _extract_retry_after(self, result: Any) -> float:
        """Extract retry_after value from rate limit result."""
        retry_after: float = 60.0  # Default retry after 60 seconds
        if hasattr(result, "state"):
            state = getattr(result, "state", None)
            if state and hasattr(state, "retry_after"):
                retry_after = float(getattr(state, "retry_after", 60.0))
        elif hasattr(result, "retry_after"):
            retry_after = float(getattr(result, "retry_after", 60.0))
        return retry_after

    def _create_rate_limit_response(self, client_ip: str, retry_after: float) -> Response:
        """Create rate limit exceeded response."""
        logger.warning(f"Rate limit exceeded for IP {client_ip}, retry after {retry_after} seconds")
        return Response(
            content="Rate limit exceeded. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(int(retry_after))},
        )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and enforce rate limiting."""
        client_ip = extract_client_ip(request)

        # Create a Throttled instance for this IP
        # Each IP gets tracked separately with the same quota
        throttle = Throttled(
            key=client_ip,
            using=RateLimiterType.TOKEN_BUCKET.value,
            quota=self.quota,
            store=self.rate_limiter_store,
        )

        # Check rate limit using limit() method - returns result object without raising exceptions
        result = throttle.limit()
        if result.limited:
            retry_after = self._extract_retry_after(result)
            return self._create_rate_limit_response(client_ip, retry_after)

        # Rate limit check passed, proceed with the request
        response: Response = await call_next(request)
        return response
