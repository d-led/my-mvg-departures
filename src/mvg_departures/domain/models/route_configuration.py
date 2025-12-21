"""Route configuration domain model."""

from dataclasses import dataclass

from .stop_configuration import StopConfiguration


@dataclass(frozen=True)
class RouteConfiguration:
    """Configuration for a route with its path and stops."""

    path: str
    stop_configs: list[StopConfiguration]
