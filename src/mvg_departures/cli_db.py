"""CLI helpers for configuring DB (Deutsche Bahn) departures."""

import asyncio
import json
import sys
from typing import Any

import aiohttp

from mvg_departures.adapters.db_api import DbDepartureRepository
from mvg_departures.adapters.db_api.http_client import DbHttpClient


async def search_stations_db(query: str) -> list[dict[str, Any]]:
    """Search for DB stations using the DB API."""
    try:
        async with aiohttp.ClientSession() as session:
            http_client = DbHttpClient(session=session)
            api_results = await http_client.search_stations(query)

            # Convert to CLI format with relevance scoring
            query_lower = query.lower().strip()
            query_words = query_lower.split()
            results = []
            for api_result in api_results:
                if not api_result.get("id"):
                    continue

                result = {
                    "id": str(api_result.get("id", "")),
                    "name": api_result.get("name", ""),
                    "place": api_result.get("place", ""),
                    "latitude": api_result.get("latitude", 0.0),
                    "longitude": api_result.get("longitude", 0.0),
                }

                # Better relevance scoring - prioritize exact matches and "Hbf"
                name_lower = result.get("name", "").lower()
                place_lower = result.get("place", "").lower()
                full_text = f"{name_lower} {place_lower}".lower()

                relevance = 0
                if query_lower == name_lower:
                    relevance = 10000  # Exact match
                elif query_lower in name_lower:
                    relevance = 5000  # Contains query
                elif all(word in full_text for word in query_words):
                    relevance = 2000  # All words present
                elif any(word in full_text for word in query_words):
                    relevance = 500  # Some words present
                else:
                    relevance = 100

                # Boost "Hbf" stations
                if "hbf" in name_lower or "hauptbahnhof" in name_lower:
                    relevance += 1000

                # Boost stations matching city name
                if "augsburg" in query_lower and "augsburg" in place_lower:
                    relevance += 500

                result["relevance"] = relevance
                results.append(result)

            results.sort(key=lambda x: (-x.get("relevance", 0), x.get("name", "")))
            for result in results:
                result.pop("relevance", None)

            return results
    except Exception as e:
        print(f"Error searching DB stations: {e}", file=sys.stderr)
        return []


async def get_station_details_db(
    station_id: str, limit: int = 100, duration_minutes: int = 120
) -> dict[str, Any] | None:
    """Get station details including routes and sub-stops from departures."""
    try:
        async with aiohttp.ClientSession() as session:
            repo = DbDepartureRepository(session=session)
            departures = await repo.get_departures(
                station_id, limit=limit, duration_minutes=duration_minutes
            )

            if not departures:
                return None

            # Extract routes and sub-stops from departures
            routes: dict[str, dict[str, Any]] = {}
            sub_stops: dict[str, dict[str, Any]] = {}

            for dep in departures:
                line = dep.line
                transport_type = dep.transport_type
                destination = dep.destination
                stop_point_id = dep.stop_point_global_id

                if not line:
                    continue

                # Track sub-stops
                if stop_point_id:
                    if stop_point_id not in sub_stops:
                        sub_stops[stop_point_id] = {
                            "id": stop_point_id,
                            "routes": {},
                            "transport_types": set(),
                        }
                    sub_stops[stop_point_id]["transport_types"].add(transport_type)

                    # Track routes per sub-stop
                    route_key = line
                    if route_key not in sub_stops[stop_point_id]["routes"]:
                        sub_stops[stop_point_id]["routes"][route_key] = {
                            "transport_type": transport_type,
                            "line": line,
                            "destinations": set(),
                        }
                    if destination:
                        sub_stops[stop_point_id]["routes"][route_key]["destinations"].add(
                            destination
                        )

                # Track overall routes
                route_key = line
                if route_key not in routes:
                    routes[route_key] = {
                        "transport_type": transport_type,
                        "line": line,
                        "destinations": set(),
                        "stop_points": set(),
                    }

                if destination:
                    routes[route_key]["destinations"].add(destination)
                if stop_point_id:
                    routes[route_key]["stop_points"].add(stop_point_id)

            # Convert sets to sorted lists
            for route in routes.values():
                route["destinations"] = sorted(route["destinations"])
                route["stop_points"] = sorted(route["stop_points"])

            for sub_stop in sub_stops.values():
                sub_stop["transport_types"] = sorted(sub_stop["transport_types"])
                for route in sub_stop["routes"].values():
                    route["destinations"] = sorted(route["destinations"])

            return {
                "station_id": station_id,
                "routes": routes,
                "sub_stops": sub_stops,
                "departures_count": len(departures),
            }
    except Exception as e:
        print(f"Error getting station details: {e}", file=sys.stderr)
        return None


async def _handle_search_command(query: str, output_json: bool) -> None:
    """Handle the search command."""
    results = await search_stations_db(query)

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


async def _handle_info_command(station_id: str, output_json: bool) -> None:
    """Handle the info command."""
    details = await get_station_details_db(station_id, limit=50)

    if output_json:
        print(json.dumps(details, indent=2, ensure_ascii=False, default=str))
        return

    if not details:
        print(f"Could not get details for station '{station_id}'", file=sys.stderr)
        sys.exit(1)

    routes = details.get("routes", {})
    print("\nStation Information:")
    print(f"  ID: {details.get('station_id', 'Unknown')}")
    print(f"\nRoutes: {len(routes)}")

    if routes:
        # Group by transport type for better readability
        by_type: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for route_name, route_data in routes.items():
            transport_type = route_data.get("transport_type", "Unknown")
            if transport_type not in by_type:
                by_type[transport_type] = []
            by_type[transport_type].append((route_name, route_data))

        # Display grouped by type
        type_order = ["Bus", "Tram", "S-Bahn", "U-Bahn", "RE", "RB", "IC/EC", "ICE"]
        for transport_type in type_order:
            if transport_type in by_type:
                print(f"\n  {transport_type}:")
                for route_name, route_data in sorted(by_type[transport_type]):
                    destinations = route_data.get("destinations", [])
                    dest_str = ", ".join(destinations[:3])
                    if len(destinations) > 3:
                        dest_str += f" (+{len(destinations) - 3} more)"
                    print(f"    {route_name}: {dest_str}")

        # Show other types
        for transport_type, route_list in sorted(by_type.items()):
            if transport_type not in type_order:
                print(f"\n  {transport_type}:")
                for route_name, route_data in sorted(route_list):
                    destinations = route_data.get("destinations", [])
                    dest_str = ", ".join(destinations[:3])
                    if len(destinations) > 3:
                        dest_str += f" (+{len(destinations) - 3} more)"
                    print(f"    {route_name}: {dest_str}")


async def _handle_routes_command(query: str, show_patterns: bool) -> None:
    """Handle the routes command."""
    # Check if query looks like a station ID (numeric)
    if query.isdigit():
        station_id = query
        station_name = f"Station {query}"
    else:
        # Search for station
        results = await search_stations_db(query)
        if not results:
            print(f"No stations found for '{query}'", file=sys.stderr)
            sys.exit(1)

        station = results[0]
        station_id = station.get("id", "")
        station_name = station.get("name", "Unknown")
        station_place = station.get("place", "")

        print(f"\nFound station: {station_name} ({station_place})")
        print(f"ID: {station_id}\n")

    details = await get_station_details_db(station_id, limit=200, duration_minutes=120)
    if not details:
        print("No routes found or station has no departures.")
        return

    routes = details.get("routes", {})
    if not routes:
        print("No routes found.")
        return

    print(f"\nStation: {station_name} ({station_id})")
    print(f"\nAvailable Routes ({len(routes)}):")
    print("=" * 70)

    # Group by transport type
    by_type: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for route_name, route_data in routes.items():
        transport_type = route_data.get("transport_type", "Unknown")
        if transport_type not in by_type:
            by_type[transport_type] = []
        by_type[transport_type].append((route_name, route_data))

    # Display grouped by type
    type_order = ["Bus", "Tram", "S-Bahn", "U-Bahn", "RE", "RB", "IC/EC", "ICE"]
    for transport_type in type_order:
        if transport_type in by_type:
            print(f"\n{transport_type}:")
            for route_name, route_data in sorted(by_type[transport_type]):
                destinations = route_data.get("destinations", [])
                print(f"  {route_name}:")
                for dest in destinations[:5]:
                    print(f"    → {dest}")
                if len(destinations) > 5:
                    print(f"    ... and {len(destinations) - 5} more")

    # Show other types
    for transport_type, route_list in sorted(by_type.items()):
        if transport_type not in type_order:
            print(f"\n{transport_type}:")
            for route_name, route_data in sorted(route_list):
                destinations = route_data.get("destinations", [])
                print(f"  {route_name}:")
                for dest in destinations[:5]:
                    print(f"    → {dest}")
                if len(destinations) > 5:
                    print(f"    ... and {len(destinations) - 5} more")

    # Show sub-stops (like MVG's stopPointGlobalId)
    sub_stops = details.get("sub_stops", {})
    if len(sub_stops) > 1:
        print("\n" + "=" * 70)
        print(f"Sub-Stops ({len(sub_stops)}):")
        print("=" * 70)
        print("# You can use sub-stop IDs to filter departures to specific platforms/areas")
        print("# Set station_id to a sub-stop ID to only show departures from that stop")

        for stop_id in sorted(sub_stops.keys()):
            sub_stop = sub_stops[stop_id]
            transport_types = sub_stop.get("transport_types", [])
            sub_routes = sub_stop.get("routes", {})
            types_str = ", ".join(transport_types)

            print(f"\n  # Sub-stop {stop_id} ({types_str}):")
            print(f'  # station_id = "{stop_id}"')

            for route_key in sorted(sub_routes.keys()):
                route = sub_routes[route_key]
                destinations = route.get("destinations", [])
                if destinations:
                    dest_str = ", ".join(destinations[:3])
                    if len(destinations) > 3:
                        dest_str += f" (+{len(destinations) - 3})"
                    print(f"  #   {route_key}: {dest_str}")

    if show_patterns:
        print("\n" + "=" * 70)
        print("Configuration Snippet:")
        print("=" * 70)
        config_snippet = generate_db_config_snippet(station_id, station_name, routes)
        print(config_snippet)
        print("=" * 70)


def generate_db_config_snippet(station_id: str, station_name: str, routes: dict[str, Any]) -> str:
    """Generate a TOML config snippet for a DB station.

    Args:
        station_id: Station ID.
        station_name: Station name.
        routes: Routes dictionary with transport types and destinations.
    """
    snippet = f"""[[stops]]
# Station ID for {station_name}
# Found using: db-config search "{station_name}"
station_id = "{station_id}"
station_name = "{station_name}"
api_provider = "db"
max_departures_per_stop = 30
max_departures_per_route = 2
show_ungrouped = true

[stops.direction_mappings]
# Configure your direction mappings here based on the routes below:
# Format: direction_name = ["pattern1", "pattern2"]
# Patterns can be: destination ("München"), route ("RE 5"), or route+destination ("RE 5 München")
"""

    # Add suggested direction mappings for each route
    for _route_name, route_data in sorted(routes.items()):
        destinations = route_data.get("destinations", [])
        transport_type = route_data.get("transport_type", "")
        line = route_data.get("line", "")

        if destinations:
            # Create a suggested direction name from first destination
            first_dest = destinations[0] if destinations else "Destination"
            direction_name = f"->{first_dest[:20]}"  # Limit length

            # Include line name in match strings for specificity
            # Show ALL destinations for copy-pasteable config
            match_strings = [f"{line} {dest}" for dest in destinations]

            snippet += f"\n# {transport_type} {line}:\n"
            snippet += f'# "{direction_name}" = {match_strings}\n'

    return snippet


async def _handle_generate_command(station_id: str, station_name: str) -> None:
    """Handle the generate command."""
    details = await get_station_details_db(station_id, limit=50)
    if not details:
        print(f"Could not get details for station '{station_id}'", file=sys.stderr)
        sys.exit(1)

    routes = details.get("routes", {})
    snippet = generate_db_config_snippet(station_id, station_name, routes)
    print(snippet)


def _setup_argparse() -> Any:
    """Set up and configure argument parser."""
    import argparse

    parser = argparse.ArgumentParser(
        description="DB (Deutsche Bahn) Departures Configuration Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for stations
  db-config search "Augsburg Hbf"

  # Show station details
  db-config info 8000013

  # List all routes for a station (by ID)
  db-config routes 8000013

  # Search for stations and show routes (by name)
  db-config routes "Augsburg Hbf"

  # Generate config snippet
  db-config generate 8000013 "Augsburg Hbf"

API: https://v6.db.transport.rest/api.html (100 req/min, no auth)
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    search_parser = subparsers.add_parser("search", help="Search for stations")
    search_parser.add_argument("query", help="Station name to search for")
    search_parser.add_argument("--json", action="store_true", help="Output as JSON")

    info_parser = subparsers.add_parser("info", help="Show station information")
    info_parser.add_argument("station_id", help="Station ID (e.g., 8000013)")
    info_parser.add_argument("--json", action="store_true", help="Output as JSON")

    routes_parser = subparsers.add_parser(
        "routes", help="List routes for a station (by ID or search query)"
    )
    routes_parser.add_argument(
        "query",
        help="Station ID (e.g., 8000013) or station name to search for",
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
            await _handle_info_command(args.station_id, args.json)
        elif args.command == "routes":
            await _handle_routes_command(args.query, not args.no_patterns)
        elif args.command == "generate":
            await _handle_generate_command(args.station_id, args.station_name)
        else:
            parser.print_help()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cli_main() -> None:
    """Synchronous entry point for the CLI command."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
