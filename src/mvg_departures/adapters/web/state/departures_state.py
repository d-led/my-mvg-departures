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
    presence_local: int = 0  # Number of users on this dashboard
    presence_total: int = 0  # Total number of users across all dashboards
