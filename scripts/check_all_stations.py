#!/usr/bin/env python3
"""Check if all stations in a TOML config file can be queried."""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

import aiohttp

# Add src to path
script_dir = Path(__file__).parent
project_dir = script_dir.parent
sys.path.insert(0, str(project_dir / "src"))

from mvg_departures.adapters.composite_departure_repository import (
    CompositeDepartureRepository,
)
from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.config.route_configuration_loader import (
    RouteConfigurationLoader,
)
from mvg_departures.application.services import DepartureGroupingService


async def check_stations(config_file: str, raw_output: bool = False) -> None:
    """Check if all stations in config can be queried."""
    config_path = Path(config_file).resolve()
    
    if not config_path.exists():
        print(f"ERROR: Config file '{config_file}' not found", file=sys.stderr)
        sys.exit(1)

    # Create config - handle .env permission errors gracefully
    try:
        config = AppConfig()
    except PermissionError:
        # If .env file has permission issues, create config without it
        # by temporarily removing the env_file from model_config
        from pydantic_settings import SettingsConfigDict
        # Create a custom config class that doesn't load .env
        class CheckConfig(AppConfig):
            model_config = SettingsConfigDict(
                env_file=None,  # Don't load .env file
                env_file_encoding="utf-8",
                case_sensitive=False,
                extra="ignore",
            )
        config = CheckConfig()
    
    config.config_file = config_path

    # Load route configurations
    try:
        route_configs = RouteConfigurationLoader.load(config)
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)

    if not route_configs:
        print("ERROR: No routes found in config", file=sys.stderr)
        sys.exit(1)

    # Collect all stop configurations
    all_stop_configs = []
    for route_config in route_configs:
        all_stop_configs.extend(route_config.stop_configs)

    if not all_stop_configs:
        print("ERROR: No stops found in config", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(all_stop_configs)} station(s) to check\n")

    # Use the same code path as the server - DepartureGroupingService
    async with aiohttp.ClientSession() as session:
        departure_repo = CompositeDepartureRepository(
            stop_configs=all_stop_configs,
            session=session,
        )
        grouping_service = DepartureGroupingService(departure_repo)

        results = []
        for stop_config in all_stop_configs:
            station_id = stop_config.station_id
            station_name = stop_config.station_name
            api_provider = stop_config.api_provider or "mvg"
            hafas_profile = stop_config.hafas_profile or "auto"

            print(f"Checking: {station_name} ({station_id})", end=" ... ")
            sys.stdout.flush()

            try:
                # For raw output, fetch raw departures first to see what API returns
                raw_departures = None
                if raw_output:
                    # Fetch raw departures using same parameters as server
                    raw_departures = await departure_repo.get_departures(
                        station_id,
                        limit=stop_config.max_departures_fetch or 200,
                        duration_minutes=stop_config.fetch_max_minutes_in_advance,
                        offset_minutes=stop_config.departure_leeway_minutes if stop_config.departure_leeway_minutes > 0 else 0,
                    )
                
                # Use the same method as the server - get_grouped_departures
                # This ensures we use the exact same code path and parameters as the server
                grouped = await grouping_service.get_grouped_departures(stop_config)
                
                # Flatten grouped departures for display
                departures = []
                for group in grouped:
                    departures.extend(group.departures)
                
                # Show counts
                if raw_output and raw_departures:
                    print(f"✓ OK ({len(departures)} grouped, {len(raw_departures)} raw departures)")
                else:
                    print(f"✓ OK ({len(departures)} departures)")
                
                if raw_output:
                    now_utc = datetime.now(UTC)
                    # Get local timezone for display
                    import zoneinfo
                    try:
                        local_tz = zoneinfo.ZoneInfo("Europe/Berlin")
                    except Exception:
                        local_tz = now_utc.astimezone().tzinfo
                    now_local = now_utc.astimezone(local_tz)
                    print(f"  Current time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  Current time (local): {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    print(f"  Raw departures (before grouping/filtering):")
                    print(f"  (Index shows position in API response - useful for adjusting fetch_max_minutes_in_advance)")
                    for idx, dep in enumerate(raw_departures, start=0):  # Show all raw departures with index
                        # Departure time is in UTC (from API)
                        dep_time_utc = dep.time.astimezone(UTC) if dep.time.tzinfo else dep.time.replace(tzinfo=UTC)
                        dep_time_local = dep_time_utc.astimezone(local_tz)
                        time_diff = (dep_time_utc - now_utc).total_seconds() / 60
                        print(f"    [{idx:3d}] {dep_time_local.strftime('%H:%M:%S %Z')} ({dep_time_utc.strftime('%H:%M:%S UTC')}, {time_diff:+.1f} min) - "
                              f"{dep.transport_type} {dep.line} -> {dep.destination} "
                              f"[Platform: {dep.platform}, Delay: {dep.delay_seconds or 0}s]")
                
                results.append(
                    (station_id, station_name, api_provider, hafas_profile, True, len(departures), None)
                )
            except Exception as e:
                error_msg = str(e)
                print(f"✗ FAILED: {error_msg}")
                if raw_output:
                    import traceback
                    print(f"  Traceback:")
                    traceback.print_exc()
                results.append(
                    (station_id, station_name, api_provider, hafas_profile, False, 0, error_msg)
                )

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r[4]]
    failed = [r for r in results if not r[4]]

    print(f"\nSuccessful: {len(successful)}/{len(results)}")
    for station_id, station_name, api_provider, hafas_profile, _, count, _ in successful:
        profile_info = f" (profile: {hafas_profile})" if api_provider == "hafas" else ""
        print(f"  ✓ {station_name} ({station_id}) [{api_provider}]{profile_info}: {count} departures")

    if failed:
        print(f"\nFailed: {len(failed)}/{len(results)}")
        for station_id, station_name, api_provider, hafas_profile, _, _, error in failed:
            profile_info = f" (profile: {hafas_profile})" if api_provider == "hafas" else ""
            print(f"  ✗ {station_name} ({station_id}) [{api_provider}]{profile_info}: {error}")

    if failed:
        sys.exit(1)
    else:
        print("\nAll stations are accessible! ✓")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check if all stations in a TOML config file can be queried"
    )
    parser.add_argument(
        "config_file",
        help="Path to the TOML configuration file",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show raw departure data with timestamps and timezone information",
    )
    
    args = parser.parse_args()
    
    asyncio.run(check_stations(args.config_file, raw_output=args.raw))

