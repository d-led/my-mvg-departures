"""Updater for departures state."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mvg_departures.adapters.web.state.departures_state import (
    DeparturesState,  # noqa: TC001 - Runtime dependency: used in __init__
)
from mvg_departures.domain.contracts.state_updater import StateUpdaterProtocol

if TYPE_CHECKING:
    from datetime import datetime

    from mvg_departures.domain.models.direction_group_with_metadata import (
        DirectionGroupWithMetadata,
    )

logger = logging.getLogger(__name__)


class StateUpdater(StateUpdaterProtocol):
    """Updates departures state."""

    def __init__(self, departures_state: DeparturesState) -> None:
        """Initialize the state updater.

        Args:
            departures_state: The DeparturesState instance to update.
        """
        self.departures_state = departures_state

    def update_departures(
        self,
        direction_groups: list[DirectionGroupWithMetadata],
    ) -> None:
        """Update the direction groups in the state.

        Args:
            direction_groups: List of direction groups with metadata.
        """
        self.departures_state.direction_groups = direction_groups
        logger.debug(f"Updated direction groups: {len(direction_groups)} groups")

    def update_api_status(self, status: str) -> None:
        """Update the API status in the state.

        Args:
            status: The API status ("success" or "error").
        """
        self.departures_state.api_status = status
        logger.debug(f"Updated API status: {status}")

    def update_last_update_time(self, time: datetime) -> None:
        """Update the last update timestamp in the state.

        Args:
            time: The timestamp of the last update.
        """
        self.departures_state.last_update = time
        logger.debug(f"Updated last update time: {time}")
