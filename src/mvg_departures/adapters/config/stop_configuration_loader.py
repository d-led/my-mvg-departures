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
            max_hours_in_advance = stop_data.get("max_hours_in_advance")
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

            # API provider per stop, fallback to global config
            api_provider = stop_data.get("api_provider", config.api_provider)
            # hafas_profile can be None (auto-detect), empty string, or a specific profile
            hafas_profile = stop_data.get("hafas_profile", config.hafas_profile)
            # Convert empty string to None for auto-detection
            if hafas_profile == "":
                hafas_profile = None
            max_departures_fetch = stop_data.get("max_departures_fetch", 50)
            platform_filter = stop_data.get("platform_filter")
            platform_filter_routes = stop_data.get("platform_filter_routes", [])
            # Support new name and legacy names for backward compatibility
            fetch_max_minutes_in_advance = (
                stop_data.get("fetch_max_minutes_in_advance") 
                or stop_data.get("api_duration_minutes") 
                or stop_data.get("vbb_api_duration_minutes", 60)
            )

            # Validate platform_filter if provided
            if platform_filter is not None:
                try:
                    platform_filter = int(platform_filter)
                except (ValueError, TypeError):
                    platform_filter = None
            else:
                platform_filter = None

            # Validate platform_filter_routes is a list
            if not isinstance(platform_filter_routes, list):
                platform_filter_routes = []
            # Ensure all items are strings
            platform_filter_routes = [
                str(item) for item in platform_filter_routes if isinstance(item, (str, int))
            ]

            # Validate fetch_max_minutes_in_advance
            try:
                fetch_max_minutes_in_advance = int(fetch_max_minutes_in_advance)
                # Ensure it's at least 1 minute
                if fetch_max_minutes_in_advance < 1:
                    fetch_max_minutes_in_advance = 60
            except (ValueError, TypeError):
                fetch_max_minutes_in_advance = 60

            stop_config = StopConfiguration(
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
                max_departures_fetch=max_departures_fetch,
                platform_filter=platform_filter,
                platform_filter_routes=platform_filter_routes,
                fetch_max_minutes_in_advance=fetch_max_minutes_in_advance,
            )
            stop_configs.append(stop_config)

        return stop_configs
