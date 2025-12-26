"""HAFAS API adapters."""

from mvg_departures.adapters.hafas_api.hafas_departure_repository import HafasDepartureRepository
from mvg_departures.adapters.hafas_api.hafas_station_repository import HafasStationRepository

__all__ = [
    "HafasDepartureRepository",
    "HafasStationRepository",
]
