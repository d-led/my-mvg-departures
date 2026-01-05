"""CLI helpers for configuring VBB (Berlin) departures."""

import asyncio
import logging
import sys
from typing import Any

import aiohttp

from mvg_departures.adapters.api_request_logger import log_api_request

_COMMON_WORDS = {
    "berlin",
    "platz",
    "str",
    "strasse",
    "bahnhof",
    "bhf",
    "u",
    "s",
    "garten",
    "der",
    "die",
    "das",
}


def _extract_meaningful_words(query: str) -> list[str]:
    """Extract meaningful words from query, filtering out common words."""
    query_lower = query.lower().strip()
    query_words = query_lower.split()
    meaningful_words = [w for w in query_words if w not in _COMMON_WORDS and len(w) > 2]
    return meaningful_words if meaningful_words else query_words


def _calculate_relevance_score(
    query_lower: str, location_name_lower: str, meaningful_words: list[str], query_words: list[str]
) -> int | None:
    """Calculate relevance score for a location. Returns None if location should be skipped."""
    if query_lower == location_name_lower:
        return 1000

    if query_lower in location_name_lower:
        return 500

    matching_meaningful = sum(1 for word in meaningful_words if word in location_name_lower)
    if matching_meaningful == 0:
        return None

    matching_all = sum(1 for word in query_words if word in location_name_lower)
    return matching_meaningful * 100 + matching_all * 10


def _process_location(
    location: dict[str, Any], query_lower: str, meaningful_words: list[str], query_words: list[str]
) -> dict[str, Any] | None:
    """Process a single location and return result dict with relevance, or None if skipped."""
    location_type = location.get("type", "")
    if location_type not in ("stop", "station"):
        return None

    location_name = location.get("name", "")
    location_name_lower = location_name.lower()
    relevance = _calculate_relevance_score(
        query_lower, location_name_lower, meaningful_words, query_words
    )
    if relevance is None:
        return None

    return {
        "id": location.get("id", ""),
        "name": location_name,
        "type": location_type,
        "place": location.get("location", {}).get("city", "Berlin"),
        "relevance": relevance,
    }


async def _fetch_locations(session: aiohttp.ClientSession, query: str) -> list[dict[str, Any]]:
    """Fetch locations from VBB API."""
    base_url = "https://v6.bvg.transport.rest"
    url = f"{base_url}/locations"
    params: dict[str, str | int] = {"query": query, "results": 20}

    log_api_request("GET", url, params=params)

    async with session.get(url, params=params, ssl=False) as response:
        if response.status != 200:
            response_text = await response.text()
            raise RuntimeError(f"VBB API returned status {response.status}: {response_text}")

        data: dict[str, Any] | list[dict[str, Any]] = await response.json()
        if isinstance(data, list):
            return data
        locations = data.get("locations", [])
        if not isinstance(locations, list):
            return []
        return locations


def _process_search_results(
    locations: list[dict[str, Any]],
    query_lower: str,
    meaningful_words: list[str],
    query_words: list[str],
) -> list[dict[str, Any]]:
    """Process and sort search results."""
    results = []
    for location in locations:
        result = _process_location(location, query_lower, meaningful_words, query_words)
        if result:
            results.append(result)

    results.sort(key=lambda x: (-x.get("relevance", 0), x.get("name", "")))
    for result in results:
        result.pop("relevance", None)

    return results


async def search_stations_vbb(query: str) -> list[dict[str, Any]]:
    """Search for VBB stations using the VBB REST API."""
    try:
        async with aiohttp.ClientSession() as session:
            locations = await _fetch_locations(session, query)

            query_lower = query.lower().strip()
            query_words = query_lower.split()
            meaningful_words = _extract_meaningful_words(query)

            return _process_search_results(locations, query_lower, meaningful_words, query_words)
    except Exception as e:
        print(f"Error searching VBB stations: {e}", file=sys.stderr)
        return []


def _extract_line_info(dep: dict[str, Any]) -> tuple[str, str] | None:
    """Extract line name and product from departure. Returns None if line_name is empty."""
    line_obj = dep.get("line", {})
    line_name = line_obj.get("name", "") or line_obj.get("id", "") or ""
    if not line_name:
        return None

    product = line_obj.get("product", "") or line_obj.get("mode", "") or ""
    return line_name, product


def _get_destination_name(dep: dict[str, Any]) -> str:
    """Extract destination name from departure dict."""
    dest_obj = dep.get("destination")
    if not dest_obj or not isinstance(dest_obj, dict):
        return ""
    return dest_obj.get("name", "") or ""


def _normalize_destination_name(dest_name: str) -> str:
    """Normalize destination name by removing common suffixes."""
    return dest_name.replace(" (Berlin)", "")


def _are_destinations_equivalent(direction: str, dest_name: str) -> bool:
    """Check if direction and destination name refer to the same place."""
    if direction == dest_name:
        return True
    dest_name_clean = _normalize_destination_name(dest_name)
    return direction == dest_name_clean


def _extract_destinations(dep: dict[str, Any]) -> list[str]:
    """Extract destinations from departure, handling both direction and destination.name."""
    direction = dep.get("direction", "") or ""
    dest_name = _get_destination_name(dep)

    if not direction and not dest_name:
        return []
    if not direction:
        return [dest_name]
    if not dest_name:
        return [direction]
    if _are_destinations_equivalent(direction, dest_name):
        return [direction]

    return [dest_name, direction]


def _process_departures(
    departures_data: list[dict[str, Any]],
) -> tuple[dict[str, set[str]], dict[str, dict[str, Any]]]:
    """Process departures and extract routes and destinations."""
    routes: dict[str, set[str]] = {}
    route_details: dict[str, dict[str, Any]] = {}

    for dep in departures_data:
        line_info = _extract_line_info(dep)
        if not line_info:
            continue

        line_name, product = line_info
        if line_name not in routes:
            routes[line_name] = set()
            route_details[line_name] = {
                "line": line_name,
                "transport_type": product or "Unknown",
            }

        destinations = _extract_destinations(dep)
        routes[line_name].update(destinations)

    return routes, route_details


async def _fetch_departures(
    session: aiohttp.ClientSession, station_id: str
) -> list[dict[str, Any]] | None:
    """Fetch departures from VBB API."""
    base_url = "https://v6.bvg.transport.rest"
    url = f"{base_url}/stops/{station_id}/departures"
    params: dict[str, int] = {"duration": 120, "results": 300}

    log_api_request("GET", url, params=params)

    async with session.get(url, params=params, ssl=False) as response:
        if response.status != 200:
            return None

        data: dict[str, Any] = await response.json()
        departures = data.get("departures", [])
        if not isinstance(departures, list):
            return []
        return departures


def _build_vbb_station_info(station_id: str, station_name: str) -> dict[str, Any]:
    """Build station info dictionary for VBB."""
    return {
        "id": station_id,
        "name": station_name,
        "place": "Berlin",
        "api_provider": "vbb",
    }


def _build_vbb_routes_dict(
    routes: dict[str, set[str]], route_details: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Build routes dictionary for VBB."""
    return {
        line: {
            "destinations": sorted(destinations),
            "transport_type": route_details[line]["transport_type"],
        }
        for line, destinations in routes.items()
    }


async def _process_vbb_station_details(
    session: aiohttp.ClientSession, station_id: str
) -> dict[str, Any] | None:
    """Process VBB station details from API."""
    departures_data = await _fetch_departures(session, station_id)
    if not departures_data:
        return None

    routes, route_details = _process_departures(departures_data)
    station_name = departures_data[0].get("stop", {}).get("name", "") or station_id

    return {
        "station": _build_vbb_station_info(station_id, station_name),
        "routes": _build_vbb_routes_dict(routes, route_details),
    }


async def get_station_details_vbb(station_id: str) -> dict[str, Any] | None:
    """Get detailed information about a VBB station including routes."""
    try:
        async with aiohttp.ClientSession() as session:
            return await _process_vbb_station_details(session, station_id)
    except Exception as e:
        print(f"Error getting station details: {e}", file=sys.stderr)
        return None


def _generate_vbb_route_snippet(line: str, route_data: dict[str, Any]) -> str:
    """Generate config snippet for a single VBB route."""
    destinations = route_data.get("destinations", [])
    transport_type = route_data.get("transport_type", "")
    if not destinations:
        return ""

    first_dest = destinations[0]
    direction_name = f"->{first_dest[:20]}"  # Limit length
    match_strings = [f"{line} {dest}" for dest in destinations]

    return f"# {transport_type} {line}:\n" f'# "{direction_name}" = {match_strings}\n' "\n"


def generate_vbb_config_snippet(station_id: str, station_name: str, routes: dict[str, Any]) -> str:
    """Generate a TOML config snippet for a VBB station."""
    snippet = f"""[[routes.stops]]
# Station ID for {station_name} (Berlin)
# Found using: vbb-config search "{station_name}"
station_id = "{station_id}"
station_name = "{station_name}"
api_provider = "vbb"  # Use VBB REST API for Berlin
max_departures_per_stop = 15
max_departures_per_route = 2
show_ungrouped = true

[routes.stops.direction_mappings]
# Configure your direction mappings here based on the routes below:
"""

    for line, route_data in sorted(routes.items()):
        snippet += _generate_vbb_route_snippet(line, route_data)

    return snippet


def _print_search_error(query: str) -> None:
    """Print error message when no stations found."""
    print(f"\n❌ No stations found for '{query}'", file=sys.stderr)
    print("\n💡 Tips:", file=sys.stderr)
    print("  - Try a more specific query (e.g., include 'Berlin')", file=sys.stderr)
    print("  - Try a different spelling or partial name", file=sys.stderr)


def _print_station_routes(routes: dict[str, Any]) -> None:
    """Print available routes for a station."""
    print(f"  Available Routes ({len(routes)}):")
    for line, route_data in sorted(routes.items()):
        transport_type = route_data.get("transport_type", "")
        destinations = route_data.get("destinations", [])
        dest_str = ", ".join(destinations)
        print(f"    {transport_type} {line}: {dest_str}")


async def _process_station_and_show_config(station: dict[str, Any], index: int, total: int) -> None:
    """Process a single station and show its configuration."""
    station_id = station.get("id", "")
    station_name = station.get("name", "Unknown")
    station_place = station.get("place", "Unknown")

    print(f"\n[{index}/{total}] {station_name} ({station_place})")
    print(f"ID: {station_id}")
    print("-" * 70)

    details = await get_station_details_vbb(station_id)
    if not details:
        print("  No routes found or station has no departures.")
        return

    routes = details.get("routes", {})
    if not routes:
        print("  No routes found.")
        return

    _print_station_routes(routes)

    print("\n" + "=" * 70)
    print("Configuration Snippet:")
    print("=" * 70)
    config_snippet = generate_vbb_config_snippet(station_id, station_name, routes)
    print(config_snippet)
    print("=" * 70)


async def search_and_show_config(query: str) -> None:
    """Search for VBB stations and show config snippets."""
    print(f"Searching VBB REST API for: '{query}'\n")

    results = await search_stations_vbb(query)

    if not results:
        _print_search_error(query)
        sys.exit(1)

    print(f"Found {len(results)} station(s):\n")
    print("=" * 70)

    for i, station in enumerate(results, 1):
        await _process_station_and_show_config(station, i, len(results))


async def main() -> None:
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="VBB (Berlin) Departures Configuration Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for stations
  vbb-config search "Zoologischer Garten"

  # Search for stations
  vbb-config search "Ernst-Reuter-Platz"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for VBB stations")
    search_parser.add_argument("query", help="Station name to search for")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "search":
        await search_and_show_config(args.query)
    else:
        parser.print_help()
        sys.exit(1)


def cli_main() -> None:
    """CLI entry point for setuptools."""
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
