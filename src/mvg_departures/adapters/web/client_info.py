"""Utilities for extracting client information from LiveView sockets.

These helpers are intentionally small and defensive so they can be used from
multiple adapter modules (views, state, presence) without introducing new
coupling to the web framework.
"""

from __future__ import annotations

from typing import Any

from mvg_departures.domain.models.client_info import ClientInfo


def _decode_header_value(value: Any) -> str:
    """Decode a header value into a readable string."""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return value.decode("latin1", errors="replace")
    return str(value)


def _extract_user_agent(headers: list[tuple[Any, Any]]) -> str:
    """Extract user agent from headers.

    Args:
        headers: List of header tuples.

    Returns:
        User agent string, or "unknown" if not found.
    """
    for name, value in headers:
        decoded_name = _decode_header_value(name).lower()
        if decoded_name == "user-agent":
            user_agent = _decode_header_value(value)
            if len(user_agent) > 200:
                user_agent = f"{user_agent[:197]}..."
            return user_agent
    return "unknown"


def _extract_ip_from_headers(headers: list[tuple[Any, Any]], scope: dict[str, Any]) -> str:
    """Extract IP address from headers or scope.

    Args:
        headers: List of header tuples.
        scope: ASGI scope dictionary.

    Returns:
        IP address string, or "unknown" if not found.
    """
    forwarded_for: str | None = None
    fly_client_ip: str | None = None

    for name, value in headers:
        decoded_name = _decode_header_value(name).lower()
        if decoded_name == "x-forwarded-for":
            forwarded_for = _decode_header_value(value)
        elif decoded_name == "fly-client-ip":
            fly_client_ip = _decode_header_value(value)

    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first

    if fly_client_ip:
        return fly_client_ip

    client = scope.get("client")
    if isinstance(client, (list, tuple)) and client:
        candidate = client[0]
        if isinstance(candidate, (str, bytes)):
            return _decode_header_value(candidate)

    return "unknown"


def _extract_browser_id(headers: list[tuple[Any, Any]]) -> str:
    """Extract browser ID from cookie header.

    Args:
        headers: List of header tuples.

    Returns:
        Browser ID string, or "unknown" if not found.
    """
    cookie_header: str | None = None

    for name, value in headers:
        decoded_name = _decode_header_value(name).lower()
        if decoded_name == "cookie":
            cookie_header = _decode_header_value(value)
            break

    if not cookie_header:
        return "unknown"

    for part in cookie_header.split(";"):
        name_value = part.strip().split("=", 1)
        if len(name_value) == 2 and name_value[0] == "mvg_browser_id":
            browser_id = name_value[1]
            if len(browser_id) > 128:
                browser_id = f"{browser_id[:125]}..."
            return browser_id

    return "unknown"


def get_client_info_from_scope(scope: dict[str, Any] | None) -> ClientInfo:
    """Extract client IP, user agent, and browser ID from an ASGI scope-like mapping.

    Returns:
        ClientInfo with ip, user_agent, and browser_id. When information is not available, the
        returned values fall back to the string ``"unknown"``.
    """
    if not isinstance(scope, dict):
        return ClientInfo(ip="unknown", user_agent="unknown", browser_id="unknown")

    headers = scope.get("headers") or []
    user_agent = _extract_user_agent(headers)
    ip = _extract_ip_from_headers(headers, scope)
    browser_id = _extract_browser_id(headers)

    return ClientInfo(ip=ip, user_agent=user_agent, browser_id=browser_id)


def get_client_info_from_socket(socket: Any) -> ClientInfo:
    """Convenience wrapper to extract client info directly from a socket.

    The socket is expected to expose a ``scope`` attribute with the usual
    ASGI shape. When that attribute is missing or malformed, this function
    returns ClientInfo with all fields set to ``"unknown"`` rather than raising.
    """
    scope = getattr(socket, "scope", None)
    return get_client_info_from_scope(scope)
