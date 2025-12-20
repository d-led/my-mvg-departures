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
            departure_leeway_minutes = stop_data.get("departure_leeway_minutes", 0)

            if not station_id:
                continue

            stop_config = StopConfiguration(
                station_id=station_id,
                station_name=station_name,
                direction_mappings=direction_mappings,
                max_departures_per_stop=max_departures,
                max_departures_per_route=max_departures_per_route,
                show_ungrouped=show_ungrouped,
                departure_leeway_minutes=departure_leeway_minutes,
            )
            stop_configs.append(stop_config)

        return stop_configs
