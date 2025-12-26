"""Grouped departures domain model."""

from pydantic import BaseModel, ConfigDict

from mvg_departures.domain.models.departure import Departure


class GroupedDepartures(BaseModel):
    """Represents departures grouped by direction."""

    model_config = ConfigDict(frozen=True)

    direction_name: str
    departures: list[Departure]
