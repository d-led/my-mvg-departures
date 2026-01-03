#!/usr/bin/env python3
"""Check if all stations in a TOML config file can be queried."""

import argparse
import asyncio
import sys
from dataclasses import dataclass
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


@dataclass(frozen=True)
class StationResult:
    """Result of checking a single station."""

    station_id: str
    station_name: str
    api_provider: str
    success: bool
    count: int
    error: str | None


def _create_config_without_env() -> AppConfig:
    """Create AppConfig without loading .env file (for permission error handling)."""
    from pydantic_settings import SettingsConfigDict
    
    class CheckConfig(AppConfig):
        model_config = SettingsConfigDict(
            env_file=None,
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
        )
    return CheckConfig()


def _load_app_config(config_file: str) -> AppConfig:
    """Load application configuration, handling .env permission errors."""
    config_path = Path(config_file).resolve()
    
    if not config_path.exists():
        print(f"ERROR: Config file '{config_file}' not found", file=sys.stderr)
        sys.exit(1)
    
    try:
        config = AppConfig()
    except PermissionError:
        config = _create_config_without_env()
    
    config.config_file = config_path
    return config


def _load_route_configs(config: AppConfig) -> list:
    """Load route configurations from config file."""
    try:
        route_configs = RouteConfigurationLoader.load(config)
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not route_configs:
        print("ERROR: No routes found in config", file=sys.stderr)
        sys.exit(1)
    
    return route_configs


def _collect_stop_configs(route_configs: list) -> list:
    """Collect all stop configurations from route configurations."""
    all_stop_configs = []
    for route_config in route_configs:
        all_stop_configs.extend(route_config.stop_configs)
    
    if not all_stop_configs:
        print("ERROR: No stops found in config", file=sys.stderr)
        sys.exit(1)
    
    return all_stop_configs


async def check_stations(config_file: str, raw_output: bool = False) -> None:
    """Check if all stations in config can be queried."""
    config = _load_app_config(config_file)
    route_configs = _load_route_configs(config)
    all_stop_configs = _collect_stop_configs(route_configs)
    
    print(f"Found {len(all_stop_configs)} station(s) to check\n")
    
    async with aiohttp.ClientSession() as session:
        departure_repo = CompositeDepartureRepository(
            stop_configs=all_stop_configs,
            session=session,
        )
        grouping_service = DepartureGroupingService(departure_repo)
        results = await _check_all_stations(
            all_stop_configs, departure_repo, grouping_service, raw_output
        )

    _print_summary(results)


def _get_local_timezone() -> object:
    """Get local timezone for display."""
    import zoneinfo
    try:
        return zoneinfo.ZoneInfo("Europe/Berlin")
    except Exception:
        return datetime.now(UTC).astimezone().tzinfo


def _print_raw_departure_details(raw_departures: list) -> None:
    """Print detailed raw departure information."""
    now_utc = datetime.now(UTC)
    local_tz = _get_local_timezone()
    now_local = now_utc.astimezone(local_tz)
    
    print(f"  Current time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Current time (local): {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  Raw departures (before grouping/filtering):")
    print(f"  (Index shows position in API response - useful for adjusting fetch_max_minutes_in_advance)")
    
    for idx, dep in enumerate(raw_departures, start=0):
        dep_time_utc = dep.time.astimezone(UTC) if dep.time.tzinfo else dep.time.replace(tzinfo=UTC)
        dep_time_local = dep_time_utc.astimezone(local_tz)
        time_diff = (dep_time_utc - now_utc).total_seconds() / 60
        print(f"    [{idx:3d}] {dep_time_local.strftime('%H:%M:%S %Z')} ({dep_time_utc.strftime('%H:%M:%S UTC')}, {time_diff:+.1f} min) - "
              f"{dep.transport_type} {dep.line} -> {dep.destination} "
              f"[Platform: {dep.platform}, Delay: {dep.delay_seconds or 0}s]")


def _flatten_grouped_departures(grouped: list) -> list:
    """Flatten grouped departures into a single list."""
    departures = []
    for group in grouped:
        departures.extend(group.departures)
    return departures


async def _fetch_raw_departures(
    departure_repo: CompositeDepartureRepository, stop_config, station_id: str
) -> list | None:
    """Fetch raw departures for a station."""
    return await departure_repo.get_departures(
        station_id,
        limit=stop_config.max_departures_fetch or 200,
        duration_minutes=stop_config.fetch_max_minutes_in_advance,
        offset_minutes=stop_config.departure_leeway_minutes if stop_config.departure_leeway_minutes > 0 else 0,
    )


async def _check_single_station(
    stop_config,
    departure_repo: CompositeDepartureRepository,
    grouping_service: DepartureGroupingService,
    raw_output: bool,
) -> tuple:
    """Check a single station and return result tuple."""
    station_id = stop_config.station_id
    station_name = stop_config.station_name
    api_provider = stop_config.api_provider or "mvg"
    
    print(f"Checking: {station_name} ({station_id})", end=" ... ")
    sys.stdout.flush()
    
    try:
        raw_departures = None
        if raw_output:
            raw_departures = await _fetch_raw_departures(departure_repo, stop_config, station_id)
        
        grouped = await grouping_service.get_grouped_departures(stop_config)
        departures = _flatten_grouped_departures(grouped)
        
        if raw_output and raw_departures:
            print(f"✓ OK ({len(departures)} grouped, {len(raw_departures)} raw departures)")
        else:
            print(f"✓ OK ({len(departures)} departures)")
        
        if raw_output:
            _print_raw_departure_details(raw_departures)
        
        return (station_id, station_name, api_provider, True, len(departures), None)
    except Exception as e:
        error_msg = str(e)
        print(f"✗ FAILED: {error_msg}")
        if raw_output:
            import traceback
            print(f"  Traceback:")
            traceback.print_exc()
        return (station_id, station_name, api_provider, False, 0, error_msg)


async def _check_all_stations(
    all_stop_configs: list,
    departure_repo: CompositeDepartureRepository,
    grouping_service: DepartureGroupingService,
    raw_output: bool,
) -> list:
    """Check all stations and return results."""
    results = []
    for stop_config in all_stop_configs:
        result = await _check_single_station(
            stop_config, departure_repo, grouping_service, raw_output
        )
        results.append(result)
    return results


def _format_station_result(result: StationResult) -> str:
    """Format a single station result line."""
    if result.error:
        return f"  ✗ {result.station_name} ({result.station_id}) [{result.api_provider}]: {result.error}"
    return f"  ✓ {result.station_name} ({result.station_id}) [{result.api_provider}]: {result.count} departures"


def _tuple_to_result(tup: tuple) -> StationResult:
    """Convert result tuple to StationResult dataclass."""
    station_id, station_name, api_provider, success, count, error = tup
    return StationResult(
        station_id=station_id,
        station_name=station_name,
        api_provider=api_provider,
        success=success,
        count=count or 0,
        error=error,
    )


def _print_successful_stations(successful: list, total: int) -> None:
    """Print successful station results."""
    print(f"\nSuccessful: {len(successful)}/{total}")
    for result_tuple in successful:
        result = _tuple_to_result(result_tuple)
        if result.success:
            print(_format_station_result(result))


def _print_failed_stations(failed: list, total: int) -> None:
    """Print failed station results."""
    if not failed:
        return
    print(f"\nFailed: {len(failed)}/{total}")
    for result_tuple in failed:
        result = _tuple_to_result(result_tuple)
        print(_format_station_result(result))


def _print_summary(results: list) -> None:
    """Print summary of station check results."""
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    successful = [r for r in results if r[3]]
    failed = [r for r in results if not r[3]]
    total = len(results)
    
    _print_successful_stations(successful, total)
    _print_failed_stations(failed, total)
    
    if failed:
        sys.exit(1)
    
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

