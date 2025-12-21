"""Presence tracking for dashboard users."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyview import LiveViewSocket

logger = logging.getLogger(__name__)


class PresenceTracker:
    """Tracks presence of users across all dashboards."""

    def __init__(self) -> None:
        """Initialize the presence tracker."""
        # Track users per dashboard route (using route path as key)
        self._dashboard_users: dict[str, set[str]] = {}
        # Track all users globally (set of user IDs)
        self._all_users: set[str] = set()

    def _get_user_id(self, socket: "LiveViewSocket") -> str:
        """Get a unique user ID from socket (anonymous, using socket object ID)."""
        # Use the socket object's ID as the unique identifier
        return f"user_{id(socket)}"

    def get_user_id(self, socket: "LiveViewSocket") -> str:
        """Get a unique user ID from socket (public method)."""
        return self._get_user_id(socket)

    def join_dashboard(self, route_path: str, socket: "LiveViewSocket") -> tuple[str, int, int]:
        """Register a user joining a dashboard.

        Args:
            route_path: The route path of the dashboard.
            socket: The socket connection.

        Returns:
            Tuple of (user_id, local_count, total_count) - the user ID and updated counts.
        """
        user_id = self._get_user_id(socket)
        normalized_path = route_path.strip("/").replace("/", ":") or "root"

        # Add to dashboard-specific set
        if normalized_path not in self._dashboard_users:
            self._dashboard_users[normalized_path] = set()
        self._dashboard_users[normalized_path].add(user_id)

        # Add to global set
        self._all_users.add(user_id)

        # Calculate counts after the join
        local_count = len(self._dashboard_users[normalized_path])
        total_count = len(self._all_users)

        logger.info(
            f"Presence join: user {user_id} on dashboard '{normalized_path}'. "
            f"Dashboard users: {local_count}, Total users: {total_count}"
        )

        return user_id, local_count, total_count

    def leave_dashboard(
        self, route_path: str, socket: "LiveViewSocket"
    ) -> tuple[str | None, int, int]:
        """Register a user leaving a dashboard.

        Args:
            route_path: The route path of the dashboard.
            socket: The socket connection.

        Returns:
            Tuple of (user_id, local_count, total_count) - the user ID (or None if not found) and updated counts.
        """
        user_id = self._get_user_id(socket)
        normalized_path = route_path.strip("/").replace("/", ":") or "root"

        # Remove from dashboard-specific set
        if normalized_path in self._dashboard_users:
            self._dashboard_users[normalized_path].discard(user_id)
            # Clean up empty dashboard sets
            if not self._dashboard_users[normalized_path]:
                del self._dashboard_users[normalized_path]

        # Remove from global set
        self._all_users.discard(user_id)

        # Calculate counts after the leave
        local_count = len(self._dashboard_users.get(normalized_path, set()))
        total_count = len(self._all_users)

        logger.info(
            f"Presence leave: user {user_id} from dashboard '{normalized_path}'. "
            f"Dashboard users: {local_count}, Total users: {total_count}"
        )

        return user_id, local_count, total_count

    def get_dashboard_count(self, route_path: str) -> int:
        """Get the number of users on a specific dashboard.

        Args:
            route_path: The route path of the dashboard.

        Returns:
            The number of users on the dashboard.
        """
        normalized_path = route_path.strip("/").replace("/", ":") or "root"
        return len(self._dashboard_users.get(normalized_path, set()))

    def get_total_count(self) -> int:
        """Get the total number of users across all dashboards.

        Returns:
            The total number of users.
        """
        return len(self._all_users)

    def is_user_tracked(self, socket: "LiveViewSocket") -> bool:
        """Check if a socket is tracked in presence.

        Args:
            socket: The socket connection.

        Returns:
            True if the socket is tracked, False otherwise.
        """
        user_id = self._get_user_id(socket)
        return user_id in self._all_users

    def ensure_dashboard_membership(
        self, route_path: str, socket: "LiveViewSocket"
    ) -> tuple[int, int]:
        """Ensure a socket is tracked in presence and belongs to the specified dashboard.

        Args:
            route_path: The route path of the dashboard.
            socket: The socket connection.

        Returns:
            Tuple of (local_count, total_count) - the updated counts.
        """
        user_id = self._get_user_id(socket)
        normalized_path = route_path.strip("/").replace("/", ":") or "root"

        # Ensure in global set
        self._all_users.add(user_id)

        # Ensure in dashboard set
        if normalized_path not in self._dashboard_users:
            self._dashboard_users[normalized_path] = set()
        self._dashboard_users[normalized_path].add(user_id)

        # Calculate counts after ensuring membership
        local_count = len(self._dashboard_users[normalized_path])
        total_count = len(self._all_users)

        return local_count, total_count

    def cleanup_stale_entries(self, route_path: str, active_sockets: set["LiveViewSocket"]) -> int:
        """Remove stale presence entries for sockets that are no longer active.

        Args:
            route_path: The route path of the dashboard.
            active_sockets: Set of currently active socket objects.

        Returns:
            Number of stale entries removed.
        """
        normalized_path = route_path.strip("/").replace("/", ":") or "root"
        active_user_ids = {self._get_user_id(socket) for socket in active_sockets}

        # Find stale entries for this dashboard
        dashboard_users = self._dashboard_users.get(normalized_path, set())
        stale_users = dashboard_users - active_user_ids

        removed_count = 0
        for user_id in stale_users:
            dashboard_users.discard(user_id)
            self._all_users.discard(user_id)
            removed_count += 1

        # Clean up empty dashboard sets
        if not dashboard_users:
            self._dashboard_users.pop(normalized_path, None)

        if removed_count > 0:
            logger.info(
                f"Cleaned up {removed_count} stale presence entries for dashboard '{normalized_path}'. "
                f"Remaining: {len(dashboard_users)} local, {len(self._all_users)} total"
            )

        return removed_count

    def sync_with_registered_sockets(
        self, route_sockets: dict[str, set["LiveViewSocket"]]
    ) -> tuple[int, int]:
        """Sync presence tracking with all registered sockets across all routes.

        This ensures that every registered socket is tracked in presence,
        and removes any presence entries for sockets that are no longer registered.

        Args:
            route_sockets: Dictionary mapping route paths to sets of registered sockets.

        Returns:
            Tuple of (added_count, removed_count) - number of entries added and removed.
        """
        # Collect all active sockets and their routes
        all_active_sockets: set[LiveViewSocket] = set()
        socket_to_route: dict[LiveViewSocket, str] = {}
        for route_path, sockets in route_sockets.items():
            for socket in sockets:
                all_active_sockets.add(socket)
                socket_to_route[socket] = route_path

        # Get all active user IDs
        active_user_ids = {self._get_user_id(socket) for socket in all_active_sockets}

        # Find missing entries (registered but not in presence)
        missing_user_ids = active_user_ids - self._all_users
        added_count = 0
        for socket in all_active_sockets:
            user_id = self._get_user_id(socket)
            if user_id in missing_user_ids:
                route_path = socket_to_route[socket]
                normalized_path = route_path.strip("/").replace("/", ":") or "root"
                if normalized_path not in self._dashboard_users:
                    self._dashboard_users[normalized_path] = set()
                self._dashboard_users[normalized_path].add(user_id)
                self._all_users.add(user_id)
                added_count += 1

        # Find stale entries (in presence but not registered)
        stale_user_ids = self._all_users - active_user_ids
        removed_count = 0
        for user_id in stale_user_ids:
            # Find which dashboard this user is in
            for normalized_path, dashboard_users in list(self._dashboard_users.items()):
                if user_id in dashboard_users:
                    dashboard_users.discard(user_id)
                    if not dashboard_users:
                        del self._dashboard_users[normalized_path]
                    break
            self._all_users.discard(user_id)
            removed_count += 1

        if added_count > 0 or removed_count > 0:
            logger.info(
                f"Presence sync: added {added_count}, removed {removed_count}. "
                f"Total users: {len(self._all_users)}"
            )

        return added_count, removed_count


# Global presence tracker instance
_presence_tracker = PresenceTracker()


def get_presence_tracker() -> PresenceTracker:
    """Get the global presence tracker instance.

    Returns:
        The global presence tracker.
    """
    return _presence_tracker
