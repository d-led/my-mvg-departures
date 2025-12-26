"""Direction group with metadata domain model."""

from pydantic import BaseModel, ConfigDict

from mvg_departures.domain.models.departure import Departure


class DirectionGroupWithMetadata(BaseModel):
    """Represents a direction group with display metadata.

    Contains station information, direction name, departures, and styling options.
    """

    model_config = ConfigDict(frozen=True)

    station_id: str
    stop_name: str
    direction_name: str
    departures: list[Departure]
    random_header_colors: bool | None = None
    header_background_brightness: float | None = None
    random_color_salt: int | None = None
