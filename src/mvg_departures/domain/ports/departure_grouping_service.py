"""Departure grouping service port."""

from typing import Protocol

from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.models.grouped_departures import GroupedDepartures
from mvg_departures.domain.models.stop_configuration import StopConfiguration


class DepartureGroupingService(Protocol):
    """Port for grouping departures by configured directions."""

    async def get_grouped_departures(
        self, stop_config: StopConfiguration
    ) -> list[GroupedDepartures]:
        """Get departures for a stop, grouped by configured directions.

        Fetches a reasonable number of departures from the API, then groups them
        by direction and limits each direction group to max_departures_per_stop.

        Args:
            stop_config: Stop configuration with direction mappings and limits.

        Returns:
            List of grouped departures for this stop.
        """
        ...

    def group_departures(
        self, departures: list[Departure], stop_config: StopConfiguration
    ) -> list[GroupedDepartures]:
        """Group pre-fetched departures by configured directions.

        This method allows grouping departures that were already fetched,
        enabling shared fetching across multiple routes.

        Args:
            departures: Pre-fetched list of departures to group.
            stop_config: Stop configuration with direction mappings and limits.

        Returns:
            List of grouped departures for this stop.
        """
        ...
