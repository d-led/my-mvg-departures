"""Utilities for extracting client information from LiveView sockets.

These helpers are intentionally small and defensive so they can be used from
multiple adapter modules (views, state, presence) without introducing new
coupling to the web framework.
"""

from __future__ import annotations

from typing import Any


def _decode_header_value(value: Any) -> str:
    """Decode a header value into a readable string."""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return value.decode("latin1", errors="replace")
    return str(value)


def get_client_info_from_scope(scope: dict[str, Any] | None) -> tuple[str, str, str]:
    """Extract client IP, user agent, and browser ID from an ASGI scope-like mapping.

    Returns:
        Tuple of (ip, user_agent, browser_id). When information is not available, the
        returned values fall back to the string ``"unknown"``.
    """
    if not isinstance(scope, dict):
        return "unknown", "unknown", "unknown"

    user_agent = "unknown"
    browser_id = "unknown"
    cookie_header: str | None = None
    forwarded_for: str | None = None
    fly_client_ip: str | None = None

    headers = scope.get("headers") or []
    for name, value in headers:
        decoded_name = _decode_header_value(name).lower()
        if decoded_name == "user-agent":
            user_agent = _decode_header_value(value)
            # Avoid excessively long user agent strings in logs
            if len(user_agent) > 200:
                user_agent = f"{user_agent[:197]}..."
        elif decoded_name == "cookie":
            cookie_header = _decode_header_value(value)
        elif decoded_name == "x-forwarded-for":
            forwarded_for = _decode_header_value(value)
        elif decoded_name == "fly-client-ip":
            fly_client_ip = _decode_header_value(value)

    # Prefer Fly/forwarded headers for IP if present, otherwise fall back to ASGI client.
    ip = "unknown"
    if forwarded_for:
        # X-Forwarded-For may contain a list: client, proxy1, proxy2, ...
        first = forwarded_for.split(",")[0].strip()
        if first:
            ip = first
    elif fly_client_ip:
        ip = fly_client_ip
    else:
        client = scope.get("client")
        if isinstance(client, (list, tuple)) and client:
            candidate = client[0]
            if isinstance(candidate, (str, bytes)):
                ip = _decode_header_value(candidate)

    if cookie_header:
        for part in cookie_header.split(";"):
            name_value = part.strip().split("=", 1)
            if len(name_value) == 2 and name_value[0] == "mvg_browser_id":
                browser_id = name_value[1]
                if len(browser_id) > 128:
                    browser_id = f"{browser_id[:125]}..."
                break

    return ip, user_agent, browser_id


def get_client_info_from_socket(socket: Any) -> tuple[str, str, str]:
    """Convenience wrapper to extract client info directly from a socket.

    The socket is expected to expose a ``scope`` attribute with the usual
    ASGI shape. When that attribute is missing or malformed, this function
    returns ``(\"unknown\", \"unknown\", \"unknown\")`` rather than raising.
    """
    scope = getattr(socket, "scope", None)
    return get_client_info_from_scope(scope)
