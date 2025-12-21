"""Protocol for departure caching."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from mvg_departures.domain.models.departure import Departure


class DepartureCacheProtocol(Protocol):
    """Protocol for caching departures by station ID."""

    def get(self, station_id: str) -> list["Departure"]:
        """Get cached departures for a station.

        Args:
            station_id: The station ID to get departures for.

        Returns:
            List of cached departures, or empty list if not found.
        """
        ...

    def set(self, station_id: str, departures: list["Departure"]) -> None:
        """Set cached departures for a station.

        Args:
            station_id: The station ID.
            departures: The departures to cache.
        """
        ...

    def get_all_station_ids(self) -> "set[str]":  # type: ignore[valid-type]
        """Get all station IDs that have cached data.

        Returns:
            Set of station IDs.
        """
        ...
