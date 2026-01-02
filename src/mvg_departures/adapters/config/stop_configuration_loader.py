"""Stop configuration loader."""

from typing import Any

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.domain.models.stop_configuration import StopConfiguration


class StopConfigurationLoader:
    """Loads stop configurations from app config."""

    @staticmethod
    def _extract_basic_fields(stop_data: dict[str, Any], config: AppConfig) -> dict[str, Any]:
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
    def _extract_api_fields(stop_data: dict[str, Any], config: AppConfig) -> dict[str, Any]:
        """Extract API-related fields from stop data.

        Args:
            stop_data: Stop data dictionary.
            config: Application configuration.

        Returns:
            Dictionary with extracted API fields.
        """
        api_provider = stop_data.get("api_provider", config.api_provider)
        hafas_profile = stop_data.get("hafas_profile", config.hafas_profile)
        if hafas_profile == "":
            hafas_profile = None

        fetch_max_minutes_in_advance = (
            stop_data.get("fetch_max_minutes_in_advance")
            or stop_data.get("api_duration_minutes")
            or stop_data.get("vbb_api_duration_minutes", 60)
        )

        return {
            "api_provider": api_provider,
            "hafas_profile": hafas_profile,
            "max_departures_fetch": stop_data.get("max_departures_fetch", 50),
            "platform_filter": stop_data.get("platform_filter"),
            "platform_filter_routes": stop_data.get("platform_filter_routes", []),
            "fetch_max_minutes_in_advance": fetch_max_minutes_in_advance,
        }

    @staticmethod
    def _validate_color_fields(fields: dict[str, Any]) -> dict[str, Any]:
        """Validate color-related fields.

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
    def _validate_list_fields(fields: dict[str, Any]) -> dict[str, Any]:
        """Validate list-type fields.

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
    def _validate_numeric_fields(fields: dict[str, Any]) -> dict[str, Any]:
        """Validate numeric fields.

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
    def _create_stop_config(fields: dict[str, Any]) -> StopConfiguration | None:
        """Create StopConfiguration from validated fields.

        Args:
            fields: Dictionary with all validated field values.

        Returns:
            StopConfiguration object, or None if station_id is missing.
        """
        station_id = fields.get("station_id")
        if not station_id:
            return None

        return StopConfiguration(
            station_id=station_id,
            station_name=fields["station_name"],
            direction_mappings=fields["direction_mappings"],
            max_departures_per_stop=fields["max_departures"],
            max_departures_per_route=fields["max_departures_per_route"],
            show_ungrouped=fields["show_ungrouped"],
            ungrouped_title=(
                fields["ungrouped_title"] if isinstance(fields["ungrouped_title"], str) else None
            ),
            departure_leeway_minutes=fields["departure_leeway_minutes"],
            max_hours_in_advance=fields["max_hours_in_advance"],
            random_header_colors=fields["random_header_colors"],
            header_background_brightness=fields["header_background_brightness"],
            random_color_salt=fields["random_color_salt"],
            exclude_destinations=fields["exclude_destinations"],
            api_provider=fields["api_provider"],
            hafas_profile=fields["hafas_profile"],
            max_departures_fetch=fields["max_departures_fetch"],
            platform_filter=fields["platform_filter"],
            platform_filter_routes=fields["platform_filter_routes"],
            fetch_max_minutes_in_advance=fields["fetch_max_minutes_in_advance"],
        )

    @staticmethod
    def load(config: AppConfig) -> list[StopConfiguration]:
        """Load stop configurations from app config."""
        stops_data = config.get_stops_config()
        stop_configs: list[StopConfiguration] = []

        for stop_data in stops_data:
            if not isinstance(stop_data, dict):
                continue

            basic_fields = StopConfigurationLoader._extract_basic_fields(stop_data, config)
            api_fields = StopConfigurationLoader._extract_api_fields(stop_data, config)

            all_fields = {**basic_fields, **api_fields}

            color_fields = StopConfigurationLoader._validate_color_fields(all_fields)
            list_fields = StopConfigurationLoader._validate_list_fields(all_fields)
            numeric_fields = StopConfigurationLoader._validate_numeric_fields(all_fields)

            all_fields.update(color_fields)
            all_fields.update(list_fields)
            all_fields.update(numeric_fields)

            stop_config = StopConfigurationLoader._create_stop_config(all_fields)
            if stop_config:
                stop_configs.append(stop_config)

        return stop_configs
