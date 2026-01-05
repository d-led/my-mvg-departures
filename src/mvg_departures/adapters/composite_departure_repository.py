"""Composite departure repository that routes to the correct API per stop."""

import logging
from typing import TYPE_CHECKING

from mvg_departures.domain.models.repository_key import RepositoryKey
from mvg_departures.domain.models.stop_configuration import StopConfiguration
from mvg_departures.domain.ports.departure_repository import DepartureRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession


class CompositeDepartureRepository(DepartureRepository):
    """Composite repository that routes to the correct API based on stop configuration."""

    def __init__(
        self,
        stop_configs: list[StopConfiguration],
        session: "ClientSession | None" = None,
    ) -> None:
        """Initialize with stop configurations and optional aiohttp session.

        Args:
            stop_configs: List of stop configurations that define which API to use per stop.
            session: Optional aiohttp session for HTTP connections.
        """
        self._session = session
        self._stop_configs = self._build_stop_configs_mapping(stop_configs)
        self._repositories: dict[str, DepartureRepository] = {}
        self._initialize_repositories()

    def _build_stop_configs_mapping(
        self, stop_configs: list[StopConfiguration]
    ) -> dict[str, StopConfiguration]:
        """Build station_id to config mapping, including base station IDs for stop points."""
        mapping: dict[str, StopConfiguration] = {}
        for config in stop_configs:
            mapping[config.station_id] = config
            # Also map by base station ID if this is a stop_point_global_id
            base_id = self._extract_base_station_id(config.station_id)
            if base_id != config.station_id and base_id not in mapping:
                mapping[base_id] = config
        return mapping

    def _extract_base_station_id(self, station_id: str) -> str:
        """Extract base station ID from a potential stop_point_global_id."""
        parts = station_id.split(":")
        if len(parts) >= 5 and parts[-1] == parts[-2]:
            return ":".join(parts[:3])
        return station_id

    def _create_repository_for_provider(self, api_provider: str) -> DepartureRepository:
        """Create a repository instance for the given API provider."""
        from mvg_departures.adapters.db_api import DbDepartureRepository
        from mvg_departures.adapters.mvg_api import MvgDepartureRepository
        from mvg_departures.adapters.vbb_api import VbbDepartureRepository

        if api_provider == "db":
            return DbDepartureRepository(session=self._session)
        if api_provider == "vbb":
            return VbbDepartureRepository(session=self._session)
        return MvgDepartureRepository(session=self._session)

    def _initialize_repositories(self) -> None:
        """Initialize repositories for each unique API provider combination."""
        # Map of RepositoryKey -> repository instance
        repo_cache: dict[RepositoryKey, DepartureRepository] = {}

        for station_id, stop_config in self._stop_configs.items():
            api_provider = stop_config.api_provider.lower()
            repo_key = RepositoryKey(api_provider=api_provider)

            # Create repository if we haven't seen this API provider
            if repo_key not in repo_cache:
                repo_cache[repo_key] = self._create_repository_for_provider(api_provider)

            # Map this station_id (including base IDs) to the appropriate repository
            self._repositories[station_id] = repo_cache[repo_key]

    def _get_repository(self, station_id: str) -> DepartureRepository:
        """Get the appropriate repository for a station."""
        stop_config = self._stop_configs.get(station_id)
        if not stop_config:
            # Fallback to MVG if station not found in config
            logger.warning(f"Station {station_id} not found in config, using MVG as fallback")
            from mvg_departures.adapters.mvg_api import MvgDepartureRepository

            return MvgDepartureRepository(session=self._session)

        repo = self._repositories.get(station_id)
        if repo:
            return repo

        # Fallback to MVG if repository not found
        from mvg_departures.adapters.mvg_api import MvgDepartureRepository

        return MvgDepartureRepository(session=self._session)

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,
        transport_types: list[str] | None = None,
        duration_minutes: int = 60,
    ) -> list:
        """Get departures for a station using the appropriate API."""
        repository = self._get_repository(station_id)
        return await repository.get_departures(
            station_id=station_id,
            limit=limit,
            offset_minutes=offset_minutes,
            transport_types=transport_types,
            duration_minutes=duration_minutes,
        )
