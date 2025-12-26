#!/usr/bin/env python3
"""Check if all stations in a TOML config file can be queried."""

import asyncio
import sys
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


async def check_stations(config_file: str) -> None:
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

    # Create composite repository
    async with aiohttp.ClientSession() as session:
        departure_repo = CompositeDepartureRepository(
            stop_configs=all_stop_configs,
            session=session,
        )

        results = []
        for stop_config in all_stop_configs:
            station_id = stop_config.station_id
            station_name = stop_config.station_name
            api_provider = stop_config.api_provider or "mvg"
            hafas_profile = stop_config.hafas_profile or "auto"

            print(f"Checking: {station_name} ({station_id})", end=" ... ")
            sys.stdout.flush()

            try:
                departures = await departure_repo.get_departures(
                    station_id, limit=5
                )
                print(f"✓ OK ({len(departures)} departures)")
                results.append(
                    (station_id, station_name, api_provider, hafas_profile, True, len(departures), None)
                )
            except Exception as e:
                error_msg = str(e)
                print(f"✗ FAILED: {error_msg}")
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
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <config.toml>", file=sys.stderr)
        print(f"Example: {sys.argv[0]} config.toml", file=sys.stderr)
        sys.exit(1)

    asyncio.run(check_stations(sys.argv[1]))

