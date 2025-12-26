"""Departure grouping service."""

import logging
import re
import unicodedata
from datetime import UTC, datetime, timedelta

from mvg_departures.domain.models.departure import Departure
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
    ) -> list[tuple[str, list[Departure]]]:
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

        # Pass VBB API duration if this is a VBB stop
        duration_minutes = 60  # Default
        if stop_config.api_provider == "vbb":
            duration_minutes = stop_config.vbb_api_duration_minutes

        departures = await self._departure_repository.get_departures(
            base_station_id,
            limit=fetch_limit,
            offset_minutes=0,
            transport_types=None,
            duration_minutes=duration_minutes,
        )

        return self.group_departures(departures, stop_config)

    def group_departures(
        self, departures: list[Departure], stop_config: StopConfiguration
    ) -> list[tuple[str, list[Departure]]]:
        """Group pre-fetched departures by configured directions.

        This method allows grouping departures that were already fetched,
        enabling shared fetching across multiple routes.

        Args:
            departures: Pre-fetched list of departures to group.
            stop_config: Stop configuration with direction mappings and limits.

        Returns:
            List of tuples (direction_name, departures) for this stop.
        """
        # Group departures by direction first
        direction_groups: dict[str, list[Departure]] = {}
        ungrouped: list[Departure] = []

        # Filter out blacklisted departures first
        if stop_config.exclude_destinations:
            initial_count = len(departures)
            departures = [
                d
                for d in departures
                if not self._matches_departure(d, stop_config.exclude_destinations)
            ]
            filtered_count = initial_count - len(departures)
            if filtered_count > 0:
                logger.debug(
                    f"Filtered out {filtered_count} blacklisted departures for {stop_config.station_name}"
                )

        # Log what we're trying to match
        if not stop_config.direction_mappings:
            logger.warning(f"No direction_mappings configured for {stop_config.station_name}")
        logger.debug(
            f"Processing {len(departures)} departures for {stop_config.station_name} with {len(stop_config.direction_mappings)} direction mappings"
        )

        for departure in departures:
            matched = False
            for direction_name, patterns in stop_config.direction_mappings.items():
                if self._matches_departure(departure, patterns):
                    if direction_name not in direction_groups:
                        direction_groups[direction_name] = []
                    direction_groups[direction_name].append(departure)
                    matched = True
                    break

            if not matched:
                ungrouped.append(departure)
                # Log unmatched departures
                logger.debug(
                    f"Unmatched departure for {stop_config.station_name}: {departure.transport_type} {departure.line} -> {departure.destination}"
                )

        # Sort departures within each group by time (datetime objects, not display strings)
        # This ensures "<1m" (0-59 seconds) sorts before "1m" (60-119 seconds), etc.
        for direction_name in direction_groups:
            direction_groups[direction_name].sort(key=lambda d: d.time)
            direction_groups[direction_name] = self._filter_and_limit_departures(
                direction_groups[direction_name], stop_config
            )

        if ungrouped:
            ungrouped.sort(key=lambda d: d.time)
            ungrouped = self._filter_and_limit_departures(ungrouped, stop_config)

        # Build result list with only directions that have departures
        # Preserve the order from the config file (direction_mappings)
        # Don't show empty direction groups - if show_ungrouped is false and no matches,
        # the stop will be shown as "no departures" at the bottom
        result = []
        # Iterate through direction_mappings in config order
        for direction_name in stop_config.direction_mappings:
            if direction_name in direction_groups:
                result.append((direction_name, direction_groups[direction_name]))

        # Add ungrouped departures if configured to show them (whitelist mode)
        # Only add ungrouped group if show_ungrouped is True AND there are ungrouped departures
        if stop_config.show_ungrouped and ungrouped:
            ungrouped_label = stop_config.ungrouped_title or "Other"
            result.append((ungrouped_label, ungrouped))

        return result

    def _filter_and_limit_departures(
        self, departures: list[Departure], stop_config: StopConfiguration
    ) -> list[Departure]:
        """Filter and limit departures based on leeway, max hours in advance, route limits, and direction limits.

        Args:
            departures: List of departures to filter and limit.
            stop_config: Stop configuration with filtering and limiting parameters.

        Returns:
            Filtered and limited list of departures.
        """
        # Filter by stop point if station_id is a stop_point_global_id (format: de:09162:1108:X:X)
        # Check if station_id has the stop point format (contains :X:X pattern)
        station_id_parts = stop_config.station_id.split(":")
        if len(station_id_parts) >= 5 and station_id_parts[-1] == station_id_parts[-2]:
            # station_id is a stop_point_global_id (e.g., "de:09162:1108:1:1")
            # Filter to only show departures from this specific stop point
            stop_point_global_id = stop_config.station_id
            initial_count = len(departures)
            available_stop_points = {
                d.stop_point_global_id for d in departures if d.stop_point_global_id is not None
            }
            departures = [
                d
                for d in departures
                if d.stop_point_global_id is not None
                and d.stop_point_global_id == stop_point_global_id
            ]
            filtered_count = len(departures)
            if initial_count > 0 and filtered_count == 0:
                logger.warning(
                    f"Filtered {initial_count} departures by stop_point_global_id={stop_point_global_id}, "
                    f"but none matched. Available stop_point_global_ids: {available_stop_points}"
                )

        # Filter by platform if platform_filter is set
        # Platform can be stored as int or str (e.g., 9, "9", "Pos. 9", "2 (U9)")
        # We match if the platform string contains the filter number as a standalone word or after "Pos."/"Platform"
        # But NOT as part of a line name like "U9" (e.g., "Platform 2 (U9)" should NOT match platform_filter=9)
        # If platform_filter_routes is set, only apply to those specific routes
        if stop_config.platform_filter is not None:
            initial_count = len(departures)
            available_platforms = {d.platform for d in departures if d.platform is not None}
            platform_filter_str = str(stop_config.platform_filter)
            # Pattern to match: "Pos. 9", "Platform 9", "9", or standalone "9" (with word boundaries)
            # But NOT "U9" or "2 (U9)" where 9 is part of a line name
            import re

            platform_pattern = re.compile(
                r"(?:^|\s|Pos\.|Platform\s)" + re.escape(platform_filter_str) + r"(?:\s|$|\)|,)"
            )

            filtered_departures = []
            for d in departures:
                # Check if this route should be filtered
                should_filter = (
                    not stop_config.platform_filter_routes  # Empty list = filter all routes
                    or d.line in stop_config.platform_filter_routes  # Filter only specified routes
                )

                if not should_filter:
                    # Don't filter this route, include it
                    filtered_departures.append(d)
                elif d.platform is not None and (
                    # Exact match (int or str)
                    d.platform == stop_config.platform_filter
                    or d.platform == platform_filter_str
                    # String matches pattern (e.g., "Pos. 9", "Platform 9", but not "U9")
                    or (isinstance(d.platform, str) and platform_pattern.search(d.platform))
                ):
                    # Platform matches, include it
                    filtered_departures.append(d)

            departures = filtered_departures
            filtered_count = len(departures)
            if initial_count > 0 and filtered_count == 0:
                logger.warning(
                    f"Filtered {initial_count} departures by platform={stop_config.platform_filter}, "
                    f"but none matched. Available platforms: {available_platforms}"
                )

        # Filter out departures that are too soon FIRST, so we only count departures that will be shown
        if stop_config.departure_leeway_minutes > 0:
            cutoff_time = datetime.now(UTC) + timedelta(
                minutes=stop_config.departure_leeway_minutes
            )
            departures = [d for d in departures if d.time >= cutoff_time]

        # Filter out departures that are too far in the future
        # Only apply if >= 1 (values < 1 or None are treated as unfiltered)
        if stop_config.max_hours_in_advance is not None and stop_config.max_hours_in_advance >= 1:
            max_time = datetime.now(UTC) + timedelta(hours=stop_config.max_hours_in_advance)
            departures = [d for d in departures if d.time <= max_time]

        # Limit each route to max_departures_per_route
        # (only counting departures that passed the leeway filter)
        max_per_route = stop_config.max_departures_per_route or 2
        route_counts: dict[str, int] = {}
        route_limited_departures: list[Departure] = []
        for departure in departures:
            route_key = departure.line
            count = route_counts.get(route_key, 0)
            if count < max_per_route:
                route_limited_departures.append(departure)
                route_counts[route_key] = count + 1

        # Limit to max_departures_per_stop
        # (only counting departures that passed the leeway filter)
        max_per_direction = stop_config.max_departures_per_stop or 20
        return route_limited_departures[:max_per_direction]

    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode text for consistent matching (handles ä, ö, ü, ß, etc.)."""
        # Normalize to NFC (composed form) to ensure consistent representation
        # This handles cases where the same character might be represented differently
        # (e.g., ä as single character vs a + combining diaeresis)
        return unicodedata.normalize("NFC", text).lower()

    def _matches_departure(self, departure: Departure, patterns: list[str]) -> bool:
        """Check if a departure matches any of the given patterns.

        Matching is done per route+destination combination:
        - Route + destination: "U2 Messestadt" (matches U2 going to Messestadt specifically)
        - Route + destination: "Bus 59 Giesing" (matches Bus 59 going to Giesing specifically)
        - Transport type + route + destination: "S-Bahn S5 Aying" (matches S-Bahn S5 going to Aying)

        Patterns can also be:
        - Route only: "U2" (matches any destination for U2 route)
        - Destination only: "Messestadt" (matches any route going to Messestadt)
        """
        # Normalize Unicode for consistent matching
        destination_normalized = self._normalize_unicode(departure.destination)
        line_normalized = self._normalize_unicode(departure.line)
        transport_type_normalized = self._normalize_unicode(departure.transport_type)

        # Create route identifiers for matching (using normalized values)
        route_line = line_normalized  # e.g., "u2", "59", "s5"
        route_full = f"{transport_type_normalized} {line_normalized}"  # e.g., "u-bahn u2", "bus 59", "s-bahn s5"

        for pattern in patterns:
            pattern_normalized = self._normalize_unicode(pattern.strip())

            # Split pattern into words to handle different formats
            pattern_words = pattern_normalized.split()

            if len(pattern_words) >= 2:
                # Pattern has multiple parts - try to match as route + destination
                # Need to identify where route ends and destination begins
                # Patterns can be:
                # 1. "U2 Messestadt" -> route="u2", dest="messestadt"
                # 2. "Bus 59 Giesing" -> route="bus 59", dest="giesing"
                # 3. "139 Messestadt West" -> route="139", dest="messestadt west"
                # 4. "Bus 54 Lorettoplatz" -> route="bus 54", dest="lorettoplatz"
                # 5. "S5 Aying" -> route="s5", dest="aying"
                # 6. "S-Bahn S5 Aying" -> route="s-bahn s5", dest="aying"

                # Try to match route from the beginning
                # Check if first word matches line number
                route_matched = False
                dest_start_idx = 1

                # Case 1: First word is the line number (e.g., "139 Messestadt West", "S5 Aying")
                if pattern_words[0] == route_line:
                    route_matched = True
                    dest_start_idx = 1
                # Case 2: First two words are transport type + line (e.g., "Bus 54 Lorettoplatz", "S-Bahn S5 Aying")
                elif len(pattern_words) >= 2:
                    first_two = " ".join(pattern_words[0:2])
                    if first_two == route_full or (
                        pattern_words[1] == route_line
                        and pattern_words[0] in transport_type_normalized
                    ):
                        route_matched = True
                        dest_start_idx = 2

                if route_matched and dest_start_idx < len(pattern_words):
                    # Destination is everything after the route
                    dest_part = " ".join(pattern_words[dest_start_idx:])
                    # Use Unicode-normalized matching for destinations
                    if self._matches_text_normalized(destination_normalized, dest_part):
                        return True
                # Don't fall back to destination-only matching when route doesn't match!
                # This prevents false matches like "N75 Ostbahnhof" matching "59 Giesing Bahnhof"
                # If route doesn't match, the pattern doesn't match
            else:
                # Single word - try as route-only or destination-only
                pattern_single = pattern_words[0]

                # Try matching as route only - EXACT match only (no substring matching)
                # Use normalized values for comparison
                route_matches = pattern_single in (route_line, route_full)

                if route_matches:
                    # Route matches exactly - match any destination for this route
                    return True

                # Try matching as destination only - use word-boundary matching with Unicode normalization
                if self._matches_text_normalized(destination_normalized, pattern_single):
                    # Destination matches - match any route to this destination
                    return True

        return False

    def _matches_text(self, text: str, pattern: str) -> bool:
        """Check if text matches pattern (exact match or word-boundary match).

        For multi-word patterns, requires exact phrase match.
        For single-word patterns, requires whole-word match.
        This prevents "Ostbahnhof" from matching "Giesing Bahnhof"
        """
        return self._matches_text_normalized(text, pattern)

    def _matches_text_normalized(self, text: str, pattern: str) -> bool:
        """Check if text matches pattern with Unicode normalization.

        Normalizes both text and pattern to handle Unicode characters consistently
        (e.g., ä, ö, ü, ß will match regardless of their Unicode representation).
        """
        # Normalize Unicode for consistent matching
        text_normalized = self._normalize_unicode(text)
        pattern_normalized = self._normalize_unicode(pattern)

        if pattern_normalized == text_normalized:
            return True

        # For multi-word patterns, require exact phrase match
        if " " in pattern_normalized:
            if pattern_normalized == text_normalized:
                return True
            # Check if pattern appears as a phrase (with word boundaries)
            pattern_escaped = re.escape(pattern_normalized)
            return bool(re.search(r"\b" + pattern_escaped + r"\b", text_normalized))

        # For single-word patterns, use word-boundary matching
        try:
            pattern_escaped = re.escape(pattern_normalized)
            if re.search(r"\b" + pattern_escaped + r"\b", text_normalized):
                return True
        except re.error:
            pass
        return False
