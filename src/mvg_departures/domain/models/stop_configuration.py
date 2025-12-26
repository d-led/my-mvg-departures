"""Stop configuration domain model."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StopConfiguration:
    """Configuration for a stop to monitor."""

    station_id: str
    station_name: str
    direction_mappings: dict[str, list[str]]  # direction_name -> list of patterns (whitelist)
    # Patterns can be: destination ("Messestadt"), route ("U2", "Bus 59"), or route+destination ("U2 Messestadt")
    max_departures_per_stop: int = (
        20  # Maximum departures to display per direction group (not total)
    )
    max_departures_per_route: int = (
        2  # Maximum departures to display per route (line) within each direction group
    )
    show_ungrouped: bool = (
        True  # If False, only show departures matching direction_mappings (strict whitelist)
    )
    ungrouped_title: str | None = (
        None  # Custom title for ungrouped departures. If None, defaults to "Other"
    )
    departure_leeway_minutes: int = (
        0  # Leeway in minutes: departures earlier than now + leeway are filtered out before counting for limits
    )
    max_hours_in_advance: float | None = (
        None  # Maximum hours in advance: departures more than this many hours in the future are filtered out. If < 1 or unset, no filtering is applied.
    )
    random_header_colors: bool | None = (
        None  # Enable hash-based pastel colors for headers. None means inherit from route/global config.
    )
    header_background_brightness: float | None = (
        None  # Brightness adjustment for random header colors (0.0-1.0). None means inherit from route/global config.
    )
    random_color_salt: int | None = (
        None  # Salt value for hash-based color generation. None means inherit from route/global config.
    )
    exclude_destinations: list[str] = field(
        default_factory=list
    )  # Blacklist patterns to exclude from display. Supports route ("54"), destination ("Messestadt"), or route+destination ("54 Münchner Freiheit")
    api_provider: str = "mvg"  # API provider: "mvg" (default) or "hafas" (optional)
    hafas_profile: str | None = (
        None  # HAFAS profile when api_provider="hafas" (e.g., "db", "bvg", "vvo"). None = auto-detect
    )
    max_departures_fetch: int = (
        50  # Maximum number of departures to fetch from API before grouping/filtering
    )
    platform_filter: int | None = (
        None  # Filter departures to only show those from this platform number (e.g., 9). None = no filtering.
    )
    platform_filter_routes: list[str] = field(
        default_factory=list
    )  # List of route/line names to apply platform_filter to (e.g., ["249"]). If empty, applies to all routes.
    vbb_api_duration_minutes: int = (
        60  # VBB API duration in minutes (how far ahead to fetch departures). Default: 60 minutes. Increase for infrequent routes.
    )
