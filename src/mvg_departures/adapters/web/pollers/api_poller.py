"""API poller for fetching and processing departures."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, replace
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


@dataclass(frozen=True)
class ApiPollerServices:
    """Service dependencies for API poller."""

    grouping_service: DepartureGroupingService
    state_updater: StateUpdaterProtocol
    state_broadcaster: StateBroadcasterProtocol


@dataclass(frozen=True)
class ApiPollerConfiguration:
    """Configuration for API poller."""

    stop_configs: list[StopConfiguration]
    config: AppConfig
    refresh_interval_seconds: int | None


@dataclass(frozen=True)
class ApiPollerSettings:
    """Runtime settings for API poller."""

    broadcast_topic: str
    shared_cache: dict[str, list[Departure]] | None = None


logger = logging.getLogger(__name__)


def _extract_status_code(error: Exception) -> int | None:
    """Extract HTTP status code from error message."""
    error_str = str(error)
    status_match = re.search(r"\((\d+)\)", error_str)
    return int(status_match.group(1)) if status_match else None


def _determine_error_reason(status_code: int | None) -> str:
    """Determine error reason from status code."""
    if status_code == 429:
        return "Rate limit exceeded"
    if status_code == 502:
        return "Bad gateway (server error)"
    if status_code == 503:
        return "Service unavailable"
    if status_code == 504:
        return "Gateway timeout"
    if status_code is not None:
        return f"HTTP {status_code}"
    return "Unknown error"


def _extract_error_details(error: Exception) -> ErrorDetails:
    """Extract HTTP status code and error reason from exception."""
    status_code = _extract_status_code(error)
    reason = _determine_error_reason(status_code)
    return ErrorDetails(status_code=status_code, reason=reason)


class ApiPoller(ApiPollerProtocol):
    """Polls API and updates state with departures."""

    def __init__(
        self,
        services: ApiPollerServices,
        configuration: ApiPollerConfiguration,
        settings: ApiPollerSettings,
    ) -> None:
        """Initialize the API poller.

        Args:
            services: Service dependencies for the poller.
            configuration: Configuration for what to poll and how.
            settings: Runtime settings for broadcasting and caching.
        """
        self.grouping_service = services.grouping_service
        self.state_updater = services.state_updater
        self.state_broadcaster = services.state_broadcaster
        self.stop_configs = configuration.stop_configs
        self.config = configuration.config
        self.refresh_interval_seconds = (
            configuration.refresh_interval_seconds
            if configuration.refresh_interval_seconds is not None
            else configuration.config.refresh_interval_seconds
        )
        self.broadcast_topic = settings.broadcast_topic
        self.shared_cache = settings.shared_cache
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

    def _create_departure_key(self, dep: Departure) -> tuple[str, str, datetime]:
        """Create a unique key for a departure."""
        return (dep.line, dep.destination, dep.time)

    def _deduplicate_group_departures(self, group: GroupedDepartures) -> GroupedDepartures:
        """Deduplicate departures within a single group."""
        seen = set()
        unique_departures = []
        for dep in group.departures:
            dep_key = self._create_departure_key(dep)
            if dep_key not in seen:
                seen.add(dep_key)
                unique_departures.append(dep)
            else:
                logger.warning(
                    f"Duplicate departure detected and removed: {dep.line} to {dep.destination} at {dep.time}"
                )
        return GroupedDepartures(direction_name=group.direction_name, departures=unique_departures)

    def _deduplicate_departures(self, groups: list[GroupedDepartures]) -> list[GroupedDepartures]:
        """Deduplicate departures within groups.

        Args:
            groups: List of grouped departures.

        Returns:
            List of grouped departures with duplicates removed.
        """
        return [self._deduplicate_group_departures(group) for group in groups]

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
            List of direction groups with metadata (only groups with departures).
        """
        result: list[DirectionGroupWithMetadata] = []
        for group in groups:
            if not group.departures:
                continue
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
            List of direction groups with metadata (marked as stale, only groups with departures).
        """
        result: list[DirectionGroupWithMetadata] = []
        for cached_group in cached_groups:
            if not cached_group.departures:
                continue
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

    def _handle_processing_error(
        self,
        stop_config: StopConfiguration,
        error: Exception,
        all_groups: list[DirectionGroupWithMetadata],
    ) -> None:
        """Handle error during stop config processing."""
        error_details = _extract_error_details(error)
        logger.error(
            f"API poller failed to process departures for {stop_config.station_name}: "
            f"{error_details.reason} (status: {error_details.status_code}, error: {error})"
        )
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

    def _determine_api_status(self, success_count: int, error_count: int) -> str:
        """Determine API status based on success/error counts."""
        if error_count == 0:
            return "success"
        if success_count > 0:
            return "degraded"
        return "error"

    async def _process_and_broadcast(self) -> None:
        """Process departures (from cache or API) and broadcast update."""
        all_groups: list[DirectionGroupWithMetadata] = []
        success_count = 0
        error_count = 0

        for stop_config in self.stop_configs:
            try:
                direction_groups = await self._process_stop_config(stop_config)
                all_groups.extend(direction_groups)
                success_count += 1
            except Exception as e:
                error_count += 1
                self._handle_processing_error(stop_config, e, all_groups)

        self.state_updater.update_departures(all_groups)
        self.state_updater.update_last_update_time(datetime.now(UTC))
        api_status = self._determine_api_status(success_count, error_count)
        self.state_updater.update_api_status(api_status)

        logger.debug(
            f"API poller updated departures at {datetime.now(UTC)}, "
            f"groups: {len(all_groups)}, api_status: {api_status}"
        )

        await self.state_broadcaster.broadcast_update(self.broadcast_topic)
