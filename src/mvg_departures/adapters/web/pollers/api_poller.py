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
        refresh_interval_seconds: int | None = None,
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
            refresh_interval_seconds: Optional route-specific poller interval in seconds.
                                    If None, uses config.refresh_interval_seconds.
        """
        self.grouping_service = grouping_service
        self.stop_configs = stop_configs
        self.config = config
        self.state_updater = state_updater
        self.state_broadcaster = state_broadcaster
        self.broadcast_topic = broadcast_topic
        self.shared_cache = shared_cache
        self.refresh_interval_seconds = (
            refresh_interval_seconds
            if refresh_interval_seconds is not None
            else config.refresh_interval_seconds
        )
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
                await asyncio.sleep(self.refresh_interval_seconds)
                await self._process_and_broadcast()
        except asyncio.CancelledError:
            logger.info("API poller cancelled")
            raise

    async def _fetch_groups_for_stop(
        self, stop_config: StopConfiguration
    ) -> list[GroupedDepartures]:
        """Fetch grouped departures for a stop (from cache or API).

        Args:
            stop_config: Stop configuration.

        Returns:
            List of grouped departures.
        """
        if stop_config.departure_leeway_minutes > 0:
            return await self.grouping_service.get_grouped_departures(stop_config)

        if self.shared_cache is None:
            return await self.grouping_service.get_grouped_departures(stop_config)

        raw_departures = self.shared_cache.get(stop_config.station_id, [])
        if not raw_departures:
            logger.info(
                f"Cache empty for {stop_config.station_name} "
                f"(station_id: {stop_config.station_id}), fetching fresh from API"
            )
            return await self.grouping_service.get_grouped_departures(stop_config)

        now = datetime.now(UTC)
        max_age = timedelta(hours=1)
        recent_departures = [d for d in raw_departures if d.time >= now - max_age]

        if not recent_departures:
            logger.warning(
                f"Cached departures for {stop_config.station_name} are too old, "
                f"fetching fresh from API"
            )
            return await self.grouping_service.get_grouped_departures(stop_config)

        return self.grouping_service.group_departures(recent_departures, stop_config)

    def _deduplicate_departures(self, groups: list[GroupedDepartures]) -> list[GroupedDepartures]:
        """Deduplicate departures within groups.

        Args:
            groups: List of grouped departures.

        Returns:
            List of grouped departures with duplicates removed.
        """
        deduplicated: list[GroupedDepartures] = []
        for group in groups:
            seen = set()
            unique_departures = []
            for dep in group.departures:
                dep_key = (dep.line, dep.destination, dep.time)
                if dep_key not in seen:
                    seen.add(dep_key)
                    unique_departures.append(dep)
                else:
                    logger.warning(
                        f"Duplicate departure detected and removed: {dep.line} to {dep.destination} at {dep.time}"
                    )
            deduplicated.append(
                GroupedDepartures(direction_name=group.direction_name, departures=unique_departures)
            )
        return deduplicated

    def _build_direction_groups_with_metadata(
        self,
        stop_config: StopConfiguration,
        groups: list[GroupedDepartures],
    ) -> list[DirectionGroupWithMetadata]:
        """Build direction groups with metadata from grouped departures.

        Args:
            stop_config: Stop configuration.
            groups: List of grouped departures.

        Returns:
            List of direction groups with metadata.
        """
        result: list[DirectionGroupWithMetadata] = []
        for group in groups:
            result.append(
                DirectionGroupWithMetadata(
                    station_id=stop_config.station_id,
                    stop_name=stop_config.station_name,
                    direction_name=group.direction_name,
                    departures=group.departures,
                    random_header_colors=stop_config.random_header_colors,
                    header_background_brightness=stop_config.header_background_brightness,
                    random_color_salt=stop_config.random_color_salt,
                )
            )
        return result

    def _build_stale_direction_groups_with_metadata(
        self,
        stop_config: StopConfiguration,
        cached_groups: list[GroupedDepartures],
    ) -> list[DirectionGroupWithMetadata]:
        """Build direction groups with metadata from cached groups, marking as stale.

        Args:
            stop_config: Stop configuration.
            cached_groups: List of cached grouped departures.

        Returns:
            List of direction groups with metadata (marked as stale).
        """
        result: list[DirectionGroupWithMetadata] = []
        for cached_group in cached_groups:
            stale_departures = [replace(dep, is_realtime=False) for dep in cached_group.departures]
            result.append(
                DirectionGroupWithMetadata(
                    station_id=stop_config.station_id,
                    stop_name=stop_config.station_name,
                    direction_name=cached_group.direction_name,
                    departures=stale_departures,
                    random_header_colors=stop_config.random_header_colors,
                    header_background_brightness=stop_config.header_background_brightness,
                    random_color_salt=stop_config.random_color_salt,
                )
            )
        return result

    async def _process_stop_config(
        self, stop_config: StopConfiguration
    ) -> list[DirectionGroupWithMetadata]:
        """Process a single stop configuration and return direction groups.

        Args:
            stop_config: Stop configuration.

        Returns:
            List of direction groups with metadata.
        """
        groups = await self._fetch_groups_for_stop(stop_config)
        deduplicated_groups = self._deduplicate_departures(groups)
        direction_groups = self._build_direction_groups_with_metadata(
            stop_config, deduplicated_groups
        )
        self.cached_departures[stop_config.station_name] = deduplicated_groups
        logger.debug(f"Successfully processed departures for {stop_config.station_name}")
        return direction_groups

    async def _process_and_broadcast(self) -> None:
        """Process departures (from cache or API) and broadcast update."""
        all_groups: list[DirectionGroupWithMetadata] = []
        has_errors = False

        for stop_config in self.stop_configs:
            try:
                direction_groups = await self._process_stop_config(stop_config)
                all_groups.extend(direction_groups)
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

                if stop_config.station_name in self.cached_departures:
                    cached_groups = self.cached_departures[stop_config.station_name]
                    logger.info(
                        f"Using cached processed departures for {stop_config.station_name} "
                        f"({len(cached_groups)} direction groups) due to {error_details.reason}"
                    )
                    stale_groups = self._build_stale_direction_groups_with_metadata(
                        stop_config, cached_groups
                    )
                    all_groups.extend(stale_groups)

        self.state_updater.update_departures(all_groups)
        self.state_updater.update_last_update_time(datetime.now(UTC))
        self.state_updater.update_api_status("error" if has_errors else "success")

        logger.debug(
            f"API poller updated departures at {datetime.now(UTC)}, "
            f"groups: {len(all_groups)}, errors: {has_errors}"
        )

        await self.state_broadcaster.broadcast_update(self.broadcast_topic)
