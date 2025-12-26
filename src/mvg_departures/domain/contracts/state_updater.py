"""Protocol for updating departures state."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime

from mvg_departures.domain.models.direction_group_with_metadata import DirectionGroupWithMetadata


class StateUpdaterProtocol(Protocol):
    """Protocol for updating departures state."""

    def update_departures(
        self,
        direction_groups: list[DirectionGroupWithMetadata],
    ) -> None:
        """Update the direction groups in the state.

        Args:
            direction_groups: List of direction groups with metadata.
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
