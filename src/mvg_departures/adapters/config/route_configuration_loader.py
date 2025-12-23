"""Route configuration loader."""

from typing import Any

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.domain.models.route_configuration import RouteConfiguration
from mvg_departures.domain.models.stop_configuration import StopConfiguration


class RouteConfigurationLoader:
    """Loads route configurations from app config."""

    @staticmethod
    def load_stop_config_from_data(
        stop_data: dict[str, Any], config: AppConfig
    ) -> StopConfiguration | None:
        """Load a single stop configuration from data dict."""
        if not isinstance(stop_data, dict):
            return None

        station_id = stop_data.get("station_id")
        station_name = stop_data.get("station_name", station_id) or ""
        if not isinstance(station_name, str):
            station_name = str(station_id) if station_id else ""
        direction_mappings = stop_data.get("direction_mappings", {})
        max_departures = stop_data.get("max_departures_per_stop", config.mvg_api_limit)
        max_departures_per_route = stop_data.get("max_departures_per_route", 2)
        show_ungrouped = stop_data.get("show_ungrouped", True)
        departure_leeway_minutes = stop_data.get("departure_leeway_minutes", 0)

        if not station_id:
            return None

        return StopConfiguration(
            station_id=station_id,
            station_name=station_name,
            direction_mappings=direction_mappings,
            max_departures_per_stop=max_departures,
            max_departures_per_route=max_departures_per_route,
            show_ungrouped=show_ungrouped,
            departure_leeway_minutes=departure_leeway_minutes,
        )

    @staticmethod
    def load(config: AppConfig) -> list[RouteConfiguration]:
        """Load route configurations from app config."""
        routes_data = config.get_routes_config()
        route_configs: list[RouteConfiguration] = []

        for route_data in routes_data:
            if not isinstance(route_data, dict):
                continue

            path = route_data.get("path", "/")
            if not isinstance(path, str):
                continue

            stops_data = route_data.get("stops", [])
            if not isinstance(stops_data, list):
                continue

            stop_configs: list[StopConfiguration] = []
            for stop_data in stops_data:
                stop_config = RouteConfigurationLoader.load_stop_config_from_data(stop_data, config)
                if stop_config:
                    stop_configs.append(stop_config)

            if stop_configs:
                # Get optional route-specific title and fill_vertical_space from routes.display
                route_title = None
                fill_vertical_space = False
                display_data = route_data.get("display")
                if display_data:
                    # Handle both dict (single display) and list (array of displays)
                    if isinstance(display_data, dict):
                        route_title = display_data.get("title")
                        fill_vertical_space = display_data.get("fill_vertical_space", False)
                    elif isinstance(display_data, list) and len(display_data) > 0:
                        # Get title and fill_vertical_space from first display entry
                        first_display = display_data[0]
                        if isinstance(first_display, dict):
                            route_title = first_display.get("title")
                            fill_vertical_space = first_display.get("fill_vertical_space", False)

                # Validate title is a string, default to None if not found
                route_title = route_title if route_title and isinstance(route_title, str) else None
                # Validate fill_vertical_space is a boolean (defaults to False if not specified)
                fill_vertical_space = (
                    bool(fill_vertical_space) if fill_vertical_space is not None else False
                )

                route_config = RouteConfiguration(
                    path=path,
                    stop_configs=stop_configs,
                    title=route_title,
                    fill_vertical_space=fill_vertical_space,
                )
                route_configs.append(route_config)

        return route_configs
