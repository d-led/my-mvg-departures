"""Tests for client info extraction helpers."""

from types import SimpleNamespace

from mvg_departures.adapters.web.client_info import (
    get_client_info_from_scope,
    get_client_info_from_socket,
)


def test_get_client_info_from_scope_with_full_data() -> None:
    """Given a scope with client and user agent, then extract both values."""
    scope = {
        "client": ("203.0.113.10", 54321),
        "headers": [
            (b"host", b"example.test"),
            (b"user-agent", b"TestBrowser/1.0 (TestOS)"),
            (b"cookie", b"mvg_browser_id=test-browser-123; other=ignore-me"),
        ],
    }

    client_info = get_client_info_from_scope(scope)

    assert client_info.ip == "203.0.113.10"
    assert client_info.user_agent == "TestBrowser/1.0 (TestOS)"
    assert client_info.browser_id == "test-browser-123"


def test_get_client_info_from_scope_without_headers() -> None:
    """Given a scope without headers, then user agent falls back to unknown."""
    scope = {
        "client": ("198.51.100.42", 12345),
    }

    client_info = get_client_info_from_scope(scope)

    assert client_info.ip == "198.51.100.42"
    assert client_info.user_agent == "unknown"
    assert client_info.browser_id == "unknown"


def test_get_client_info_from_scope_with_invalid_scope() -> None:
    """Given an invalid scope, then both values are unknown."""
    client_info = get_client_info_from_scope(None)

    assert client_info.ip == "unknown"
    assert client_info.user_agent == "unknown"
    assert client_info.browser_id == "unknown"


def test_get_client_info_from_socket_uses_scope_attribute() -> None:
    """Given a socket with a scope attribute, then delegates to scope helper."""
    scope = {
        "client": ("192.0.2.1", 80),
        "headers": [
            (b"user-agent", b"AnotherBrowser/2.0"),
            (b"cookie", b"mvg_browser_id=from-socket-999"),
        ],
    }
    socket = SimpleNamespace(scope=scope)

    client_info = get_client_info_from_socket(socket)

    assert client_info.ip == "192.0.2.1"
    assert client_info.user_agent == "AnotherBrowser/2.0"
    assert client_info.browser_id == "from-socket-999"


def test_get_client_info_from_scope_ignores_unrelated_cookies() -> None:
    """Given cookies without our browser ID, then browser_id is unknown."""
    scope = {
        "client": ("192.0.2.55", 80),
        "headers": [
            (b"cookie", b"session=abc; other=value"),
        ],
    }

    client_info = get_client_info_from_scope(scope)

    assert client_info.browser_id == "unknown"


def test_get_client_info_from_scope_prefers_x_forwarded_for_over_client_ip() -> None:
    """Given X-Forwarded-For header, when extracting IP, then uses first forwarded IP."""
    scope = {
        "client": ("10.0.0.1", 80),  # Internal proxy IP
        "headers": [
            (b"x-forwarded-for", b"203.0.113.50, 70.41.3.18, 150.172.238.178"),
            (b"user-agent", b"Browser/1.0"),
        ],
    }

    client_info = get_client_info_from_scope(scope)

    assert client_info.ip == "203.0.113.50"  # First in chain is original client


def test_get_client_info_from_scope_prefers_fly_client_ip_when_no_forwarded_for() -> None:
    """Given Fly-Client-IP header but no X-Forwarded-For, when extracting, then uses Fly IP."""
    scope = {
        "client": ("10.0.0.1", 80),
        "headers": [
            (b"fly-client-ip", b"198.51.100.42"),
            (b"user-agent", b"Browser/1.0"),
        ],
    }

    client_info = get_client_info_from_scope(scope)

    assert client_info.ip == "198.51.100.42"


def test_get_client_info_from_scope_truncates_long_user_agent() -> None:
    """Given very long user agent, when extracting, then truncates with ellipsis."""
    long_ua = "A" * 300  # Way over 200 char limit
    scope = {
        "client": ("192.0.2.1", 80),
        "headers": [
            (b"user-agent", long_ua.encode()),
        ],
    }

    client_info = get_client_info_from_scope(scope)

    assert len(client_info.user_agent) == 200
    assert client_info.user_agent.endswith("...")


def test_get_client_info_from_scope_truncates_long_browser_id() -> None:
    """Given very long browser ID in cookie, when extracting, then truncates with ellipsis."""
    long_id = "B" * 200  # Over 128 char limit
    scope = {
        "client": ("192.0.2.1", 80),
        "headers": [
            (b"cookie", f"mvg_browser_id={long_id}".encode()),
        ],
    }

    client_info = get_client_info_from_scope(scope)

    assert len(client_info.browser_id) == 128
    assert client_info.browser_id.endswith("...")
