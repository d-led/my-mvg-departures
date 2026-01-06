"""CLI helpers for configuring MVG departures."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import argparse

import aiohttp
from mvg import MvgApi

from mvg_departures.adapters.api_request_logger import log_api_request
from mvg_departures.domain.models.cli_types import (
    ConfigPattern,
    DestinationPlatformInfo,
    StopPointRouteInfo,
)


@dataclass(frozen=True)
class RouteEntryConfig:
    """Configuration for initializing a route entry.

    Groups together route identification and display information.
    """

    route_key: str
    line: str
    transport_type: str
    icon: str


@dataclass(frozen=True)
class StationResultData:
    """Data required to build a station result.

    Groups together all the data structures needed to build the final station result.
    """

    station_id: str
    routes: dict[str, set[str]]
    route_details: dict[str, dict[str, Any]]
    stop_point_mapping: dict[str, Any]
    departures: list[dict[str, Any]]
    routes_from_endpoint: dict[str, Any] | None


@dataclass(frozen=True)
class DeparturesDisplayContext:
    """Context for displaying departures header and content."""

    station_name: str
    station_id: str
    departures_count: int
    filter_stop_point: str | None = None
    total_before_filter: int | None = None


async def _try_direct_search(query: str, session: aiohttp.ClientSession) -> dict[str, Any] | None:
    """Try direct search for a station."""
    try:
        result = await MvgApi.station_async(query, session=session)
        return result if result else None
    except Exception:
        return None


async def _try_search_with_munich(
    query: str, session: aiohttp.ClientSession
) -> dict[str, Any] | None:
    """Try search with 'München' appended if not already present."""
    if "München" in query or "Munich" in query:
        return None

    try:
        result = await MvgApi.station_async(f"{query}, München", session=session)
        return result if result else None
    except Exception:
        return None


def _filter_stations_by_query(
    all_stations: list[dict[str, Any]], query: str, existing_ids: set[str]
) -> list[dict[str, Any]]:
    """Filter stations by query string."""
    query_lower = query.lower()
    matches = [
        s
        for s in all_stations
        if query_lower in s.get("name", "").lower() or query_lower in s.get("place", "").lower()
    ]
    return [match for match in matches[:20] if match.get("id") not in existing_ids]


async def _try_search_all_stations(
    query: str, session: aiohttp.ClientSession, existing_ids: set[str]
) -> list[dict[str, Any]]:
    """Try to get all stations and filter by query."""
    if not hasattr(MvgApi, "stations_async"):
        return []

    try:
        all_stations = await MvgApi.stations_async(session=session)
        if not all_stations:
            return []
        return _filter_stations_by_query(all_stations, query, existing_ids)
    except Exception:
        return []


async def search_stations(query: str) -> list[dict[str, Any]]:
    """Search for stations by name."""
    async with aiohttp.ClientSession() as session:
        results: list[dict[str, Any]] = []

        direct_result = await _try_direct_search(query, session)
        if direct_result:
            results.append(direct_result)

        munich_result = await _try_search_with_munich(query, session)
        if munich_result and munich_result not in results:
            results.append(munich_result)

        existing_ids: set[str] = {str(r.get("id", "")) for r in results if r.get("id")}
        all_station_matches = await _try_search_all_stations(query, session, existing_ids)
        results.extend(all_station_matches)

        return results


def _normalize_transport_type(transport_type: str) -> str:
    """Normalize transport type from API format to display format."""
    if not transport_type:
        return transport_type

    type_map = {
        "BUS": "Bus",
        "TRAM": "Tram",
        "UBAHN": "U-Bahn",
        "SBAHN": "S-Bahn",
        "REGIONAL_BUS": "Bus",
    }
    return type_map.get(transport_type, transport_type)


def _extract_list_field(line_info: dict[str, Any], field_name: str) -> list[str]:
    """Extract and convert list field to string list."""
    field_value = line_info.get(field_name)
    if isinstance(field_value, list):
        return [str(d) for d in field_value]
    return []


def _extract_single_field(line_info: dict[str, Any], field_name: str) -> list[str]:
    """Extract single field and return as list."""
    if field_name in line_info:
        return [str(line_info[field_name])]
    return []


def _extract_destinations_from_line_info(line_info: dict[str, Any]) -> list[str]:
    """Extract destinations from line info in various possible formats."""
    if result := _extract_list_field(line_info, "destinations"):
        return result
    if result := _extract_single_field(line_info, "destination"):
        return result
    if result := _extract_list_field(line_info, "directions"):
        return result
    if result := _extract_single_field(line_info, "direction"):
        return result
    return []


def _normalize_destination_name(dest: Any) -> str:
    """Normalize destination name from various formats."""
    if isinstance(dest, dict):
        name = dest.get("name") or dest.get("destination")
        return str(name) if name is not None else ""
    return str(dest)


def _extract_line_info(line_info: dict[str, Any]) -> tuple[str, str, str]:
    """Extract line, transport type, and icon from line info."""
    line = str(line_info.get("label", line_info.get("line", line_info.get("number", ""))))
    transport_type = line_info.get("transportType", line_info.get("type", ""))
    icon = line_info.get("icon", line_info.get("symbol", ""))
    transport_type = _normalize_transport_type(transport_type)
    return line, transport_type, icon


def _extract_lines_from_dict(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract lines list from dictionary response."""
    lines = data.get("lines", [])
    if not lines:
        lines = data.get("routes", data.get("data", []))
    if isinstance(lines, list):
        return [item for item in lines if isinstance(item, dict)]
    return []


def _parse_routes_response(data: Any) -> list[dict[str, Any]]:
    """Parse routes response and extract lines list."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    if isinstance(data, dict):
        return _extract_lines_from_dict(data)

    return []


def _initialize_route_entry(
    routes: dict[str, set[str]],
    route_details: dict[str, dict[str, Any]],
    config: RouteEntryConfig,
) -> None:
    """Initialize a new route entry."""
    if config.route_key not in routes:
        routes[config.route_key] = set()
        route_details[config.route_key] = {
            "line": config.line,
            "transport_type": config.transport_type,
            "icon": config.icon,
        }


def _add_destinations_to_route(
    routes: dict[str, set[str]], route_key: str, destinations_raw: list[str]
) -> None:
    """Add destinations to a route."""
    for dest in destinations_raw:
        dest_name = _normalize_destination_name(dest)
        if dest_name:
            routes[route_key].add(dest_name)


def _build_routes_dict(
    lines: list[dict[str, Any]],
) -> tuple[dict[str, set[str]], dict[str, dict[str, Any]]]:
    """Build routes dictionary from parsed lines.

    Args:
        lines: List of line information dictionaries.

    Returns:
        Tuple of (routes, route_details).
    """
    routes: dict[str, set[str]] = {}
    route_details: dict[str, dict[str, Any]] = {}

    for line_info in lines:
        if not isinstance(line_info, dict):
            continue

        line, transport_type, icon = _extract_line_info(line_info)
        destinations_raw = _extract_destinations_from_line_info(line_info)

        route_key = f"{transport_type} {line}"
        config = RouteEntryConfig(
            route_key=route_key, line=line, transport_type=transport_type, icon=icon
        )
        _initialize_route_entry(routes, route_details, config)
        _add_destinations_to_route(routes, route_key, destinations_raw)

    return routes, route_details


def _build_routes_result(
    station_id: str,
    routes: dict[str, set[str]],
    route_details: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Build final routes result dictionary.

    Args:
        station_id: Station ID.
        routes: Dictionary mapping route keys to destination sets.
        route_details: Dictionary mapping route keys to route metadata.

    Returns:
        Routes result dictionary, or None if invalid.
    """
    if not routes:
        return None

    total_destinations = sum(len(destinations) for destinations in routes.values())
    if total_destinations == 0:
        return None

    return {
        "station": {
            "id": station_id,
            "name": station_id,
            "place": "München",
        },
        "routes": {
            route: {
                "destinations": sorted(destinations),
                **route_details[route],
            }
            for route, destinations in routes.items()
        },
        "source": "routes_endpoint",
    }


async def _process_routes_response(data: Any, station_id: str) -> dict[str, Any] | None:
    """Process routes API response and build result."""
    if not data:
        return None

    lines = _parse_routes_response(data)
    if not lines:
        return None

    routes, route_details = _build_routes_dict(lines)
    return _build_routes_result(station_id, routes, route_details)


def _get_mvg_routes_headers() -> dict[str, str]:
    """Get headers for MVG routes API request."""
    return {
        "accept": "application/json",
        "user-agent": "Mozilla/5.0",
    }


async def _handle_routes_response(
    response: aiohttp.ClientResponse, station_id: str
) -> dict[str, Any] | None:
    """Handle routes API response."""
    if response.status != 200:
        return None

    data = await response.json()
    return await _process_routes_response(data, station_id)


async def _get_routes_from_endpoint(
    station_id: str, session: aiohttp.ClientSession
) -> dict[str, Any] | None:
    """Get routes from the MVG routes endpoint."""
    try:
        url = f"https://www.mvg.de/api/bgw-pt/v3/lines/{station_id}"
        headers = _get_mvg_routes_headers()
        log_api_request("GET", url, headers=headers)
        async with session.get(url, headers=headers) as response:
            return await _handle_routes_response(response, station_id)
    except Exception:
        return None


def _extract_departure_fields(dep: dict[str, Any]) -> tuple[str, str, str, str, int | None]:
    """Extract fields from departure dictionary.

    Returns:
        Tuple of (line, destination, transport_type, stop_point_id, platform).
    """
    line = str(dep.get("label", dep.get("line", "")))
    destination = str(dep.get("destination", ""))
    transport_type = str(dep.get("transportType", dep.get("type", "")))
    stop_point_id = dep.get("stopPointGlobalId") or dep.get("stop_point_global_id") or ""
    platform = dep.get("platform")
    return line, destination, transport_type, stop_point_id, platform


def _ensure_mapping_entry(stop_point_mapping: dict[str, dict[str, Any]], mapping_key: str) -> None:
    """Ensure mapping entry exists for the given key."""
    if mapping_key not in stop_point_mapping:
        stop_point_mapping[mapping_key] = {
            "stop_points": set(),
            "platforms": set(),
            "platform_to_stop_point": {},
        }


def _add_stop_point_info(
    stop_point_mapping: dict[str, dict[str, Any]],
    mapping_key: str,
    stop_point_id: str,
    platform: int | None,
) -> None:
    """Add stop point and platform information to mapping."""
    if stop_point_id and stop_point_id.strip():
        stop_point_mapping[mapping_key]["stop_points"].add(stop_point_id)

    if platform is not None:
        stop_point_mapping[mapping_key]["platforms"].add(platform)
        platform_map = stop_point_mapping[mapping_key]["platform_to_stop_point"]
        if platform not in platform_map:
            platform_map[platform] = set()
        if stop_point_id and stop_point_id.strip():
            platform_map[platform].add(stop_point_id)


def _process_departure_for_stop_point_mapping(
    dep: dict[str, Any], stop_point_mapping: dict[str, dict[str, Any]]
) -> None:
    """Process a single departure to extract stop point and platform information."""
    line, destination, transport_type, stop_point_id, platform = _extract_departure_fields(dep)

    if not line or not destination:
        return

    transport_type = _normalize_transport_type(transport_type)
    route_key = f"{transport_type} {line}"
    mapping_key = f"{route_key}|{destination}"

    _ensure_mapping_entry(stop_point_mapping, mapping_key)
    _add_stop_point_info(stop_point_mapping, mapping_key, stop_point_id, platform)


def _process_departures_for_mapping(
    data: list[dict[str, Any]], stop_point_mapping: dict[str, dict[str, Any]]
) -> None:
    """Process departures list to build stop point mapping."""
    for dep in data:
        _process_departure_for_stop_point_mapping(dep, stop_point_mapping)


def _build_stop_point_mapping_url(station_id: str, limit: int) -> str:
    """Build URL for stop point mapping API request."""
    return (
        f"https://www.mvg.de/api/bgw-pt/v3/departures"
        f"?globalId={station_id}&limit={limit}&transportTypes=UBAHN,TRAM,SBAHN,BUS,REGIONAL_BUS,BAHN"
    )


def _process_stop_point_mapping_response(
    data: Any, stop_point_mapping: dict[str, dict[str, Any]]
) -> None:
    """Process stop point mapping API response."""
    if isinstance(data, list):
        _process_departures_for_mapping(data, stop_point_mapping)


async def _handle_stop_point_mapping_response(
    response: aiohttp.ClientResponse, stop_point_mapping: dict[str, dict[str, Any]]
) -> None:
    """Handle stop point mapping API response."""
    if response.status != 200:
        return

    data = await response.json()
    _process_stop_point_mapping_response(data, stop_point_mapping)


async def _get_stop_point_mapping(
    station_id: str, session: aiohttp.ClientSession, limit: int = 100
) -> dict[str, dict[str, Any]]:
    """Get mapping of route+destination to stop point IDs and platform info from raw API response."""
    stop_point_mapping: dict[str, dict[str, Any]] = {}

    try:
        url = _build_stop_point_mapping_url(station_id, limit)
        headers = _get_mvg_routes_headers()
        log_api_request("GET", url, headers=headers)
        async with session.get(url, headers=headers) as response:
            await _handle_stop_point_mapping_response(response, stop_point_mapping)
    except Exception:
        pass

    return stop_point_mapping


def _extract_route_from_departure(dep: dict[str, Any]) -> tuple[str, str, str, str]:
    """Extract route information from a departure."""
    line = dep.get("line", "")
    destination = dep.get("destination", "")
    transport_type = dep.get("type", "")
    icon = dep.get("icon", "")
    return line, destination, transport_type, icon


def _build_routes_from_departures(
    departures: list[dict[str, Any]],
) -> tuple[dict[str, set[str]], dict[str, dict[str, Any]]]:
    """Build routes dictionary from departures."""
    routes: dict[str, set[str]] = {}
    route_details: dict[str, dict[str, Any]] = {}

    for dep in departures:
        line, destination, transport_type, icon = _extract_route_from_departure(dep)
        route_key = f"{transport_type} {line}"

        if route_key not in routes:
            routes[route_key] = set()
            route_details[route_key] = {
                "line": line,
                "transport_type": transport_type,
                "icon": icon,
            }
        routes[route_key].add(destination)

    return routes, route_details


def _merge_route_details(
    routes: dict[str, set[str]],
    route_details: dict[str, dict[str, Any]],
    routes_from_endpoint: dict[str, Any] | None,
) -> None:
    """Merge route details from endpoint while keeping destinations from departures."""
    if not routes_from_endpoint:
        return

    routes_from_endpoint_data = routes_from_endpoint.get("routes", {})
    for route_key, endpoint_route_data in routes_from_endpoint_data.items():
        if route_key not in routes or not isinstance(endpoint_route_data, dict):
            continue

        route_details[route_key].update(
            {
                k: v
                for k, v in endpoint_route_data.items()
                if k != "destinations"  # Don't overwrite destinations
            }
        )


def _build_station_result(data: StationResultData) -> dict[str, Any]:
    """Build the final station result dictionary."""
    source = "departures_sampling" + (" + routes_endpoint" if data.routes_from_endpoint else "")

    return {
        "station": {
            "id": data.station_id,
            "name": data.station_id,  # MVG API might not return station name in departures
            "place": "München",
        },
        "routes": {
            route: {
                "destinations": sorted(destinations),
                **data.route_details[route],
            }
            for route, destinations in data.routes.items()
        },
        "stop_point_mapping": data.stop_point_mapping,
        "total_departures_found": len(data.departures),
        "source": source,
    }


async def _process_station_details(
    session: aiohttp.ClientSession, station_id: str, limit: int
) -> dict[str, Any] | None:
    """Process station details from API."""
    stop_point_mapping = await _get_stop_point_mapping(station_id, session, limit)
    routes_from_endpoint = await _get_routes_from_endpoint(station_id, session)

    departures = await MvgApi.departures_async(station_id, limit=limit, session=session)
    if not departures:
        return None

    routes, route_details = _build_routes_from_departures(departures)
    _merge_route_details(routes, route_details, routes_from_endpoint)

    data = StationResultData(
        station_id=station_id,
        routes=routes,
        route_details=route_details,
        stop_point_mapping=stop_point_mapping,
        departures=departures,
        routes_from_endpoint=routes_from_endpoint,
    )
    return _build_station_result(data)


async def get_station_details(station_id: str, limit: int = 100) -> dict[str, Any] | None:
    """Get detailed information about a station."""
    async with aiohttp.ClientSession() as session:
        try:
            return await _process_station_details(session, station_id, limit)
        except Exception as e:
            print(f"Error fetching station details: {e}", file=sys.stderr)
            return None


def _collect_all_patterns(config_patterns_by_route: dict[str, list[ConfigPattern]]) -> list[str]:
    """Collect all patterns from all routes."""
    all_patterns = []
    for patterns in config_patterns_by_route.values():
        all_patterns.extend([p.pattern for p in patterns])
    return all_patterns


def _collect_unique_destinations(
    config_patterns_by_route: dict[str, list[ConfigPattern]],
) -> list[str]:
    """Collect unique destinations from all patterns."""
    unique_destinations = set()
    for patterns in config_patterns_by_route.values():
        for config_pattern in patterns:
            unique_destinations.add(config_pattern.destination)
    return sorted(unique_destinations)


def _display_config_patterns_detailed(
    config_patterns_by_route: dict[str, list[ConfigPattern]],
) -> None:
    """Display config patterns with alternative format for list_routes."""
    if not config_patterns_by_route:
        return

    print("\n" + "=" * 70)
    print("Config patterns (copy these into your direction_mappings):")
    print("=" * 70)
    print("\n# Format: Patterns match 'line destination' or 'transport_type line destination'")
    print("# Examples: '139 Messestadt West' or 'Bus 139 Messestadt West'")
    print("\n# Grouped by route (recommended format: line + destination):")

    for route_key, patterns in sorted(config_patterns_by_route.items()):
        route_display = route_key.replace(" ", " ")
        print(f"\n# {route_display}:")
        for config_pattern in patterns:
            route_line = route_key.split()[-1] if route_key.split() else ""
            print(
                f'  "{config_pattern.pattern}"  # Matches: {route_line} -> {config_pattern.destination}'
            )

    print("\n# Alternative format (transport type + line + destination):")
    for route_key, patterns in sorted(config_patterns_by_route.items()):
        route_display = route_key.replace(" ", " ")
        print(f"\n# {route_display}:")
        for config_pattern in patterns:
            print(
                f'  "{config_pattern.full_pattern}"  # Matches: {route_key} -> {config_pattern.destination}'
            )

    print("\n# Flat list (line + destination format) - ready to paste:")
    all_patterns = _collect_all_patterns(config_patterns_by_route)
    pattern_str = ", ".join(f'"{p}"' for p in all_patterns)
    print(f"  [{pattern_str}]")

    print("\n# Destination-only patterns (matches any route to that destination):")
    unique_destinations = _collect_unique_destinations(config_patterns_by_route)
    dest_pattern_str = ", ".join(f'"{d}"' for d in unique_destinations)
    print(f"  [{dest_pattern_str}]")


def _display_route_info_single(route_display: str, destinations: list[str]) -> None:
    """Display route information for single station view."""
    dest_count = len(destinations)
    multi_dest_note = (
        f" ({dest_count} destination{'s' if dest_count > 1 else ''})" if dest_count > 1 else ""
    )
    print(f"\n{route_display}{multi_dest_note}:")
    for dest in destinations:
        print(f"  → {dest}")


def _process_station_routes_single(routes: dict[str, Any]) -> dict[str, list[ConfigPattern]]:
    """Process routes and collect config patterns for single station view."""
    config_patterns_by_route: dict[str, list[ConfigPattern]] = {}

    for route_key, route_data in sorted(routes.items()):
        destinations, transport_type, line, route_display = _extract_route_info(
            route_key, route_data
        )
        _display_route_info_single(route_display, destinations)

        route_patterns = _collect_route_patterns(route_data, destinations, transport_type, line)
        if route_patterns:
            config_patterns_by_route[route_key] = route_patterns

    return config_patterns_by_route


async def list_routes(station_id: str, show_patterns: bool = True) -> None:
    """List all available routes and destinations for a station."""
    details = await get_station_details(station_id)
    if not details:
        print(f"Station {station_id} not found or has no departures.", file=sys.stderr)
        sys.exit(1)

    station = details.get("station", {})
    routes = details.get("routes", {})

    print(f"\nStation: {station.get('name', station_id)} ({station_id})")
    print(f"Place: {station.get('place', 'München')}")
    print(f"\nAvailable Routes ({len(routes)}):")
    print("=" * 70)

    config_patterns_by_route = _process_station_routes_single(routes)
    print(f"\nTotal departures found: {details.get('total_departures_found', 0)}")

    if show_patterns:
        _display_config_patterns_detailed(config_patterns_by_route)

    stop_point_mapping = details.get("stop_point_mapping", {})
    _display_stop_point_hints(stop_point_mapping, station_id)


def _extract_route_info(route_key: str, route_data: Any) -> tuple[list[str], str, str, str]:
    """Extract route information from route data."""
    if isinstance(route_data, dict):
        destinations = route_data.get("destinations", [])
        transport_type = route_data.get("transport_type", "")
        line = route_data.get("line", "")
        route_display = f"{transport_type} {line}"
    else:
        destinations = route_data if isinstance(route_data, list) else []
        transport_type = route_key.split()[0] if route_key.split() else ""
        line = route_key.split()[-1] if route_key.split() else route_key
        route_display = route_key
    return destinations, transport_type, line, route_display


def _collect_route_patterns(
    route_data: Any, destinations: list[str], transport_type: str, line: str
) -> list[ConfigPattern]:
    """Collect config patterns for a route."""
    route_patterns = []
    for dest in destinations:
        if isinstance(route_data, dict) and transport_type and line:
            pattern = f"{line} {dest}"
            full_pattern = f"{transport_type} {line} {dest}"
            route_patterns.append(
                ConfigPattern(pattern=pattern, full_pattern=full_pattern, destination=dest)
            )
    return route_patterns


def _display_route_info(route_display: str, destinations: list[str]) -> None:
    """Display route information."""
    dest_count = len(destinations)
    multi_dest_note = (
        f" ({dest_count} destination{'s' if dest_count > 1 else ''})" if dest_count > 1 else ""
    )
    print(f"\n  {route_display}{multi_dest_note}:")
    for dest in destinations:
        print(f"    → {dest}")


def _print_pattern_header_indented() -> None:
    """Print indented header for config patterns section."""
    print("\n  " + "-" * 68)
    print("  Config patterns (copy into your direction_mappings):")
    print("  " + "-" * 68)
    print("\n  # Format: Patterns match 'line destination' or 'transport_type line destination'")
    print("  # Examples: '139 Messestadt West' or 'Bus 139 Messestadt West'")


def _print_route_patterns_indented(
    config_patterns_by_route: dict[str, list[ConfigPattern]],
) -> None:
    """Print indented patterns grouped by route."""
    print("\n  # Grouped by route (recommended format: line + destination):")
    for route_key, patterns in sorted(config_patterns_by_route.items()):
        route_display = route_key.replace(" ", " ")
        print(f"\n  # {route_display}:")
        for config_pattern in patterns:
            route_line = route_key.split()[-1] if route_key.split() else ""
            print(
                f'    "{config_pattern.pattern}"  # Matches: {route_line} -> {config_pattern.destination}'
            )


def _print_flat_pattern_list_indented(all_patterns: list[str]) -> None:
    """Print indented flat list of patterns."""
    print("\n  # Flat list (line + destination format) - ready to paste:")
    pattern_str = ", ".join(f'"{p}"' for p in all_patterns)
    print(f"    [{pattern_str}]")


def _print_destination_patterns_indented(destinations: list[str]) -> None:
    """Print indented destination-only patterns."""
    print("\n  # Destination-only patterns (matches any route to that destination):")
    dest_pattern_str = ", ".join(f'"{d}"' for d in destinations)
    print(f"    [{dest_pattern_str}]")


def _display_config_patterns(config_patterns_by_route: dict[str, list[ConfigPattern]]) -> None:
    """Display config patterns for copying into configuration."""
    if not config_patterns_by_route:
        return

    _print_pattern_header_indented()
    _print_route_patterns_indented(config_patterns_by_route)

    all_patterns = _collect_all_patterns(config_patterns_by_route)
    _print_flat_pattern_list_indented(all_patterns)

    unique_destinations = _collect_unique_destinations(config_patterns_by_route)
    _print_destination_patterns_indented(unique_destinations)


def _process_station_routes(routes: dict[str, Any]) -> dict[str, list[ConfigPattern]]:
    """Process routes and collect config patterns."""
    config_patterns_by_route: dict[str, list[ConfigPattern]] = {}

    for route_key, route_data in sorted(routes.items()):
        destinations, transport_type, line, route_display = _extract_route_info(
            route_key, route_data
        )
        _display_route_info(route_display, destinations)

        route_patterns = _collect_route_patterns(route_data, destinations, transport_type, line)
        if route_patterns:
            config_patterns_by_route[route_key] = route_patterns

    return config_patterns_by_route


def _find_platform_for_stop_point(
    stop_point: str, platform_to_stop_point: dict[int, set[str]]
) -> str | None:
    """Find platform info for a stop point."""
    for platform, sp_set in platform_to_stop_point.items():
        if stop_point in sp_set:
            return f"Platform {platform}"
    return None


def _process_stop_points_for_mapping(
    mapping_key: str,
    mapping_data: dict[str, Any],
    stops_with_routes: dict[str, list[StopPointRouteInfo]],
) -> None:
    """Process stop points for a single mapping entry."""
    route_key, destination = mapping_key.split("|", 1)
    stop_points = mapping_data.get("stop_points", set())
    platform_to_stop_point = mapping_data.get("platform_to_stop_point", {})

    for stop_point in stop_points:
        if stop_point not in stops_with_routes:
            stops_with_routes[stop_point] = []

        platform_info = _find_platform_for_stop_point(stop_point, platform_to_stop_point)
        stops_with_routes[stop_point].append(
            StopPointRouteInfo(
                route_key=route_key,
                destination=destination,
                platform_info=platform_info,
            )
        )


def _get_transport_type_key(route_key: str) -> str:
    """Extract transport type key from route key."""
    return route_key.split()[0] if route_key.split() else "Other"


def _process_platforms_without_stop_points(
    route_key: str,
    destination: str,
    platforms: set[int],
    s_bahn_platforms: dict[str, dict[str, dict[int, list[DestinationPlatformInfo]]]],
) -> None:
    """Process platforms that don't have stop points."""
    transport_type_key = _get_transport_type_key(route_key)

    if transport_type_key not in s_bahn_platforms:
        s_bahn_platforms[transport_type_key] = {}
    if route_key not in s_bahn_platforms[transport_type_key]:
        s_bahn_platforms[transport_type_key][route_key] = {}

    for platform in platforms:
        if platform not in s_bahn_platforms[transport_type_key][route_key]:
            s_bahn_platforms[transport_type_key][route_key][platform] = []
        s_bahn_platforms[transport_type_key][route_key][platform].append(
            DestinationPlatformInfo(destination=destination, platform_info=f"Platform {platform}")
        )


def _group_stop_points(
    stop_point_mapping: dict[str, Any],
) -> tuple[
    dict[str, list[StopPointRouteInfo]],
    dict[str, dict[str, dict[int, list[DestinationPlatformInfo]]]],
]:
    """Group stop points and platforms from mapping data."""
    stops_with_routes: dict[str, list[StopPointRouteInfo]] = {}
    s_bahn_platforms: dict[str, dict[str, dict[int, list[DestinationPlatformInfo]]]] = {}

    for mapping_key, mapping_data in sorted(stop_point_mapping.items()):
        if "|" not in mapping_key:
            continue

        route_key, destination = mapping_key.split("|", 1)
        stop_points = mapping_data.get("stop_points", set())
        platforms = mapping_data.get("platforms", set())

        if stop_points:
            _process_stop_points_for_mapping(mapping_key, mapping_data, stops_with_routes)

        if platforms and not stop_points:
            _process_platforms_without_stop_points(
                route_key, destination, platforms, s_bahn_platforms
            )

    return stops_with_routes, s_bahn_platforms


def _extract_stop_number(stop_point: str) -> str:
    """Extract stop number from stop point ID."""
    return stop_point.split(":")[-1] if ":" in stop_point else stop_point


def _has_platform_info(route_infos: list[StopPointRouteInfo]) -> bool:
    """Check if any route info has platform information."""
    return any(route_info.platform_info for route_info in route_infos if route_info.platform_info)


def _build_route_pattern(route_info: StopPointRouteInfo) -> str:
    """Build route pattern string from route info."""
    line = route_info.route_key.split()[-1] if route_info.route_key.split() else ""
    return f"{line} {route_info.destination}" if line else route_info.destination


def _display_single_stop_point(stop_point: str, route_infos: list[StopPointRouteInfo]) -> None:
    """Display a single stop point with its routes."""
    stop_num = _extract_stop_number(stop_point)
    print(f"\n  # Stop {stop_num} ({stop_point}):")
    print(f'  # station_id = "{stop_point}"')

    if _has_platform_info(route_infos):
        print(
            "  # Note: You can use this stopPointGlobalId directly, or use base station_id with direction_mappings for additional filtering."
        )

    for route_info in sorted(route_infos, key=lambda r: (r.route_key, r.destination)):
        pattern = _build_route_pattern(route_info)
        if route_info.platform_info:
            print(f'    {route_info.route_key} -> "{pattern}"  # {route_info.platform_info}')
        else:
            print(f'    {route_info.route_key} -> "{pattern}"')


def _display_stop_points(stops_with_routes: dict[str, list[StopPointRouteInfo]]) -> None:
    """Display stop points with their routes."""
    for stop_point in sorted(stops_with_routes.keys(), reverse=True):
        _display_single_stop_point(stop_point, stops_with_routes[stop_point])


def _display_platform_for_route(
    route_key: str,
    platform: int,
    destinations: list[DestinationPlatformInfo],
    station_id: str,
) -> None:
    """Display platform information for a specific route."""
    route_parts = route_key.split()
    line = route_parts[-1] if route_parts else ""

    print(f"\n  # {route_key} - Platform {platform}:")
    print(f'  # station_id = "{station_id}"  # Use base station_id')
    print("  # Configure direction_mappings to filter by destination:")

    for dest_info in sorted(destinations, key=lambda d: d.destination):
        pattern = f"{line} {dest_info.destination}" if line else dest_info.destination
        print(f'    "{pattern}"')


def _display_platforms_for_transport_type(
    transport_type_key: str,
    platforms_by_route: dict[str, dict[int, list[DestinationPlatformInfo]]],
    station_id: str,
) -> None:
    """Display platforms for a specific transport type."""
    print(f"\n  # {transport_type_key} platforms by route and destination:")
    print(f"  # Note: These {transport_type_key} platforms don't have stopPointGlobalId values.")
    print("  # Use base station_id with direction_mappings to filter by destination.")

    for route_key in sorted(platforms_by_route.keys()):
        for platform in sorted(platforms_by_route[route_key].keys()):
            destinations = platforms_by_route[route_key][platform]
            _display_platform_for_route(route_key, platform, destinations, station_id)

    print("  # Then add these destinations to exclude_destinations in the main config.")


def _display_platforms_without_stop_points(
    s_bahn_platforms: dict[str, dict[str, dict[int, list[DestinationPlatformInfo]]]],
    station_id: str,
) -> None:
    """Display platforms that don't have stopPointGlobalId values."""
    if not s_bahn_platforms:
        return

    for transport_type_key in sorted(s_bahn_platforms.keys()):
        _display_platforms_for_transport_type(
            transport_type_key, s_bahn_platforms[transport_type_key], station_id
        )


def _display_stop_point_hints(stop_point_mapping: dict[str, Any], station_id: str) -> None:
    """Display stop point differentiation hints."""
    if not stop_point_mapping:
        return

    print("\n  " + "-" * 68)
    print("  Stop Point Differentiation Hints:")
    print("  " + "-" * 68)
    print("\n  # Some destinations use different physical stops at this station.")
    print("  # Define separate [[stops]] entries for each physical stop you want to monitor.")
    print("\n  # Stop points by route and destination:")

    stops_with_routes, s_bahn_platforms = _group_stop_points(stop_point_mapping)
    _display_stop_points(stops_with_routes)
    _display_platforms_without_stop_points(s_bahn_platforms, station_id)

    all_stop_points = set()
    for mapping_data in stop_point_mapping.values():
        if isinstance(mapping_data, dict):
            all_stop_points.update(mapping_data.get("stop_points", set()))
        else:
            all_stop_points.update(mapping_data if isinstance(mapping_data, set) else [])

    if all_stop_points:
        print("\n  # All unique stop points at this station:")
        for stop_point in sorted(all_stop_points):
            stop_num = stop_point.split(":")[-1] if ":" in stop_point else stop_point
            print(f'  #   "{stop_point}"  # Stop {stop_num}')


async def search_and_list_routes(query: str, show_patterns: bool = True) -> None:
    """Search for stations by name and list routes for each match."""
    results = await search_stations(query)

    if not results:
        print(f"No stations found for '{query}'", file=sys.stderr)
        sys.exit(1)

    print(f"\nFound {len(results)} station(s) matching '{query}':\n")
    print("=" * 70)

    for i, station in enumerate(results, 1):
        station_id = station.get("id", "")
        station_name = station.get("name", "Unknown")
        station_place = station.get("place", "Unknown")

        print(f"\n[{i}/{len(results)}] {station_name} ({station_place})")
        print(f"ID: {station_id}")
        print("-" * 70)

        details = await get_station_details(station_id, limit=100)
        if not details:
            print("  No routes found or station has no departures.")
            continue

        routes = details.get("routes", {})
        if not routes:
            print("  No routes found.")
            continue

        print(f"  Available Routes ({len(routes)}):")
        config_patterns_by_route = _process_station_routes(routes)

        if show_patterns:
            _display_config_patterns(config_patterns_by_route)

        stop_point_mapping = details.get("stop_point_mapping", {})
        _display_stop_point_hints(stop_point_mapping, station_id)

        if i < len(results):
            print()


def _convert_sets_to_lists(obj: Any) -> Any:
    """Recursively convert sets to lists for JSON serialization."""
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, dict):
        return {k: _convert_sets_to_lists(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_sets_to_lists(item) for item in obj]
    return obj


async def show_station_info(station_id: str, format_json: bool = False) -> None:
    """Show detailed information about a station."""
    details = await get_station_details(station_id)
    if not details:
        print(f"Station {station_id} not found or has no departures.", file=sys.stderr)
        sys.exit(1)

    if format_json:
        # Convert sets to lists for JSON serialization
        serializable_details = _convert_sets_to_lists(details)
        print(json.dumps(serializable_details, indent=2, ensure_ascii=False))
    else:
        station = details.get("station", {})
        routes = details.get("routes", {})

        print("\nStation Information:")
        print(f"  ID: {station.get('id', 'Unknown')}")
        print(f"  Name: {station.get('name', 'Unknown')}")
        print(f"  Place: {station.get('place', 'München')}")
        print(f"\nRoutes: {len(routes)}")
        for route, route_data in sorted(routes.items()):
            destinations = (
                route_data.get("destinations", []) if isinstance(route_data, dict) else []
            )
            destinations_list = (
                sorted(destinations) if isinstance(destinations, set) else destinations
            )
            destinations_display = ", ".join(destinations_list[:3]) + (
                "..." if len(destinations_list) > 3 else ""
            )
            print(f"  {route}: {destinations_display}")


def _extract_destinations_from_dict(route_data: dict[str, Any]) -> list[str]:
    """Extract destinations from dictionary route data."""
    destinations = route_data.get("destinations", [])
    if isinstance(destinations, list):
        return [str(d) for d in destinations]
    return []


def _extract_destinations_from_route_data(route_data: Any) -> list[str]:
    """Extract destinations from a single route data item."""
    if isinstance(route_data, dict):
        return _extract_destinations_from_dict(route_data)
    if isinstance(route_data, list):
        return [str(d) for d in route_data]
    return []


def _extract_all_destinations(routes: dict[str, Any]) -> set[str]:
    """Extract all destinations from routes dictionary."""
    all_destinations = set()
    for route_data in routes.values():
        destinations = _extract_destinations_from_route_data(route_data)
        all_destinations.update(destinations)
    return all_destinations


def _create_destination_chunks(destinations_list: list[str]) -> list[list[str]]:
    """Create chunks of destinations for direction grouping."""
    chunk_size = max(2, len(destinations_list) // 3)
    return [
        destinations_list[j : j + chunk_size] for j in range(0, len(destinations_list), chunk_size)
    ]


def _add_direction_mappings_to_snippet(snippet: str, destinations_list: list[str]) -> str:
    """Add direction mappings to config snippet."""
    chunks = _create_destination_chunks(destinations_list)
    for i, chunk in enumerate(chunks, 1):
        snippet += f'"->Direction{i}" = {json.dumps(chunk, ensure_ascii=False)}\n'
    return snippet


def generate_config_snippet(station_id: str, station_name: str, routes: dict[str, Any]) -> str:
    """Generate a TOML config snippet for a station."""
    all_destinations = _extract_all_destinations(routes)

    snippet = f"""[[stops]]
station_id = "{station_id}"
station_name = "{station_name}"
max_departures_per_stop = 30

[stops.direction_mappings]
# Configure your direction mappings here
# Example based on available destinations:
"""

    destinations_list = sorted(all_destinations)
    if destinations_list:
        snippet = _add_direction_mappings_to_snippet(snippet, destinations_list)

    return snippet


def _setup_mvg_argparse_subparsers(subparsers: Any) -> None:
    """Set up subparsers for MVG CLI commands."""
    search_parser = subparsers.add_parser("search", help="Search for stations")
    search_parser.add_argument("query", help="Station name to search for")
    search_parser.add_argument("--json", action="store_true", help="Output as JSON")

    info_parser = subparsers.add_parser("info", help="Show station information")
    info_parser.add_argument("station_id", help="Station ID (e.g., de:09162:100)")
    info_parser.add_argument("--json", action="store_true", help="Output as JSON")

    routes_parser = subparsers.add_parser(
        "routes", help="List routes for a station (by ID or search query)"
    )
    routes_parser.add_argument(
        "query",
        help="Station ID (e.g., de:09162:100) or station name to search for",
    )
    routes_parser.add_argument(
        "--no-patterns",
        action="store_true",
        help="Don't show config patterns",
    )

    departures_parser = subparsers.add_parser(
        "departures", help="Show live departures for a station (by ID or search query)"
    )
    departures_parser.add_argument(
        "query",
        help="Station ID (e.g., de:09162:100 or de:09162:100:4:4) or station name",
    )
    departures_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of departures to fetch (default: 100)",
    )
    departures_parser.add_argument("--json", action="store_true", help="Output as JSON")

    generate_parser = subparsers.add_parser("generate", help="Generate config snippet")
    generate_parser.add_argument("station_id", help="Station ID")
    generate_parser.add_argument("station_name", help="Station name")


def _setup_argparse() -> argparse.ArgumentParser:
    """Set up and configure argument parser."""
    import argparse

    parser = argparse.ArgumentParser(
        description="MVG Departures Configuration Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for stations
  mvg-config search "Giesing"

  # Show station details
  mvg-config info de:09162:100

  # List all routes for a station (by ID)
  mvg-config routes de:09162:100

  # Search for stations and show routes (by name)
  mvg-config routes "Giesing"

  # Show live departures for a station
  mvg-config departures de:09162:100

  # Show departures for a specific stop point (physical stop)
  mvg-config departures de:09162:1108:4:4

  # Search and show departures
  mvg-config departures "Chiemgaustr"

  # Generate config snippet
  mvg-config generate de:09162:100 "Giesing"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    _setup_mvg_argparse_subparsers(subparsers)

    return parser


async def _handle_search_command(query: str, output_json: bool) -> None:
    """Handle the search command."""
    results = await search_stations(query)
    if output_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    if not results:
        print(f"No stations found for '{query}'", file=sys.stderr)
        sys.exit(1)

    print(f"\nFound {len(results)} station(s):\n")
    for station in results:
        print(f"  {station.get('name', 'Unknown')} ({station.get('place', 'Unknown')})")
        print(f"    ID: {station.get('id', 'Unknown')}")
        print()


async def _handle_routes_command(query: str, show_patterns: bool) -> None:
    """Handle the routes command."""
    if ":" in query:
        await list_routes(query, show_patterns=show_patterns)
    else:
        await search_and_list_routes(query, show_patterns=show_patterns)


async def _handle_generate_command(station_id: str, station_name: str) -> None:
    """Handle the generate command."""
    details = await get_station_details(station_id)
    if not details:
        print(f"Station {station_id} not found.", file=sys.stderr)
        sys.exit(1)
    routes = details.get("routes", {})
    snippet = generate_config_snippet(station_id, station_name, routes)
    print(snippet)


def _format_departure_time(dep: dict[str, Any]) -> str:
    """Format departure time from API response."""
    realtime_ms = dep.get("realtimeDepartureTime") or dep.get("time")

    if not realtime_ms:
        return "??:??"

    if isinstance(realtime_ms, int) and realtime_ms > 1000000000000:
        dt = datetime.fromtimestamp(realtime_ms / 1000, tz=UTC)
    elif isinstance(realtime_ms, int):
        dt = datetime.fromtimestamp(realtime_ms, tz=UTC)
    else:
        return "??:??"

    local_dt = dt.astimezone()
    now = datetime.now(UTC)
    diff_minutes = int((dt - now).total_seconds() / 60)

    delay_min = dep.get("delayInMinutes") or dep.get("delay", 0) or 0
    delay_str = f" (+{delay_min})" if delay_min > 0 else ""

    return f"{local_dt.strftime('%H:%M')}{delay_str} (in {diff_minutes} min)"


def _display_departure(dep: dict[str, Any], index: int, show_stop_point: bool = True) -> None:
    """Display a single departure.

    Args:
        dep: Departure dictionary.
        index: Departure index number.
        show_stop_point: Whether to show stop point ID (False when already grouped by stop point).
    """
    line = dep.get("label") or dep.get("line", "?")
    destination = dep.get("destination", "?")
    transport_type = _normalize_transport_type(dep.get("transportType") or dep.get("type", ""))
    stop_point = dep.get("stopPointGlobalId") or dep.get("stop_point_global_id") or ""
    platform = dep.get("platform", "")
    cancelled = dep.get("cancelled", False)

    time_str = _format_departure_time(dep)
    platform_str = f" [Platform {platform}]" if platform else ""
    stop_point_str = f" | Stop: {stop_point}" if show_stop_point and stop_point else ""
    cancelled_str = " [CANCELLED]" if cancelled else ""

    print(
        f"  {index:3}. {time_str:25} {transport_type:12} {line:6} → {destination}{platform_str}{stop_point_str}{cancelled_str}"
    )


def _parse_stop_point_filter(station_id: str) -> tuple[str, str | None]:
    """Parse station_id to extract base station and optional stop point filter.

    Args:
        station_id: Station ID, possibly with stop point suffix (e.g., de:09162:1108:4:4).

    Returns:
        Tuple of (base_station_id, filter_stop_point or None).
    """
    parts = station_id.split(":")
    is_stop_point_id = len(parts) >= 5 and parts[-1] == parts[-2]

    if is_stop_point_id:
        return ":".join(parts[:3]), station_id

    return station_id, None


def _build_departures_api_url(station_id: str, limit: int) -> str:
    """Build MVG departures API URL."""
    return (
        f"https://www.mvg.de/api/bgw-pt/v3/departures"
        f"?globalId={station_id}&limit={limit}&transportTypes=UBAHN,TRAM,SBAHN,BUS,REGIONAL_BUS,BAHN"
    )


async def _fetch_departures_from_api(
    session: aiohttp.ClientSession, url: str
) -> list[dict[str, Any]]:
    """Fetch departures from API URL."""
    headers = _get_mvg_routes_headers()
    log_api_request("GET", url, headers=headers)
    try:
        response = await session.get(url, headers=headers)
    except Exception as e:
        print(f"Error fetching departures: {e}", file=sys.stderr)
        return []

    try:
        if response.status != 200:
            return []
        data = await response.json()
        return data if isinstance(data, list) else []
    finally:
        response.release()


async def _fetch_raw_departures(
    station_id: str, limit: int
) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch raw departures from MVG API."""
    base_station_id, filter_stop_point = _parse_stop_point_filter(station_id)
    url = _build_departures_api_url(base_station_id, limit)

    async with aiohttp.ClientSession() as session:
        departures = await _fetch_departures_from_api(session, url)
        return departures, filter_stop_point


async def _resolve_station(query: str) -> tuple[str, str]:
    """Resolve query to station_id and station_name."""
    if ":" in query:
        return query, query

    results = await search_stations(query)
    if not results:
        print(f"No stations found for '{query}'", file=sys.stderr)
        sys.exit(1)

    return results[0].get("id", ""), results[0].get("name", query)


def _filter_by_stop_point(
    departures: list[dict[str, Any]], filter_stop_point: str | None
) -> tuple[list[dict[str, Any]], int | None]:
    """Filter departures by stop point if specified."""
    if not filter_stop_point:
        return departures, None

    total_before = len(departures)
    # Check both camelCase and snake_case field names (API might use either)
    filtered = [
        d
        for d in departures
        if (d.get("stopPointGlobalId") or d.get("stop_point_global_id")) == filter_stop_point
    ]
    return filtered, total_before


def _print_departures_header(ctx: DeparturesDisplayContext) -> None:
    """Print the departures display header."""
    print(f"\n{'=' * 100}")
    print(f"Live Departures: {ctx.station_name} ({ctx.station_id})")
    print(f"{'=' * 100}")

    if ctx.filter_stop_point:
        print(f"Filtered by stop point: {ctx.filter_stop_point}")
        print(f"Showing {ctx.departures_count} of {ctx.total_before_filter} total departures")
    else:
        print(f"Total departures: {ctx.departures_count}")

    print(f"{'-' * 100}")


async def _show_available_stop_points(station_id: str, limit: int) -> None:
    """Show available stop points when filter returns no results."""
    print("\n  No departures match the filter!")
    print("\n  Available stop points at this station:")

    base_station = station_id.rsplit(":", 2)[0]
    all_deps, _ = await _fetch_raw_departures(base_station, limit)

    stop_points: dict[str, int] = {}
    for d in all_deps:
        sp = d.get("stopPointGlobalId") or d.get("stop_point_global_id") or "unknown"
        stop_points[sp] = stop_points.get(sp, 0) + 1

    for sp, count in sorted(stop_points.items()):
        print(f"    {sp}: {count} departures")


def _group_by_stop_point(departures: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group departures by stop point ID."""
    by_stop_point: dict[str, list[dict[str, Any]]] = {}
    for dep in departures:
        sp = dep.get("stopPointGlobalId") or dep.get("stop_point_global_id") or "unknown"
        if sp not in by_stop_point:
            by_stop_point[sp] = []
        by_stop_point[sp].append(dep)
    return by_stop_point


def _display_departures_flat(departures: list[dict[str, Any]]) -> None:
    """Display departures as a flat list."""
    for i, dep in enumerate(departures, 1):
        _display_departure(dep, i)


def _display_departures_grouped(by_stop_point: dict[str, list[dict[str, Any]]]) -> None:
    """Display departures grouped by stop point."""
    for sp in sorted(by_stop_point.keys()):
        stop_num = sp.split(":")[-1] if ":" in sp else sp
        print(f"\n  Stop {stop_num} ({sp}):")
        for i, dep in enumerate(by_stop_point[sp], 1):
            _display_departure(dep, i, show_stop_point=False)


def _print_departures_footer() -> None:
    """Print the departures display footer."""
    print(f"\n{'-' * 100}")
    print(
        "Tip: Use station_id with stop point (e.g., de:09162:1108:4:4) to filter by physical stop."
    )


async def list_departures(query: str, limit: int = 100, format_json: bool = False) -> None:
    """List live departures for a station."""
    station_id, station_name = await _resolve_station(query)
    departures, filter_stop_point = await _fetch_raw_departures(station_id, limit)

    if not departures:
        print(f"No departures found for station {station_id}", file=sys.stderr)
        sys.exit(1)

    departures, total_before_filter = _filter_by_stop_point(departures, filter_stop_point)

    if format_json:
        print(json.dumps(departures, indent=2, ensure_ascii=False))
        return

    ctx = DeparturesDisplayContext(
        station_name=station_name,
        station_id=station_id,
        departures_count=len(departures),
        filter_stop_point=filter_stop_point,
        total_before_filter=total_before_filter,
    )
    _print_departures_header(ctx)

    if not departures:
        await _show_available_stop_points(station_id, limit)
        return

    by_stop_point = _group_by_stop_point(departures)
    use_flat_display = len(by_stop_point) == 1 or filter_stop_point

    if use_flat_display:
        _display_departures_flat(departures)
    else:
        _display_departures_grouped(by_stop_point)

    _print_departures_footer()


async def _execute_cli_command(args: Any) -> None:
    """Execute the appropriate CLI command based on args."""
    command_handlers: dict[str, Any] = {
        "search": lambda: _handle_search_command(args.query, args.json),
        "info": lambda: show_station_info(args.station_id, format_json=args.json),
        "routes": lambda: _handle_routes_command(args.query, show_patterns=not args.no_patterns),
        "departures": lambda: list_departures(args.query, limit=args.limit, format_json=args.json),
        "generate": lambda: _handle_generate_command(args.station_id, args.station_name),
    }

    handler = command_handlers.get(args.command)
    if handler:
        await handler()


async def main() -> None:
    """Main CLI entry point."""
    parser = _setup_argparse()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        await _execute_cli_command(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cli_main() -> None:
    """Synchronous entry point for the CLI command."""
    # Configure logging for CLI (needed for API request logging)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
