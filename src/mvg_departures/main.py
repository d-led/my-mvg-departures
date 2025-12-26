"""Main entry point for the MVG departures application."""

import asyncio
import logging
import sys

import aiohttp

from mvg_departures.adapters.composite_departure_repository import (
    CompositeDepartureRepository,
)
from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.config.route_configuration_loader import (
    RouteConfigurationLoader,
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

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main application entry point."""
    config = AppConfig()

    # Load route configurations
    try:
        route_configs = RouteConfigurationLoader.load(config)
        logger.info(f"Loaded {len(route_configs)} route(s):")
        for route_config in route_configs:
            logger.info(
                f"  - Path: '{route_config.path}' with {len(route_config.stop_configs)} stop(s)"
            )
    except ValueError as e:
        logger.error(f"Invalid route configuration: {e}")
        sys.exit(1)

    if not route_configs:
        logger.error("No routes configured.")
        logger.error("Please configure routes in your config.toml file.")
        logger.error(
            "Either use [[routes]] with path and stops, or use [[stops]] for default route at '/'."
        )
        logger.error("Or copy config.example.toml to config.toml and customize it.")
        sys.exit(1)

    # Validate that all routes have at least one stop
    for route_config in route_configs:
        if not route_config.stop_configs:
            logger.error(f"Route at path '{route_config.path}' has no stops configured.")
            sys.exit(1)

    # Create aiohttp session for efficient HTTP connections
    async with aiohttp.ClientSession() as session:
        # Collect all stop configurations from all routes
        all_stop_configs = []
        for route_config in route_configs:
            all_stop_configs.extend(route_config.stop_configs)

        # Initialize composite repository that routes to correct API per stop
        departure_repo = CompositeDepartureRepository(
            stop_configs=all_stop_configs,
            session=session,
        )

        # Initialize services
        grouping_service = DepartureGroupingService(departure_repo)

        # Initialize display adapter
        display_adapter = PyViewWebAdapter(
            grouping_service,
            route_configs,
            config,
            departure_repository=departure_repo,
            session=session,
        )

        try:
            await display_adapter.start()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await display_adapter.stop()


if __name__ == "__main__":
    asyncio.run(main())
