"""CLI helpers for configuring MVG departures."""

import asyncio
import json
import sys
from typing import Any

import aiohttp
from mvg import MvgApi


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

            # Parse the routes endpoint response
            # The structure may vary, so we need to handle it flexibly
            routes: dict[str, set[str]] = {}  # transport_type + line -> set of destinations
            route_details: dict[str, dict[str, Any]] = {}  # route_key -> details

            # Handle different possible response structures
            lines = data if isinstance(data, list) else data.get("lines", [])
            if not lines and isinstance(data, dict):
                # Try other possible keys
                lines = data.get("routes", data.get("data", []))

            for line_info in lines:
                if not isinstance(line_info, dict):
                    continue

                # Extract line information
                line = str(
                    line_info.get("label", line_info.get("line", line_info.get("number", "")))
                )
                transport_type = line_info.get("transportType", line_info.get("type", ""))
                icon = line_info.get("icon", line_info.get("symbol", ""))

                # Get destinations - could be in various formats
                destinations = []
                if "destinations" in line_info:
                    destinations = line_info["destinations"]
                elif "destination" in line_info:
                    destinations = [line_info["destination"]]
                elif "directions" in line_info:
                    destinations = line_info["directions"]
                elif "direction" in line_info:
                    destinations = [line_info["direction"]]

                # Normalize transport type
                if transport_type:
                    # Map API transport types to our format
                    type_map = {
                        "BUS": "Bus",
                        "TRAM": "Tram",
                        "UBAHN": "U-Bahn",
                        "SBAHN": "S-Bahn",
                        "REGIONAL_BUS": "Bus",
                    }
                    transport_type = type_map.get(transport_type, transport_type)

                route_key = f"{transport_type} {line}"
                if route_key not in routes:
                    routes[route_key] = set()
                    route_details[route_key] = {
                        "line": line,
                        "transport_type": transport_type,
                        "icon": icon,
                    }

                # Add destinations
                for dest in destinations:
                    if isinstance(dest, dict):
                        dest_name = dest.get("name", dest.get("destination", ""))
                    else:
                        dest_name = str(dest)
                    if dest_name:
                        routes[route_key].add(dest_name)

            if not routes:
                return None

            # Check if we actually got any destinations
            total_destinations = sum(len(destinations) for destinations in routes.values())
            if total_destinations == 0:
                # Routes endpoint returned routes but no destinations - fall back to departures
                return None

            return {
                "station": {
                    "id": station_id,
                    "name": station_id,  # Routes endpoint may not include station name
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
        # If routes endpoint fails, return None to fall back to departures sampling
        return None


async def _get_stop_point_mapping(
    station_id: str, session: aiohttp.ClientSession, limit: int = 100
) -> dict[str, dict[str, Any]]:
    """Get mapping of route+destination to stop point IDs and platform info from raw API response."""
    stop_point_mapping: dict[str, dict[str, Any]] = (
        {}
    )  # "route_key destination" -> {"stop_points": set, "platforms": set}

    try:
        # Fetch raw departures to get stopPointGlobalId and platform info
        url = f"https://www.mvg.de/api/bgw-pt/v3/departures?globalId={station_id}&limit={limit}&transportTypes=UBAHN,TRAM,SBAHN,BUS,REGIONAL_BUS,BAHN"
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0",
        }
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if isinstance(data, list):
                    for dep in data:
                        line = str(dep.get("label", dep.get("line", "")))
                        destination = str(dep.get("destination", ""))
                        transport_type = str(dep.get("transportType", dep.get("type", "")))
                        stop_point_id = dep.get("stopPointGlobalId", "")
                        platform = dep.get("platform")

                        if line and destination:
                            # Normalize transport type
                            type_map = {
                                "BUS": "Bus",
                                "TRAM": "Tram",
                                "UBAHN": "U-Bahn",
                                "SBAHN": "S-Bahn",
                                "REGIONAL_BUS": "Bus",
                            }
                            transport_type = type_map.get(transport_type, transport_type)

                            route_key = f"{transport_type} {line}"
                            mapping_key = f"{route_key}|{destination}"

                            if mapping_key not in stop_point_mapping:
                                stop_point_mapping[mapping_key] = {
                                    "stop_points": set(),
                                    "platforms": set(),
                                    "platform_to_stop_point": {},  # For S-Bahn: platform -> set of stop_point_ids
                                }

                            # Add stop point ID if available (non-empty)
                            if stop_point_id and stop_point_id.strip():
                                stop_point_mapping[mapping_key]["stop_points"].add(stop_point_id)

                            # Track platform information for all transport types (including S-Bahn)
                            if platform is not None:
                                stop_point_mapping[mapping_key]["platforms"].add(platform)
                                if "platform_to_stop_point" not in stop_point_mapping[mapping_key]:
                                    stop_point_mapping[mapping_key]["platform_to_stop_point"] = {}
                                if (
                                    platform
                                    not in stop_point_mapping[mapping_key]["platform_to_stop_point"]
                                ):
                                    stop_point_mapping[mapping_key]["platform_to_stop_point"][
                                        platform
                                    ] = set()
                                # Track stopPointGlobalId for this platform
                                if stop_point_id and stop_point_id.strip():
                                    stop_point_mapping[mapping_key]["platform_to_stop_point"][
                                        platform
                                    ].add(stop_point_id)
    except Exception:
        # If stop point mapping fails, continue without it
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

    # Collect patterns for config, grouped by route
    config_patterns_by_route: dict[str, list[tuple[str, str, str]]] = {}

    for route_key, route_data in sorted(routes.items()):
        if isinstance(route_data, dict):
            destinations = route_data.get("destinations", [])
            transport_type = route_data.get("transport_type", "")
            line = route_data.get("line", "")
            route_display = f"{transport_type} {line}"
        else:
            # Fallback for old format
            destinations = route_data if isinstance(route_data, list) else []
            transport_type = route_key.split()[0] if route_key.split() else ""
            line = route_key.split()[-1] if route_key.split() else route_key
            route_display = route_key

        # Show route with destination count
        dest_count = len(destinations)
        multi_dest_note = (
            f" ({dest_count} destination{'s' if dest_count > 1 else ''})" if dest_count > 1 else ""
        )
        print(f"\n{route_display}{multi_dest_note}:")

        # Collect patterns for this route
        route_patterns = []

        for dest in destinations:
            print(f"  → {dest}")
            # Generate pattern for config
            if isinstance(route_data, dict) and transport_type and line:
                pattern = f"{line} {dest}"
                full_pattern = f"{transport_type} {line} {dest}"
                route_patterns.append((pattern, full_pattern, dest))

        if route_patterns:
            config_patterns_by_route[route_key] = route_patterns

    print(f"\nTotal departures found: {details.get('total_departures_found', 0)}")

    if show_patterns and config_patterns_by_route:
        print("\n" + "=" * 70)
        print("Config patterns (copy these into your direction_mappings):")
        print("=" * 70)
        print("\n# Format: Patterns match 'line destination' or 'transport_type line destination'")
        print("# Examples: '139 Messestadt West' or 'Bus 139 Messestadt West'")
        print("\n# Grouped by route (recommended format: line + destination):")
        for route_key, patterns in sorted(config_patterns_by_route.items()):
            route_display = route_key.replace(" ", " ")
            print(f"\n# {route_display}:")
            for pattern, _full_pattern, dest in patterns:
                print(
                    f'  "{pattern}"  # Matches: {route_key.split()[-1] if route_key.split() else ""} -> {dest}'
                )

        print("\n# Alternative format (transport type + line + destination):")
        for route_key, patterns in sorted(config_patterns_by_route.items()):
            route_display = route_key.replace(" ", " ")
            print(f"\n# {route_display}:")
            for _pattern, full_pattern, dest in patterns:
                print(f'  "{full_pattern}"  # Matches: {route_key} -> {dest}')

        # Also show a flat list for easy copy-paste
        print("\n# Flat list (line + destination format) - ready to paste:")
        all_patterns = []
        for patterns in config_patterns_by_route.values():
            all_patterns.extend([p[0] for p in patterns])
        pattern_str = ", ".join(f'"{p}"' for p in all_patterns)
        print(f"  [{pattern_str}]")

        # Show destination-only patterns as well
        print("\n# Destination-only patterns (matches any route to that destination):")
        unique_destinations = set()
        for patterns in config_patterns_by_route.values():
            for _pattern, _full_pattern, dest in patterns:
                unique_destinations.add(dest)
        dest_patterns = sorted(unique_destinations)
        dest_pattern_str = ", ".join(f'"{d}"' for d in dest_patterns)
        print(f"  [{dest_pattern_str}]")

    # Show stop point differentiation hints
    stop_point_mapping = details.get("stop_point_mapping", {})
    if stop_point_mapping and len(stop_point_mapping) > 0:
        print("\n" + "=" * 70)
        print("Stop Point Differentiation Hints:")
        print("=" * 70)
        print("\n# Some destinations use different physical stops at this station.")
        print("# Define separate [[stops]] entries for each physical stop you want to monitor.")
        print("\n# Stop points by route and destination:")

        # Group by stop point (reverse sorted)
        stops_with_routes: dict[str, list[tuple[str, str, str | None]]] = (
            {}
        )  # stop_point -> list of (route_key, destination, platform_info)
        s_bahn_platforms: dict[str, dict[str, dict[int, list[tuple[str, str]]]]] = (
            {}
        )  # transport_type -> route_key -> platform -> list of (destination, platform_info)

        for mapping_key, mapping_data in sorted(stop_point_mapping.items()):
            if "|" in mapping_key:
                route_key, destination = mapping_key.split("|", 1)
                stop_points = mapping_data.get("stop_points", set())
                platforms = mapping_data.get("platforms", set())

                # Handle regular stop points (including all transport types with stopPointGlobalId)
                # Include platform info if available
                platform_to_stop_point = mapping_data.get("platform_to_stop_point", {})
                for stop_point in stop_points:
                    if stop_point not in stops_with_routes:
                        stops_with_routes[stop_point] = []
                    # Check if this stop_point corresponds to a specific platform
                    platform_info = None
                    if platform_to_stop_point:
                        for platform, sp_set in platform_to_stop_point.items():
                            if stop_point in sp_set:
                                platform_info = f"Platform {platform}"
                                break
                    stops_with_routes[stop_point].append((route_key, destination, platform_info))

                # Handle platforms separately only if they don't have unique stopPointGlobalId
                # If they have stopPointGlobalId values, they're already handled above
                if platforms and not stop_points:
                    # Group by transport type for display
                    transport_type_key = route_key.split()[0] if route_key.split() else "Other"
                    if transport_type_key not in s_bahn_platforms:
                        s_bahn_platforms[transport_type_key] = {}
                    if route_key not in s_bahn_platforms[transport_type_key]:
                        s_bahn_platforms[transport_type_key][route_key] = {}
                    for platform in platforms:
                        if platform not in s_bahn_platforms[transport_type_key][route_key]:
                            s_bahn_platforms[transport_type_key][route_key][platform] = []
                        s_bahn_platforms[transport_type_key][route_key][platform].append(
                            (destination, f"Platform {platform}")
                        )

        # Display regular stop points (all transport types with stopPointGlobalId)
        for stop_point in sorted(stops_with_routes.keys(), reverse=True):
            stop_num = stop_point.split(":")[-1] if ":" in stop_point else stop_point
            print(f"\n# Stop {stop_num} ({stop_point}):")
            print(f'# station_id = "{stop_point}"')
            # Check if this stop has platform info (S-Bahn/U-Bahn)
            has_platforms = any(
                platform_info
                for _, _, platform_info in stops_with_routes[stop_point]
                if platform_info
            )
            if has_platforms:
                print(
                    "# Note: You can use this stopPointGlobalId directly, or use base station_id with direction_mappings for additional filtering."
                )
            # Sort routes and destinations for this stop point
            for route_key, destination, platform_info in sorted(stops_with_routes[stop_point]):
                # Extract line number from route_key (format: "Bus 139" -> "139")
                line = route_key.split()[-1] if route_key.split() else ""
                pattern = f"{line} {destination}" if line else destination
                if platform_info:
                    print(f'  {route_key} -> "{pattern}"  # {platform_info}')
                else:
                    print(f'  {route_key} -> "{pattern}"')

        # Display platforms without stopPointGlobalId (grouped by transport type)
        if s_bahn_platforms:
            for transport_type_key in sorted(s_bahn_platforms.keys()):
                print(f"\n# {transport_type_key} platforms by route and destination:")
                print(
                    f"# Note: These {transport_type_key} platforms don't have stopPointGlobalId values."
                )
                print("# Use base station_id with direction_mappings to filter by destination.")
                for route_key in sorted(s_bahn_platforms[transport_type_key].keys()):
                    route_parts = route_key.split()
                    line = route_parts[-1] if route_parts else ""
                    for platform in sorted(s_bahn_platforms[transport_type_key][route_key].keys()):
                        destinations = s_bahn_platforms[transport_type_key][route_key][platform]
                        print(f"\n# {route_key} - Platform {platform}:")
                        print(f'# station_id = "{station_id}"  # Use base station_id')
                        print("# Configure direction_mappings to filter by destination:")
                        for destination, _platform_info in sorted(destinations):
                            pattern = f"{line} {destination}" if line else destination
                            print(f'  "{pattern}"')
                        print(
                            "# Then add these destinations to exclude_destinations in the main config."
                        )

        # Summary of unique stop points
        all_stop_points = set()
        for mapping_data in stop_point_mapping.values():
            if isinstance(mapping_data, dict):
                all_stop_points.update(mapping_data.get("stop_points", set()))
            else:
                # Backward compatibility with old format
                all_stop_points.update(mapping_data if isinstance(mapping_data, set) else [])

        if all_stop_points:
            print("\n# All unique stop points at this station:")
            for stop_point in sorted(all_stop_points):
                stop_num = stop_point.split(":")[-1] if ":" in stop_point else stop_point
                print(f'#   "{stop_point}"  # Stop {stop_num}')


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

        # Get routes for this station (use higher limit to get all destinations)
        details = await get_station_details(station_id, limit=100)
        if not details:
            print("  No routes found or station has no departures.")
            continue

        routes = details.get("routes", {})
        if not routes:
            print("  No routes found.")
            continue

        print(f"  Available Routes ({len(routes)}):")

        # Collect patterns for config, grouped by route
        config_patterns_by_route: dict[str, list[tuple[str, str, str]]] = {}

        for route_key, route_data in sorted(routes.items()):
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

            # Show route with destination count
            dest_count = len(destinations)
            multi_dest_note = (
                f" ({dest_count} destination{'s' if dest_count > 1 else ''})"
                if dest_count > 1
                else ""
            )
            print(f"\n  {route_display}{multi_dest_note}:")

            # Collect patterns for this route
            route_patterns = []

            for dest in destinations:
                print(f"    → {dest}")
                # Generate pattern for config
                if isinstance(route_data, dict) and transport_type and line:
                    pattern = f"{line} {dest}"
                    full_pattern = f"{transport_type} {line} {dest}"
                    route_patterns.append((pattern, full_pattern, dest))

            if route_patterns:
                config_patterns_by_route[route_key] = route_patterns

        if show_patterns and config_patterns_by_route:
            print("\n  " + "-" * 68)
            print("  Config patterns (copy into your direction_mappings):")
            print("  " + "-" * 68)
            print(
                "\n  # Format: Patterns match 'line destination' or 'transport_type line destination'"
            )
            print("  # Examples: '139 Messestadt West' or 'Bus 139 Messestadt West'")
            print("\n  # Grouped by route (recommended format: line + destination):")
            for route_key, patterns in sorted(config_patterns_by_route.items()):
                route_display = route_key.replace(" ", " ")
                print(f"\n  # {route_display}:")
                for pattern, _full_pattern, dest in patterns:
                    route_line = route_key.split()[-1] if route_key.split() else ""
                    print(f'    "{pattern}"  # Matches: {route_line} -> {dest}')

            print("\n  # Flat list (line + destination format) - ready to paste:")
            all_patterns = []
            for patterns in config_patterns_by_route.values():
                all_patterns.extend([p[0] for p in patterns])
            pattern_str = ", ".join(f'"{p}"' for p in all_patterns)
            print(f"    [{pattern_str}]")

            # Show destination-only patterns
            print("\n  # Destination-only patterns (matches any route to that destination):")
            unique_destinations = set()
            for patterns in config_patterns_by_route.values():
                for _pattern, _full_pattern, dest in patterns:
                    unique_destinations.add(dest)
            dest_patterns = sorted(unique_destinations)
            dest_pattern_str = ", ".join(f'"{d}"' for d in dest_patterns)
            print(f"    [{dest_pattern_str}]")

        # Show stop point differentiation hints
        stop_point_mapping = details.get("stop_point_mapping", {})
        if stop_point_mapping and len(stop_point_mapping) > 0:
            print("\n  " + "-" * 68)
            print("  Stop Point Differentiation Hints:")
            print("  " + "-" * 68)
            print("\n  # Some destinations use different physical stops at this station.")
            print(
                "  # Define separate [[stops]] entries for each physical stop you want to monitor."
            )
            print("\n  # Stop points by route and destination:")

            # Group by stop point (reverse sorted)
            stops_with_routes: dict[str, list[tuple[str, str, str | None]]] = (
                {}
            )  # stop_point -> list of (route_key, destination, platform_info)
            s_bahn_platforms: dict[str, dict[str, dict[int, list[tuple[str, str]]]]] = (
                {}
            )  # transport_type -> route_key -> platform -> list of (destination, platform_info)

            for mapping_key, mapping_data in sorted(stop_point_mapping.items()):
                if "|" in mapping_key:
                    route_key, destination = mapping_key.split("|", 1)
                    stop_points = mapping_data.get("stop_points", set())
                    platforms = mapping_data.get("platforms", set())

                    # Handle regular stop points (all transport types including S-Bahn)
                    # Include platform info if available
                    platform_to_stop_point = mapping_data.get("platform_to_stop_point", {})
                    for stop_point in stop_points:
                        if stop_point not in stops_with_routes:
                            stops_with_routes[stop_point] = []
                        # Check if this stop_point corresponds to a specific platform
                        platform_info = None
                        if platform_to_stop_point:
                            for platform, sp_set in platform_to_stop_point.items():
                                if stop_point in sp_set:
                                    platform_info = f"Platform {platform}"
                                    break
                        stops_with_routes[stop_point].append(
                            (route_key, destination, platform_info)
                        )

                    # Handle platforms without stopPointGlobalId separately
                    if platforms and not stop_points:
                        # Group by transport type for display
                        transport_type_key = route_key.split()[0] if route_key.split() else "Other"
                        if transport_type_key not in s_bahn_platforms:
                            s_bahn_platforms[transport_type_key] = {}
                        if route_key not in s_bahn_platforms[transport_type_key]:
                            s_bahn_platforms[transport_type_key][route_key] = {}
                        for platform in platforms:
                            if platform not in s_bahn_platforms[transport_type_key][route_key]:
                                s_bahn_platforms[transport_type_key][route_key][platform] = []
                            s_bahn_platforms[transport_type_key][route_key][platform].append(
                                (destination, f"Platform {platform}")
                            )

            # Display regular stop points (all transport types with stopPointGlobalId)
            for stop_point in sorted(stops_with_routes.keys(), reverse=True):
                stop_num = stop_point.split(":")[-1] if ":" in stop_point else stop_point
                print(f"\n  # Stop {stop_num} ({stop_point}):")
                print(f'  # station_id = "{stop_point}"')
                # Check if this stop has platform info (S-Bahn/U-Bahn)
                has_platforms = any(
                    platform_info
                    for _, _, platform_info in stops_with_routes[stop_point]
                    if platform_info
                )
                if has_platforms:
                    print(
                        "  # Note: You can use this stopPointGlobalId directly, or use base station_id with direction_mappings for additional filtering."
                    )
                # Sort routes and destinations for this stop point
                for route_key, destination, platform_info in sorted(stops_with_routes[stop_point]):
                    # Extract line number from route_key (format: "Bus 139" -> "139")
                    line = route_key.split()[-1] if route_key.split() else ""
                    pattern = f"{line} {destination}" if line else destination
                    if platform_info:
                        print(f'    {route_key} -> "{pattern}"  # {platform_info}')
                    else:
                        print(f'    {route_key} -> "{pattern}"')

            # Display platforms without stopPointGlobalId (grouped by transport type)
            if s_bahn_platforms:
                for transport_type_key in sorted(s_bahn_platforms.keys()):
                    print(f"\n  # {transport_type_key} platforms by route and destination:")
                    print(
                        f"  # Note: These {transport_type_key} platforms don't have stopPointGlobalId values."
                    )
                    print(
                        "  # Use base station_id with direction_mappings to filter by destination."
                    )
                    for route_key in sorted(s_bahn_platforms[transport_type_key].keys()):
                        route_parts = route_key.split()
                        line = route_parts[-1] if route_parts else ""
                        for platform in sorted(
                            s_bahn_platforms[transport_type_key][route_key].keys()
                        ):
                            destinations = s_bahn_platforms[transport_type_key][route_key][platform]
                            print(f"\n  # {route_key} - Platform {platform}:")
                            print(f'  # station_id = "{station_id}"  # Use base station_id')
                            print("  # Configure direction_mappings to filter by destination:")
                            for destination, _platform_info in sorted(destinations):
                                pattern = f"{line} {destination}" if line else destination
                                print(f'    "{pattern}"')
                            print(
                                "  # Then add these destinations to exclude_destinations in the main config."
                            )

            # Summary of unique stop points
            all_stop_points = set()
            for mapping_data in stop_point_mapping.values():
                if isinstance(mapping_data, dict):
                    all_stop_points.update(mapping_data.get("stop_points", set()))
                else:
                    # Backward compatibility with old format
                    all_stop_points.update(mapping_data if isinstance(mapping_data, set) else [])

            if all_stop_points:
                print("\n  # All unique stop points at this station:")
                for stop_point in sorted(all_stop_points):
                    stop_num = stop_point.split(":")[-1] if ":" in stop_point else stop_point
                    print(f'  #   "{stop_point}"  # Stop {stop_num}')

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


async def main() -> None:
    """Main CLI entry point."""
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

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for stations")
    search_parser.add_argument("query", help="Station name to search for")
    search_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Info command
    info_parser = subparsers.add_parser("info", help="Show station information")
    info_parser.add_argument("station_id", help="Station ID (e.g., de:09162:100)")
    info_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Routes command
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

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate config snippet")
    generate_parser.add_argument("station_id", help="Station ID")
    generate_parser.add_argument("station_name", help="Station name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "search":
            results = await search_stations(args.query)
            if args.json:
                print(json.dumps(results, indent=2, ensure_ascii=False))
            else:
                if not results:
                    print(f"No stations found for '{args.query}'", file=sys.stderr)
                    sys.exit(1)
                print(f"\nFound {len(results)} station(s):\n")
                for station in results:
                    print(f"  {station.get('name', 'Unknown')} ({station.get('place', 'Unknown')})")
                    print(f"    ID: {station.get('id', 'Unknown')}")
                    print()

        elif args.command == "info":
            await show_station_info(args.station_id, format_json=args.json)

        elif args.command == "routes":
            # Check if query looks like a station ID (contains ':')
            if ":" in args.query:
                # Treat as station ID
                await list_routes(args.query, show_patterns=not args.no_patterns)
            else:
                # Treat as search query
                await search_and_list_routes(args.query, show_patterns=not args.no_patterns)

        elif args.command == "generate":
            details = await get_station_details(args.station_id)
            if not details:
                print(f"Station {args.station_id} not found.", file=sys.stderr)
                sys.exit(1)
            routes = details.get("routes", {})
            snippet = generate_config_snippet(args.station_id, args.station_name, routes)
            print(snippet)

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
