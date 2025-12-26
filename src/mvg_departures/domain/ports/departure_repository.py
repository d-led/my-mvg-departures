"""Departure repository port."""

from typing import Protocol

from mvg_departures.domain.models.departure import Departure


class DepartureRepository(Protocol):
    """Port for retrieving departure information."""

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,
        transport_types: list[str] | None = None,
        duration_minutes: int = 60,  # VBB API duration parameter (optional, ignored by other APIs)
    ) -> list[Departure]:
        """Get departures for a station."""
        ...
