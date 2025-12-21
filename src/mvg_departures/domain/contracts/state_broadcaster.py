"""Protocol for broadcasting state updates."""

from typing import Protocol


class StateBroadcasterProtocol(Protocol):
    """Protocol for broadcasting state updates via PubSub."""

    async def broadcast_update(self, topic: str) -> None:
        """Broadcast an update signal to all subscribers on the topic.

        Args:
            topic: The pub/sub topic to broadcast to.
        """
        ...
