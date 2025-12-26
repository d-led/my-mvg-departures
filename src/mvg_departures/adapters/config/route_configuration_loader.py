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
        ungrouped_title = stop_data.get("ungrouped_title")
        departure_leeway_minutes = stop_data.get("departure_leeway_minutes", 0)
        max_hours_in_advance = stop_data.get("max_hours_in_advance")
        random_header_colors = stop_data.get("random_header_colors")
        header_background_brightness = stop_data.get("header_background_brightness")
        random_color_salt = stop_data.get("random_color_salt")
        exclude_destinations = stop_data.get("exclude_destinations", [])
        # API provider per stop, fallback to global config
        api_provider = stop_data.get("api_provider", config.api_provider)
        # hafas_profile can be None (auto-detect), empty string, or a specific profile
        hafas_profile = stop_data.get("hafas_profile", config.hafas_profile)
        # Convert empty string to None for auto-detection
        if hafas_profile == "":
            hafas_profile = None

        if not station_id:
            return None

        # Validate random_header_colors if provided
        if random_header_colors is not None:
            random_header_colors = bool(random_header_colors)
        else:
            random_header_colors = None

        # Validate header_background_brightness if provided
        if header_background_brightness is not None:
            try:
                header_background_brightness = float(header_background_brightness)
                # Clamp to valid range [0.0, 1.0]
                header_background_brightness = max(0.0, min(1.0, header_background_brightness))
            except (ValueError, TypeError):
                header_background_brightness = None
        else:
            header_background_brightness = None

        # Validate random_color_salt if provided
        if random_color_salt is not None:
            try:
                random_color_salt = int(random_color_salt)
            except (ValueError, TypeError):
                random_color_salt = None
        else:
            random_color_salt = None

        # Validate exclude_destinations is a list
        if not isinstance(exclude_destinations, list):
            exclude_destinations = []
        # Ensure all items are strings
        exclude_destinations = [
            str(item) for item in exclude_destinations if isinstance(item, (str, int))
        ]

        # Validate max_hours_in_advance if provided
        if max_hours_in_advance is not None:
            try:
                max_hours_in_advance = float(max_hours_in_advance)
                # If < 1, treat as None (unfiltered)
                if max_hours_in_advance < 1:
                    max_hours_in_advance = None
            except (ValueError, TypeError):
                max_hours_in_advance = None
        else:
            max_hours_in_advance = None

        return StopConfiguration(
            station_id=station_id,
            station_name=station_name,
            direction_mappings=direction_mappings,
            max_departures_per_stop=max_departures,
            max_departures_per_route=max_departures_per_route,
            show_ungrouped=show_ungrouped,
            ungrouped_title=ungrouped_title if isinstance(ungrouped_title, str) else None,
            departure_leeway_minutes=departure_leeway_minutes,
            max_hours_in_advance=max_hours_in_advance,
            random_header_colors=random_header_colors,
            header_background_brightness=header_background_brightness,
            random_color_salt=random_color_salt,
            exclude_destinations=exclude_destinations,
            api_provider=api_provider,
            hafas_profile=hafas_profile,
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
                # Get optional route-specific title, theme, fill_vertical_space, font_scaling_factor_when_filling, random_header_colors, and header_background_brightness from routes.display
                route_title = None
                route_theme = None
                fill_vertical_space = False
                font_scaling_factor_when_filling = 1.0
                random_header_colors = False
                header_background_brightness = 0.7
                random_color_salt = 0
                display_data = route_data.get("display")
                if display_data:
                    # Handle both dict (single display) and list (array of displays)
                    if isinstance(display_data, dict):
                        route_title = display_data.get("title")
                        route_theme = display_data.get("theme")
                        fill_vertical_space = display_data.get("fill_vertical_space", False)
                        font_scaling_factor_when_filling = display_data.get(
                            "font_scaling_factor_when_filling", 1.0
                        )
                        random_header_colors = display_data.get("random_header_colors", False)
                        header_background_brightness = display_data.get(
                            "header_background_brightness", 0.7
                        )
                        random_color_salt = display_data.get("random_color_salt", 0)
                    elif isinstance(display_data, list) and len(display_data) > 0:
                        # Get title, theme, fill_vertical_space, font_scaling_factor_when_filling, random_header_colors, and header_background_brightness from first display entry
                        first_display = display_data[0]
                        if isinstance(first_display, dict):
                            route_title = first_display.get("title")
                            route_theme = first_display.get("theme")
                            fill_vertical_space = first_display.get("fill_vertical_space", False)
                            font_scaling_factor_when_filling = first_display.get(
                                "font_scaling_factor_when_filling", 1.0
                            )
                            random_header_colors = first_display.get("random_header_colors", False)
                            header_background_brightness = first_display.get(
                                "header_background_brightness", 0.7
                            )
                            random_color_salt = first_display.get("random_color_salt", 0)

                # Validate title is a string, default to None if not found
                route_title = route_title if route_title and isinstance(route_title, str) else None
                # Validate theme is a string and one of the valid values, default to None if not found
                if route_theme and isinstance(route_theme, str):
                    route_theme_lower = route_theme.lower()
                    if route_theme_lower not in ("light", "dark", "auto"):
                        route_theme = None
                    else:
                        route_theme = route_theme_lower
                else:
                    route_theme = None
                # Validate fill_vertical_space is a boolean (defaults to False if not specified)
                fill_vertical_space = (
                    bool(fill_vertical_space) if fill_vertical_space is not None else False
                )
                # Validate font_scaling_factor_when_filling is a float (defaults to 1.0 if not specified)
                try:
                    font_scaling_factor_when_filling = (
                        float(font_scaling_factor_when_filling)
                        if font_scaling_factor_when_filling is not None
                        else 1.0
                    )
                except (ValueError, TypeError):
                    font_scaling_factor_when_filling = 1.0
                # Validate random_header_colors is a boolean (defaults to False if not specified)
                random_header_colors = (
                    bool(random_header_colors) if random_header_colors is not None else False
                )
                # Validate header_background_brightness is a float (defaults to 0.7 if not specified)
                try:
                    header_background_brightness = (
                        float(header_background_brightness)
                        if header_background_brightness is not None
                        else 0.7
                    )
                    # Clamp to valid range [0.0, 1.0]
                    header_background_brightness = max(0.0, min(1.0, header_background_brightness))
                except (ValueError, TypeError):
                    header_background_brightness = 0.7
                # Validate random_color_salt is an int (defaults to 0 if not specified)
                try:
                    random_color_salt = (
                        int(random_color_salt) if random_color_salt is not None else 0
                    )
                except (ValueError, TypeError):
                    random_color_salt = 0

                route_config = RouteConfiguration(
                    path=path,
                    stop_configs=stop_configs,
                    title=route_title,
                    theme=route_theme,
                    fill_vertical_space=fill_vertical_space,
                    font_scaling_factor_when_filling=font_scaling_factor_when_filling,
                    random_header_colors=random_header_colors,
                    header_background_brightness=header_background_brightness,
                    random_color_salt=random_color_salt,
                )
                route_configs.append(route_config)

        return route_configs
