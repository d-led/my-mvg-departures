"""Tests for API request logger."""

import json
from unittest.mock import patch

import pytest

from mvg_departures.adapters.api_request_logger import (
    log_api_request,
    should_log_requests,
)


class TestShouldLogRequests:
    """Tests for should_log_requests function."""

    def test_when_env_not_set_then_returns_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Given MMD_LOG_REQUESTS not set, when checking, then returns False."""
        monkeypatch.delenv("MMD_LOG_REQUESTS", raising=False)

        result = should_log_requests()

        assert result is False

    def test_when_env_set_to_true_then_returns_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Given MMD_LOG_REQUESTS=true, when checking, then returns True."""
        monkeypatch.setenv("MMD_LOG_REQUESTS", "true")

        result = should_log_requests()

        assert result is True

    def test_when_env_set_to_true_capitalized_then_returns_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Given MMD_LOG_REQUESTS=True (capitalized), when checking, then returns True."""
        monkeypatch.setenv("MMD_LOG_REQUESTS", "True")

        result = should_log_requests()

        assert result is True

    def test_when_env_set_to_false_then_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Given MMD_LOG_REQUESTS=false, when checking, then returns False."""
        monkeypatch.setenv("MMD_LOG_REQUESTS", "false")

        result = should_log_requests()

        assert result is False


class TestLogApiRequest:
    """Tests for log_api_request function."""

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_logging_disabled_then_does_not_log(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given logging disabled, when calling log_api_request, then does not log."""
        mock_should_log.return_value = False

        log_api_request("GET", "https://example.com/api")

        mock_logger.info.assert_not_called()

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_logging_enabled_then_logs_method_and_url(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given logging enabled, when calling with method and URL, then logs them."""
        mock_should_log.return_value = True

        log_api_request("GET", "https://example.com/api")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "GET https://example.com/api" in call_args

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_logging_enabled_with_params_then_logs_full_url(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given logging enabled with params, when calling, then logs URL with params."""
        mock_should_log.return_value = True

        log_api_request("GET", "https://example.com/api", params={"limit": 10, "offset": 0})

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "GET https://example.com/api?limit=10&offset=0" in call_args

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_url_has_existing_params_then_appends_params(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given URL with existing params, when adding more params, then appends correctly."""
        mock_should_log.return_value = True

        log_api_request("GET", "https://example.com/api?existing=1", params={"new": 2})

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "existing=1" in call_args
        assert "new=2" in call_args
        assert "&" in call_args or "?" in call_args

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_logging_enabled_with_headers_then_logs_headers(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given logging enabled with headers, when calling, then logs headers."""
        mock_should_log.return_value = True

        log_api_request("GET", "https://example.com/api", headers={"User-Agent": "Test"})

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Headers:" in call_args
        assert "User-Agent" in call_args
        assert "Test" in call_args

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_logging_with_authorization_header_then_redacts_it(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given Authorization header, when logging, then redacts the value."""
        mock_should_log.return_value = True

        log_api_request(
            "GET", "https://example.com/api", headers={"Authorization": "Bearer secret-token"}
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Authorization" in call_args
        assert "***REDACTED***" in call_args
        assert "secret-token" not in call_args

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_logging_with_cookie_header_then_redacts_it(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given Cookie header, when logging, then redacts the value."""
        mock_should_log.return_value = True

        log_api_request("GET", "https://example.com/api", headers={"Cookie": "session=abc123"})

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Cookie" in call_args
        assert "***REDACTED***" in call_args
        assert "abc123" not in call_args

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_logging_with_x_api_key_header_then_redacts_it(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given X-API-Key header, when logging, then redacts the value."""
        mock_should_log.return_value = True

        log_api_request("GET", "https://example.com/api", headers={"X-API-Key": "secret-key"})

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "X-API-Key" in call_args
        assert "***REDACTED***" in call_args
        assert "secret-key" not in call_args

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_logging_with_dict_payload_then_logs_as_json(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given dict payload, when logging, then logs as formatted JSON."""
        mock_should_log.return_value = True
        payload = {"key": "value", "number": 42}

        log_api_request("POST", "https://example.com/api", payload=payload)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Payload:" in call_args
        # Check that it's formatted JSON (has newlines/indentation)
        assert "\n" in call_args or json.dumps(payload) in call_args

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_logging_with_string_payload_then_logs_as_string(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given string payload, when logging, then logs as string."""
        mock_should_log.return_value = True

        log_api_request("POST", "https://example.com/api", payload="simple string")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Payload:" in call_args
        assert "simple string" in call_args

    @patch("mvg_departures.adapters.api_request_logger.should_log_requests")
    @patch("mvg_departures.adapters.api_request_logger.logger")
    def test_when_logging_with_all_fields_then_logs_all(
        self, mock_logger: object, mock_should_log: object
    ) -> None:
        """Given all fields provided, when logging, then logs all of them."""
        mock_should_log.return_value = True

        log_api_request(
            "POST",
            "https://example.com/api",
            params={"limit": 10},
            headers={"Content-Type": "application/json"},
            payload={"data": "test"},
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "POST" in call_args
        assert "https://example.com/api" in call_args
        assert "limit=10" in call_args
        assert "Content-Type" in call_args
        assert "Payload:" in call_args
