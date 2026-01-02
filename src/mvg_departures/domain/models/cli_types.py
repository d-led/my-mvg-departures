"""CLI-specific domain types for configuration and station information."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigPattern:
    """Configuration pattern for route matching.

    Represents a pattern that can be used in direction_mappings to match
    departures by route and destination.
    """

    pattern: str  # Line + destination pattern (e.g., "139 Messestadt West")
    full_pattern: (
        str  # Transport type + line + destination pattern (e.g., "Bus 139 Messestadt West")
    )
    destination: str  # Destination name (e.g., "Messestadt West")


@dataclass(frozen=True)
class StopPointRouteInfo:
    """Information about a route and destination at a specific stop point.

    Associates a route and destination with optional platform information
    for a physical stop point.
    """

    route_key: str  # Route identifier (e.g., "Bus 139")
    destination: str  # Destination name
    platform_info: str | None  # Optional platform information (e.g., "Platform 9")


@dataclass(frozen=True)
class DestinationPlatformInfo:
    """Information about a destination and its platform.

    Associates a destination with platform information for display purposes.
    """

    destination: str  # Destination name
    platform_info: str  # Platform information (e.g., "Platform 9")
