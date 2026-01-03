"""Behavior-focused tests for rate limiting middleware."""

from unittest.mock import MagicMock

from mvg_departures.adapters.web.rate_limit_middleware import extract_client_ip


class TestExtractClientIp:
    """Tests for client IP extraction behavior."""

    def test_when_x_forwarded_for_has_single_ip_then_returns_that_ip(self) -> None:
        """Given X-Forwarded-For with single IP, when extracting, then returns it."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.50"}
        request.client = None

        result = extract_client_ip(request)

        assert result == "203.0.113.50"

    def test_when_x_forwarded_for_has_chain_then_returns_first_ip(self) -> None:
        """Given X-Forwarded-For with IP chain, when extracting, then returns original client IP."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.50, 70.41.3.18, 150.172.238.178"}
        request.client = None

        result = extract_client_ip(request)

        assert result == "203.0.113.50"

    def test_when_x_forwarded_for_has_whitespace_then_trims_ip(self) -> None:
        """Given X-Forwarded-For with whitespace, when extracting, then returns trimmed IP."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "  192.168.1.1  , 10.0.0.1"}
        request.client = None

        result = extract_client_ip(request)

        assert result == "192.168.1.1"

    def test_when_no_x_forwarded_for_then_uses_direct_client_ip(self) -> None:
        """Given no X-Forwarded-For, when extracting, then uses direct connection IP."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        result = extract_client_ip(request)

        assert result == "10.0.0.1"

    def test_when_x_forwarded_for_empty_then_uses_direct_client_ip(self) -> None:
        """Given empty X-Forwarded-For, when extracting, then falls back to direct IP."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": ""}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        result = extract_client_ip(request)

        assert result == "192.168.1.100"

    def test_when_no_client_info_available_then_returns_unknown(self) -> None:
        """Given no client information, when extracting, then returns 'unknown'."""
        request = MagicMock()
        request.headers = {}
        request.client = None

        result = extract_client_ip(request)

        assert result == "unknown"

    def test_when_client_has_no_host_then_returns_unknown(self) -> None:
        """Given client without host, when extracting, then returns 'unknown'."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = None

        result = extract_client_ip(request)

        assert result == "unknown"


class TestRateLimitMiddlewareRetryAfterExtraction:
    """Tests for retry_after extraction from rate limit results."""

    def test_when_result_has_state_with_retry_after_then_extracts_it(self) -> None:
        """Given result with state.retry_after, when extracting, then returns that value."""
        from mvg_departures.adapters.web.rate_limit_middleware import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=MagicMock(), requests_per_minute=100)

        result = MagicMock()
        result.state = MagicMock()
        result.state.retry_after = 45.5

        retry_after = middleware._extract_retry_after(result)

        assert retry_after == 45.5

    def test_when_result_has_direct_retry_after_then_extracts_it(self) -> None:
        """Given result with direct retry_after, when extracting, then returns that value."""
        from mvg_departures.adapters.web.rate_limit_middleware import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=MagicMock(), requests_per_minute=100)

        result = MagicMock(spec=["retry_after"])
        result.retry_after = 30.0

        retry_after = middleware._extract_retry_after(result)

        assert retry_after == 30.0

    def test_when_result_has_no_retry_after_then_returns_default(self) -> None:
        """Given result without retry_after, when extracting, then returns 60 seconds default."""
        from mvg_departures.adapters.web.rate_limit_middleware import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=MagicMock(), requests_per_minute=100)

        result = MagicMock(spec=[])

        retry_after = middleware._extract_retry_after(result)

        assert retry_after == 60.0


class TestRateLimitMiddlewareResponseCreation:
    """Tests for rate limit response creation."""

    def test_when_rate_limited_then_returns_429_with_retry_header(self) -> None:
        """Given rate limit exceeded, when creating response, then returns 429 with Retry-After."""
        from mvg_departures.adapters.web.rate_limit_middleware import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=MagicMock(), requests_per_minute=100)

        response = middleware._create_rate_limit_response("192.168.1.1", 45.5)

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "45"
        assert b"Rate limit exceeded" in response.body
