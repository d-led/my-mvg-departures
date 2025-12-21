"""Protocol for broadcasting presence updates."""

from typing import Protocol


class PresenceBroadcasterProtocol(Protocol):
    """Protocol for broadcasting presence updates via PubSub."""

    async def broadcast_join(
        self,
        route_path: str,
        user_id: str,
        local_count: int,
        total_count: int,
        socket: object | None = None,  # LiveViewSocket - for subscribing only, optional
    ) -> None:
        """Broadcast that a user joined a dashboard.

        Broadcasts to all subscribers on the topic, regardless of socket connection state.
        The socket parameter is only used for subscribing the joining user to topics.

        Args:
            route_path: The route path of the dashboard.
            user_id: The user ID that joined.
            local_count: Number of users on this dashboard.
            total_count: Total number of users across all dashboards.
            socket: Optional socket connection (only used for subscribing to topics if connected).
        """
        ...

    async def broadcast_leave(
        self,
        route_path: str,
        user_id: str,
        local_count: int,
        total_count: int,
        socket: object | None = None,  # LiveViewSocket - not used, kept for API compatibility
    ) -> None:
        """Broadcast that a user left a dashboard.

        Broadcasts to all subscribers on the topic, regardless of socket connection state.

        Args:
            route_path: The route path of the dashboard.
            user_id: The user ID that left.
            local_count: Number of users on this dashboard.
            total_count: Total number of users across all dashboards.
            socket: Optional socket (not used, kept for API compatibility).
        """
        ...
