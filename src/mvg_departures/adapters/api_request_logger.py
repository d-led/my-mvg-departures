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


def log_api_request(
    method: str,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,  # noqa: ARG001
    payload: Any = None,
) -> None:
    """Log API request details if MMD_LOG_REQUESTS is enabled.

    Args:
        method: HTTP method (GET, POST, etc.).
        url: Request URL.
        params: Query parameters (optional).
        headers: Request headers (optional, not logged, kept for API compatibility).
        payload: Request payload/body (optional).
    """
    if not should_log_requests():
        return

    full_url = _build_url_with_params(url, params)
    log_parts = [f"{method} {full_url}"]

    if payload is not None:
        log_parts.append(f"Payload: {_format_payload(payload)}")

    logger.info("API Request:\n" + "\n".join(log_parts))
