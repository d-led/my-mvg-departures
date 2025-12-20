"""Main entry point for the MVG departures application."""

import asyncio
import logging
import sys
from typing import Any

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.mvg_api import (
    MvgDepartureRepository,
    MvgStationRepository,
)
from mvg_departures.adapters.web import PyViewWebAdapter
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import StopConfiguration


def load_stop_configurations(config: AppConfig) -> list[StopConfiguration]:
    """Load stop configurations from app config."""
    stops_data = config.get_stops_config()
    stop_configs: list[StopConfiguration] = []

    for stop_data in stops_data:
        if not isinstance(stop_data, dict):
            continue

        station_id = stop_data.get("station_id")
        station_name = stop_data.get("station_name", station_id) or ""
        if not isinstance(station_name, str):
            station_name = str(station_id) if station_id else ""
        direction_mappings = stop_data.get("direction_mappings", {})
        max_departures = stop_data.get("max_departures_per_stop", config.mvg_api_limit)
        max_departures_per_route = stop_data.get("max_departures_per_route", 2)
        show_ungrouped = stop_data.get("show_ungrouped", True)  # Default to showing ungrouped

        if not station_id:
            continue

        stop_config = StopConfiguration(
            station_id=station_id,
            station_name=station_name,
            direction_mappings=direction_mappings,
            max_departures_per_stop=max_departures,
            max_departures_per_route=max_departures_per_route,
            show_ungrouped=show_ungrouped,
        )
        stop_configs.append(stop_config)

    return stop_configs


async def main() -> None:
    """Main application entry point."""
    config = AppConfig()

    # Load stop configurations
    stop_configs = load_stop_configurations(config)

    if not stop_configs:
        print(
            "Error: No stops configured.",
            file=sys.stderr,
        )
        print(
            "Please set STOPS_CONFIG environment variable or create a config.toml file.",
            file=sys.stderr,
        )
        print(
            'Example: STOPS_CONFIG=\'[{"station_id": "de:09162:100", "station_name": "Giesing", "direction_mappings": {"->Balanstr.": ["Messestadt"]}}]\'',
            file=sys.stderr,
        )
        print(
            "Or copy config.example.toml to config.toml and customize it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create aiohttp session for efficient HTTP connections
    async with aiohttp.ClientSession() as session:
        # Initialize repositories
        departure_repo = MvgDepartureRepository(session=session)
        station_repo = MvgStationRepository(session=session)

        # Initialize services
        grouping_service = DepartureGroupingService(departure_repo)

        # Initialize display adapter
        display_adapter = PyViewWebAdapter(grouping_service, stop_configs, config, session=session)

        try:
            await display_adapter.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
            await display_adapter.stop()


if __name__ == "__main__":
    asyncio.run(main())
