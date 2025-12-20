"""Application services (use cases) for departure management."""

import re
from typing import TYPE_CHECKING

from mvg_departures.domain.models import Departure, StopConfiguration

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
        """Get departures for a stop, grouped by configured directions."""
        departures = await self._departure_repository.get_departures(
            stop_config.station_id, limit=stop_config.max_departures_per_stop or 20
        )

        # Group departures by direction first
        direction_groups: dict[str, list[Departure]] = {}
        ungrouped: list[Departure] = []

        # Debug: log what we're trying to match
        import sys
        if not stop_config.direction_mappings:
            print(f"WARNING: No direction_mappings configured for {stop_config.station_name}", file=sys.stderr)
        
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
                # Debug: log unmatched departures
                #print(f"DEBUG: Unmatched departure: {departure.transport_type} {departure.line} -> {departure.destination}", file=sys.stderr)

        # Sort departures within each group by time (datetime objects, not display strings)
        # This ensures "<1m" (0-59 seconds) sorts before "1m" (60-119 seconds), etc.
        for direction_name in direction_groups:
            direction_groups[direction_name].sort(key=lambda d: d.time)
        
        if ungrouped:
            ungrouped.sort(key=lambda d: d.time)

        # Build result list with only directions that have departures
        # Don't show empty direction groups - if show_ungrouped is false and no matches, 
        # the stop will be shown as "no departures" at the bottom
        result = []
        for direction_name in sorted(direction_groups.keys()):
            result.append((direction_name, direction_groups[direction_name]))

        # Add ungrouped departures if configured to show them (whitelist mode)
        # Only add "Other" group if show_ungrouped is True AND there are ungrouped departures
        if stop_config.show_ungrouped and ungrouped:
            result.append(("Other", ungrouped))

        return result

    def _matches_departure(
        self, departure: Departure, patterns: list[str]
    ) -> bool:
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
                    if first_two == route_full or (pattern_words[1] == route_line and pattern_words[0] in transport_type_lower):
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
                # Single word - try as route-only or destination-only (fallback)
                pattern_single = pattern_words[0]
                
                # Try matching as route only
                route_matches = (
                    pattern_single == route_line
                    or pattern_single == route_full
                    or route_line.endswith(pattern_single)
                    or route_full.endswith(pattern_single)
                    or pattern_single in route_line
                    or pattern_single in route_full
                )
                
                if route_matches:
                    # Route matches - match any destination for this route
                    return True
                
                # Try matching as destination only
                if self._matches_text(destination_lower, pattern_single):
                    # Destination matches - match any route to this destination
                    return True
        
        return False
    
    def _matches_text(self, text: str, pattern: str) -> bool:
        """Check if text matches pattern (exact match or word-boundary match)."""
        if pattern == text:
            return True
        # Check if pattern matches as whole words (word boundaries)
        # This prevents "Ostbahnhof" from matching "Giesing Bahnhof"
        try:
            # Use word boundaries to ensure we match whole words, not substrings
            pattern_escaped = re.escape(pattern)
            if re.search(r'\b' + pattern_escaped + r'\b', text, re.IGNORECASE):
                return True
        except re.error:
            pass
        return False

