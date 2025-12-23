"""Tests for per-browser session limits in State."""

from unittest.mock import MagicMock

from mvg_departures.adapters.web.state import State


def _make_socket_with_browser_id(browser_id: str) -> object:
    """Create a minimal socket-like object with a scope that includes a browser id cookie."""
    scope = {
        "client": ("192.0.2.1", 12345),
        "headers": [
            (b"user-agent", b"TestBrowser/1.0"),
            (b"cookie", f"mvg_browser_id={browser_id}".encode()),
        ],
    }
    socket = MagicMock()
    socket.scope = scope
    return socket


def test_register_socket_enforces_per_browser_limit() -> None:
    """Given a browser id, when exceeding the limit, then additional sockets are rejected."""
    # Limit to 1 connection per browser to make the test small and clear.
    state = State(route_path="/", max_sessions_per_browser=1)
    browser_id = "browser-123"

    first_socket = _make_socket_with_browser_id(browser_id)
    second_socket = _make_socket_with_browser_id(browser_id)

    assert state.register_socket(first_socket, "session-1") is True
    assert first_socket in state.connected_sockets

    # Second socket from same browser should be rejected.
    assert state.register_socket(second_socket, "session-2") is False
    assert second_socket not in state.connected_sockets
    # The first socket remains registered.
    assert first_socket in state.connected_sockets


def test_register_socket_does_not_limit_unknown_browser_id() -> None:
    """Given a socket without browser id, when registering, then no browser limit is applied."""
    # Use a small limit but sockets without browser_id should bypass it.
    state = State(route_path="/", max_sessions_per_browser=1)

    first_socket = MagicMock()
    second_socket = MagicMock()

    assert state.register_socket(first_socket, "session-1") is True
    assert state.register_socket(second_socket, "session-2") is True

    assert first_socket in state.connected_sockets
    assert second_socket in state.connected_sockets
