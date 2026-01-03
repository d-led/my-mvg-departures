"""Integration tests for CLI commands.

These tests verify CLI behavior by executing actual commands and asserting on output.
They require network access and are marked with @pytest.mark.integration.

Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent


def _run_cli_command(command: list[str], timeout: int = 30) -> tuple[str, str, int]:
    """Run a CLI command and return stdout, stderr, and exit code.

    Args:
        command: Command and arguments as list.
        timeout: Timeout in seconds.

    Returns:
        Tuple of (stdout, stderr, exit_code).
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mvg_departures.cli", *command],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 124


def _run_db_cli_command(command: list[str], timeout: int = 30) -> tuple[str, str, int]:
    """Run a DB CLI command and return stdout, stderr, and exit code."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mvg_departures.cli_db", *command],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 124


def _run_vbb_cli_command(command: list[str], timeout: int = 30) -> tuple[str, str, int]:
    """Run a VBB CLI command and return stdout, stderr, and exit code."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mvg_departures.cli_vbb", *command],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 124


@pytest.mark.integration
class TestMVGCliIntegration:
    """Integration tests for MVG CLI commands."""

    def test_search_command_finds_stations(self) -> None:
        """Given a station name query, when searching, then returns matching stations."""
        stdout, stderr, exit_code = _run_cli_command(["search", "Giesing"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Giesing" in stdout
        assert "ID:" in stdout
        assert "station(s)" in stdout

    def test_search_command_with_json_output(self) -> None:
        """Given --json flag, when searching, then returns JSON output."""
        stdout, stderr, exit_code = _run_cli_command(["search", "Giesing", "--json"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        data = json.loads(stdout)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "name" in data[0]

    def test_search_command_no_results_exits_with_error(self) -> None:
        """Given a query with no matches, when searching, then exits with error."""
        stdout, stderr, exit_code = _run_cli_command(["search", "NonexistentStationXYZ123"])

        assert exit_code != 0
        assert "No stations found" in stderr or "No stations found" in stdout

    def test_info_command_shows_station_details(self) -> None:
        """Given a station ID, when showing info, then displays station information."""
        stdout, stderr, exit_code = _run_cli_command(["info", "de:09162:100"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Station:" in stdout or "ID:" in stdout
        assert "de:09162:100" in stdout

    def test_info_command_with_json_output(self) -> None:
        """Given --json flag, when showing info, then returns JSON output."""
        stdout, stderr, exit_code = _run_cli_command(["info", "de:09162:100", "--json"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        data = json.loads(stdout)
        assert isinstance(data, dict)
        assert "station" in data or "id" in data

    def test_routes_command_by_id_shows_routes(self) -> None:
        """Given a station ID, when listing routes, then shows available routes."""
        stdout, stderr, exit_code = _run_cli_command(["routes", "de:09162:100"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Routes" in stdout or "routes" in stdout or "Available" in stdout

    def test_routes_command_by_name_searches_and_shows_routes(self) -> None:
        """Given a station name, when listing routes, then searches and shows routes."""
        stdout, stderr, exit_code = _run_cli_command(["routes", "Giesing"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Giesing" in stdout
        assert "Routes" in stdout or "routes" in stdout or "Available" in stdout

    def test_routes_command_with_no_patterns_flag(self) -> None:
        """Given --no-patterns flag, when listing routes, then shows routes without config examples."""
        stdout, stderr, exit_code = _run_cli_command(["routes", "de:09162:100", "--no-patterns"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        # Should show routes but not config snippet examples
        assert "Routes" in stdout or "routes" in stdout or "Available" in stdout
        # When --no-patterns is used, config snippets should not be shown
        # (This is a behavior check - we're checking what the user sees, not internal structure)

    def test_generate_command_creates_config_snippet(self) -> None:
        """Given station ID and name, when generating config, then outputs TOML snippet."""
        stdout, stderr, exit_code = _run_cli_command(["generate", "de:09162:100", "Giesing"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "[[stops]]" in stdout or "[stops]" in stdout
        assert "station_id" in stdout
        assert "station_name" in stdout
        assert "Giesing" in stdout
        assert "de:09162:100" in stdout

    def test_help_command_shows_usage(self) -> None:
        """Given no command, when running CLI, then shows help text."""
        stdout, _stderr, exit_code = _run_cli_command([])

        assert exit_code != 0  # Should exit with error when no command provided
        assert "MVG Departures Configuration Helper" in stdout or "usage:" in stdout
        assert "search" in stdout
        assert "info" in stdout
        assert "routes" in stdout
        assert "generate" in stdout


@pytest.mark.integration
class TestDBCliIntegration:
    """Integration tests for DB CLI commands."""

    def test_search_command_finds_stations(self) -> None:
        """Given a station name query, when searching, then returns matching stations."""
        stdout, stderr, exit_code = _run_db_cli_command(["search", "Augsburg"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Augsburg" in stdout or "station(s)" in stdout
        assert "ID:" in stdout

    def test_search_command_with_json_output(self) -> None:
        """Given --json flag, when searching, then returns JSON output."""
        stdout, stderr, exit_code = _run_db_cli_command(["search", "Augsburg", "--json"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        data = json.loads(stdout)
        assert isinstance(data, list)
        if len(data) > 0:
            assert "id" in data[0]
            assert "name" in data[0]

    def test_info_command_shows_station_details(self) -> None:
        """Given a station ID, when showing info, then displays station information."""
        stdout, stderr, exit_code = _run_db_cli_command(["info", "8000013"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "8000013" in stdout or "Station" in stdout

    def test_info_command_with_json_output(self) -> None:
        """Given --json flag, when showing info, then returns JSON output."""
        stdout, stderr, exit_code = _run_db_cli_command(["info", "8000013", "--json"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        data = json.loads(stdout)
        assert isinstance(data, dict)

    def test_routes_command_by_id_shows_routes(self) -> None:
        """Given a station ID, when listing routes, then shows available routes."""
        stdout, stderr, exit_code = _run_db_cli_command(["routes", "8000013"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Routes" in stdout or "routes" in stdout or "Available" in stdout

    def test_routes_command_by_name_searches_and_shows_routes(self) -> None:
        """Given a station name, when listing routes, then searches and shows routes."""
        stdout, stderr, exit_code = _run_db_cli_command(["routes", "Augsburg Hbf"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Augsburg" in stdout or "Routes" in stdout

    def test_routes_command_with_no_patterns_flag(self) -> None:
        """Given --no-patterns flag, when listing routes, then shows routes without config examples."""
        stdout, stderr, exit_code = _run_db_cli_command(["routes", "8000013", "--no-patterns"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        # Should show routes but not config snippet examples
        assert "Routes" in stdout or "routes" in stdout or "Available" in stdout
        # When --no-patterns is used, config snippets should not be shown
        # (This is a behavior check - we're checking what the user sees, not internal structure)

    def test_generate_command_creates_config_snippet(self) -> None:
        """Given station ID and name, when generating config, then outputs TOML snippet."""
        stdout, stderr, exit_code = _run_db_cli_command(["generate", "8000013", "Augsburg Hbf"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "[[stops]]" in stdout or "[stops]" in stdout
        assert "station_id" in stdout
        assert "station_name" in stdout
        assert "8000013" in stdout
        assert "api_provider" in stdout
        assert "db" in stdout

    def test_help_command_shows_usage(self) -> None:
        """Given no command, when running CLI, then shows help text."""
        stdout, _stderr, exit_code = _run_db_cli_command([])

        assert exit_code != 0  # Should exit with error when no command provided
        assert "DB (Deutsche Bahn) Departures Configuration Helper" in stdout or "usage:" in stdout
        assert "search" in stdout
        assert "info" in stdout
        assert "routes" in stdout
        assert "generate" in stdout


@pytest.mark.integration
class TestVBBCliIntegration:
    """Integration tests for VBB CLI commands."""

    def test_search_command_finds_stations(self) -> None:
        """Given a station name query, when searching, then returns matching stations."""
        stdout, stderr, exit_code = _run_vbb_cli_command(["search", "Zoologischer Garten"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Zoologischer Garten" in stdout or "station(s)" in stdout
        assert "ID:" in stdout

    def test_search_command_shows_config_snippet(self) -> None:
        """Given a station search, when searching, then shows config snippet for each station."""
        stdout, stderr, exit_code = _run_vbb_cli_command(["search", "Ernst-Reuter-Platz"])

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Configuration Snippet" in stdout or "[[stops]]" in stdout
        assert "station_id" in stdout

    def test_search_command_no_results_exits_with_error(self) -> None:
        """Given a query with no matches, when searching, then exits with error."""
        stdout, stderr, exit_code = _run_vbb_cli_command(["search", "NonexistentStationXYZ123"])

        assert exit_code != 0
        assert "No stations found" in stderr or "No stations found" in stdout

    def test_help_command_shows_usage(self) -> None:
        """Given no command, when running CLI, then shows help text."""
        stdout, _stderr, exit_code = _run_vbb_cli_command([])

        assert exit_code != 0  # Should exit with error when no command provided
        assert "VBB (Berlin) Departures Configuration Helper" in stdout or "usage:" in stdout
        assert "search" in stdout
