"""Protocol for updating departures state."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from mvg_departures.domain.models.departure import Departure


class StateUpdaterProtocol(Protocol):
    """Protocol for updating departures state."""

    def update_departures(
        self,
        direction_groups: list[
            tuple[str, str, str, list["Departure"], bool | None, float | None, int | None]
        ],
    ) -> None:
        """Update the direction groups in the state.

        Args:
            direction_groups: List of (station_id, station_name, direction_name, departures, random_header_colors, header_background_brightness, random_color_salt) tuples.
        """
        ...

    def update_api_status(self, status: str) -> None:
        """Update the API status in the state.

        Args:
            status: The API status ("success" or "error").
        """
        ...

    def update_last_update_time(self, time: "datetime") -> None:
        """Update the last update timestamp in the state.

        Args:
            time: The timestamp of the last update.
        """
        ...
