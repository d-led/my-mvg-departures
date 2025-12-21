"""Ports (interfaces) for the ports-and-adapters architecture."""

from mvg_departures.domain.ports.departure_grouping_service import DepartureGroupingService
from mvg_departures.domain.ports.departure_repository import DepartureRepository
from mvg_departures.domain.ports.display_adapter import DisplayAdapter
from mvg_departures.domain.ports.station_repository import StationRepository

__all__ = [
    "DepartureGroupingService",
    "DepartureRepository",
    "DisplayAdapter",
    "StationRepository",
]
