"""Departure grouping service."""

import logging
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any

from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.models.grouped_departures import GroupedDepartures
from mvg_departures.domain.models.stop_configuration import StopConfiguration
from mvg_departures.domain.ports.departure_repository import DepartureRepository

logger = logging.getLogger(__name__)


class DepartureGroupingService:
    """Service for grouping departures by configured directions."""

    def __init__(self, departure_repository: DepartureRepository) -> None:
        """Initialize with a departure repository."""
        self._departure_repository = departure_repository

    async def get_grouped_departures(
        self, stop_config: StopConfiguration
    ) -> list[GroupedDepartures]:
        """Get departures for a stop, grouped by configured directions.

        Fetches a reasonable number of departures from the API, then groups them
        by direction and limits each direction group to max_departures_per_stop.
        """
        # Extract base station_id if station_id is a stop_point_global_id
        # API only accepts base stationGlobalId, not stop_point_global_id format
        station_id_parts = stop_config.station_id.split(":")
        if len(station_id_parts) >= 5 and station_id_parts[-1] == station_id_parts[-2]:
            # station_id is a stop_point_global_id (e.g., "de:09162:1108:1:1")
            # Extract base station_id (e.g., "de:09162:1108")
            base_station_id = ":".join(station_id_parts[:3])
        else:
            base_station_id = stop_config.station_id

        # Fetch departures from API - use configurable limit per stop
        # The repository will fetch more data (e.g., 300 results over configurable duration) but return up to this limit
        fetch_limit = stop_config.max_departures_fetch

        # Use configured fetch window (repository will handle provider-specific behavior)
        duration_minutes = stop_config.fetch_max_minutes_in_advance

        # Capture the time we're fetching at - this is the "now" we'll use for filtering
        fetch_time_utc = datetime.now(UTC)

        # Pass offset_minutes if leeway is configured (repository will handle provider-specific behavior)
        # This ensures the API returns departures starting from "now + leeway" when applicable
        offset_minutes = (
            stop_config.departure_leeway_minutes if stop_config.departure_leeway_minutes > 0 else 0
        )

        departures = await self._departure_repository.get_departures(
            base_station_id,
            limit=fetch_limit,
            offset_minutes=offset_minutes,
            transport_types=None,
            duration_minutes=duration_minutes,
        )

        # Pass the fetch time as reference time for consistent filtering
        # This ensures we compare against the same "now" we used when calling the API
        return self.group_departures(departures, stop_config, reference_time_utc=fetch_time_utc)

    def _filter_blacklisted_departures(
        self, departures: list[Departure], stop_config: StopConfiguration
    ) -> list[Departure]:
        """Filter out blacklisted departures.

        Args:
            departures: List of departures to filter.
            stop_config: Stop configuration.

        Returns:
            Filtered list of departures.
        """
        if not stop_config.exclude_destinations:
            return departures

        initial_count = len(departures)
        filtered = [
            d
            for d in departures
            if not self._matches_departure(d, stop_config.exclude_destinations)
        ]
        filtered_count = initial_count - len(filtered)

        if filtered_count > 0:
            logger.debug(
                f"Filtered out {filtered_count} blacklisted departures for {stop_config.station_name}"
            )

        return filtered

    def _find_matching_direction(
        self, departure: Departure, direction_mappings: dict[str, list[str]]
    ) -> str | None:
        """Find the direction name that matches a departure."""
        for direction_name, patterns in direction_mappings.items():
            if self._matches_departure(departure, patterns):
                return direction_name
        return None

    def _add_departure_to_group(
        self,
        direction_groups: dict[str, list[Departure]],
        direction_name: str,
        departure: Departure,
    ) -> None:
        """Add a departure to the appropriate direction group."""
        if direction_name not in direction_groups:
            direction_groups[direction_name] = []
        direction_groups[direction_name].append(departure)

    def _group_by_direction(
        self,
        departures: list[Departure],
        stop_config: StopConfiguration,
    ) -> tuple[dict[str, list[Departure]], list[Departure]]:
        """Group departures by configured directions.

        Args:
            departures: List of departures to group.
            stop_config: Stop configuration.

        Returns:
            Tuple of (direction_groups, ungrouped).
        """
        direction_groups: dict[str, list[Departure]] = {}
        ungrouped: list[Departure] = []

        if not stop_config.direction_mappings:
            logger.warning(f"No direction_mappings configured for {stop_config.station_name}")
        logger.debug(
            f"Processing {len(departures)} departures for {stop_config.station_name} with {len(stop_config.direction_mappings)} direction mappings"
        )

        for departure in departures:
            direction_name = self._find_matching_direction(
                departure, stop_config.direction_mappings
            )
            if direction_name:
                self._add_departure_to_group(direction_groups, direction_name, departure)
            else:
                ungrouped.append(departure)
                logger.debug(
                    f"Unmatched departure for {stop_config.station_name}: {departure.transport_type} {departure.line} -> {departure.destination}"
                )

        return direction_groups, ungrouped

    def _process_direction_groups(
        self,
        direction_groups: dict[str, list[Departure]],
        stop_config: StopConfiguration,
        reference_time_utc: datetime,
    ) -> dict[str, list[Departure]]:
        """Sort and filter departures in each direction group.

        Args:
            direction_groups: Dictionary mapping direction names to departures.
            stop_config: Stop configuration.
            reference_time_utc: Reference time for filtering.

        Returns:
            Processed direction groups.
        """
        for direction_name in direction_groups:
            direction_groups[direction_name].sort(key=lambda d: d.time)
            direction_groups[direction_name] = self._filter_and_limit_departures(
                direction_groups[direction_name], stop_config, reference_time_utc=reference_time_utc
            )
        return direction_groups

    def _build_result_list(
        self,
        direction_groups: dict[str, list[Departure]],
        ungrouped: list[Departure],
        stop_config: StopConfiguration,
    ) -> list[GroupedDepartures]:
        """Build result list from direction groups and ungrouped departures.

        Args:
            direction_groups: Dictionary mapping direction names to departures.
            ungrouped: List of ungrouped departures.
            stop_config: Stop configuration.

        Returns:
            List of GroupedDepartures.
        """
        result = []
        for direction_name in stop_config.direction_mappings:
            if direction_name in direction_groups:
                result.append(
                    GroupedDepartures(
                        direction_name=direction_name, departures=direction_groups[direction_name]
                    )
                )

        if stop_config.show_ungrouped and ungrouped:
            ungrouped_label = stop_config.ungrouped_title or "Other"
            result.append(GroupedDepartures(direction_name=ungrouped_label, departures=ungrouped))

        return result

    def group_departures(
        self,
        departures: list[Departure],
        stop_config: StopConfiguration,
        reference_time_utc: datetime | None = None,
    ) -> list[GroupedDepartures]:
        """Group pre-fetched departures by configured directions.

        This method allows grouping departures that were already fetched,
        enabling shared fetching across multiple routes.

        Args:
            departures: Pre-fetched list of departures to group.
            stop_config: Stop configuration with direction mappings and limits.
            reference_time_utc: Optional reference time for filtering (defaults to current time).

        Returns:
            List of tuples (direction_name, departures) for this stop.
        """
        if reference_time_utc is None:
            reference_time_utc = datetime.now(UTC)

        departures = self._filter_blacklisted_departures(departures, stop_config)
        direction_groups, ungrouped = self._group_by_direction(departures, stop_config)

        direction_groups = self._process_direction_groups(
            direction_groups, stop_config, reference_time_utc
        )

        if ungrouped:
            ungrouped.sort(key=lambda d: d.time)
            ungrouped = self._filter_and_limit_departures(
                ungrouped, stop_config, reference_time_utc=reference_time_utc
            )

        return self._build_result_list(direction_groups, ungrouped, stop_config)

    def _filter_by_stop_point(
        self, departures: list[Departure], stop_config: StopConfiguration
    ) -> list[Departure]:
        """Filter departures by stop point if station_id is a stop_point_global_id.

        Args:
            departures: List of departures to filter.
            stop_config: Stop configuration.

        Returns:
            Filtered list of departures.
        """
        station_id_parts = stop_config.station_id.split(":")
        if len(station_id_parts) < 5 or station_id_parts[-1] != station_id_parts[-2]:
            return departures

        stop_point_global_id = stop_config.station_id
        initial_count = len(departures)
        available_stop_points = {
            d.stop_point_global_id for d in departures if d.stop_point_global_id is not None
        }
        filtered = [
            d
            for d in departures
            if d.stop_point_global_id is not None and d.stop_point_global_id == stop_point_global_id
        ]

        if initial_count > 0 and len(filtered) == 0:
            logger.warning(
                f"Filtered {initial_count} departures by stop_point_global_id={stop_point_global_id}, "
                f"but none matched. Available stop_point_global_ids: {available_stop_points}"
            )

        return filtered

    def _should_apply_platform_filter(
        self, departure: Departure, stop_config: StopConfiguration
    ) -> bool:
        """Check if platform filter should be applied to this departure."""
        if not stop_config.platform_filter_routes:
            return True
        return departure.line in stop_config.platform_filter_routes

    def _matches_platform_filter(
        self,
        departure: Departure,
        platform_filter: int,
        platform_filter_str: str,
        platform_pattern: re.Pattern[str],
    ) -> bool:
        """Check if departure matches platform filter."""
        if departure.platform is None:
            return False
        return self._platform_matches(
            departure.platform, platform_filter, platform_filter_str, platform_pattern
        )

    def _filter_by_platform(
        self, departures: list[Departure], stop_config: StopConfiguration
    ) -> list[Departure]:
        """Filter departures by platform if platform_filter is set.

        Args:
            departures: List of departures to filter.
            stop_config: Stop configuration.

        Returns:
            Filtered list of departures.
        """
        if stop_config.platform_filter is None:
            return departures

        initial_count = len(departures)
        available_platforms = {d.platform for d in departures if d.platform is not None}
        platform_filter_str = str(stop_config.platform_filter)
        platform_pattern = re.compile(
            r"(?:^|\s|Pos\.|Platform\s)" + re.escape(platform_filter_str) + r"(?:\s|$|\)|,)"
        )

        filtered = []
        for departure in departures:
            should_filter = self._should_apply_platform_filter(departure, stop_config)
            if not should_filter or self._matches_platform_filter(
                departure,
                stop_config.platform_filter,
                platform_filter_str,
                platform_pattern,
            ):
                filtered.append(departure)

        if initial_count > 0 and len(filtered) == 0:
            logger.warning(
                f"Filtered {initial_count} departures by platform={stop_config.platform_filter}, "
                f"but none matched. Available platforms: {available_platforms}"
            )

        return filtered

    def _platform_matches(
        self, platform: int | str, platform_filter: int, platform_filter_str: str, pattern: Any
    ) -> bool:
        """Check if platform matches the filter.

        Args:
            platform: Platform value to check.
            platform_filter: Filter value (int).
            platform_filter_str: Filter value (str).
            pattern: Compiled regex pattern.

        Returns:
            True if platform matches, False otherwise.
        """
        return platform in (platform_filter, platform_filter_str) or (
            isinstance(platform, str) and pattern.search(platform)
        )

    def _filter_by_leeway(
        self,
        departures: list[Departure],
        stop_config: StopConfiguration,
        reference_time_utc: datetime | None = None,
    ) -> list[Departure]:
        """Filter departures by departure leeway.

        Args:
            departures: List of departures to filter.
            stop_config: Stop configuration.
            reference_time_utc: Reference time for comparison.

        Returns:
            Filtered list of departures.
        """
        if stop_config.departure_leeway_minutes <= 0:
            return departures

        now_utc = reference_time_utc if reference_time_utc is not None else datetime.now(UTC)
        cutoff_time = now_utc + timedelta(minutes=stop_config.departure_leeway_minutes)

        filtered = []
        for d in departures:
            dep_time = d.time
            if dep_time.tzinfo is None:
                dep_time = dep_time.replace(tzinfo=UTC)
            else:
                dep_time = dep_time.astimezone(UTC)
            if dep_time >= cutoff_time:
                filtered.append(d)

        return filtered

    def _filter_by_max_hours(
        self, departures: list[Departure], stop_config: StopConfiguration
    ) -> list[Departure]:
        """Filter departures by max hours in advance.

        Args:
            departures: List of departures to filter.
            stop_config: Stop configuration.

        Returns:
            Filtered list of departures.
        """
        if stop_config.max_hours_in_advance is None or stop_config.max_hours_in_advance < 1:
            return departures

        max_time = datetime.now(UTC) + timedelta(hours=stop_config.max_hours_in_advance)
        return [d for d in departures if d.time <= max_time]

    def _limit_by_route(
        self, departures: list[Departure], stop_config: StopConfiguration
    ) -> list[Departure]:
        """Limit departures per route.

        Args:
            departures: List of departures to limit.
            stop_config: Stop configuration.

        Returns:
            Limited list of departures.
        """
        max_per_route = stop_config.max_departures_per_route or 2
        route_counts: dict[str, int] = {}
        limited: list[Departure] = []

        for departure in departures:
            route_key = departure.line
            count = route_counts.get(route_key, 0)
            if count < max_per_route:
                limited.append(departure)
                route_counts[route_key] = count + 1

        return limited

    def _limit_by_stop(
        self, departures: list[Departure], stop_config: StopConfiguration
    ) -> list[Departure]:
        """Limit departures per stop.

        Args:
            departures: List of departures to limit.
            stop_config: Stop configuration.

        Returns:
            Limited list of departures.
        """
        max_per_direction = stop_config.max_departures_per_stop or 20
        return departures[:max_per_direction]

    def _filter_and_limit_departures(
        self,
        departures: list[Departure],
        stop_config: StopConfiguration,
        reference_time_utc: datetime | None = None,
    ) -> list[Departure]:
        """Filter and limit departures based on leeway, max hours in advance, route limits, and direction limits.

        Args:
            departures: List of departures to filter and limit.
            stop_config: Stop configuration with filtering and limiting parameters.
            reference_time_utc: Reference time for leeway filtering.

        Returns:
            Filtered and limited list of departures.
        """
        departures = self._filter_by_stop_point(departures, stop_config)
        departures = self._filter_by_platform(departures, stop_config)
        departures = self._filter_by_leeway(departures, stop_config, reference_time_utc)
        departures = self._filter_by_max_hours(departures, stop_config)
        departures = self._limit_by_route(departures, stop_config)
        return self._limit_by_stop(departures, stop_config)

    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode text for consistent matching (handles ä, ö, ü, ß, etc.)."""
        # Normalize to NFC (composed form) to ensure consistent representation
        # This handles cases where the same character might be represented differently
        # (e.g., ä as single character vs a + combining diaeresis)
        return unicodedata.normalize("NFC", text).lower()

    def _matches_departure(self, departure: Departure, patterns: list[str]) -> bool:
        """Check if a departure matches any of the given patterns.

        Simple substring matching: pattern matches if it appears in the search text.
        Search text is "{transport_type} {line} {destination}" (normalized to lowercase).

        Examples:
        - "U9 Bundesplatz" matches line="U9" destination="S+U Bundesplatz (Berlin)"
        - "U 9 Bundesplatz" matches line="U 9" destination="Bundesplatz (S+U), Berlin"
        - "Bus 59 Giesing" matches transport_type="Bus" line="59" destination="Giesing Bahnhof"
        - "Messestadt" matches any departure with "Messestadt" in destination
        """
        # Build search text: "{transport_type} {line} {destination}"
        search_text = self._normalize_unicode(
            f"{departure.transport_type} {departure.line} {departure.destination}"
        )

        for pattern in patterns:
            pattern_normalized = self._normalize_unicode(pattern.strip())
            if pattern_normalized in search_text:
                return True

        return False
