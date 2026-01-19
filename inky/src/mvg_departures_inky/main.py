"""Main entry point for Inky display version."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime  # noqa: TC003  # Used at runtime in update_last_update_time
from typing import TYPE_CHECKING

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
from mvg_departures.domain.models.route_configuration import (
    RouteConfiguration,  # noqa: TC002  # Used at runtime (route_config.path, route_config.stop_configs)
)
from mvg_departures.domain.models.stop_configuration import (
    StopConfiguration,  # noqa: TC002  # Used at runtime (stop_config.station_id, etc.)
)

if TYPE_CHECKING:
    from mvg_departures.domain.models.grouped_departures import GroupedDepartures

from .adapter import InkyDisplayAdapter
from .config import InkyDisplayConfig
from .formatter import InkyDepartureFormatter

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
        route_configs: list[RouteConfiguration] = RouteConfigurationLoader.load(config)
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
    inky_config: InkyDisplayConfig,
    app_config: AppConfig,
) -> None:
    """Continuously fetch and display departures using ApiPoller logic."""
    from mvg_departures.adapters.web.pollers.api_poller import (
        ApiPoller,
        ApiPollerConfiguration,
        ApiPollerServices,
        ApiPollerSettings,
    )

    logger.info(f"Starting display loop for route '{route_config.path}'")

    # Create a minimal state updater and broadcaster (not used, but required by ApiPoller)
    # We'll intercept the broadcast to call the Inky adapter instead
    class InkyStateUpdater:
        def __init__(self) -> None:
            self.all_groups: list[DirectionGroupWithMetadata] = []

        def update_departures(self, groups: list[DirectionGroupWithMetadata]) -> None:
            self.all_groups = groups

        def update_last_update_time(self, time: datetime) -> None:
            pass

        def update_api_status(self, status: str) -> None:
            pass

    class InkyStateBroadcaster:
        def __init__(self, adapter: InkyDisplayAdapter, route_config: RouteConfiguration) -> None:
            self.adapter = adapter
            self.route_config = route_config
            self.state_updater: InkyStateUpdater | None = None

        async def broadcast_update(self, _topic: str) -> None:
            # Instead of broadcasting, display on Inky
            if self.state_updater and self.state_updater.all_groups:
                # Convert DirectionGroupWithMetadata to (GroupedDepartures, StopConfiguration) tuples
                # Group by stop_config to match what adapter expects
                from mvg_departures.domain.models.grouped_departures import GroupedDepartures

                grouped_by_stop: dict[str, list[GroupedDepartures]] = {}
                stop_configs_by_name: dict[str, StopConfiguration] = {}

                for group in self.state_updater.all_groups:
                    stop_name = group.stop_name
                    if stop_name not in grouped_by_stop:
                        grouped_by_stop[stop_name] = []
                        # Find matching stop_config
                        for stop_config in self.route_config.stop_configs:
                            if stop_config.station_name == stop_name:
                                stop_configs_by_name[stop_name] = stop_config
                                break

                    grouped_departures = GroupedDepartures(
                        direction_name=group.direction_name, departures=group.departures
                    )
                    grouped_by_stop[stop_name].append(grouped_departures)

                # Build tuples of (GroupedDepartures, StopConfiguration)
                all_grouped_departures: list[tuple[GroupedDepartures, StopConfiguration]] = []
                for stop_name, groups in grouped_by_stop.items():
                    cached_stop_config: StopConfiguration | None = stop_configs_by_name.get(
                        stop_name
                    )
                    if cached_stop_config is not None:
                        for group_item in groups:
                            # group_item is GroupedDepartures from the groups list
                            all_grouped_departures.append((group_item, cached_stop_config))

                if all_grouped_departures:
                    await self.adapter.display_departures(all_grouped_departures)

    state_updater = InkyStateUpdater()
    state_broadcaster = InkyStateBroadcaster(adapter, route_config)
    state_broadcaster.state_updater = state_updater

    # Create ApiPoller with Inky-specific settings
    # InkyStateUpdater and InkyStateBroadcaster implement the required protocols
    services = ApiPollerServices(
        grouping_service=grouping_service,
        state_updater=state_updater,
        state_broadcaster=state_broadcaster,
    )
    configuration = ApiPollerConfiguration(
        stop_configs=route_config.stop_configs,
        config=app_config,
        refresh_interval_seconds=inky_config.refresh_interval_seconds,
    )
    settings = ApiPollerSettings(
        broadcast_topic="inky_display",  # Not used, but required
        shared_cache=None,  # No shared cache for Inky
    )

    poller = ApiPoller(services=services, configuration=configuration, settings=settings)

    try:
        await poller.start()
        # Keep running until cancelled
        while True:
            await asyncio.sleep(60)  # Just keep the loop alive
    except asyncio.CancelledError:
        logger.info("Display loop cancelled")
        await poller.stop()
        raise


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

        # Try my.config.toml first, then fall back to config.example.toml
        default_config = project_root / "my.config.toml"
        if not default_config.exists():
            default_config = project_root / "config.example.toml"

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

    # Filter to only "/" route for Inky display (main config only)
    main_route_configs = [rc for rc in route_configs if rc.path == "/"]
    if not main_route_configs:
        logger.error("No route with path '/' found. Inky display requires the main route at '/'.")
        logger.error(
            f"Available routes: {[rc.path for rc in route_configs]}. "
            "Please configure a route with path='/' in your config.toml."
        )
        sys.exit(1)
    if len(main_route_configs) > 1:
        logger.warning(
            f"Multiple routes with path '/' found ({len(main_route_configs)}), "
            f"using first one for Inky display"
        )
    route_config = main_route_configs[0]
    if len(route_configs) > 1:
        logger.info(f"Filtered {len(route_configs)} route(s) to main route '/' for Inky display")

    # Create Inky display config from TOML
    # Loads from [inky] section and route-specific [[routes.display]] section
    # Note: fill_vertical_space is always True for Inky displays (not configurable)
    inky_config = InkyDisplayConfig.from_toml(
        config_file=config.config_file,
        route_path=route_config.path,
    )

    async with aiohttp.ClientSession() as session:
        all_stop_configs = _collect_all_stop_configs(route_configs)
        _departure_repo, grouping_service = _initialize_services(all_stop_configs, session)

        # Initialize formatter and calculator
        # Use Inky-specific formatter that applies slow refresh compensation
        base_formatter = DepartureFormatter(config)
        formatter = InkyDepartureFormatter(base_formatter, inky_config)
        calculator_config = DepartureGroupingCalculatorConfig(
            stop_configs=all_stop_configs,
            config=config,
        )
        grouping_calculator = DepartureGroupingCalculator(
            calculator_config,
            formatter,
            HeaderDisplaySettings(),  # Use defaults for now
        )

        # Initialize adapter with calculator and stop configs
        adapter = InkyDisplayAdapter(
            inky_config, grouping_calculator, stop_configs=all_stop_configs
        )

        try:
            # Start adapter
            await adapter.start()

            # Start display loop
            await _fetch_and_display_loop(
                adapter, grouping_service, route_config, inky_config, config
            )
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await adapter.stop()
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            await adapter.stop()
            raise


if __name__ == "__main__":
    asyncio.run(main())
