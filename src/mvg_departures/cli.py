"""CLI helpers for configuring MVG departures."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import argparse

import aiohttp
from mvg import MvgApi

from mvg_departures.domain.models.cli_types import (
    ConfigPattern,
    DestinationPlatformInfo,
    StopPointRouteInfo,
)


async def search_stations(query: str) -> list[dict[str, Any]]:
    """Search for stations by name."""
    async with aiohttp.ClientSession() as session:
        results = []

        # Try direct search first
        try:
            result = await MvgApi.station_async(query, session=session)
            if result:
                results.append(result)
        except Exception:
            pass

        # Try with "München" appended if not already there
        if "München" not in query and "Munich" not in query:
            try:
                result = await MvgApi.station_async(f"{query}, München", session=session)
                if result and result not in results:
                    results.append(result)
            except Exception:
                pass

        # Try to get all stations and filter (if API supports it)
        try:
            if hasattr(MvgApi, "stations_async"):
                all_stations = await MvgApi.stations_async(session=session)
                if all_stations:
                    query_lower = query.lower()
                    matches = [
                        s
                        for s in all_stations
                        if query_lower in s.get("name", "").lower()
                        or query_lower in s.get("place", "").lower()
                    ]
                    # Add unique matches
                    existing_ids = {r.get("id") for r in results}
                    for match in matches[:20]:
                        if match.get("id") not in existing_ids:
                            results.append(match)
        except Exception:
            pass

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


def _extract_destinations_from_line_info(line_info: dict[str, Any]) -> list[str]:
    """Extract destinations from line info in various possible formats."""
    if "destinations" in line_info:
        destinations = line_info["destinations"]
        if isinstance(destinations, list):
            return [str(d) for d in destinations]
        return []
    if "destination" in line_info:
        return [str(line_info["destination"])]
    if "directions" in line_info:
        directions = line_info["directions"]
        if isinstance(directions, list):
            return [str(d) for d in directions]
        return []
    if "direction" in line_info:
        return [str(line_info["direction"])]
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


def _parse_routes_response(data: Any) -> list[dict[str, Any]]:
    """Parse routes response and extract lines list."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    if isinstance(data, dict):
        lines = data.get("lines", [])
        if not lines:
            lines = data.get("routes", data.get("data", []))
        if isinstance(lines, list):
            return [item for item in lines if isinstance(item, dict)]
        return []

    return []


async def _get_routes_from_endpoint(
    station_id: str, session: aiohttp.ClientSession
) -> dict[str, Any] | None:
    """Get routes from the MVG routes endpoint."""
    try:
        url = f"https://www.mvg.de/api/bgw-pt/v3/lines/{station_id}"
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0",
        }
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return None

            data = await response.json()
            if not data:
                return None

            lines = _parse_routes_response(data)
            if not lines:
                return None

            routes: dict[str, set[str]] = {}
            route_details: dict[str, dict[str, Any]] = {}

            for line_info in lines:
                if not isinstance(line_info, dict):
                    continue

                line, transport_type, icon = _extract_line_info(line_info)
                destinations_raw = _extract_destinations_from_line_info(line_info)

                route_key = f"{transport_type} {line}"
                if route_key not in routes:
                    routes[route_key] = set()
                    route_details[route_key] = {
                        "line": line,
                        "transport_type": transport_type,
                        "icon": icon,
                    }

                for dest in destinations_raw:
                    dest_name = _normalize_destination_name(dest)
                    if dest_name:
                        routes[route_key].add(dest_name)

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
    except Exception:
        return None


def _process_departure_for_stop_point_mapping(
    dep: dict[str, Any], stop_point_mapping: dict[str, dict[str, Any]]
) -> None:
    """Process a single departure to extract stop point and platform information."""
    line = str(dep.get("label", dep.get("line", "")))
    destination = str(dep.get("destination", ""))
    transport_type = str(dep.get("transportType", dep.get("type", "")))
    stop_point_id = dep.get("stopPointGlobalId", "")
    platform = dep.get("platform")

    if not line or not destination:
        return

    transport_type = _normalize_transport_type(transport_type)
    route_key = f"{transport_type} {line}"
    mapping_key = f"{route_key}|{destination}"

    if mapping_key not in stop_point_mapping:
        stop_point_mapping[mapping_key] = {
            "stop_points": set(),
            "platforms": set(),
            "platform_to_stop_point": {},
        }

    if stop_point_id and stop_point_id.strip():
        stop_point_mapping[mapping_key]["stop_points"].add(stop_point_id)

    if platform is not None:
        stop_point_mapping[mapping_key]["platforms"].add(platform)
        platform_map = stop_point_mapping[mapping_key]["platform_to_stop_point"]
        if platform not in platform_map:
            platform_map[platform] = set()
        if stop_point_id and stop_point_id.strip():
            platform_map[platform].add(stop_point_id)


async def _get_stop_point_mapping(
    station_id: str, session: aiohttp.ClientSession, limit: int = 100
) -> dict[str, dict[str, Any]]:
    """Get mapping of route+destination to stop point IDs and platform info from raw API response."""
    stop_point_mapping: dict[str, dict[str, Any]] = {}

    try:
        url = f"https://www.mvg.de/api/bgw-pt/v3/departures?globalId={station_id}&limit={limit}&transportTypes=UBAHN,TRAM,SBAHN,BUS,REGIONAL_BUS,BAHN"
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0",
        }
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return stop_point_mapping

            data = await response.json()
            if not isinstance(data, list):
                return stop_point_mapping

            for dep in data:
                _process_departure_for_stop_point_mapping(dep, stop_point_mapping)
    except Exception:
        pass

    return stop_point_mapping


async def get_station_details(station_id: str, limit: int = 100) -> dict[str, Any] | None:
    """Get detailed information about a station."""
    async with aiohttp.ClientSession() as session:
        try:
            # Always fetch stop point mapping from raw API
            stop_point_mapping = await _get_stop_point_mapping(station_id, session, limit)

            # Try to get routes from routes endpoint (for route list)
            routes_from_endpoint = await _get_routes_from_endpoint(station_id, session)

            # Always use departures sampling for destinations (more reliable)
            # Get departures to infer station info and available routes
            # Use a higher limit to capture all destinations for routes
            departures = await MvgApi.departures_async(station_id, limit=limit, session=session)
            if not departures:
                return None

            # Extract unique routes and destinations from departures
            routes: dict[str, set[str]] = {}  # transport_type + line -> set of destinations
            route_details: dict[str, dict[str, Any]] = {}  # route_key -> details

            for dep in departures:
                line = dep.get("line", "")
                destination = dep.get("destination", "")
                transport_type = dep.get("type", "")
                icon = dep.get("icon", "")

                route_key = f"{transport_type} {line}"
                if route_key not in routes:
                    routes[route_key] = set()
                    route_details[route_key] = {
                        "line": line,
                        "transport_type": transport_type,
                        "icon": icon,
                    }
                routes[route_key].add(destination)

            # If routes endpoint provided route info, merge it (but keep destinations from departures)
            if routes_from_endpoint:
                routes_from_endpoint_data = routes_from_endpoint.get("routes", {})
                # Update route details from endpoint if available, but keep destinations from departures
                for route_key, endpoint_route_data in routes_from_endpoint_data.items():
                    if route_key in routes and isinstance(endpoint_route_data, dict):
                        # Merge route details (icon, etc.) but keep our destinations
                        route_details[route_key].update(
                            {
                                k: v
                                for k, v in endpoint_route_data.items()
                                if k != "destinations"  # Don't overwrite destinations
                            }
                        )

            # Try to get station name from first departure or use ID
            station_name = station_id
            # The MVG API might not return station name in departures
            # We'll use the station_id as fallback

            return {
                "station": {
                    "id": station_id,
                    "name": station_name,
                    "place": "München",
                },
                "routes": {
                    route: {
                        "destinations": sorted(destinations),
                        **route_details[route],
                    }
                    for route, destinations in routes.items()
                },
                "stop_point_mapping": stop_point_mapping,
                "total_departures_found": len(departures),
                "source": "departures_sampling"
                + (" + routes_endpoint" if routes_from_endpoint else ""),
            }
        except Exception as e:
            print(f"Error fetching station details: {e}", file=sys.stderr)
            return None


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
    all_patterns = []
    for patterns in config_patterns_by_route.values():
        all_patterns.extend([p.pattern for p in patterns])
    pattern_str = ", ".join(f'"{p}"' for p in all_patterns)
    print(f"  [{pattern_str}]")

    print("\n# Destination-only patterns (matches any route to that destination):")
    unique_destinations = set()
    for patterns in config_patterns_by_route.values():
        for config_pattern in patterns:
            unique_destinations.add(config_pattern.destination)
    dest_patterns = sorted(unique_destinations)
    dest_pattern_str = ", ".join(f'"{d}"' for d in dest_patterns)
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


def _display_config_patterns(config_patterns_by_route: dict[str, list[ConfigPattern]]) -> None:
    """Display config patterns for copying into configuration."""
    if not config_patterns_by_route:
        return

    print("\n  " + "-" * 68)
    print("  Config patterns (copy into your direction_mappings):")
    print("  " + "-" * 68)
    print("\n  # Format: Patterns match 'line destination' or 'transport_type line destination'")
    print("  # Examples: '139 Messestadt West' or 'Bus 139 Messestadt West'")
    print("\n  # Grouped by route (recommended format: line + destination):")

    for route_key, patterns in sorted(config_patterns_by_route.items()):
        route_display = route_key.replace(" ", " ")
        print(f"\n  # {route_display}:")
        for config_pattern in patterns:
            route_line = route_key.split()[-1] if route_key.split() else ""
            print(
                f'    "{config_pattern.pattern}"  # Matches: {route_line} -> {config_pattern.destination}'
            )

    print("\n  # Flat list (line + destination format) - ready to paste:")
    all_patterns = []
    for patterns in config_patterns_by_route.values():
        all_patterns.extend([p.pattern for p in patterns])
    pattern_str = ", ".join(f'"{p}"' for p in all_patterns)
    print(f"    [{pattern_str}]")

    print("\n  # Destination-only patterns (matches any route to that destination):")
    unique_destinations = set()
    for patterns in config_patterns_by_route.values():
        for config_pattern in patterns:
            unique_destinations.add(config_pattern.destination)
    dest_patterns = sorted(unique_destinations)
    dest_pattern_str = ", ".join(f'"{d}"' for d in dest_patterns)
    print(f"    [{dest_pattern_str}]")


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
        platform_to_stop_point = mapping_data.get("platform_to_stop_point", {})

        for stop_point in stop_points:
            if stop_point not in stops_with_routes:
                stops_with_routes[stop_point] = []

            platform_info = None
            if platform_to_stop_point:
                for platform, sp_set in platform_to_stop_point.items():
                    if stop_point in sp_set:
                        platform_info = f"Platform {platform}"
                        break

            stops_with_routes[stop_point].append(
                StopPointRouteInfo(
                    route_key=route_key,
                    destination=destination,
                    platform_info=platform_info,
                )
            )

        if platforms and not stop_points:
            transport_type_key = route_key.split()[0] if route_key.split() else "Other"
            if transport_type_key not in s_bahn_platforms:
                s_bahn_platforms[transport_type_key] = {}
            if route_key not in s_bahn_platforms[transport_type_key]:
                s_bahn_platforms[transport_type_key][route_key] = {}

            for platform in platforms:
                if platform not in s_bahn_platforms[transport_type_key][route_key]:
                    s_bahn_platforms[transport_type_key][route_key][platform] = []
                s_bahn_platforms[transport_type_key][route_key][platform].append(
                    DestinationPlatformInfo(
                        destination=destination, platform_info=f"Platform {platform}"
                    )
                )

    return stops_with_routes, s_bahn_platforms


def _display_stop_points(stops_with_routes: dict[str, list[StopPointRouteInfo]]) -> None:
    """Display stop points with their routes."""
    for stop_point in sorted(stops_with_routes.keys(), reverse=True):
        stop_num = stop_point.split(":")[-1] if ":" in stop_point else stop_point
        print(f"\n  # Stop {stop_num} ({stop_point}):")
        print(f'  # station_id = "{stop_point}"')

        has_platforms = any(
            route_info.platform_info
            for route_info in stops_with_routes[stop_point]
            if route_info.platform_info
        )
        if has_platforms:
            print(
                "  # Note: You can use this stopPointGlobalId directly, or use base station_id with direction_mappings for additional filtering."
            )

        for route_info in sorted(
            stops_with_routes[stop_point], key=lambda r: (r.route_key, r.destination)
        ):
            line = route_info.route_key.split()[-1] if route_info.route_key.split() else ""
            pattern = f"{line} {route_info.destination}" if line else route_info.destination
            if route_info.platform_info:
                print(f'    {route_info.route_key} -> "{pattern}"  # {route_info.platform_info}')
            else:
                print(f'    {route_info.route_key} -> "{pattern}"')


def _display_platforms_without_stop_points(
    s_bahn_platforms: dict[str, dict[str, dict[int, list[DestinationPlatformInfo]]]],
    station_id: str,
) -> None:
    """Display platforms that don't have stopPointGlobalId values."""
    if not s_bahn_platforms:
        return

    for transport_type_key in sorted(s_bahn_platforms.keys()):
        print(f"\n  # {transport_type_key} platforms by route and destination:")
        print(
            f"  # Note: These {transport_type_key} platforms don't have stopPointGlobalId values."
        )
        print("  # Use base station_id with direction_mappings to filter by destination.")

        for route_key in sorted(s_bahn_platforms[transport_type_key].keys()):
            route_parts = route_key.split()
            line = route_parts[-1] if route_parts else ""

            for platform in sorted(s_bahn_platforms[transport_type_key][route_key].keys()):
                destinations = s_bahn_platforms[transport_type_key][route_key][platform]
                print(f"\n  # {route_key} - Platform {platform}:")
                print(f'  # station_id = "{station_id}"  # Use base station_id')
                print("  # Configure direction_mappings to filter by destination:")

                for dest_info in sorted(destinations, key=lambda d: d.destination):
                    pattern = f"{line} {dest_info.destination}" if line else dest_info.destination
                    print(f'    "{pattern}"')
                print("  # Then add these destinations to exclude_destinations in the main config.")


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


async def show_station_info(station_id: str, format_json: bool = False) -> None:
    """Show detailed information about a station."""
    details = await get_station_details(station_id)
    if not details:
        print(f"Station {station_id} not found or has no departures.", file=sys.stderr)
        sys.exit(1)

    if format_json:
        print(json.dumps(details, indent=2, ensure_ascii=False))
    else:
        station = details.get("station", {})
        routes = details.get("routes", {})

        print("\nStation Information:")
        print(f"  ID: {station.get('id', 'Unknown')}")
        print(f"  Name: {station.get('name', 'Unknown')}")
        print(f"  Place: {station.get('place', 'München')}")
        print(f"\nRoutes: {len(routes)}")
        for route, destinations in sorted(routes.items()):
            print(
                f"  {route}: {', '.join(destinations[:3])}{'...' if len(destinations) > 3 else ''}"
            )


def generate_config_snippet(station_id: str, station_name: str, routes: dict[str, Any]) -> str:
    """Generate a TOML config snippet for a station."""
    # Extract all destinations from routes
    all_destinations = set()
    for route_data in routes.values():
        if isinstance(route_data, dict):
            destinations = route_data.get("destinations", [])
            all_destinations.update(destinations)
        elif isinstance(route_data, list):
            all_destinations.update(route_data)

    # Create a simple config snippet
    snippet = f"""[[stops]]
station_id = "{station_id}"
station_name = "{station_name}"
max_departures_per_stop = 30

[stops.direction_mappings]
# Configure your direction mappings here
# Example based on available destinations:
"""

    # Suggest some direction mappings based on common destination patterns
    destinations_list = sorted(all_destinations)
    if destinations_list:
        # Simple grouping - user can customize
        # Group into 2-3 directions
        chunk_size = max(2, len(destinations_list) // 3)
        for i, chunk in enumerate(
            [
                destinations_list[j : j + chunk_size]
                for j in range(0, len(destinations_list), chunk_size)
            ],
            1,
        ):
            snippet += f'"->Direction{i}" = {json.dumps(chunk, ensure_ascii=False)}\n'

    return snippet


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

  # Generate config snippet
  mvg-config generate de:09162:100 "Giesing"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

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

    generate_parser = subparsers.add_parser("generate", help="Generate config snippet")
    generate_parser.add_argument("station_id", help="Station ID")
    generate_parser.add_argument("station_name", help="Station name")

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


async def main() -> None:
    """Main CLI entry point."""
    parser = _setup_argparse()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "search":
            await _handle_search_command(args.query, args.json)
        elif args.command == "info":
            await show_station_info(args.station_id, format_json=args.json)
        elif args.command == "routes":
            await _handle_routes_command(args.query, show_patterns=not args.no_patterns)
        elif args.command == "generate":
            await _handle_generate_command(args.station_id, args.station_name)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cli_main() -> None:
    """Synchronous entry point for the CLI command."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
