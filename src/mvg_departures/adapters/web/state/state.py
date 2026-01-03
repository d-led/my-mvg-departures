"""State management class."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.adapters.web.broadcasters import StateBroadcaster
from mvg_departures.adapters.web.client_info import (
    ClientInfo,
    get_client_info_from_socket,
)
from mvg_departures.adapters.web.pollers import ApiPoller
from mvg_departures.adapters.web.updaters import StateUpdater

from .departures_state import DeparturesState

if TYPE_CHECKING:
    from pyview import LiveViewSocket

    from mvg_departures.domain.models.departure import Departure

from mvg_departures.domain.models.stop_configuration import StopConfiguration
from mvg_departures.domain.ports import (
    DepartureGroupingService,  # noqa: TC001 - Runtime dependency: methods called at runtime
)

logger = logging.getLogger(__name__)


class State:
    """Manages shared state for departures LiveView and API polling."""

    def __init__(self, route_path: str = "/", max_sessions_per_browser: int = 15) -> None:
        """Initialize the state manager.

        Args:
            route_path: The path for this route, used to create a unique topic.
        """
        self.route_path = route_path
        self.departures_state = DeparturesState()
        self.connected_sockets: set[LiveViewSocket[DeparturesState]] = set()
        # Track sockets per logical presence session so that reconnects from the same
        # client do not leak "stale" sockets in connected_sockets.
        self._session_sockets: dict[str, LiveViewSocket[DeparturesState]] = {}
        # Optional per-browser connection limiting.
        self.max_sessions_per_browser = max_sessions_per_browser
        self._browser_sockets: dict[str, set[LiveViewSocket[DeparturesState]]] = {}
        self._socket_browser: dict[LiveViewSocket[DeparturesState], str] = {}
        self.api_poller: ApiPoller | None = None
        # Create route-specific topic based on path
        # Normalize path: remove leading/trailing slashes and replace / with :
        normalized_path = route_path.strip("/").replace("/", ":") or "root"
        self.broadcast_topic: str = f"departures:updates:{normalized_path}"

    def _validate_api_poller_parameters(
        self,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
        shared_cache: dict[str, list[Departure]] | None,
    ) -> None:
        """Validate parameters for API poller startup."""
        if not isinstance(config, AppConfig):
            raise TypeError("config must be an AppConfig instance")
        if not isinstance(stop_configs, list) or not all(
            isinstance(sc, StopConfiguration) for sc in stop_configs
        ):
            raise TypeError("stop_configs must be a list of StopConfiguration instances")
        _ = grouping_service.group_departures  # Runtime usage - ensures Ruff detects dependency
        if not callable(grouping_service.group_departures):
            raise TypeError("grouping_service must implement DepartureGroupingService protocol")
        if shared_cache is not None and not isinstance(shared_cache, dict):
            raise TypeError("shared_cache must be a dict or None")

    def _create_api_poller(
        self,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
        shared_cache: dict[str, list[Departure]] | None,
        refresh_interval_seconds: int | None,
    ) -> ApiPoller:
        """Create and configure API poller instance."""
        state_updater = StateUpdater(self.departures_state)
        state_broadcaster = StateBroadcaster()
        return ApiPoller(
            grouping_service=grouping_service,
            stop_configs=stop_configs,
            config=config,
            state_updater=state_updater,
            state_broadcaster=state_broadcaster,
            broadcast_topic=self.broadcast_topic,
            shared_cache=shared_cache,
            refresh_interval_seconds=refresh_interval_seconds,
        )

    async def start_api_poller(
        self,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
        shared_cache: dict[str, list[Departure]] | None = None,
        refresh_interval_seconds: int | None = None,
    ) -> None:
        """Start the API poller task.

        Args:
            grouping_service: Service for grouping departures.
            stop_configs: List of stop configurations for this route.
            config: Application configuration.
            shared_cache: Optional shared cache of raw departures by station_id.
                         If provided, will use cached data instead of fetching.
            refresh_interval_seconds: Optional route-specific poller interval in seconds.
                                    If None, uses config.refresh_interval_seconds.
        """
        self._validate_api_poller_parameters(grouping_service, stop_configs, config, shared_cache)

        if self.api_poller is not None:
            logger.warning("API poller already running")
            return

        self.api_poller = self._create_api_poller(
            grouping_service, stop_configs, config, shared_cache, refresh_interval_seconds
        )
        await self.api_poller.start()
        logger.info(f"Started API poller for route '{self.route_path}'")

    async def stop_api_poller(self) -> None:
        """Stop the API poller task."""
        if self.api_poller is not None:
            await self.api_poller.stop()
            self.api_poller = None
            logger.info("Stopped API poller")

    def _check_browser_session_limit(self, client_info: ClientInfo) -> bool:
        """Check if registering socket would exceed browser session limit.

        Returns:
            True if socket should be rejected, False otherwise.
        """
        if client_info.browser_id == "unknown" or self.max_sessions_per_browser <= 0:
            return False

        sockets_for_browser = self._browser_sockets.get(client_info.browser_id)
        active_count = len(sockets_for_browser) if sockets_for_browser is not None else 0
        if active_count >= self.max_sessions_per_browser:
            logger.warning(
                "Rejecting socket from ip=%s, agent=%s, browser_id=%s for route '%s' "
                "because it would exceed max_sessions_per_browser=%s "
                "(currently %s active sockets for this browser).",
                client_info.ip,
                client_info.user_agent,
                client_info.browser_id,
                self.route_path,
                self.max_sessions_per_browser,
                active_count,
            )
            return True
        return False

    def _register_socket_for_session(
        self, socket: LiveViewSocket[DeparturesState], session_id: str | None
    ) -> None:
        """Register socket for a session, removing any existing socket for that session."""
        if not session_id:
            return

        existing_socket = self._session_sockets.get(session_id)
        if existing_socket is not None and existing_socket is not socket:
            self.connected_sockets.discard(existing_socket)
        self._session_sockets[session_id] = socket

    def _register_socket_for_browser(
        self, socket: LiveViewSocket[DeparturesState], client_info: ClientInfo
    ) -> None:
        """Register socket for browser tracking."""
        if client_info.browser_id != "unknown":
            self._browser_sockets.setdefault(client_info.browser_id, set()).add(socket)
            self._socket_browser[socket] = client_info.browser_id

    def register_socket(
        self, socket: LiveViewSocket[DeparturesState], session_id: str | None = None
    ) -> bool:
        """Register a socket for updates.

        When a logical client (identified by session_id) reconnects, pyview may create
        a new LiveViewSocket instance. To keep the server-side accounting stable, we
        ensure that at most one socket is registered per session:

        - If session_id is provided and we already have a socket for that session,
          the old socket is first removed from the connected set.
        - The new socket is then registered and associated with the session.

        Returns:
            True if the socket was registered, False if it was rejected due to
            per-browser session limits.
        """
        client_info = get_client_info_from_socket(socket)

        if self._check_browser_session_limit(client_info):
            return False

        self._register_socket_for_session(socket, session_id)
        self.connected_sockets.add(socket)
        self._register_socket_for_browser(socket, client_info)

        logger.info(
            "Registered socket from ip=%s, agent=%s, browser_id=%s, total connected: %s",
            client_info.ip,
            client_info.user_agent,
            client_info.browser_id,
            len(self.connected_sockets),
        )
        return True

    def _cleanup_empty_browser_tracking(self, browser_id: str) -> None:
        """Remove browser tracking if no sockets remain."""
        sockets_for_browser = self._browser_sockets.get(browser_id)
        if sockets_for_browser is not None and not sockets_for_browser:
            del self._browser_sockets[browser_id]

    def _remove_socket_from_browser_tracking(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Remove socket from browser-based tracking."""
        browser_id = self._socket_browser.pop(socket, None)
        if browser_id is not None:
            sockets_for_browser = self._browser_sockets.get(browser_id)
            if sockets_for_browser is not None:
                sockets_for_browser.discard(socket)
                self._cleanup_empty_browser_tracking(browser_id)

    def _remove_socket_from_session_tracking(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Remove socket from session-based tracking."""
        stale_session_ids = [
            session_id
            for session_id, registered_socket in self._session_sockets.items()
            if registered_socket is socket
        ]
        for session_id in stale_session_ids:
            del self._session_sockets[session_id]

    def unregister_socket(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Unregister a socket.

        This method is idempotent and also cleans up any session mapping that still
        points at the given socket.
        """
        self.connected_sockets.discard(socket)
        self._remove_socket_from_browser_tracking(socket)
        self._remove_socket_from_session_tracking(socket)
        logger.info(f"Unregistered socket, total connected: {len(self.connected_sockets)}")
