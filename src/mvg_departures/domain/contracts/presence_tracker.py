"""Presence tracker contract (protocol)."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pyview import LiveViewSocket


class PresenceTrackerProtocol(Protocol):
    """Protocol for presence tracking functionality."""

    def get_user_id(self, socket: "LiveViewSocket", session: dict | None = None) -> str:
        """Get a unique user ID from socket.

        Args:
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            A unique user identifier.
        """
        ...

    def join_dashboard(
        self, route_path: str, socket: "LiveViewSocket", session: dict | None = None
    ) -> tuple[str, int, int]:
        """Join a dashboard and track the socket.

        Args:
            route_path: The route path of the dashboard.
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            Tuple of (user_id, local_count, total_count).
        """
        ...

    def leave_dashboard(
        self, route_path: str, socket: "LiveViewSocket", session: dict | None = None
    ) -> tuple[str, int, int]:
        """Leave a dashboard and untrack the socket.

        Args:
            route_path: The route path of the dashboard.
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            Tuple of (user_id, local_count, total_count).
        """
        ...

    def ensure_dashboard_membership(
        self, route_path: str, socket: "LiveViewSocket", session: dict | None = None
    ) -> tuple[int, int]:
        """Ensure a socket is tracked in presence and belongs to the specified dashboard.

        Args:
            route_path: The route path of the dashboard.
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            Tuple of (local_count, total_count) - the updated counts.
        """
        ...

    def is_user_tracked(self, socket: "LiveViewSocket", session: dict | None = None) -> bool:
        """Check if a socket is tracked in presence.

        Args:
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            True if the socket is tracked, False otherwise.
        """
        ...
