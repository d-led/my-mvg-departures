"""State management for departures LiveView and API polling."""

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pyview import LiveViewSocket

from mvg_departures.adapters.config import AppConfig
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import Departure, StopConfiguration

logger = logging.getLogger(__name__)


@dataclass
class DeparturesState:
    """State for the departures LiveView."""

    direction_groups: list[tuple[str, str, list[Departure]]] = field(default_factory=list)
    last_update: datetime | None = None
    api_status: str = "unknown"


class State:
    """Manages shared state for departures LiveView and API polling."""

    def __init__(self) -> None:
        """Initialize the state manager."""
        self.departures_state = DeparturesState()
        self.connected_sockets: set[LiveViewSocket[DeparturesState]] = set()
        self.api_poller_task: asyncio.Task | None = None
        self.cached_departures: dict[str, list[tuple[str, list[Departure]]]] = {}
        self.broadcast_topic: str = "departures:updates"

    async def start_api_poller(
        self,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
    ) -> None:
        """Start the API poller task."""
        if self.api_poller_task is not None and not self.api_poller_task.done():
            logger.warning("API poller already running")
            return

        self.api_poller_task = asyncio.create_task(
            self._api_poller(grouping_service, stop_configs, config)
        )
        logger.info("Started API poller task")

    async def stop_api_poller(self) -> None:
        """Stop the API poller task."""
        if self.api_poller_task and not self.api_poller_task.done():
            self.api_poller_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.api_poller_task
            logger.info("Stopped API poller")

    async def _api_poller(
        self,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
    ) -> None:
        """Independent API poller that updates shared state and broadcasts to connected sockets.

        This runs as a separate background task, completely independent of LiveView instances.
        It polls the API periodically and broadcasts updates to all connected sockets.
        """
        from pyview.live_socket import pub_sub_hub
        from pyview.vendor.flet.pubsub import PubSub

        # Create PubSub instance once and reuse it
        pubsub = PubSub(pub_sub_hub, self.broadcast_topic)

        logger.info("API poller started (independent of client connections)")

        def extract_error_details(error: Exception) -> tuple[int | None, str]:
            """Extract HTTP status code and error reason from exception."""
            import re

            error_str = str(error)
            # Try to extract HTTP status code from error message
            # Format: "Bad API call: Got response (502) from ..."
            status_match = re.search(r"\((\d+)\)", error_str)
            status_code = int(status_match.group(1)) if status_match else None

            # Determine error reason
            if status_code == 429:
                reason = "Rate limit exceeded"
            elif status_code == 502:
                reason = "Bad gateway (server error)"
            elif status_code == 503:
                reason = "Service unavailable"
            elif status_code == 504:
                reason = "Gateway timeout"
            elif status_code is not None:
                reason = f"HTTP {status_code}"
            else:
                reason = "Unknown error"

            return status_code, reason

        async def _fetch_and_broadcast() -> None:
            """Fetch departures and broadcast update to all connected sockets."""
            # Fetch departures from API - handle errors per stop
            all_groups: list[tuple[str, str, list[Departure]]] = []
            has_errors = False

            for stop_config in stop_configs:
                try:
                    groups = await grouping_service.get_grouped_departures(stop_config)
                    # Convert to format with station_name
                    stop_groups: list[tuple[str, list[Departure]]] = []
                    for direction_name, departures in groups:
                        stop_groups.append((direction_name, departures))
                        all_groups.append((stop_config.station_name, direction_name, departures))
                    # Cache successful fetch
                    self.cached_departures[stop_config.station_name] = stop_groups
                    logger.debug(f"Successfully fetched departures for {stop_config.station_name}")
                except Exception as e:
                    status_code, reason = extract_error_details(e)
                    logger.error(
                        f"API poller failed to fetch departures for {stop_config.station_name}: "
                        f"{reason} (status: {status_code}, error: {e})"
                    )
                    has_errors = True
                    if status_code == 429:
                        logger.warning(
                            f"Rate limit (429) detected for {stop_config.station_name} - "
                            "consider adding delays between API calls"
                        )

                    # Use cached data if available, mark as stale
                    if stop_config.station_name in self.cached_departures:
                        cached_groups = self.cached_departures[stop_config.station_name]
                        logger.info(
                            f"Using cached departures for {stop_config.station_name} "
                            f"({len(cached_groups)} direction groups) due to {reason}"
                        )
                        # Mark departures as stale (non-realtime)
                        from dataclasses import replace

                        for direction_name, cached_departures in cached_groups:
                            stale_departures = [
                                replace(dep, is_realtime=False) for dep in cached_departures
                            ]
                            all_groups.append(
                                (stop_config.station_name, direction_name, stale_departures)
                            )
                    # Continue with other stops even if one fails

            # Update shared state (even if some stops failed, use what we got)
            self.departures_state.direction_groups = all_groups
            self.departures_state.last_update = datetime.now(UTC)
            self.departures_state.api_status = "error" if has_errors else "success"

            logger.debug(
                f"API poller updated departures at {datetime.now(UTC)}, "
                f"groups: {len(all_groups)}, errors: {has_errors}"
            )

            # Broadcast update via pubsub to all subscribed sockets
            try:
                await pubsub.send_all_on_topic_async(self.broadcast_topic, "update")
                logger.info(f"Broadcasted update via pubsub to topic: {self.broadcast_topic}")
            except Exception as pubsub_err:
                logger.error(f"Failed to broadcast via pubsub: {pubsub_err}", exc_info=True)

        # Do initial update immediately
        await _fetch_and_broadcast()

        # Then poll periodically
        try:
            while True:
                await asyncio.sleep(config.refresh_interval_seconds)
                await _fetch_and_broadcast()
        except asyncio.CancelledError:
            logger.info("API poller cancelled")
            raise

    def register_socket(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Register a socket for updates."""
        self.connected_sockets.add(socket)
        logger.info(f"Registered socket, total connected: {len(self.connected_sockets)}")

    def unregister_socket(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Unregister a socket."""
        self.connected_sockets.discard(socket)
        logger.info(f"Unregistered socket, total connected: {len(self.connected_sockets)}")
