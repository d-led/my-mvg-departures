"""Domain models for MVG departures."""

from mvg_departures.domain.models.client_info import ClientInfo
from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.models.direction_group import DirectionGroup
from mvg_departures.domain.models.direction_group_with_metadata import DirectionGroupWithMetadata
from mvg_departures.domain.models.error_details import ErrorDetails
from mvg_departures.domain.models.grouped_departures import GroupedDepartures
from mvg_departures.domain.models.presence_result import PresenceCounts, PresenceResult
from mvg_departures.domain.models.route_configuration import RouteConfiguration
from mvg_departures.domain.models.station import Station
from mvg_departures.domain.models.stop_configuration import StopConfiguration

__all__ = [
    "ClientInfo",
    "Departure",
    "DirectionGroup",
    "DirectionGroupWithMetadata",
    "ErrorDetails",
    "GroupedDepartures",
    "PresenceCounts",
    "PresenceResult",
    "RouteConfiguration",
    "Station",
    "StopConfiguration",
]
