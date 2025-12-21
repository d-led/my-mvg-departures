"""Protocol for fetching departures."""

from typing import Protocol


class DepartureFetcherProtocol(Protocol):
    """Protocol for fetching departures and populating cache."""

    async def start(self) -> None:
        """Start the fetcher."""
        ...

    async def stop(self) -> None:
        """Stop the fetcher."""
        ...
