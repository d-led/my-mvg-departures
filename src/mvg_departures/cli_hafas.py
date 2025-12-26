"""CLI helpers for configuring HAFAS departures."""

import asyncio
import sys
from typing import Any

from pyhafas import HafasClient
from pyhafas.profile import (
    DBProfile,
    KVBProfile,
    NASAProfile,
    NVVProfile,
    RKRPProfile,
    VSNProfile,
    VVVProfile,
)

from mvg_departures.adapters.hafas_api.bvg_profile import BVGProfile
from mvg_departures.adapters.hafas_api.ssl_context import hafas_ssl_context
from mvg_departures.adapters.hafas_api.vbb_profile import VBBProfile

# List of profiles to try
# Note: VVO (Verkehrsverbund Oberelbe) might use DB profile or another profile
# The detect command will try all profiles to find which one works
PROFILES = {
    "db": DBProfile,
    "bvg": BVGProfile,
    "vbb": VBBProfile,
    "kvb": KVBProfile,
    "nvv": NVVProfile,
    "vvv": VVVProfile,
    "vsn": VSNProfile,
    "rkrp": RKRPProfile,
    "nasa": NASAProfile,
}


async def search_stations_hafas(query: str, profile: str | None = None) -> list[dict[str, Any]]:
    """Search for stations using HAFAS, trying different profiles if needed."""
    results: list[dict[str, Any]] = []

    # If profile specified, only try that one
    profiles_to_try = [profile] if profile else list(PROFILES.keys())

    for profile_name in profiles_to_try:
        if profile_name not in PROFILES:
            continue

        try:
            profile_class = PROFILES[profile_name]
            # Create client and make request with SSL verification disabled
            # (pyhafas may create connections during initialization)
            # Note: pyhafas methods are synchronous, not async
            with hafas_ssl_context():
                client = HafasClient(profile_class())
                locations = client.locations(query)  # Not async
            if locations:
                for location in locations:
                    location_obj = getattr(location, "location", None)
                    if not location_obj:
                        continue

                    station_id = getattr(location, "id", "")
                    station_name = getattr(location, "name", "")
                    city = (
                        getattr(location_obj, "city", None)
                        or getattr(location_obj, "name", None)
                        or ""
                    )

                    # Check if we already have this station
                    existing = next((r for r in results if r.get("id") == station_id), None)
                    if not existing:
                        results.append(
                            {
                                "id": station_id,
                                "name": station_name,
                                "place": city,
                                "profile": profile_name,
                            }
                        )
        except Exception as e:
            # Log the error for debugging but continue to next profile
            import sys

            print(f"  Profile '{profile_name}' failed: {e}", file=sys.stderr)
            continue

    return results


async def detect_profile_for_station(station_id: str) -> str | None:
    """Detect which HAFAS profile works for a given station ID."""
    from datetime import UTC, datetime

    for profile_name, profile_class in PROFILES.items():
        try:
            # Create client and make request with SSL verification disabled
            # (pyhafas may create connections during initialization)
            # Note: pyhafas methods are synchronous, not async
            with hafas_ssl_context():
                client = HafasClient(profile_class())
                # Try to get a single departure to test if this profile works
                departures = client.departures(  # Not async
                    station=station_id,
                    date=datetime.now(UTC),
                    max_trips=1,
                )
            # If we got results (even empty list means the station exists), this profile works
            if departures is not None:
                return profile_name
        except Exception as e:
            # Log the error for debugging but continue to next profile
            import sys

            print(f"  Profile '{profile_name}' failed: {e}", file=sys.stderr)
            continue

    return None


async def get_station_details_hafas(
    station_id: str, profile: str, limit: int = 50
) -> dict[str, Any] | None:
    """Get detailed information about a HAFAS station."""
    try:
        if profile not in PROFILES:
            return None

        profile_class = PROFILES[profile]

        from datetime import UTC, datetime

        # Create client and make request with SSL verification disabled
        # (pyhafas may create connections during initialization)
        # Note: pyhafas methods are synchronous, not async
        with hafas_ssl_context():
            client = HafasClient(profile_class())
            departures = client.departures(  # Not async
                station=station_id,
                date=datetime.now(UTC),
                max_trips=limit,
            )

        if not departures:
            return None

        # Extract unique routes and destinations
        routes: dict[str, set[str]] = {}  # line -> set of destinations
        route_details: dict[str, dict[str, Any]] = {}  # line -> details

        for dep in departures:
            line_obj = getattr(dep, "line", None)
            line_name = (
                getattr(line_obj, "name", None)
                or getattr(line_obj, "id", None)
                or getattr(line_obj, "fahrtNr", None)
                or ""
            )
            destination = getattr(dep, "direction", None) or getattr(dep, "destination", None) or ""
            product = getattr(line_obj, "product", None) or getattr(line_obj, "mode", None) or ""

            if not line_name:
                continue

            if line_name not in routes:
                routes[line_name] = set()
                route_details[line_name] = {
                    "line": line_name,
                    "transport_type": product or "Unknown",
                }
            if destination:
                routes[line_name].add(destination)

        # Try to get station name
        try:
            # Use SSL context manager to disable verification only for this HAFAS call
            # Note: client was created inside the context above, but we need to wrap the call
            # Note: pyhafas methods are synchronous, not async
            with hafas_ssl_context():
                location = client.location(station_id)  # Not async
            station_name = getattr(location, "name", None) or station_id
            location_obj = getattr(location, "location", None)
            city = (getattr(location_obj, "city", None) if location_obj else None) or ""
        except Exception:
            station_name = station_id
            city = ""

        return {
            "station": {
                "id": station_id,
                "name": station_name,
                "place": city,
                "profile": profile,
            },
            "routes": {
                line: {
                    "destinations": sorted(destinations),
                    "transport_type": route_details[line]["transport_type"],
                }
                for line, destinations in routes.items()
            },
        }
    except Exception:
        return None


def generate_hafas_config_snippet(
    station_id: str, station_name: str, profile: str, routes: dict[str, Any]
) -> str:
    """Generate a TOML config snippet for a HAFAS station."""
    snippet = f"""# HAFAS Station Configuration
# Generated for: {station_name} (Profile: {profile})

[[routes.stops]]
station_id = "{station_id}"
station_name = "{station_name}"
api_provider = "hafas"
hafas_profile = "{profile}"  # Auto-detected profile
max_departures_per_stop = 15
max_departures_per_route = 2
show_ungrouped = true

[routes.stops.direction_mappings]
# Configure your direction mappings here based on available routes:
"""

    # Group destinations by route for easier configuration
    for line, route_data in sorted(routes.items()):
        destinations = route_data.get("destinations", [])
        transport_type = route_data.get("transport_type", "")
        if destinations:
            # Create a suggested direction name
            # Use first destination or a generic name
            first_dest = destinations[0] if destinations else "Destination"
            direction_name = f"->{first_dest[:20]}"  # Limit length

            snippet += f"# {transport_type} {line}:\n"
            snippet += f'# "{direction_name}" = {destinations[:3]}\n'  # Show first 3
            if len(destinations) > 3:
                snippet += f"#   # ... and {len(destinations) - 3} more destinations\n"
            snippet += "\n"

    return snippet


async def search_and_show_config(query: str) -> None:
    """Search for HAFAS stations and show config snippets."""
    print(f"Searching HAFAS for: '{query}'\n")
    print("Trying profiles: " + ", ".join(PROFILES.keys()) + "\n")

    results = await search_stations_hafas(query)

    if not results:
        print(f"No stations found for '{query}'", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(results)} station(s):\n")
    print("=" * 70)

    for i, station in enumerate(results, 1):
        station_id = station.get("id", "")
        station_name = station.get("name", "Unknown")
        station_place = station.get("place", "Unknown")
        profile = station.get("profile", "unknown")

        print(f"\n[{i}/{len(results)}] {station_name} ({station_place})")
        print(f"ID: {station_id}")
        print(f"Profile: {profile}")
        print("-" * 70)

        # Get routes for this station
        details = await get_station_details_hafas(station_id, profile, limit=50)
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
        config_snippet = generate_hafas_config_snippet(station_id, station_name, profile, routes)
        print(config_snippet)
        print("=" * 70)


async def detect_and_show_config(station_id: str) -> None:
    """Detect profile for a station ID and show config."""
    print(f"Detecting HAFAS profile for station ID: {station_id}\n")
    print("Trying profiles: " + ", ".join(PROFILES.keys()) + "\n")

    profile = await detect_profile_for_station(station_id)

    if not profile:
        print(f"Could not detect profile for station '{station_id}'", file=sys.stderr)
        print("Tried profiles: " + ", ".join(PROFILES.keys()), file=sys.stderr)
        sys.exit(1)

    print(f"✓ Detected profile: {profile}\n")

    # Get station details
    details = await get_station_details_hafas(station_id, profile, limit=50)
    if not details:
        print(f"Could not get details for station '{station_id}'", file=sys.stderr)
        sys.exit(1)

    station_info = details.get("station", {})
    station_name = station_info.get("name", station_id)
    routes = details.get("routes", {})

    print(f"Station: {station_name}")
    print(f"Profile: {profile}")
    if routes:
        print(f"Routes: {len(routes)}")
        for line, route_data in sorted(list(routes.items())[:5]):
            destinations = route_data.get("destinations", [])
            print(f"  {line}: {', '.join(destinations[:3])}")
        if len(routes) > 5:
            print(f"  ... and {len(routes) - 5} more routes")

    print("\n" + "=" * 70)
    print("Configuration Snippet:")
    print("=" * 70)
    config_snippet = generate_hafas_config_snippet(station_id, station_name, profile, routes)
    print(config_snippet)


async def main() -> None:
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="HAFAS Departures Configuration Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for stations (tries all profiles)
  hafas-config search "Augsburg Hbf"

  # Detect profile for a known station ID
  hafas-config detect 9000589

  # Search with specific profile
  hafas-config search "Augsburg" --profile vvo
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for HAFAS stations")
    search_parser.add_argument("query", help="Station name to search for")
    search_parser.add_argument(
        "--profile",
        choices=list(PROFILES.keys()),
        help="Specific profile to use (default: try all)",
    )

    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect profile for a station ID")
    detect_parser.add_argument("station_id", help="Station ID (e.g., 9000589)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "search":
            await search_and_show_config(args.query)

        elif args.command == "detect":
            await detect_and_show_config(args.station_id)

    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


def cli_main() -> None:
    """Synchronous entry point for the CLI command."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
