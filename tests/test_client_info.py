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
