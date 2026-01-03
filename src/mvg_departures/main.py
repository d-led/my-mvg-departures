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
from mvg_departures.adapters.web.pyview_app import PyViewWebAdapterConfig
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models.route_configuration import RouteConfiguration
from mvg_departures.domain.models.stop_configuration import StopConfiguration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


def _load_route_configurations(config: AppConfig) -> list[RouteConfiguration]:
    """Load and validate route configurations."""
    try:
        route_configs = RouteConfigurationLoader.load(config)
        logger.info(f"Loaded {len(route_configs)} route(s):")
        for route_config in route_configs:
            logger.info(
                f"  - Path: '{route_config.path}' with {len(route_config.stop_configs)} stop(s)"
            )
        return route_configs
    except ValueError as e:
        logger.error(f"Invalid route configuration: {e}")
        sys.exit(1)


def _validate_route_configurations(route_configs: list[RouteConfiguration]) -> None:
    """Validate that route configurations are valid."""
    if not route_configs:
        logger.error("No routes configured.")
        logger.error("Please configure routes in your config.toml file.")
        logger.error(
            "Either use [[routes]] with path and stops, or use [[stops]] for default route at '/'."
        )
        logger.error("Or copy config.example.toml to config.toml and customize it.")
        sys.exit(1)

    for route_config in route_configs:
        if not route_config.stop_configs:
            logger.error(f"Route at path '{route_config.path}' has no stops configured.")
            sys.exit(1)


def _collect_all_stop_configs(route_configs: list[RouteConfiguration]) -> list[StopConfiguration]:
    """Collect all stop configurations from all routes."""
    all_stop_configs = []
    for route_config in route_configs:
        all_stop_configs.extend(route_config.stop_configs)
    return all_stop_configs


def _initialize_services(
    all_stop_configs: list[StopConfiguration],
    session: aiohttp.ClientSession,
) -> tuple[CompositeDepartureRepository, DepartureGroupingService]:
    """Initialize departure repository and grouping service."""
    departure_repo = CompositeDepartureRepository(
        stop_configs=all_stop_configs,
        session=session,
    )
    grouping_service = DepartureGroupingService(departure_repo)
    return departure_repo, grouping_service


def _initialize_display_adapter(adapter_config: PyViewWebAdapterConfig) -> PyViewWebAdapter:
    """Initialize display adapter.

    Args:
        adapter_config: Complete configuration for the adapter.

    Returns:
        Initialized PyViewWebAdapter instance.
    """
    return PyViewWebAdapter(adapter_config)


async def main() -> None:
    """Main application entry point."""
    config = AppConfig()

    route_configs = _load_route_configurations(config)
    _validate_route_configurations(route_configs)

    async with aiohttp.ClientSession() as session:
        all_stop_configs = _collect_all_stop_configs(route_configs)
        departure_repo, grouping_service = _initialize_services(all_stop_configs, session)
        adapter_config = PyViewWebAdapterConfig(
            grouping_service=grouping_service,
            route_configs=route_configs,
            config=config,
            departure_repository=departure_repo,
            session=session,
        )
        display_adapter = _initialize_display_adapter(adapter_config)

        try:
            await display_adapter.start()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await display_adapter.stop()


if __name__ == "__main__":
    asyncio.run(main())
