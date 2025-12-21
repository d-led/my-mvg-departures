"""State management class."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.adapters.web.broadcasters import StateBroadcaster
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

    def __init__(self, route_path: str = "/") -> None:
        """Initialize the state manager.

        Args:
            route_path: The path for this route, used to create a unique topic.
        """
        self.route_path = route_path
        self.departures_state = DeparturesState()
        self.connected_sockets: set[LiveViewSocket[DeparturesState]] = set()
        self.api_poller: ApiPoller | None = None
        # Create route-specific topic based on path
        # Normalize path: remove leading/trailing slashes and replace / with :
        normalized_path = route_path.strip("/").replace("/", ":") or "root"
        self.broadcast_topic: str = f"departures:updates:{normalized_path}"

    async def start_api_poller(
        self,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
        shared_cache: dict[str, list[Departure]] | None = None,
    ) -> None:
        """Start the API poller task.

        Args:
            grouping_service: Service for grouping departures.
            stop_configs: List of stop configurations for this route.
            config: Application configuration.
            shared_cache: Optional shared cache of raw departures by station_id.
                         If provided, will use cached data instead of fetching.
        """
        # Runtime usage - these checks ensure Ruff detects runtime dependency
        if not isinstance(config, AppConfig):
            raise TypeError("config must be an AppConfig instance")
        if not isinstance(stop_configs, list) or not all(
            isinstance(sc, StopConfiguration) for sc in stop_configs
        ):
            raise TypeError("stop_configs must be a list of StopConfiguration instances")
        # Protocols can't be checked with isinstance, but we verify required method exists
        # This explicit check ensures Ruff detects runtime usage of DepartureGroupingService
        # Access the method directly to make runtime dependency explicit for Ruff
        _ = grouping_service.group_departures  # Runtime usage - ensures Ruff detects dependency
        if not callable(grouping_service.group_departures):
            raise TypeError("grouping_service must implement DepartureGroupingService protocol")
        if shared_cache is not None and not isinstance(shared_cache, dict):
            raise TypeError("shared_cache must be a dict or None")

        if self.api_poller is not None:
            logger.warning("API poller already running")
            return

        # Create components
        state_updater = StateUpdater(self.departures_state)
        state_broadcaster = StateBroadcaster()

        # Create API poller
        self.api_poller = ApiPoller(
            grouping_service=grouping_service,
            stop_configs=stop_configs,
            config=config,
            state_updater=state_updater,
            state_broadcaster=state_broadcaster,
            broadcast_topic=self.broadcast_topic,
            shared_cache=shared_cache,
        )

        await self.api_poller.start()
        logger.info("Started API poller")

    async def stop_api_poller(self) -> None:
        """Stop the API poller task."""
        if self.api_poller is not None:
            await self.api_poller.stop()
            self.api_poller = None
            logger.info("Stopped API poller")

    def register_socket(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Register a socket for updates."""
        self.connected_sockets.add(socket)
        logger.info(f"Registered socket, total connected: {len(self.connected_sockets)}")

    def unregister_socket(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Unregister a socket."""
        self.connected_sockets.discard(socket)
        logger.info(f"Unregistered socket, total connected: {len(self.connected_sockets)}")
