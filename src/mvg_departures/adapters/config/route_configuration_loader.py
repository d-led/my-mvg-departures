"""Route configuration loader."""

from typing import Any

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.domain.models.route_configuration import RouteConfiguration
from mvg_departures.domain.models.stop_configuration import StopConfiguration


class RouteConfigurationLoader:
    """Loads route configurations from app config."""

    @staticmethod
    def _extract_basic_stop_fields(stop_data: dict[str, Any], config: AppConfig) -> dict[str, Any]:
        """Extract basic fields from stop data.

        Args:
            stop_data: Stop data dictionary.
            config: Application configuration.

        Returns:
            Dictionary with extracted basic fields.
        """
        station_id = stop_data.get("station_id")
        station_name = stop_data.get("station_name", station_id) or ""
        if not isinstance(station_name, str):
            station_name = str(station_id) if station_id else ""

        return {
            "station_id": station_id,
            "station_name": station_name,
            "direction_mappings": stop_data.get("direction_mappings", {}),
            "max_departures": stop_data.get("max_departures_per_stop", config.mvg_api_limit),
            "max_departures_per_route": stop_data.get("max_departures_per_route", 2),
            "show_ungrouped": stop_data.get("show_ungrouped", True),
            "ungrouped_title": stop_data.get("ungrouped_title"),
            "departure_leeway_minutes": stop_data.get("departure_leeway_minutes", 0),
            "max_hours_in_advance": stop_data.get("max_hours_in_advance"),
            "random_header_colors": stop_data.get("random_header_colors"),
            "header_background_brightness": stop_data.get("header_background_brightness"),
            "random_color_salt": stop_data.get("random_color_salt"),
            "exclude_destinations": stop_data.get("exclude_destinations", []),
        }

    @staticmethod
    def _extract_api_stop_fields(stop_data: dict[str, Any], config: AppConfig) -> dict[str, Any]:
        """Extract API-related fields from stop data.

        Args:
            stop_data: Stop data dictionary.
            config: Application configuration.

        Returns:
            Dictionary with extracted API fields.
        """
        api_provider = stop_data.get("api_provider", config.api_provider)

        fetch_max_minutes_in_advance = (
            stop_data.get("fetch_max_minutes_in_advance")
            or stop_data.get("api_duration_minutes")
            or stop_data.get("vbb_api_duration_minutes", 60)
        )

        return {
            "api_provider": api_provider,
            "max_departures_fetch": stop_data.get("max_departures_fetch", 50),
            "platform_filter": stop_data.get("platform_filter"),
            "platform_filter_routes": stop_data.get("platform_filter_routes", []),
            "fetch_max_minutes_in_advance": fetch_max_minutes_in_advance,
        }

    @staticmethod
    def _validate_stop_color_fields(fields: dict[str, Any]) -> dict[str, Any]:
        """Validate color-related fields for stop configuration.

        Args:
            fields: Dictionary with field values.

        Returns:
            Dictionary with validated color fields.
        """
        random_header_colors = fields.get("random_header_colors")
        if random_header_colors is not None:
            random_header_colors = bool(random_header_colors)
        else:
            random_header_colors = None

        header_background_brightness = fields.get("header_background_brightness")
        if header_background_brightness is not None:
            try:
                header_background_brightness = float(header_background_brightness)
                header_background_brightness = max(0.0, min(1.0, header_background_brightness))
            except (ValueError, TypeError):
                header_background_brightness = None
        else:
            header_background_brightness = None

        random_color_salt = fields.get("random_color_salt")
        if random_color_salt is not None:
            try:
                random_color_salt = int(random_color_salt)
            except (ValueError, TypeError):
                random_color_salt = None
        else:
            random_color_salt = None

        return {
            "random_header_colors": random_header_colors,
            "header_background_brightness": header_background_brightness,
            "random_color_salt": random_color_salt,
        }

    @staticmethod
    def _validate_stop_list_fields(fields: dict[str, Any]) -> dict[str, Any]:
        """Validate list-type fields for stop configuration.

        Args:
            fields: Dictionary with field values.

        Returns:
            Dictionary with validated list fields.
        """
        exclude_destinations = fields.get("exclude_destinations", [])
        if not isinstance(exclude_destinations, list):
            exclude_destinations = []
        exclude_destinations = [
            str(item) for item in exclude_destinations if isinstance(item, (str, int))
        ]

        platform_filter_routes = fields.get("platform_filter_routes", [])
        if not isinstance(platform_filter_routes, list):
            platform_filter_routes = []
        platform_filter_routes = [
            str(item) for item in platform_filter_routes if isinstance(item, (str, int))
        ]

        return {
            "exclude_destinations": exclude_destinations,
            "platform_filter_routes": platform_filter_routes,
        }

    @staticmethod
    def _validate_stop_numeric_fields(fields: dict[str, Any]) -> dict[str, Any]:
        """Validate numeric fields for stop configuration.

        Args:
            fields: Dictionary with field values.

        Returns:
            Dictionary with validated numeric fields.
        """
        max_hours_in_advance = fields.get("max_hours_in_advance")
        if max_hours_in_advance is not None:
            try:
                max_hours_in_advance = float(max_hours_in_advance)
                if max_hours_in_advance < 1:
                    max_hours_in_advance = None
            except (ValueError, TypeError):
                max_hours_in_advance = None
        else:
            max_hours_in_advance = None

        platform_filter = fields.get("platform_filter")
        if platform_filter is not None:
            try:
                platform_filter = int(platform_filter)
            except (ValueError, TypeError):
                platform_filter = None
        else:
            platform_filter = None

        fetch_max_minutes_in_advance_raw = fields.get("fetch_max_minutes_in_advance")
        try:
            if fetch_max_minutes_in_advance_raw is not None:
                fetch_max_minutes_in_advance = int(fetch_max_minutes_in_advance_raw)
                if fetch_max_minutes_in_advance < 1:
                    fetch_max_minutes_in_advance = 60
            else:
                fetch_max_minutes_in_advance = 60
        except (ValueError, TypeError):
            fetch_max_minutes_in_advance = 60

        return {
            "max_hours_in_advance": max_hours_in_advance,
            "platform_filter": platform_filter,
            "fetch_max_minutes_in_advance": fetch_max_minutes_in_advance,
        }

    @staticmethod
    def load_stop_config_from_data(
        stop_data: dict[str, Any], config: AppConfig
    ) -> StopConfiguration | None:
        """Load a single stop configuration from data dict."""
        if not isinstance(stop_data, dict):
            return None

        basic_fields = RouteConfigurationLoader._extract_basic_stop_fields(stop_data, config)
        api_fields = RouteConfigurationLoader._extract_api_stop_fields(stop_data, config)

        all_fields = {**basic_fields, **api_fields}

        if not all_fields.get("station_id"):
            return None

        color_fields = RouteConfigurationLoader._validate_stop_color_fields(all_fields)
        list_fields = RouteConfigurationLoader._validate_stop_list_fields(all_fields)
        numeric_fields = RouteConfigurationLoader._validate_stop_numeric_fields(all_fields)

        all_fields.update(color_fields)
        all_fields.update(list_fields)
        all_fields.update(numeric_fields)

        return StopConfiguration(
            station_id=all_fields["station_id"],
            station_name=all_fields["station_name"],
            direction_mappings=all_fields["direction_mappings"],
            max_departures_per_stop=all_fields["max_departures"],
            max_departures_per_route=all_fields["max_departures_per_route"],
            show_ungrouped=all_fields["show_ungrouped"],
            ungrouped_title=(
                all_fields["ungrouped_title"]
                if isinstance(all_fields["ungrouped_title"], str)
                else None
            ),
            departure_leeway_minutes=all_fields["departure_leeway_minutes"],
            max_hours_in_advance=all_fields["max_hours_in_advance"],
            random_header_colors=all_fields["random_header_colors"],
            header_background_brightness=all_fields["header_background_brightness"],
            random_color_salt=all_fields["random_color_salt"],
            exclude_destinations=all_fields["exclude_destinations"],
            api_provider=all_fields["api_provider"],
            max_departures_fetch=all_fields["max_departures_fetch"],
            platform_filter=all_fields["platform_filter"],
            platform_filter_routes=all_fields["platform_filter_routes"],
            fetch_max_minutes_in_advance=all_fields["fetch_max_minutes_in_advance"],
        )

    @staticmethod
    def _parse_display_data(display_data: Any) -> dict[str, Any]:
        """Parse display data from route configuration.

        Args:
            display_data: Display data (dict or list).

        Returns:
            Dictionary with parsed display values.
        """
        defaults = {
            "title": None,
            "theme": None,
            "fill_vertical_space": False,
            "font_scaling_factor_when_filling": 1.0,
            "random_header_colors": False,
            "header_background_brightness": 0.7,
            "random_color_salt": 0,
            "refresh_interval_seconds": None,
        }

        if not display_data:
            return defaults

        if isinstance(display_data, dict):
            return {
                "title": display_data.get("title"),
                "theme": display_data.get("theme"),
                "fill_vertical_space": display_data.get("fill_vertical_space", False),
                "font_scaling_factor_when_filling": display_data.get(
                    "font_scaling_factor_when_filling", 1.0
                ),
                "random_header_colors": display_data.get("random_header_colors", False),
                "header_background_brightness": display_data.get(
                    "header_background_brightness", 0.7
                ),
                "random_color_salt": display_data.get("random_color_salt", 0),
                "refresh_interval_seconds": display_data.get("refresh_interval_seconds"),
            }

        if isinstance(display_data, list) and len(display_data) > 0:
            first_display = display_data[0]
            if isinstance(first_display, dict):
                return {
                    "title": first_display.get("title"),
                    "theme": first_display.get("theme"),
                    "fill_vertical_space": first_display.get("fill_vertical_space", False),
                    "font_scaling_factor_when_filling": first_display.get(
                        "font_scaling_factor_when_filling", 1.0
                    ),
                    "random_header_colors": first_display.get("random_header_colors", False),
                    "header_background_brightness": first_display.get(
                        "header_background_brightness", 0.7
                    ),
                    "random_color_salt": first_display.get("random_color_salt", 0),
                    "refresh_interval_seconds": first_display.get("refresh_interval_seconds"),
                }

        return defaults

    @staticmethod
    def _validate_display_values(display_values: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize display values.

        Args:
            display_values: Dictionary with raw display values.

        Returns:
            Dictionary with validated display values.
        """
        # Validate title
        route_title = (
            display_values["title"]
            if display_values["title"] and isinstance(display_values["title"], str)
            else None
        )

        # Validate theme
        route_theme = None
        if display_values["theme"] and isinstance(display_values["theme"], str):
            theme_lower = display_values["theme"].lower()
            if theme_lower in ("light", "dark", "auto"):
                route_theme = theme_lower

        # Validate fill_vertical_space
        fill_vertical_space = (
            bool(display_values["fill_vertical_space"])
            if display_values["fill_vertical_space"] is not None
            else False
        )

        # Validate font_scaling_factor_when_filling
        try:
            font_scaling_factor_when_filling = (
                float(display_values["font_scaling_factor_when_filling"])
                if display_values["font_scaling_factor_when_filling"] is not None
                else 1.0
            )
        except (ValueError, TypeError):
            font_scaling_factor_when_filling = 1.0

        # Validate random_header_colors
        random_header_colors = (
            bool(display_values["random_header_colors"])
            if display_values["random_header_colors"] is not None
            else False
        )

        # Validate header_background_brightness
        try:
            header_background_brightness = (
                float(display_values["header_background_brightness"])
                if display_values["header_background_brightness"] is not None
                else 0.7
            )
            header_background_brightness = max(0.0, min(1.0, header_background_brightness))
        except (ValueError, TypeError):
            header_background_brightness = 0.7

        # Validate random_color_salt
        try:
            random_color_salt = (
                int(display_values["random_color_salt"])
                if display_values["random_color_salt"] is not None
                else 0
            )
        except (ValueError, TypeError):
            random_color_salt = 0

        # Validate refresh_interval_seconds
        try:
            refresh_interval_seconds = (
                int(display_values["refresh_interval_seconds"])
                if display_values["refresh_interval_seconds"] is not None
                else None
            )
            if refresh_interval_seconds is not None and refresh_interval_seconds < 1:
                refresh_interval_seconds = None
        except (ValueError, TypeError):
            refresh_interval_seconds = None

        return {
            "title": route_title,
            "theme": route_theme,
            "fill_vertical_space": fill_vertical_space,
            "font_scaling_factor_when_filling": font_scaling_factor_when_filling,
            "random_header_colors": random_header_colors,
            "header_background_brightness": header_background_brightness,
            "random_color_salt": random_color_salt,
            "refresh_interval_seconds": refresh_interval_seconds,
        }

    @staticmethod
    def _load_stop_configs(stops_data: list[Any], config: AppConfig) -> list[StopConfiguration]:
        """Load stop configurations from stops data.

        Args:
            stops_data: List of stop data dictionaries.
            config: Application configuration.

        Returns:
            List of stop configurations.
        """
        stop_configs: list[StopConfiguration] = []
        for stop_data in stops_data:
            stop_config = RouteConfigurationLoader.load_stop_config_from_data(stop_data, config)
            if stop_config:
                stop_configs.append(stop_config)
        return stop_configs

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

            stop_configs = RouteConfigurationLoader._load_stop_configs(stops_data, config)
            if not stop_configs:
                continue

            display_data = route_data.get("display")
            display_values = RouteConfigurationLoader._parse_display_data(display_data)
            validated_values = RouteConfigurationLoader._validate_display_values(display_values)

            route_config = RouteConfiguration(
                path=path,
                stop_configs=stop_configs,
                title=validated_values["title"],
                theme=validated_values["theme"],
                fill_vertical_space=validated_values["fill_vertical_space"],
                font_scaling_factor_when_filling=validated_values[
                    "font_scaling_factor_when_filling"
                ],
                random_header_colors=validated_values["random_header_colors"],
                header_background_brightness=validated_values["header_background_brightness"],
                random_color_salt=validated_values["random_color_salt"],
                refresh_interval_seconds=validated_values["refresh_interval_seconds"],
            )
            route_configs.append(route_config)

        return route_configs
