"""Main entry point for Inky display version."""

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
from mvg_departures.adapters.web.builders.departure_grouping_calculator import (
    DepartureGroupingCalculator,
    DepartureGroupingCalculatorConfig,
    HeaderDisplaySettings,
)
from mvg_departures.adapters.web.formatters.departure_formatter import DepartureFormatter
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models.direction_group_with_metadata import (
    DirectionGroupWithMetadata,
)
from mvg_departures.domain.models.route_configuration import RouteConfiguration
from mvg_departures.domain.models.stop_configuration import StopConfiguration

from .adapter import InkyDisplayAdapter
from .config import InkyDisplayConfig

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
        logger.info(f"Loaded {len(route_configs)} route(s)")
        return route_configs
    except ValueError as e:
        logger.error(f"Invalid route configuration: {e}")
        sys.exit(1)


def _validate_route_configurations(route_configs: list[RouteConfiguration]) -> None:
    """Validate that route configurations are valid."""
    if not route_configs:
        logger.error("No routes configured.")
        logger.error("Please configure routes in your config.toml file.")
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


def _build_direction_groups_with_metadata(
    stop_config: StopConfiguration,
    grouped_departures: list,
) -> list[DirectionGroupWithMetadata]:
    """Build direction groups with metadata from grouped departures (same as web version).
    
    Args:
        stop_config: Stop configuration.
        grouped_departures: List of grouped departures from DepartureGroupingService.
        
    Returns:
        List of direction groups with metadata.
    """
    result: list[DirectionGroupWithMetadata] = []
    for group in grouped_departures:
        if not group.departures:
            continue
        result.append(
            DirectionGroupWithMetadata(
                station_id=stop_config.station_id,
                stop_name=stop_config.station_name,
                direction_name=group.direction_name,
                departures=group.departures,
                random_header_colors=stop_config.random_header_colors,
                header_background_brightness=stop_config.header_background_brightness,
                random_color_salt=stop_config.random_color_salt,
            )
        )
    return result


async def _fetch_and_display_loop(
    adapter: InkyDisplayAdapter,
    grouping_service: DepartureGroupingService,
    route_config: RouteConfiguration,
    config: AppConfig,
) -> None:
    """Continuously fetch and display departures."""
    logger.info(f"Starting display loop for route '{route_config.path}'")

    while True:
        try:
            # Get grouped departures for all stops in the route
            # Build DirectionGroupWithMetadata (same as web version)
            all_direction_groups: list[DirectionGroupWithMetadata] = []
            for stop_config in route_config.stop_configs:
                grouped_departures = await grouping_service.get_grouped_departures(stop_config)
                direction_groups = _build_direction_groups_with_metadata(
                    stop_config, grouped_departures
                )
                all_direction_groups.extend(direction_groups)

            # Display on Inky
            await adapter.display_departures(all_direction_groups)

            # Wait before next update
            refresh_interval = (
                route_config.refresh_interval_seconds
                if route_config.refresh_interval_seconds is not None
                else config.refresh_interval_seconds
            )
            logger.debug(f"Waiting {refresh_interval} seconds before next update")
            await asyncio.sleep(refresh_interval)
        except asyncio.CancelledError:
            logger.info("Display loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in display loop: {e}", exc_info=True)
            # Wait a bit before retrying
            await asyncio.sleep(10)


async def main() -> None:
    """Main application entry point."""
    # If CONFIG_FILE is not set, default to config.example.toml in project root
    import os
    from pathlib import Path
    
    if not os.getenv("CONFIG_FILE"):
        # Find project root (parent of inky directory)
        # __file__ is: inky/src/mvg_departures_inky/main.py
        # So we go: main.py -> mvg_departures_inky -> src -> inky -> project_root
        # That's 4 levels up from __file__
        current_file = Path(__file__).resolve()
        # main.py -> mvg_departures_inky -> src -> inky -> project_root
        project_root = current_file.parent.parent.parent.parent
        
        # Try config.example.toml first, then my.config.toml
        default_config = project_root / "config.example.toml"
        if not default_config.exists():
            default_config = project_root / "my.config.toml"
        
        if default_config.exists():
            os.environ["CONFIG_FILE"] = str(default_config)
            logger.info(f"Using default config file: {default_config}")
        else:
            logger.warning(
                f"No config file found. Tried: {project_root / 'config.example.toml'} "
                f"and {project_root / 'my.config.toml'}. "
                f"Set CONFIG_FILE environment variable to specify a config file."
            )
    
    config = AppConfig()

    route_configs = _load_route_configurations(config)
    _validate_route_configurations(route_configs)

    # Use the first route for Inky display
    if len(route_configs) > 1:
        logger.warning(
            f"Multiple routes configured ({len(route_configs)}), "
            f"using first route '{route_configs[0].path}' for Inky display"
        )
    route_config = route_configs[0]

    # Create Inky display config
    inky_config = InkyDisplayConfig(
        fill_vertical_space=route_config.fill_vertical_space or True,
        show_time=True,  # Show time (alternating between relative and absolute)
    )

    async with aiohttp.ClientSession() as session:
        all_stop_configs = _collect_all_stop_configs(route_configs)
        departure_repo, grouping_service = _initialize_services(all_stop_configs, session)

        # Initialize formatter and calculator (same as web version)
        formatter = DepartureFormatter(config)
        calculator_config = DepartureGroupingCalculatorConfig(
            stop_configs=all_stop_configs,
            config=config,
        )
        grouping_calculator = DepartureGroupingCalculator(
            calculator_config,
            formatter,
            HeaderDisplaySettings(),  # Use defaults for now
        )

        # Initialize adapter with calculator
        adapter = InkyDisplayAdapter(inky_config, grouping_calculator)

        try:
            # Start adapter
            await adapter.start()

            # Start display loop
            await _fetch_and_display_loop(adapter, grouping_service, route_config, config)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await adapter.stop()
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            await adapter.stop()
            raise


if __name__ == "__main__":
    asyncio.run(main())
