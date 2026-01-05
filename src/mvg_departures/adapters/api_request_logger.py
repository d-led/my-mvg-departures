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


def _redact_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    """Redact sensitive headers from logging."""
    sensitive_keys = {"authorization", "cookie", "x-api-key"}
    return {k: "***REDACTED***" if k.lower() in sensitive_keys else v for k, v in headers.items()}


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
    headers: dict[str, str] | None = None,
    payload: Any = None,
) -> None:
    """Log API request details if MMD_LOG_REQUESTS is enabled.

    Args:
        method: HTTP method (GET, POST, etc.).
        url: Request URL.
        params: Query parameters (optional).
        headers: Request headers (optional, sensitive headers may be redacted).
        payload: Request payload/body (optional).
    """
    if not should_log_requests():
        return

    full_url = _build_url_with_params(url, params)
    log_parts = [f"{method} {full_url}"]

    if headers:
        safe_headers = _redact_sensitive_headers(headers)
        log_parts.append(f"Headers: {json.dumps(safe_headers, indent=2)}")

    if payload is not None:
        log_parts.append(f"Payload: {_format_payload(payload)}")

    logger.info("API Request:\n" + "\n".join(log_parts))
