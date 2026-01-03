"""Tests for the API rate limiter."""

import asyncio
import time

import pytest

from mvg_departures.adapters.api_rate_limiter import ApiRateLimiter


class TestApiRateLimiter:
    """Tests for ApiRateLimiter class."""

    @pytest.fixture(autouse=True)
    def reset_instances(self) -> None:
        """Reset the shared instances before each test."""
        ApiRateLimiter._instances.clear()
        ApiRateLimiter._registry_lock = None

    @pytest.mark.asyncio
    async def test_first_request_is_immediate(self) -> None:
        """First request should not wait."""
        limiter = ApiRateLimiter("test_api", min_delay_seconds=1.0)

        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start

        # First request should be nearly instant (< 50ms)
        assert elapsed < 0.05

    @pytest.mark.asyncio
    async def test_second_request_waits_for_delay(self) -> None:
        """Second request should wait for the minimum delay."""
        delay = 0.2  # Use short delay for fast tests
        limiter = ApiRateLimiter("test_api", min_delay_seconds=delay)

        # First request
        await limiter.acquire()

        # Second request should wait
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should have waited approximately the delay time
        assert elapsed >= delay * 0.9  # Allow 10% tolerance

    @pytest.mark.asyncio
    async def test_request_after_delay_is_immediate(self) -> None:
        """Request after the delay period should not wait."""
        delay = 0.1
        limiter = ApiRateLimiter("test_api", min_delay_seconds=delay)

        # First request
        await limiter.acquire()

        # Wait longer than the delay
        await asyncio.sleep(delay * 1.5)

        # Next request should be immediate
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should be nearly instant
        assert elapsed < 0.05

    @pytest.mark.asyncio
    async def test_shared_instance_returns_same_limiter(self) -> None:
        """get_instance should return the same limiter for the same API."""
        limiter1 = await ApiRateLimiter.get_instance("shared_api", 1.0)
        limiter2 = await ApiRateLimiter.get_instance("shared_api", 1.0)

        assert limiter1 is limiter2

    @pytest.mark.asyncio
    async def test_different_apis_get_different_limiters(self) -> None:
        """Different APIs should get different limiters."""
        limiter1 = await ApiRateLimiter.get_instance("api_one", 1.0)
        limiter2 = await ApiRateLimiter.get_instance("api_two", 1.0)

        assert limiter1 is not limiter2

    @pytest.mark.asyncio
    async def test_shared_limiter_enforces_global_rate(self) -> None:
        """Shared limiter should enforce rate across all callers."""
        delay = 0.15
        limiter = await ApiRateLimiter.get_instance("global_test", delay)

        # Simulate two "clients" using the same shared limiter
        start = time.monotonic()

        # First client acquires
        await limiter.acquire()
        time1 = time.monotonic() - start

        # Second client acquires (should wait)
        await limiter.acquire()
        time2 = time.monotonic() - start

        # Third client acquires (should wait more)
        await limiter.acquire()
        time3 = time.monotonic() - start

        # First should be immediate
        assert time1 < 0.05
        # Second should wait ~delay
        assert time2 >= delay * 0.9
        # Third should wait ~2*delay
        assert time3 >= delay * 1.8

    @pytest.mark.asyncio
    async def test_context_manager_acquires_on_enter(self) -> None:
        """Context manager should acquire on entry."""
        delay = 0.15
        limiter = ApiRateLimiter("context_test", min_delay_seconds=delay)

        # First use
        async with limiter:
            pass

        # Second use should wait
        start = time.monotonic()
        async with limiter:
            elapsed = time.monotonic() - start

        assert elapsed >= delay * 0.9

    @pytest.mark.asyncio
    async def test_concurrent_requests_are_serialized(self) -> None:
        """Concurrent requests should be serialized by the lock."""
        delay = 0.1
        limiter = ApiRateLimiter("concurrent_test", min_delay_seconds=delay)

        results: list[float] = []
        start = time.monotonic()

        async def make_request() -> None:
            await limiter.acquire()
            results.append(time.monotonic() - start)

        # Launch 3 concurrent requests
        await asyncio.gather(
            make_request(),
            make_request(),
            make_request(),
        )

        # All 3 should complete
        assert len(results) == 3

        # Sort results to check timing
        results.sort()

        # First should be quick
        assert results[0] < 0.05
        # Second should wait ~delay
        assert results[1] >= delay * 0.8
        # Third should wait ~2*delay
        assert results[2] >= delay * 1.6

    @pytest.mark.asyncio
    async def test_different_apis_dont_block_each_other(self) -> None:
        """Different APIs should have independent rate limits."""
        delay = 0.2
        limiter_a = await ApiRateLimiter.get_instance("api_a", delay)
        limiter_b = await ApiRateLimiter.get_instance("api_b", delay)

        # Acquire from API A
        await limiter_a.acquire()

        # API B should be immediate (different limiter)
        start = time.monotonic()
        await limiter_b.acquire()
        elapsed = time.monotonic() - start

        assert elapsed < 0.05  # Should be immediate
