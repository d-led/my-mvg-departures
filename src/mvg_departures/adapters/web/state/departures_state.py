"""Departures state dataclass."""

from dataclasses import dataclass, field
from datetime import datetime

from mvg_departures.domain.models.direction_group_with_metadata import DirectionGroupWithMetadata


@dataclass
class DeparturesState:
    """State for the departures LiveView."""

    direction_groups: list[DirectionGroupWithMetadata] = field(default_factory=list)
    last_update: datetime | None = None
    api_status: str = "unknown"
    presence_local: int = 0  # Number of users on this dashboard
    presence_total: int = 0  # Total number of users across all dashboards
    # Server-initiated reload coordination:
    # - When the server increments reload_request_id and pushes an update,
    #   clients can detect the new value and perform a hard reload once.
    # - Clients should remember the last seen value (e.g. in sessionStorage)
    #   to avoid infinite reload loops.
    reload_request_id: int = 0
