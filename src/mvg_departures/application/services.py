"""Application services (use cases) for departure management."""

import logging
import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from mvg_departures.domain.models import Departure, StopConfiguration

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mvg_departures.domain.ports import DepartureRepository


class DepartureGroupingService:
    """Service for grouping departures by configured directions."""

    def __init__(self, departure_repository: "DepartureRepository") -> None:
        """Initialize with a departure repository."""
        self._departure_repository = departure_repository

    async def get_grouped_departures(
        self, stop_config: StopConfiguration
    ) -> list[tuple[str, list[Departure]]]:
        """Get departures for a stop, grouped by configured directions.

        Fetches a reasonable number of departures from the API, then groups them
        by direction and limits each direction group to max_departures_per_stop.
        """
        # Fetch more departures than needed to ensure we have enough for all directions
        # Use a higher limit (50) to get a good sample, then limit per direction
        fetch_limit = 50
        departures = await self._departure_repository.get_departures(
            stop_config.station_id, limit=fetch_limit
        )

        # Group departures by direction first
        direction_groups: dict[str, list[Departure]] = {}
        ungrouped: list[Departure] = []

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
            # Limit each route within the direction group to max_departures_per_route
            max_per_route = stop_config.max_departures_per_route or 2
            route_counts: dict[str, int] = {}
            filtered_departures: list[Departure] = []
            for departure in direction_groups[direction_name]:
                route_key = departure.line
                count = route_counts.get(route_key, 0)
                if count < max_per_route:
                    filtered_departures.append(departure)
                    route_counts[route_key] = count + 1
            direction_groups[direction_name] = filtered_departures
            # Then limit each direction group to max_departures_per_stop
            max_per_direction = stop_config.max_departures_per_stop or 20
            direction_groups[direction_name] = direction_groups[direction_name][:max_per_direction]
            # Filter out departures that are too soon (after limits are applied, so counts aren't affected)
            if stop_config.departure_leeway_minutes > 0:
                cutoff_time = datetime.now() + timedelta(
                    minutes=stop_config.departure_leeway_minutes
                )
                direction_groups[direction_name] = [
                    d for d in direction_groups[direction_name] if d.time >= cutoff_time
                ]

        if ungrouped:
            ungrouped.sort(key=lambda d: d.time)
            # Limit each route within ungrouped to max_departures_per_route
            max_per_route = stop_config.max_departures_per_route or 2
            ungrouped_route_counts: dict[str, int] = {}
            filtered_ungrouped: list[Departure] = []
            for departure in ungrouped:
                route_key = departure.line
                count = ungrouped_route_counts.get(route_key, 0)
                if count < max_per_route:
                    filtered_ungrouped.append(departure)
                    ungrouped_route_counts[route_key] = count + 1
            ungrouped = filtered_ungrouped
            # Also limit ungrouped departures
            max_per_direction = stop_config.max_departures_per_stop or 20
            ungrouped = ungrouped[:max_per_direction]
            # Filter out departures that are too soon (after limits are applied, so counts aren't affected)
            if stop_config.departure_leeway_minutes > 0:
                cutoff_time = datetime.now() + timedelta(
                    minutes=stop_config.departure_leeway_minutes
                )
                ungrouped = [d for d in ungrouped if d.time >= cutoff_time]

        # Build result list with only directions that have departures
        # Preserve the order from the config file (direction_mappings)
        # Don't show empty direction groups - if show_ungrouped is false and no matches,
        # the stop will be shown as "no departures" at the bottom
        result = []
        # Iterate through direction_mappings in config order
        for direction_name in stop_config.direction_mappings.keys():
            if direction_name in direction_groups:
                result.append((direction_name, direction_groups[direction_name]))

        # Add ungrouped departures if configured to show them (whitelist mode)
        # Only add "Other" group if show_ungrouped is True AND there are ungrouped departures
        if stop_config.show_ungrouped and ungrouped:
            result.append(("Other", ungrouped))

        return result

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
        destination_lower = departure.destination.lower()
        line_lower = departure.line.lower()
        transport_type_lower = departure.transport_type.lower()

        # Create route identifiers for matching
        route_line = line_lower  # e.g., "u2", "59"
        route_full = f"{transport_type_lower} {line_lower}"  # e.g., "u-bahn u2", "bus 59"

        for pattern in patterns:
            pattern_lower = pattern.lower().strip()

            # Split pattern into words to handle different formats
            pattern_words = pattern_lower.split()

            if len(pattern_words) >= 2:
                # Pattern has multiple parts - try to match as route + destination
                # Need to identify where route ends and destination begins
                # Patterns can be:
                # 1. "U2 Messestadt" -> route="u2", dest="messestadt"
                # 2. "Bus 59 Giesing" -> route="bus 59", dest="giesing"
                # 3. "139 Messestadt West" -> route="139", dest="messestadt west"
                # 4. "Bus 54 Lorettoplatz" -> route="bus 54", dest="lorettoplatz"

                # Try to match route from the beginning
                # Check if first word matches line number
                route_matched = False
                dest_start_idx = 1

                # Case 1: First word is the line number (e.g., "139 Messestadt West")
                if pattern_words[0] == route_line:
                    route_matched = True
                    dest_start_idx = 1
                # Case 2: First two words are transport type + line (e.g., "Bus 54 Lorettoplatz")
                elif len(pattern_words) >= 2:
                    first_two = " ".join(pattern_words[0:2])
                    if first_two == route_full or (
                        pattern_words[1] == route_line and pattern_words[0] in transport_type_lower
                    ):
                        route_matched = True
                        dest_start_idx = 2

                if route_matched and dest_start_idx < len(pattern_words):
                    # Destination is everything after the route
                    dest_part = " ".join(pattern_words[dest_start_idx:])
                    if self._matches_text(destination_lower, dest_part):
                        return True
                # Don't fall back to destination-only matching when route doesn't match!
                # This prevents false matches like "N75 Ostbahnhof" matching "59 Giesing Bahnhof"
                # If route doesn't match, the pattern doesn't match
            else:
                # Single word - try as route-only or destination-only
                pattern_single = pattern_words[0]

                # Try matching as route only - EXACT match only (no substring matching)
                route_matches = pattern_single == route_line or pattern_single == route_full

                if route_matches:
                    # Route matches exactly - match any destination for this route
                    return True

                # Try matching as destination only - use word-boundary matching
                if self._matches_text(destination_lower, pattern_single):
                    # Destination matches - match any route to this destination
                    return True

        return False

    def _matches_text(self, text: str, pattern: str) -> bool:
        """Check if text matches pattern (exact match or word-boundary match).

        For multi-word patterns, requires exact phrase match.
        For single-word patterns, requires whole-word match.
        This prevents "Ostbahnhof" from matching "Giesing Bahnhof"
        """
        if pattern == text:
            return True

        # For multi-word patterns, require exact phrase match
        if " " in pattern:
            pattern_lower = pattern.lower()
            text_lower = text.lower()
            if pattern_lower == text_lower:
                return True
            # Check if pattern appears as a phrase (with word boundaries)
            pattern_escaped = re.escape(pattern_lower)
            if re.search(r"\b" + pattern_escaped + r"\b", text_lower):
                return True
            return False

        # For single-word patterns, use word-boundary matching
        try:
            pattern_escaped = re.escape(pattern.lower())
            if re.search(r"\b" + pattern_escaped + r"\b", text.lower()):
                return True
        except re.error:
            pass
        return False
