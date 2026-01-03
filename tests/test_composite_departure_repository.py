"""Behavior-focused tests for CompositeDepartureRepository routing logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mvg_departures.adapters.composite_departure_repository import (
    CompositeDepartureRepository,
)
from mvg_departures.domain.models import StopConfiguration


class TestRepositoryCreation:
    """Tests for repository creation based on API provider."""

    def test_when_provider_is_mvg_then_creates_mvg_repository(self) -> None:
        """Given MVG provider, when creating repository, then returns MvgDepartureRepository."""
        stop_config = StopConfiguration(
            station_id="de:09162:6",
            station_name="Marienplatz",
            direction_mappings={},
            api_provider="mvg",
        )

        composite = CompositeDepartureRepository(stop_configs=[stop_config])
        repo = composite._create_repository_for_provider("mvg")

        assert repo.__class__.__name__ == "MvgDepartureRepository"

    def test_when_provider_is_db_then_creates_db_repository(self) -> None:
        """Given DB provider, when creating repository, then returns DbDepartureRepository."""
        stop_config = StopConfiguration(
            station_id="8000261",
            station_name="München Hbf",
            direction_mappings={},
            api_provider="db",
        )

        composite = CompositeDepartureRepository(stop_configs=[stop_config])
        repo = composite._create_repository_for_provider("db")

        assert repo.__class__.__name__ == "DbDepartureRepository"

    def test_when_provider_is_vbb_then_creates_vbb_repository(self) -> None:
        """Given VBB provider, when creating repository, then returns VbbDepartureRepository."""
        stop_config = StopConfiguration(
            station_id="900000024101",
            station_name="Berlin Ostbahnhof",
            direction_mappings={},
            api_provider="vbb",
        )

        composite = CompositeDepartureRepository(stop_configs=[stop_config])
        repo = composite._create_repository_for_provider("vbb")

        assert repo.__class__.__name__ == "VbbDepartureRepository"

    def test_when_provider_unknown_then_defaults_to_mvg(self) -> None:
        """Given unknown provider, when creating repository, then defaults to MVG."""
        stop_config = StopConfiguration(
            station_id="test:123",
            station_name="Test Station",
            direction_mappings={},
            api_provider="unknown_api",
        )

        composite = CompositeDepartureRepository(stop_configs=[stop_config])
        repo = composite._create_repository_for_provider("unknown_api")

        assert repo.__class__.__name__ == "MvgDepartureRepository"


class TestRepositoryRouting:
    """Tests for routing requests to the correct repository."""

    def test_when_station_in_config_then_uses_configured_repository(self) -> None:
        """Given station with configured provider, when getting repo, then uses that provider."""
        stop_config = StopConfiguration(
            station_id="de:09162:6",
            station_name="Marienplatz",
            direction_mappings={},
            api_provider="mvg",
        )

        composite = CompositeDepartureRepository(stop_configs=[stop_config])
        repo = composite._get_repository("de:09162:6")

        assert repo.__class__.__name__ == "MvgDepartureRepository"

    def test_when_station_not_in_config_then_falls_back_to_mvg(self) -> None:
        """Given station not in config, when getting repo, then falls back to MVG."""
        stop_config = StopConfiguration(
            station_id="de:09162:6",
            station_name="Marienplatz",
            direction_mappings={},
            api_provider="mvg",
        )

        composite = CompositeDepartureRepository(stop_configs=[stop_config])
        repo = composite._get_repository("unknown:station:id")

        assert repo.__class__.__name__ == "MvgDepartureRepository"

    def test_when_multiple_stops_with_same_provider_then_reuses_repository(self) -> None:
        """Given multiple stops with same provider, when initialized, then reuses repository."""
        stop1 = StopConfiguration(
            station_id="de:09162:6",
            station_name="Marienplatz",
            direction_mappings={},
            api_provider="mvg",
        )
        stop2 = StopConfiguration(
            station_id="de:09162:70",
            station_name="Universität",
            direction_mappings={},
            api_provider="mvg",
        )

        composite = CompositeDepartureRepository(stop_configs=[stop1, stop2])

        # Both stations should use the same repository instance
        repo1 = composite._repositories["de:09162:6"]
        repo2 = composite._repositories["de:09162:70"]
        assert repo1 is repo2

    def test_when_stops_with_different_providers_then_uses_separate_repositories(self) -> None:
        """Given stops with different providers, when initialized, then uses separate repos."""
        mvg_stop = StopConfiguration(
            station_id="de:09162:6",
            station_name="Marienplatz",
            direction_mappings={},
            api_provider="mvg",
        )
        db_stop = StopConfiguration(
            station_id="8000261",
            station_name="München Hbf",
            direction_mappings={},
            api_provider="db",
        )

        composite = CompositeDepartureRepository(stop_configs=[mvg_stop, db_stop])

        mvg_repo = composite._repositories["de:09162:6"]
        db_repo = composite._repositories["8000261"]
        assert mvg_repo is not db_repo
        assert mvg_repo.__class__.__name__ == "MvgDepartureRepository"
        assert db_repo.__class__.__name__ == "DbDepartureRepository"


class TestGetDepartures:
    """Tests for the get_departures method delegation."""

    @pytest.mark.asyncio
    async def test_when_getting_departures_then_delegates_to_correct_repository(self) -> None:
        """Given a station, when getting departures, then delegates to correct repository."""
        stop_config = StopConfiguration(
            station_id="de:09162:6",
            station_name="Marienplatz",
            direction_mappings={},
            api_provider="mvg",
        )

        composite = CompositeDepartureRepository(stop_configs=[stop_config])

        # Mock the repository's get_departures method
        mock_departures = [MagicMock(), MagicMock()]
        with patch.object(
            composite._repositories["de:09162:6"],
            "get_departures",
            new_callable=AsyncMock,
            return_value=mock_departures,
        ) as mock_get:
            result = await composite.get_departures(
                station_id="de:09162:6",
                limit=20,
                offset_minutes=5,
            )

            mock_get.assert_called_once_with(
                station_id="de:09162:6",
                limit=20,
                offset_minutes=5,
                transport_types=None,
                duration_minutes=60,
            )
            assert result == mock_departures
