"""Utility for logging API requests when MMD_LOG_REQUESTS is enabled."""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def should_log_requests() -> bool:
    """Check if request logging is enabled via MMD_LOG_REQUESTS environment variable."""
    return os.getenv("MMD_LOG_REQUESTS", "").lower() == "true"


def _build_url_with_params(url: str, params: dict[str, Any] | None) -> str:
    """Build full URL with query parameters."""
    if not params:
        return url
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"{url}?{param_str}" if "?" not in url else f"{url}&{param_str}"


def _format_payload(payload: Any) -> str:
    """Format payload for logging."""
    try:
        return json.dumps(payload, indent=2) if isinstance(payload, dict) else str(payload)
    except (TypeError, ValueError):
        return str(payload)


def _build_log_message(method: str, url: str, params: dict[str, Any] | None, payload: Any) -> str:
    """Build log message for API request.

    Args:
        method: HTTP method.
        url: Request URL.
        params: Query parameters.
        payload: Request payload.

    Returns:
        Formatted log message.
    """
    full_url = _build_url_with_params(url, params)
    log_parts = [f"{method} {full_url}"]
    if payload is not None:
        log_parts.append(f"Payload: {_format_payload(payload)}")
    return "API Request:\n" + "\n".join(log_parts)


def log_api_request(
    method: str,
    url: str,
    params: dict[str, Any] | None = None,
    payload: Any = None,
    **kwargs: Any,  # noqa: ARG001 - Accept headers and other args for API compatibility
) -> None:
    """Log API request details if MMD_LOG_REQUESTS is enabled.

    Args:
        method: HTTP method (GET, POST, etc.).
        url: Request URL.
        params: Query parameters (optional).
        payload: Request payload/body (optional).
        **kwargs: Additional arguments (e.g., headers) accepted for API compatibility but not logged.
    """
    if not should_log_requests():
        return
    logger.info(_build_log_message(method, url, params, payload))
