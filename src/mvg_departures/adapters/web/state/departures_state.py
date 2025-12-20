"""Departures state dataclass."""

from dataclasses import dataclass, field
from datetime import datetime

from mvg_departures.domain.models.departure import Departure


@dataclass
class DeparturesState:
    """State for the departures LiveView."""

    direction_groups: list[tuple[str, str, list[Departure]]] = field(default_factory=list)
    last_update: datetime | None = None
    api_status: str = "unknown"
