"""Display adapter port."""

from abc import ABC, abstractmethod

from mvg_departures.domain.models.departure import Departure


class DisplayAdapter(ABC):
    """Port for displaying departure information to users."""

    @abstractmethod
    async def display_departures(self, direction_groups: list[tuple[str, list[Departure]]]) -> None:
        """Display grouped departures."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the display adapter."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the display adapter."""
        ...
