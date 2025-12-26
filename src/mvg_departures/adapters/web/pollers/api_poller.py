"""API poller for fetching and processing departures."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from mvg_departures.domain.contracts.api_poller import ApiPollerProtocol
from mvg_departures.domain.contracts.state_broadcaster import (
    StateBroadcasterProtocol,  # noqa: TC001 - Runtime dependency: used in __init__ signature
)
from mvg_departures.domain.contracts.state_updater import (
    StateUpdaterProtocol,  # noqa: TC001 - Runtime dependency: used in __init__ signature
)
from mvg_departures.domain.models.direction_group_with_metadata import DirectionGroupWithMetadata
from mvg_departures.domain.models.error_details import ErrorDetails
from mvg_departures.domain.models.grouped_departures import GroupedDepartures

if TYPE_CHECKING:
    from mvg_departures.adapters.config.app_config import AppConfig
    from mvg_departures.domain.models.departure import Departure
    from mvg_departures.domain.models.stop_configuration import StopConfiguration
    from mvg_departures.domain.ports import DepartureGroupingService

logger = logging.getLogger(__name__)


def _extract_error_details(error: Exception) -> ErrorDetails:
    """Extract HTTP status code and error reason from exception."""
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

    return ErrorDetails(status_code=status_code, reason=reason)


class ApiPoller(ApiPollerProtocol):
    """Polls API and updates state with departures."""

    def __init__(
        self,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
        state_updater: StateUpdaterProtocol,
        state_broadcaster: StateBroadcasterProtocol,
        broadcast_topic: str,
        shared_cache: dict[str, list[Departure]] | None = None,
    ) -> None:
        """Initialize the API poller.

        Args:
            grouping_service: Service for grouping departures.
            stop_configs: List of stop configurations for this route.
            config: Application configuration.
            state_updater: Updater for state.
            state_broadcaster: Broadcaster for state updates.
            broadcast_topic: The pub/sub topic to broadcast to.
            shared_cache: Optional shared cache of raw departures by station_id.
        """
        self.grouping_service = grouping_service
        self.stop_configs = stop_configs
        self.config = config
        self.state_updater = state_updater
        self.state_broadcaster = state_broadcaster
        self.broadcast_topic = broadcast_topic
        self.shared_cache = shared_cache
        self.cached_departures: dict[str, list[GroupedDepartures]] = {}
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the API poller."""
        if self._task is not None and not self._task.done():
            logger.warning("API poller already running")
            return

        if self.shared_cache is not None:
            logger.info("API poller started with shared cache (independent of client connections)")
        else:
            logger.info("API poller started (independent of client connections)")

        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Started API poller task")

    async def stop(self) -> None:
        """Stop the API poller."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("API poller cancelled")
            logger.info("Stopped API poller")

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        # Do initial update immediately
        await self._process_and_broadcast()

        # Then poll periodically
        # If using shared cache, we still need to reprocess periodically as cache updates
        try:
            while True:
                await asyncio.sleep(self.config.refresh_interval_seconds)
                await self._process_and_broadcast()
        except asyncio.CancelledError:
            logger.info("API poller cancelled")
            raise

    async def _process_and_broadcast(self) -> None:
        """Process departures (from cache or API) and broadcast update."""
        all_groups: list[DirectionGroupWithMetadata] = []
        has_errors = False

        for stop_config in self.stop_configs:
            try:
                if self.shared_cache is not None:
                    # Use shared cache - get raw departures and process them
                    raw_departures = self.shared_cache.get(stop_config.station_id, [])
                    if not raw_departures:
                        # Cache is empty - fetch fresh data directly from API
                        # This ensures we always have fresh data, per requirement
                        logger.info(
                            f"Cache empty for {stop_config.station_name} "
                            f"(station_id: {stop_config.station_id}), fetching fresh from API"
                        )
                        # Fetch directly from API to get fresh data
                        groups = await self.grouping_service.get_grouped_departures(stop_config)
                    else:
                        # Check if cached departures are too old (more than 1 hour old)
                        # Filter out departures that are more than 1 hour in the past
                        now = datetime.now(UTC)
                        max_age = timedelta(hours=1)
                        recent_departures = [d for d in raw_departures if d.time >= now - max_age]

                        if not recent_departures:
                            # All cached departures are too old - fetch fresh data
                            logger.warning(
                                f"Cached departures for {stop_config.station_name} are too old, "
                                f"fetching fresh from API"
                            )
                            groups = await self.grouping_service.get_grouped_departures(stop_config)
                        else:
                            # Process cached raw departures using this route's stop configuration
                            groups = self.grouping_service.group_departures(
                                recent_departures, stop_config
                            )
                else:
                    # Fetch from API (fallback if no shared cache)
                    groups = await self.grouping_service.get_grouped_departures(stop_config)

                # Convert to format with station_name and deduplicate departures
                # Deduplication: same line + destination + time = same departure
                stop_groups: list[GroupedDepartures] = []
                for group in groups:
                    # Deduplicate departures within this direction group
                    seen = set()
                    unique_departures = []
                    for dep in group.departures:
                        # Create a unique key: line + destination + time
                        dep_key = (dep.line, dep.destination, dep.time)
                        if dep_key not in seen:
                            seen.add(dep_key)
                            unique_departures.append(dep)
                        else:
                            logger.warning(
                                f"Duplicate departure detected and removed: {dep.line} to {dep.destination} at {dep.time}"
                            )
                    stop_groups.append(
                        GroupedDepartures(
                            direction_name=group.direction_name, departures=unique_departures
                        )
                    )
                    # Include config settings directly - no matching needed
                    # Use stop-level settings if provided, otherwise use route-level defaults
                    random_colors = (
                        stop_config.random_header_colors
                        if stop_config.random_header_colors is not None
                        else None  # Will use route-level default in calculator
                    )
                    brightness = (
                        stop_config.header_background_brightness
                        if stop_config.header_background_brightness is not None
                        else None  # Will use route-level default in calculator
                    )
                    salt = (
                        stop_config.random_color_salt
                        if stop_config.random_color_salt is not None
                        else None  # Will use route-level default in calculator
                    )
                    all_groups.append(
                        DirectionGroupWithMetadata(
                            station_id=stop_config.station_id,
                            stop_name=stop_config.station_name,
                            direction_name=group.direction_name,
                            departures=unique_departures,
                            random_header_colors=random_colors,
                            header_background_brightness=brightness,
                            random_color_salt=salt,
                        )
                    )
                # Cache successful processing - always replace with fresh data
                self.cached_departures[stop_config.station_name] = stop_groups
                logger.debug(f"Successfully processed departures for {stop_config.station_name}")
            except Exception as e:
                error_details = _extract_error_details(e)
                logger.error(
                    f"API poller failed to process departures for {stop_config.station_name}: "
                    f"{error_details.reason} (status: {error_details.status_code}, error: {e})"
                )
                has_errors = True
                if error_details.status_code == 429:
                    logger.warning(
                        f"Rate limit (429) detected for {stop_config.station_name} - "
                        "consider adding delays between API calls"
                    )

                # Use cached processed groups if available, mark as stale
                if stop_config.station_name in self.cached_departures:
                    cached_groups = self.cached_departures[stop_config.station_name]
                    logger.info(
                        f"Using cached processed departures for {stop_config.station_name} "
                        f"({len(cached_groups)} direction groups) due to {error_details.reason}"
                    )
                    # Mark departures as stale (non-realtime)
                    for cached_group in cached_groups:
                        stale_departures = [
                            replace(dep, is_realtime=False) for dep in cached_group.departures
                        ]
                        # Include config settings directly - no matching needed
                        random_colors = (
                            stop_config.random_header_colors
                            if stop_config.random_header_colors is not None
                            else None
                        )
                        brightness = (
                            stop_config.header_background_brightness
                            if stop_config.header_background_brightness is not None
                            else None
                        )
                        salt = (
                            stop_config.random_color_salt
                            if stop_config.random_color_salt is not None
                            else None
                        )
                        all_groups.append(
                            DirectionGroupWithMetadata(
                                station_id=stop_config.station_id,
                                stop_name=stop_config.station_name,
                                direction_name=cached_group.direction_name,
                                departures=stale_departures,
                                random_header_colors=random_colors,
                                header_background_brightness=brightness,
                                random_color_salt=salt,
                            )
                        )
                # Continue with other stops even if one fails

        # Update shared state (even if some stops failed, use what we got)
        self.state_updater.update_departures(all_groups)
        self.state_updater.update_last_update_time(datetime.now(UTC))
        self.state_updater.update_api_status("error" if has_errors else "success")

        logger.debug(
            f"API poller updated departures at {datetime.now(UTC)}, "
            f"groups: {len(all_groups)}, errors: {has_errors}"
        )

        # Broadcast update via pubsub to all subscribed sockets
        await self.state_broadcaster.broadcast_update(self.broadcast_topic)
