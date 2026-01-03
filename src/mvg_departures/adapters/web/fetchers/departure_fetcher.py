"""Departure fetcher implementation."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from datetime import UTC, datetime
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
        """Filter out departed entries and mark remaining as stale (not realtime).

        Args:
            departures: List of cached departures.

        Returns:
            Filtered list with departures that haven't departed yet, marked as stale.
        """
        now = datetime.now(UTC)
        stale_departures = []
        for dep in departures:
            # Keep only departures that haven't departed yet
            if dep.time >= now:
                # Mark as stale (not realtime) since we couldn't refresh from API
                stale_dep = replace(dep, is_realtime=False)
                stale_departures.append(stale_dep)
        return stale_departures

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
        # Keep stale cached data: filter out departed entries and mark as stale
        cached = self.cache.get(station_id)
        if cached:
            stale_departures = self._filter_and_mark_stale(cached)
            self.cache.set(station_id, stale_departures)
            logger.info(
                f"Using {len(stale_departures)} stale departures for station {station_id} "
                f"(filtered from {len(cached)} cached entries)"
            )
        # If no cached data at all, leave cache empty (don't set empty list)

    async def _fetch_all_stations(self) -> None:
        """Fetch raw departures for all stations."""
        fetch_limit = 50  # Same as in DepartureGroupingService
        sleep_ms = self.config.sleep_ms_between_calls
        station_list = list(self.station_ids)

        for i, station_id in enumerate(station_list):
            try:
                await self._fetch_single_station(station_id, fetch_limit)
            except Exception as e:
                self._handle_fetch_error(station_id, e)

            # Add delay between calls (except after the last one)
            if sleep_ms > 0 and i < len(station_list) - 1:
                await asyncio.sleep(sleep_ms / 1000.0)
