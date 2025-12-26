"""Departure domain model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Departure:
    """Represents a single departure from a station."""

    time: datetime
    planned_time: datetime
    delay_seconds: int | None
    platform: int | None
    is_realtime: bool
    line: str
    destination: str
    transport_type: str
    icon: str
    is_cancelled: bool
    messages: list[str]
    stop_point_global_id: str | None = (
        None  # Physical stop point identifier (e.g., "de:09162:1108:4:4")
    )
