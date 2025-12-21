"""Protocol for API polling."""

from typing import Protocol


class ApiPollerProtocol(Protocol):
    """Protocol for polling API and updating state."""

    async def start(self) -> None:
        """Start the API poller."""
        ...

    async def stop(self) -> None:
        """Stop the API poller."""
        ...
