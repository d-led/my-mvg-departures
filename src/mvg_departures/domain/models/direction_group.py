"""Direction group domain model."""

from dataclasses import dataclass

from mvg_departures.domain.models.departure import Departure


@dataclass(frozen=True)
class DirectionGroup:
    """Represents a group of departures heading in the same direction."""

    direction_name: str
    stop_name: str
    departures: list[Departure]
