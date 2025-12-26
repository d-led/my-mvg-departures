"""Composite departure repository that routes to the correct API per stop."""

import logging
from typing import TYPE_CHECKING

from mvg_departures.adapters.hafas_api.profile_detector import ProfileDetector
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
        self._stop_configs = {config.station_id: config for config in stop_configs}
        self._repositories: dict[str, DepartureRepository] = {}
        # Shared profile detector for caching across all HAFAS repositories
        self._profile_detector = ProfileDetector(session=session)
        self._initialize_repositories()

    def _initialize_repositories(self) -> None:
        """Initialize repositories for each unique API provider/profile combination."""
        from mvg_departures.adapters.hafas_api import HafasDepartureRepository
        from mvg_departures.adapters.mvg_api import MvgDepartureRepository
        from mvg_departures.adapters.vbb_api import VbbDepartureRepository

        # Map of (api_provider, hafas_profile) -> repository instance
        # Use None for hafas_profile to indicate auto-detection
        repo_cache: dict[tuple[str, str | None], DepartureRepository] = {}

        for stop_config in self._stop_configs.values():
            api_provider = stop_config.api_provider.lower()
            # Use None for empty string or None to indicate auto-detection
            hafas_profile = (
                stop_config.hafas_profile.lower()
                if stop_config.hafas_profile and stop_config.hafas_profile.strip()
                else None
            )
            repo_key = (api_provider, hafas_profile)

            # Create repository if we haven't seen this API/profile combination
            if repo_key not in repo_cache:
                repo: DepartureRepository
                if api_provider == "hafas":
                    repo = HafasDepartureRepository(
                        profile=hafas_profile,
                        session=self._session,
                        profile_detector=self._profile_detector,
                    )
                elif api_provider == "vbb":
                    repo = VbbDepartureRepository(session=self._session)
                else:
                    repo = MvgDepartureRepository(session=self._session)
                repo_cache[repo_key] = repo

            # Map this station to the appropriate repository
            self._repositories[stop_config.station_id] = repo_cache[repo_key]

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
    ) -> list:
        """Get departures for a station using the appropriate API."""
        repository = self._get_repository(station_id)
        return await repository.get_departures(
            station_id=station_id,
            limit=limit,
            offset_minutes=offset_minutes,
            transport_types=transport_types,
        )
