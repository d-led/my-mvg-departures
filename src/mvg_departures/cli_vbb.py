"""CLI helpers for configuring VBB (Berlin) departures."""

import asyncio
import sys
from typing import Any

import aiohttp


async def search_stations_vbb(query: str) -> list[dict[str, Any]]:
    """Search for VBB stations using the VBB REST API."""
    base_url = "https://v6.bvg.transport.rest"
    url = f"{base_url}/locations"
    params: dict[str, str | int] = {"query": query, "results": 20}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, ssl=False) as response:
                if response.status != 200:
                    response_text = await response.text()
                    raise RuntimeError(
                        f"VBB API returned status {response.status}: {response_text}"
                    )

                data = await response.json()
                locations = data if isinstance(data, list) else data.get("locations", [])

                results = []
                query_lower = query.lower()
                query_words = set(query_lower.split())

                for location in locations:
                    location_id = location.get("id", "")
                    location_name = location.get("name", "")
                    location_type = location.get("type", "")

                    # Only include stops/stations, not POIs
                    if location_type not in ("stop", "station"):
                        continue

                    # Filter by relevance: check if query words appear in station name
                    location_name_lower = location_name.lower()
                    # Count how many query words match
                    matching_words = sum(1 for word in query_words if word in location_name_lower)

                    # Only include if at least one word matches (or exact match)
                    if matching_words > 0 or query_lower in location_name_lower:
                        results.append(
                            {
                                "id": location_id,
                                "name": location_name,
                                "type": location_type,
                                "place": location.get("location", {}).get("city", "Berlin"),
                                "relevance": matching_words,  # For sorting
                            }
                        )

                # Sort by relevance (more matching words first), then alphabetically
                results.sort(key=lambda x: (-x.get("relevance", 0), x.get("name", "")))
                # Remove relevance from output
                for result in results:
                    result.pop("relevance", None)

                return results
        except Exception as e:
            print(f"Error searching VBB stations: {e}", file=sys.stderr)
            return []


async def get_station_details_vbb(station_id: str) -> dict[str, Any] | None:
    """Get detailed information about a VBB station including routes."""
    base_url = "https://v6.bvg.transport.rest"
    url = f"{base_url}/stops/{station_id}/departures"
    # Get many departures to capture all unique destinations
    # Use a longer duration (2 hours) and high result count to get all destinations
    # This is especially important for lines like U2 which have many stops
    params: dict[str, int] = {"duration": 120, "results": 300}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, ssl=False) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                departures_data = data.get("departures", [])

                if not departures_data:
                    return None

                # Extract unique routes and destinations
                routes: dict[str, set[str]] = {}  # line -> set of destinations
                route_details: dict[str, dict[str, Any]] = {}  # line -> details

                for dep in departures_data:
                    line_obj = dep.get("line", {})
                    line_name = line_obj.get("name", "") or line_obj.get("id", "") or ""
                    product = line_obj.get("product", "") or line_obj.get("mode", "") or ""

                    if not line_name:
                        continue

                    # Extract destination - prefer destination.name (dict) over direction (string)
                    destination = ""
                    dest_obj = dep.get("destination")
                    if dest_obj and isinstance(dest_obj, dict):
                        destination = dest_obj.get("name", "") or ""
                    if not destination:
                        destination = dep.get("direction", "") or ""

                    if line_name not in routes:
                        routes[line_name] = set()
                        route_details[line_name] = {
                            "line": line_name,
                            "transport_type": product or "Unknown",
                        }
                    if destination:
                        routes[line_name].add(destination)

                # Get station name from first departure or use station_id
                station_name = departures_data[0].get("stop", {}).get("name", "") or station_id

                return {
                    "station": {
                        "id": station_id,
                        "name": station_name,
                        "place": "Berlin",
                        "api_provider": "vbb",
                    },
                    "routes": {
                        line: {
                            "destinations": sorted(destinations),
                            "transport_type": route_details[line]["transport_type"],
                        }
                        for line, destinations in routes.items()
                    },
                }
        except Exception as e:
            print(f"Error getting station details: {e}", file=sys.stderr)
            return None


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
        destinations = route_data.get("destinations", [])
        transport_type = route_data.get("transport_type", "")
        if destinations:
            # Create a suggested direction name
            first_dest = destinations[0] if destinations else "Destination"
            direction_name = f"->{first_dest[:20]}"  # Limit length

            # Include line name in match strings (e.g., "U9 Osloer Str." instead of just "Osloer Str.")
            # This makes matching more specific and avoids conflicts between different lines
            match_strings = [f"{line} {dest}" for dest in destinations[:3]]

            snippet += f"# {transport_type} {line}:\n"
            snippet += f'# "{direction_name}" = {match_strings}\n'  # Show first 3 with line names
            if len(destinations) > 3:
                snippet += f"#   # ... and {len(destinations) - 3} more destinations\n"
            snippet += "\n"

    return snippet


async def search_and_show_config(query: str) -> None:
    """Search for VBB stations and show config snippets."""
    print(f"Searching VBB REST API for: '{query}'\n")

    results = await search_stations_vbb(query)

    if not results:
        print(f"\n❌ No stations found for '{query}'", file=sys.stderr)
        print("\n💡 Tips:", file=sys.stderr)
        print("  - Try a more specific query (e.g., include 'Berlin')", file=sys.stderr)
        print("  - Try a different spelling or partial name", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(results)} station(s):\n")
    print("=" * 70)

    for i, station in enumerate(results, 1):
        station_id = station.get("id", "")
        station_name = station.get("name", "Unknown")
        station_place = station.get("place", "Unknown")

        print(f"\n[{i}/{len(results)}] {station_name} ({station_place})")
        print(f"ID: {station_id}")
        print("-" * 70)

        # Get routes for this station
        details = await get_station_details_vbb(station_id)
        if not details:
            print("  No routes found or station has no departures.")
            continue

        routes = details.get("routes", {})
        if not routes:
            print("  No routes found.")
            continue

        print(f"  Available Routes ({len(routes)}):")
        for line, route_data in sorted(routes.items()):
            transport_type = route_data.get("transport_type", "")
            destinations = route_data.get("destinations", [])
            dest_str = ", ".join(destinations[:5])
            if len(destinations) > 5:
                dest_str += f" ... (+{len(destinations) - 5} more)"
            print(f"    {transport_type} {line}: {dest_str}")

        # Generate and show config snippet
        print("\n" + "=" * 70)
        print("Configuration Snippet:")
        print("=" * 70)
        config_snippet = generate_vbb_config_snippet(station_id, station_name, routes)
        print(config_snippet)
        print("=" * 70)


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
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
