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


def _truncate_user_agent(user_agent: str, max_length: int = 200) -> str:
    """Truncate user agent string if too long."""
    if len(user_agent) > max_length:
        return f"{user_agent[:max_length-3]}..."
    return user_agent


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
            return _truncate_user_agent(user_agent)
    return "unknown"


def _process_header_for_forwarded_ip(
    name: Any, value: Any, forwarded_for: str | None, fly_client_ip: str | None
) -> tuple[str | None, str | None]:
    """Process a single header for forwarded IP extraction."""
    decoded_name = _decode_header_value(name).lower()
    if decoded_name == "x-forwarded-for":
        forwarded_for = _decode_header_value(value)
    elif decoded_name == "fly-client-ip":
        fly_client_ip = _decode_header_value(value)
    return forwarded_for, fly_client_ip


def _extract_forwarded_ip(headers: list[tuple[Any, Any]]) -> tuple[str | None, str | None]:
    """Extract forwarded IP addresses from headers."""
    forwarded_for: str | None = None
    fly_client_ip: str | None = None

    for name, value in headers:
        forwarded_for, fly_client_ip = _process_header_for_forwarded_ip(
            name, value, forwarded_for, fly_client_ip
        )

    return forwarded_for, fly_client_ip


def _get_first_forwarded_ip(forwarded_for: str) -> str | None:
    """Get first IP from X-Forwarded-For header."""
    first = forwarded_for.split(",")[0].strip()
    return first if first else None


def _extract_ip_from_scope(scope: dict[str, Any]) -> str | None:
    """Extract IP address from ASGI scope."""
    client = scope.get("client")
    if isinstance(client, (list, tuple)) and client:
        candidate = client[0]
        if isinstance(candidate, (str, bytes)):
            return _decode_header_value(candidate)
    return None


def _extract_ip_from_headers(headers: list[tuple[Any, Any]], scope: dict[str, Any]) -> str:
    """Extract IP address from headers or scope.

    Args:
        headers: List of header tuples.
        scope: ASGI scope dictionary.

    Returns:
        IP address string, or "unknown" if not found.
    """
    forwarded_for, fly_client_ip = _extract_forwarded_ip(headers)

    if forwarded_for:
        first_ip = _get_first_forwarded_ip(forwarded_for)
        if first_ip:
            return first_ip

    if fly_client_ip:
        return fly_client_ip

    scope_ip = _extract_ip_from_scope(scope)
    if scope_ip:
        return scope_ip

    return "unknown"


def _extract_cookie_header(headers: list[tuple[Any, Any]]) -> str | None:
    """Extract cookie header value from headers."""
    for name, value in headers:
        decoded_name = _decode_header_value(name).lower()
        if decoded_name == "cookie":
            return _decode_header_value(value)
    return None


def _parse_cookie_part(part: str) -> str | None:
    """Parse a single cookie part for browser ID."""
    name_value = part.strip().split("=", 1)
    if len(name_value) == 2 and name_value[0] == "mvg_browser_id":
        browser_id = name_value[1]
        if len(browser_id) > 128:
            browser_id = f"{browser_id[:125]}..."
        return browser_id
    return None


def _parse_browser_id_from_cookie(cookie_header: str) -> str | None:
    """Parse browser ID from cookie header."""
    for part in cookie_header.split(";"):
        browser_id = _parse_cookie_part(part)
        if browser_id:
            return browser_id
    return None


def _extract_browser_id(headers: list[tuple[Any, Any]]) -> str:
    """Extract browser ID from cookie header.

    Args:
        headers: List of header tuples.

    Returns:
        Browser ID string, or "unknown" if not found.
    """
    cookie_header = _extract_cookie_header(headers)
    if not cookie_header:
        return "unknown"

    browser_id = _parse_browser_id_from_cookie(cookie_header)
    return browser_id if browser_id else "unknown"


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
