"""Route configuration domain model."""

from dataclasses import dataclass

from .stop_configuration import StopConfiguration


@dataclass(frozen=True)
class RouteConfiguration:
    """Configuration for a route with its path and stops."""

    path: str
    stop_configs: list[StopConfiguration]
    title: str | None = None  # Optional route-specific title
    fill_vertical_space: bool = False  # Enable dynamic font sizing to fill viewport
