"""SSL context manager for HAFAS API operations.

This module provides a context manager to temporarily disable SSL verification
only for HAFAS operations, ensuring MVG API calls still use SSL verification.
"""

import ssl
from collections.abc import Callable
from typing import Any

import requests
import urllib3


class HafasSSLContext:
    """Context manager to temporarily disable SSL verification only for HAFAS operations.

    This ensures MVG API calls still use SSL verification while HAFAS calls don't.

    Usage:
        with HafasSSLContext():
            # HAFAS API calls here will have SSL verification disabled
            await client.departures(...)
        # SSL verification is restored after the context
    """

    def __init__(self) -> None:
        """Initialize the context manager."""
        self._original_ssl_context: Callable[..., ssl.SSLContext] | None = None
        self._urllib3_original_init: Callable[..., None] | None = None
        self._urllib3_original_match_hostname: Callable[..., None] | None = None
        self._urllib3_patched = False
        self._requests_original_request: Callable[..., Any] | None = None
        self._requests_patched = False

    def __enter__(self) -> "HafasSSLContext":
        """Disable SSL verification for HAFAS operations."""
        # Store original SSL context
        self._original_ssl_context = ssl._create_default_https_context

        # Temporarily set unverified context
        ssl._create_default_https_context = ssl._create_unverified_context  # type: ignore[assignment]

        # Also patch urllib3 for requests-based clients (temporarily)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Patch HTTPSConnection.__init__ to disable SSL verification
        self._urllib3_original_init = urllib3.connection.HTTPSConnection.__init__

        original_init = self._urllib3_original_init

        def patched_https_connection_init(self: Any, *args: Any, **kwargs: Any) -> None:
            # Set cert_reqs to disable certificate verification
            kwargs.setdefault("cert_reqs", ssl.CERT_NONE)
            # Disable hostname verification (urllib3 parameter)
            kwargs.setdefault("assert_hostname", False)
            # Also create an unverified SSL context if ssl_context is not provided
            if "ssl_context" not in kwargs:
                unverified_context = ssl._create_unverified_context()
                # Explicitly disable hostname checking in SSL context
                unverified_context.check_hostname = False
                unverified_context.verify_mode = ssl.CERT_NONE
                kwargs["ssl_context"] = unverified_context
            else:
                # If ssl_context is provided, modify it to disable verification
                ssl_ctx = kwargs["ssl_context"]
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
            return original_init(self, *args, **kwargs)

        urllib3.connection.HTTPSConnection.__init__ = patched_https_connection_init  # type: ignore[method-assign]

        # Also patch urllib3's hostname verification function if it exists
        # This is a more aggressive approach to disable hostname checking
        if hasattr(urllib3.connection, "_match_hostname"):
            self._urllib3_original_match_hostname = urllib3.connection._match_hostname

            def patched_match_hostname(*_args: Any, **_kwargs: Any) -> None:
                # Skip hostname verification entirely
                return None

            urllib3.connection._match_hostname = patched_match_hostname

        self._urllib3_patched = True

        # Also patch requests library (pyhafas uses requests)
        # Store original request method
        self._requests_original_request = requests.Session.request

        original_request = self._requests_original_request

        def patched_request(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Disable SSL verification for all requests
            kwargs.setdefault("verify", False)
            return original_request(self, *args, **kwargs)

        requests.Session.request = patched_request
        self._requests_patched = True

        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        """Restore original SSL verification."""
        # Restore original SSL context
        if self._original_ssl_context is not None:
            ssl._create_default_https_context = self._original_ssl_context

        # Restore urllib3 if we patched it
        if self._urllib3_patched:
            if self._urllib3_original_init is not None:
                urllib3.connection.HTTPSConnection.__init__ = self._urllib3_original_init  # type: ignore[method-assign]
            if self._urllib3_original_match_hostname is not None:
                urllib3.connection._match_hostname = self._urllib3_original_match_hostname

        # Restore requests if we patched it
        if self._requests_patched and self._requests_original_request is not None:
            requests.Session.request = self._requests_original_request


def hafas_ssl_context() -> HafasSSLContext:
    """Factory function for HafasSSLContext.

    Returns:
        A context manager that disables SSL verification for HAFAS operations.
    """
    return HafasSSLContext()


def run_with_ssl_disabled(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a function with SSL verification disabled.

    This is useful when running pyhafas methods in threads via asyncio.to_thread(),
    as the SSL context patches need to be active in the thread where the function runs.

    Args:
        func: The function to call
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        The result of calling func(*args, **kwargs)
    """
    with hafas_ssl_context():
        return func(*args, **kwargs)


def run_with_ssl_disabled_kwargs(args_tuple: tuple[Callable[..., Any], dict[str, Any]]) -> Any:
    """Run a function with SSL verification disabled, passing keyword arguments.

    This is a convenience wrapper for methods that accept keyword arguments.
    Designed to work with asyncio.to_thread() which requires a single argument.

    Args:
        args_tuple: A tuple of (func, kwargs_dict) where func is the function to call
                    and kwargs_dict is a dict of keyword arguments

    Returns:
        The result of calling func(**kwargs_dict)
    """
    func, kwargs = args_tuple
    with hafas_ssl_context():
        return func(**kwargs)
