"""Main entry point for the MVG departures application."""

import asyncio
import logging
import sys

import aiohttp

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.config.route_configuration_loader import (
    RouteConfigurationLoader,
)
from mvg_departures.adapters.mvg_api import (
    MvgDepartureRepository,
)
from mvg_departures.adapters.web import PyViewWebAdapter
from mvg_departures.application.services import DepartureGroupingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)


async def main() -> None:
    """Main application entry point."""
    config = AppConfig()

    # Load route configurations
    try:
        route_configs = RouteConfigurationLoader.load(config)
        logger = logging.getLogger(__name__)
        logger.info(f"Loaded {len(route_configs)} route(s):")
        for route_config in route_configs:
            logger.info(
                f"  - Path: '{route_config.path}' with {len(route_config.stop_configs)} stop(s)"
            )
    except ValueError as e:
        print(f"Error: Invalid route configuration: {e}", file=sys.stderr)
        sys.exit(1)

    if not route_configs:
        print(
            "Error: No routes configured.",
            file=sys.stderr,
        )
        print(
            "Please configure routes in your config.toml file.",
            file=sys.stderr,
        )
        print(
            "Either use [[routes]] with path and stops, or use [[stops]] for default route at '/'.",
            file=sys.stderr,
        )
        print(
            "Or copy config.example.toml to config.toml and customize it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate that all routes have at least one stop
    for route_config in route_configs:
        if not route_config.stop_configs:
            print(
                f"Error: Route at path '{route_config.path}' has no stops configured.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Create aiohttp session for efficient HTTP connections
    async with aiohttp.ClientSession() as session:
        # Initialize repositories
        departure_repo = MvgDepartureRepository(session=session)

        # Initialize services
        grouping_service = DepartureGroupingService(departure_repo)

        # Initialize display adapter
        display_adapter = PyViewWebAdapter(grouping_service, route_configs, config, session=session)

        try:
            await display_adapter.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
            await display_adapter.stop()


if __name__ == "__main__":
    asyncio.run(main())
