"""Stop configuration loader."""

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.domain.models.stop_configuration import StopConfiguration


class StopConfigurationLoader:
    """Loads stop configurations from app config."""

    @staticmethod
    def load(config: AppConfig) -> list[StopConfiguration]:
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
            ungrouped_title = stop_data.get("ungrouped_title")
            departure_leeway_minutes = stop_data.get("departure_leeway_minutes", 0)
            random_header_colors = stop_data.get("random_header_colors")
            header_background_brightness = stop_data.get("header_background_brightness")
            random_color_salt = stop_data.get("random_color_salt")
            exclude_destinations = stop_data.get("exclude_destinations", [])

            if not station_id:
                continue

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

            stop_config = StopConfiguration(
                station_id=station_id,
                station_name=station_name,
                direction_mappings=direction_mappings,
                max_departures_per_stop=max_departures,
                max_departures_per_route=max_departures_per_route,
                show_ungrouped=show_ungrouped,
                ungrouped_title=ungrouped_title if isinstance(ungrouped_title, str) else None,
                departure_leeway_minutes=departure_leeway_minutes,
                random_header_colors=random_header_colors,
                header_background_brightness=header_background_brightness,
                random_color_salt=random_color_salt,
                exclude_destinations=exclude_destinations,
            )
            stop_configs.append(stop_config)

        return stop_configs
