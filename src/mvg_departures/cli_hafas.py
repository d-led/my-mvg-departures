"""CLI helpers for configuring HAFAS departures."""

import argparse
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

from mvg_departures.adapters.hafas_api.ssl_context import hafas_ssl_context

# List of profiles to try
# Note: VVO (Verkehrsverbund Oberelbe) might use DB profile or another profile
# The detect command will try all profiles to find which one works
# Note: BVG and VBB profiles are not included here because Berlin stations
# should use the VBB REST API (api_provider = "vbb") instead of HAFAS
PROFILES = {
    "db": DBProfile,
    # "bvg": BVGProfile,  # Use VBB REST API for Berlin instead
    # "vbb": VBBProfile,  # Use VBB REST API for Berlin instead
    "kvb": KVBProfile,
    "nvv": NVVProfile,
    "vvv": VVVProfile,
    "vsn": VSNProfile,
    "rkrp": RKRPProfile,
    "nasa": NASAProfile,
}


def _extract_error_message(e: Exception) -> str:
    """Extract detailed error message from exception."""
    error_msg = str(e) if str(e) else f"{type(e).__name__}"

    if hasattr(e, "message") and e.message:
        error_msg = f"{error_msg}: {e.message}"
    elif hasattr(e, "args") and e.args:
        if len(e.args) > 1:
            error_msg = f"{error_msg}: {e.args[1]}"
        elif len(e.args) == 1 and str(e.args[0]) != error_msg:
            error_msg = f"{error_msg}: {e.args[0]}"

    if hasattr(e, "__cause__") and e.__cause__:
        error_msg = f"{error_msg} (caused by: {e.__cause__})"
    elif hasattr(e, "__context__") and e.__context__:
        error_msg = f"{error_msg} (context: {e.__context__})"

    return error_msg


def _process_location(
    location: Any, profile_name: str, existing_ids: set[str]
) -> dict[str, Any] | None:
    """Process a single location and return station dict, or None if skipped."""
    location_obj = getattr(location, "location", None)
    if not location_obj:
        return None

    station_id = getattr(location, "id", "")
    if station_id in existing_ids:
        return None

    station_name = getattr(location, "name", "")
    city = getattr(location_obj, "city", None) or getattr(location_obj, "name", None) or ""

    return {
        "id": station_id,
        "name": station_name,
        "place": city,
        "profile": profile_name,
    }


def _search_with_profile(query: str, profile_name: str) -> list[dict[str, Any]]:
    """Search for stations using a specific HAFAS profile."""
    if profile_name not in PROFILES:
        return []

    try:
        profile_class = PROFILES[profile_name]
        with hafas_ssl_context():
            client = HafasClient(profile_class())
            locations = client.locations(query)

        if not locations:
            return []

        existing_ids: set[str] = set()
        results = []
        for location in locations:
            station = _process_location(location, profile_name, existing_ids)
            if station:
                existing_ids.add(station["id"])
                results.append(station)

        return results
    except Exception as e:
        error_msg = _extract_error_message(e)
        print(f"  Profile '{profile_name}' failed: {error_msg}", file=sys.stderr)
        return []


async def search_stations_hafas(query: str, profile: str | None = None) -> list[dict[str, Any]]:
    """Search for stations using HAFAS, trying different profiles if needed."""
    profiles_to_try = [profile] if profile else list(PROFILES.keys())

    all_results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for profile_name in profiles_to_try:
        profile_results = _search_with_profile(query, profile_name)
        for result in profile_results:
            if result["id"] not in seen_ids:
                seen_ids.add(result["id"])
                all_results.append(result)

    return all_results


def _test_profile_for_station(station_id: str, profile_name: str, profile_class: type) -> bool:
    """Test if a profile works for a given station ID. Returns True if profile works."""
    from datetime import UTC, datetime

    try:
        with hafas_ssl_context():
            client = HafasClient(profile_class())
            departures = client.departures(
                station=station_id,
                date=datetime.now(UTC),
                max_trips=1,
            )
        return departures is not None
    except Exception as e:
        error_msg = _extract_error_message(e)
        print(f"  Profile '{profile_name}' failed: {error_msg}", file=sys.stderr)
        return False


async def detect_profile_for_station(station_id: str) -> str | None:
    """Detect which HAFAS profile works for a given station ID."""
    for profile_name, profile_class in PROFILES.items():
        if _test_profile_for_station(station_id, profile_name, profile_class):
            return profile_name
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
    except Exception as e:
        # Log the error for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"Error getting station details for {station_id} with profile {profile}: {e}")
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


async def search_and_show_config(query: str, profile: str | None = None) -> None:
    """Search for HAFAS stations and show config snippets."""
    print(f"Searching HAFAS for: '{query}'\n")
    if profile:
        print(f"Using profile: {profile}\n")
    else:
        print("Trying profiles: " + ", ".join(PROFILES.keys()) + "\n")

    results = await search_stations_hafas(query, profile=profile)

    if not results:
        print(f"\n❌ No stations found for '{query}'", file=sys.stderr)
        print("\n💡 Tips:", file=sys.stderr)
        print("  - Try a more specific query (e.g., include city name)", file=sys.stderr)
        print("  - Try a different spelling or partial name", file=sys.stderr)
        if not profile:
            print("  - Try specifying a profile: --profile <profile_name>", file=sys.stderr)
            print("    Available profiles: " + ", ".join(PROFILES.keys()), file=sys.stderr)
            print("\n    Profile regions:", file=sys.stderr)
            print("      db    - Deutsche Bahn (Germany-wide)", file=sys.stderr)
            print("      kvb   - Cologne", file=sys.stderr)
            print("      nvv   - North Hesse (e.g., Kassel)", file=sys.stderr)
            print("      vvv   - Vorarlberg, Austria", file=sys.stderr)
            print("      vsn   - South Lower Saxony", file=sys.stderr)
            print("      rkrp  - Rhine district Neuss", file=sys.stderr)
            print("      nasa  - Augsburg", file=sys.stderr)
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
        print(
            f"⚠ Could not get details for station '{station_id}' with profile '{profile}'",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print("This might mean:", file=sys.stderr)
        print("  - No departures available at this time", file=sys.stderr)
        print("  - The station ID is invalid for this profile", file=sys.stderr)
        print("  - Network/API error occurred", file=sys.stderr)
        print("", file=sys.stderr)
        print("However, you can still use this station ID in your config file:")
        print("", file=sys.stderr)
        print(f'station_id = "{station_id}"')
        print('api_provider = "hafas"')
        print(f'hafas_profile = "{profile}"')
        print("", file=sys.stderr)
        sys.exit(0)  # Exit with success since we detected the profile

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


def _setup_argparse() -> argparse.ArgumentParser:
    """Set up and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="HAFAS Departures Configuration Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for stations (tries all profiles)
  hafas-config search "München Hbf"
  hafas-config search "Köln Hbf"

  # Search with specific profile (faster and more reliable)
  hafas-config search "Augsburg Hbf" --profile nasa
  hafas-config search "Kassel Hbf" --profile nvv

  # Detect profile for a known station ID
  hafas-config detect 9000589

Available profiles and their regions:
  db    - Deutsche Bahn (Germany-wide, most common)
  kvb   - Kölner Verkehrs-Betriebe (Cologne)
  nvv   - Nordhessischer VerkehrsVerbund (North Hesse, e.g., Kassel)
  vvv   - Verkehrsverbund Vorarlberg (Vorarlberg, Austria)
  vsn   - Verkehrsverbund Süd-Niedersachsen (South Lower Saxony)
  rkrp  - Rhein-Kreis Neuss (Rhine district Neuss)
  nasa  - Nahverkehrsservice Augsburg (Augsburg)

Note: For Berlin stations, use the VBB REST API instead:
  curl "https://v6.bvg.transport.rest/locations?query=Zoologischer%20Garten"
  Then use api_provider = "vbb" in your config (not "hafas")
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    search_parser = subparsers.add_parser("search", help="Search for HAFAS stations")
    search_parser.add_argument("query", help="Station name to search for")
    search_parser.add_argument(
        "--profile",
        choices=list(PROFILES.keys()),
        help="Specific profile to use (default: try all)",
    )

    detect_parser = subparsers.add_parser("detect", help="Detect profile for a station ID")
    detect_parser.add_argument("station_id", help="Station ID (e.g., 9000589)")
    detect_parser.add_argument(
        "--profile",
        choices=list(PROFILES.keys()),
        help="Force a specific profile instead of auto-detecting",
    )

    return parser


def _display_station_details(station_name: str, profile: str, routes: dict[str, Any]) -> None:
    """Display station details and routes."""
    print(f"Station: {station_name}")
    print(f"Profile: {profile}")
    if routes:
        print(f"Routes: {len(routes)}")
        for line, route_data in sorted(list(routes.items())[:5]):
            destinations = route_data.get("destinations", [])
            print(f"  {line}: {', '.join(destinations[:3])}")
        if len(routes) > 5:
            print(f"  ... and {len(routes) - 5} more routes")


async def _handle_detect_with_profile(station_id: str, profile: str) -> None:
    """Handle detect command with forced profile."""
    print(f"Using profile '{profile}' for station ID: {station_id}\n")
    details = await get_station_details_hafas(station_id, profile, limit=50)
    if not details:
        print(
            f"Could not get details for station '{station_id}' with profile '{profile}'",
            file=sys.stderr,
        )
        print(f"Station ID: {station_id}", file=sys.stderr)
        print(f"Profile: {profile}", file=sys.stderr)
        sys.exit(1)

    station_info = details.get("station", {})
    station_name = station_info.get("name", station_id)
    routes = details.get("routes", {})

    _display_station_details(station_name, profile, routes)

    config_snippet = generate_hafas_config_snippet(station_id, station_name, profile, routes)
    print("\n" + "=" * 70)
    print("Configuration Snippet:")
    print("=" * 70)
    print(config_snippet)


async def _handle_detect_command(station_id: str, profile: str | None) -> None:
    """Handle detect command, either with forced profile or auto-detection."""
    if profile:
        await _handle_detect_with_profile(station_id, profile)
    else:
        await detect_and_show_config(station_id)


async def main() -> None:
    """Main CLI entry point."""
    parser = _setup_argparse()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "search":
            await search_and_show_config(args.query, profile=getattr(args, "profile", None))
        elif args.command == "detect":
            profile = getattr(args, "profile", None)
            await _handle_detect_command(args.station_id, profile)
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
