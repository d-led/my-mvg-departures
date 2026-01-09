"""Departure fetcher implementation."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from mvg_departures.domain.contracts.departure_cache import DepartureCacheProtocol  # noqa: TC001

if TYPE_CHECKING:
    from mvg_departures.adapters.config.app_config import AppConfig
    from mvg_departures.domain.models.departure import Departure
    from mvg_departures.domain.ports import DepartureRepository

logger = logging.getLogger(__name__)


class DepartureFetcher:
    """Fetches departures and populates cache."""

    def __init__(
        self,
        departure_repository: DepartureRepository,
        cache: DepartureCacheProtocol,
        station_ids: set[str],
        config: AppConfig,
    ) -> None:
        """Initialize the fetcher.

        Args:
            departure_repository: Repository for fetching departures.
            cache: Cache to store fetched departures.
            station_ids: Set of station IDs to fetch.
            config: Application configuration.
        """
        self.departure_repository = departure_repository
        self.cache = cache
        self.station_ids = station_ids
        self.config = config
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the fetcher."""
        if self._task is not None and not self._task.done():
            logger.warning("Departure fetcher already running")
            return

        logger.info(f"Departure fetcher: {len(self.station_ids)} unique station(s) to fetch")

        # Do initial fetch immediately
        await self._fetch_all_stations()

        # Then fetch periodically
        self._task = asyncio.create_task(self._fetch_loop())
        logger.info("Started departure fetcher")

    async def stop(self) -> None:
        """Stop the fetcher."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("Departure fetcher cancelled")
            logger.info("Stopped departure fetcher")

    async def _fetch_with_error_handling(self) -> None:
        """Fetch all stations with error handling."""
        try:
            await self._fetch_all_stations()
        except Exception as e:
            # Log error but continue the loop - don't stop fetching on errors
            logger.error(
                f"Error in departure fetcher loop (will retry): {e}",
                exc_info=True,
            )

    async def _fetch_loop(self) -> None:
        """Main fetching loop."""
        try:
            while True:
                await asyncio.sleep(self.config.refresh_interval_seconds)
                await self._fetch_with_error_handling()
        except asyncio.CancelledError:
            logger.info("Departure fetcher cancelled")
            raise

    def _filter_and_mark_stale(self, departures: list[Departure]) -> list[Departure]:
        """Mark all departures as stale (not realtime) without filtering.

        Keep ALL departures including past ones - users can extrapolate from old data.
        Stale data is only purged when fresh API data arrives (which replaces cache).

        Args:
            departures: List of cached departures.

        Returns:
            All departures marked as stale (not realtime).
        """
        # Keep ALL departures, just mark as stale
        return [replace(dep, is_realtime=False) for dep in departures]

    async def _fetch_single_station(self, station_id: str, fetch_limit: int) -> None:
        """Fetch departures for a single station."""
        departures = await self.departure_repository.get_departures(station_id, limit=fetch_limit)
        self.cache.set(station_id, departures)
        logger.debug(f"Fetched {len(departures)} raw departures for station {station_id}")

    def _handle_fetch_error(self, station_id: str, error: Exception) -> None:
        """Handle error when fetching departures for a station."""
        logger.error(
            f"Failed to fetch departures for station {station_id}: {error}",
            exc_info=True,
        )
        # Keep ALL stale cached data (even past departures) - mark as non-realtime
        # Users can extrapolate from old data. Stale data purges automatically when
        # fresh API data arrives (cache.set() with new data replaces stale data)
        cached = self.cache.get(station_id)
        if cached:
            stale_departures = self._filter_and_mark_stale(cached)
            self.cache.set(station_id, stale_departures)
            logger.info(
                f"Keeping {len(stale_departures)} stale departures for station {station_id} "
                f"until API recovers (marked as non-realtime)"
            )
        # If no cached data at all, leave cache empty

    async def _fetch_all_stations(self) -> None:
        """Fetch raw departures for all stations.

        Each station fetch is completely isolated - failures in one request
        do not affect other requests.
        """
        fetch_limit = 50  # Same as in DepartureGroupingService
        sleep_ms = self.config.sleep_ms_between_calls
        station_list = list(self.station_ids)

        for i, station_id in enumerate(station_list):
            # Isolate each request - catch ALL exceptions to ensure one failure doesn't stop other requests
            # Even CancelledError from individual requests should be handled (converted to RuntimeError by repository)
            try:
                await self._fetch_single_station(station_id, fetch_limit)
            except Exception as e:
                # Handle all exceptions - this isolates failures
                # The repository should have converted CancelledError/TimeoutError to RuntimeError
                # so we can handle them here without stopping the loop
                self._handle_fetch_error(station_id, e)

            # Add delay between calls (except after the last one)
            # This happens even if the previous request failed
            if sleep_ms > 0 and i < len(station_list) - 1:
                await asyncio.sleep(sleep_ms / 1000.0)
