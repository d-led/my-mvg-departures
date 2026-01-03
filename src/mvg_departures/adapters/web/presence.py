"""Presence tracking for dashboard users."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyview import LiveViewSocket

from mvg_departures.domain.contracts import PresenceTrackerProtocol
from mvg_departures.domain.models.presence_result import (
    PresenceCounts,
    PresenceResult,
    PresenceSyncResult,
)

logger = logging.getLogger(__name__)


class PresenceTracker(PresenceTrackerProtocol):
    """Tracks presence of users across all dashboards."""

    def __init__(self) -> None:
        """Initialize the presence tracker."""
        # Track users per dashboard route (using route path as key)
        self._dashboard_users: dict[str, set[str]] = {}
        # Track all users globally (set of user IDs)
        self._all_users: set[str] = set()

    def _get_user_id(self, socket: "LiveViewSocket", session: dict | None = None) -> str:
        """Get a unique user ID from socket (anonymous, using session ID or socket object ID).

        Args:
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            A unique user identifier.
        """
        # Try to use session ID if available (more stable across reconnections)
        if session is not None:
            # Check for our custom presence session ID first (most reliable)
            presence_session_id = session.get("_presence_session_id")
            if presence_session_id:
                return f"user_{presence_session_id}"
            # Fallback to other common session ID keys
            session_id = (
                session.get("session_id") or session.get("id") or session.get("_session_id")
            )
            if session_id:
                return f"user_{session_id}"

        # Fallback to socket object ID (changes on reconnection, but better than nothing)
        return f"user_{id(socket)}"

    def get_user_id(self, socket: "LiveViewSocket", session: dict | None = None) -> str:
        """Get a unique user ID from socket (anonymous, using session ID or socket object ID).

        Args:
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            A unique user identifier.
        """
        return self._get_user_id(socket, session)

    def join_dashboard(
        self, route_path: str, socket: "LiveViewSocket", session: dict | None = None
    ) -> PresenceResult:
        """Join a dashboard and track the socket.

        Args:
            route_path: The route path of the dashboard.
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            PresenceResult with user_id, local_count, and total_count.
        """
        user_id = self._get_user_id(socket, session)
        normalized_path = route_path.strip("/").replace("/", ":") or "root"

        # Add to global set (if not already there)
        is_new_user = user_id not in self._all_users
        self._all_users.add(user_id)

        # Add to dashboard set
        if normalized_path not in self._dashboard_users:
            self._dashboard_users[normalized_path] = set()
        self._dashboard_users[normalized_path].add(user_id)

        # Calculate counts after joining
        local_count = len(self._dashboard_users[normalized_path])
        total_count = len(self._all_users)

        if is_new_user:
            logger.info(
                f"User {user_id} joined dashboard {route_path}. "
                f"Local: {local_count}, Total: {total_count}"
            )

        return PresenceResult(user_id=user_id, local_count=local_count, total_count=total_count)

    def leave_dashboard(
        self, route_path: str, socket: "LiveViewSocket", session: dict | None = None
    ) -> PresenceResult:
        """Leave a dashboard and untrack the socket.

        Args:
            route_path: The route path of the dashboard.
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            PresenceResult with user_id, local_count, and total_count.
        """
        user_id = self._get_user_id(socket, session)
        normalized_path = route_path.strip("/").replace("/", ":") or "root"

        # Remove from dashboard set
        if normalized_path in self._dashboard_users:
            self._dashboard_users[normalized_path].discard(user_id)
            # Clean up empty dashboard sets
            if not self._dashboard_users[normalized_path]:
                del self._dashboard_users[normalized_path]

        # Remove from global set
        self._all_users.discard(user_id)

        # Calculate counts after leaving
        local_count = len(self._dashboard_users.get(normalized_path, set()))
        total_count = len(self._all_users)

        logger.info(
            f"User {user_id} left dashboard {route_path}. "
            f"Local: {local_count}, Total: {total_count}"
        )

        return PresenceResult(user_id=user_id, local_count=local_count, total_count=total_count)

    def get_dashboard_count(self, route_path: str) -> int:
        """Get the number of users in a specific dashboard.

        Args:
            route_path: The route path of the dashboard.

        Returns:
            The number of users in the dashboard.
        """
        normalized_path = route_path.strip("/").replace("/", ":") or "root"

        return len(self._dashboard_users.get(normalized_path, set()))

    def get_total_count(self) -> int:
        """Get the total number of users across all dashboards.

        Returns:
            The total number of users.
        """
        return len(self._all_users)

    def is_user_tracked(self, socket: "LiveViewSocket", session: dict | None = None) -> bool:
        """Check if a socket is tracked in presence.

        Args:
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            True if the socket is tracked, False otherwise.
        """
        user_id = self._get_user_id(socket, session)
        return user_id in self._all_users

    def ensure_dashboard_membership(
        self, route_path: str, socket: "LiveViewSocket", session: dict | None = None
    ) -> PresenceCounts:
        """Ensure a socket is tracked in presence and belongs to the specified dashboard.

        Args:
            route_path: The route path of the dashboard.
            socket: The socket connection.
            session: Optional session dict that may contain a stable session ID.

        Returns:
            PresenceCounts with local_count and total_count.
        """
        user_id = self._get_user_id(socket, session)
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

        return PresenceCounts(local_count=local_count, total_count=total_count)

    def cleanup_stale_entries(self, route_path: str, active_sockets: set["LiveViewSocket"]) -> int:
        """Clean up stale presence entries for a route.

        Args:
            route_path: The route path of the dashboard.
            active_sockets: Set of currently active sockets for this route.

        Returns:
            Number of stale entries removed.
        """
        normalized_path = route_path.strip("/").replace("/", ":") or "root"
        dashboard_users = self._dashboard_users.get(normalized_path, set()).copy()

        # Get user IDs for active sockets
        active_user_ids = {self._get_user_id(socket) for socket in active_sockets}

        # Remove users that are no longer active
        removed_count = 0
        for user_id in dashboard_users:
            if user_id not in active_user_ids:
                self._dashboard_users[normalized_path].discard(user_id)
                self._all_users.discard(user_id)
                removed_count += 1

        # Clean up empty dashboard sets
        if not self._dashboard_users.get(normalized_path):
            del self._dashboard_users[normalized_path]

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} stale presence entries for {route_path}")

        return removed_count

    def _normalize_route_path(self, route_path: str) -> str:
        """Normalize route path for internal tracking."""
        return route_path.strip("/").replace("/", ":") or "root"

    def _get_tracked_route_users(self) -> dict[str, set[str]]:
        """Get all currently tracked user IDs per route."""
        return {
            route_path: user_set.copy() for route_path, user_set in self._dashboard_users.items()
        }

    def _add_user_to_all_users(self, user_id: str) -> int:
        """Add user to all_users set. Returns 1 if added, 0 if already present."""
        if user_id not in self._all_users:
            self._all_users.add(user_id)
            return 1
        return 0

    def _add_user_to_dashboard(self, normalized_path: str, user_id: str) -> int:
        """Add user to dashboard users. Returns 1 if added, 0 if already present."""
        if normalized_path not in self._dashboard_users:
            self._dashboard_users[normalized_path] = set()
        if user_id not in self._dashboard_users[normalized_path]:
            self._dashboard_users[normalized_path].add(user_id)
            return 1
        return 0

    def _add_registered_users(self, route_sockets: dict[str, set["LiveViewSocket"]]) -> int:
        """Add users for registered sockets that aren't tracked. Returns count of added users."""
        added_count = 0
        for route_path, sockets in route_sockets.items():
            normalized_path = self._normalize_route_path(route_path)
            for socket in sockets:
                user_id = self._get_user_id(socket)
                added_count += self._add_user_to_all_users(user_id)
                added_count += self._add_user_to_dashboard(normalized_path, user_id)
        return added_count

    def _find_matching_route(
        self, normalized_path: str, route_sockets: dict[str, set["LiveViewSocket"]]
    ) -> str | None:
        """Find matching route in route_sockets for a normalized path."""
        for registered_route in route_sockets:
            normalized_registered = self._normalize_route_path(registered_route)
            if normalized_registered == normalized_path:
                return registered_route
        return None

    def _remove_users_for_route(self, route_path: str, user_set: set[str]) -> int:
        """Remove all users for a route. Returns count of removed users."""
        removed_count = 0
        for user_id in user_set:
            self._all_users.discard(user_id)
            removed_count += 1
        if route_path in self._dashboard_users:
            del self._dashboard_users[route_path]
        return removed_count

    def _remove_inactive_users(
        self,
        route_path: str,
        user_set: set[str],
        active_user_ids: set[str],
    ) -> int:
        """Remove users that are no longer active. Returns count of removed users."""
        removed_count = 0
        for user_id in user_set:
            if user_id not in active_user_ids:
                self._dashboard_users[route_path].discard(user_id)
                self._all_users.discard(user_id)
                removed_count += 1

        if route_path in self._dashboard_users and not self._dashboard_users[route_path]:
            del self._dashboard_users[route_path]

        return removed_count

    def _remove_tracked_users_not_registered(
        self,
        tracked_route_users: dict[str, set[str]],
        route_sockets: dict[str, set["LiveViewSocket"]],
    ) -> int:
        """Remove users that are tracked but no longer registered. Returns count of removed users."""
        removed_count = 0
        for route_path, user_set in tracked_route_users.items():
            matching_route = self._find_matching_route(route_path, route_sockets)

            if matching_route is None:
                removed_count += self._remove_users_for_route(route_path, user_set)
                continue

            active_user_ids = {
                self._get_user_id(socket) for socket in route_sockets[matching_route]
            }
            removed_count += self._remove_inactive_users(route_path, user_set, active_user_ids)

        return removed_count

    def sync_with_registered_sockets(
        self, route_sockets: dict[str, set["LiveViewSocket"]]
    ) -> PresenceSyncResult:
        """Sync presence tracking with registered sockets for all routes.

        This method ensures that presence tracking matches the actual registered sockets.
        It adds users for sockets that are registered but not tracked, and removes users
        for sockets that are tracked but no longer registered.

        Args:
            route_sockets: Dictionary mapping route paths to sets of registered sockets.

        Returns:
            PresenceSyncResult with added_count and removed_count.
        """
        tracked_route_users = self._get_tracked_route_users()
        added_count = self._add_registered_users(route_sockets)
        removed_count = self._remove_tracked_users_not_registered(
            tracked_route_users, route_sockets
        )

        if added_count > 0 or removed_count > 0:
            logger.info(
                f"Presence sync: added {added_count}, removed {removed_count}. "
                f"Total users: {len(self._all_users)}"
            )

        return PresenceSyncResult(added_count=added_count, removed_count=removed_count)


# Global presence tracker instance
_presence_tracker = PresenceTracker()


def get_presence_tracker() -> PresenceTracker:
    """Get the global presence tracker instance.

    Returns:
        The global presence tracker.
    """
    return _presence_tracker
