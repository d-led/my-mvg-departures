"""HAFAS station repository adapter."""

import logging
from typing import TYPE_CHECKING

from pyhafas import HafasClient
from pyhafas.profile import DBProfile

from mvg_departures.adapters.hafas_api.ssl_context import hafas_ssl_context
from mvg_departures.domain.models.station import Station
from mvg_departures.domain.ports.station_repository import StationRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession


class HafasStationRepository(StationRepository):
    """Adapter for HAFAS station repository."""

    def __init__(
        self,
        profile: str = "db",
        session: "ClientSession | None" = None,
    ) -> None:
        """Initialize with HAFAS profile and optional aiohttp session.

        Args:
            profile: HAFAS profile name (e.g., 'db', 'vvo'). Defaults to 'db'.
            session: Optional aiohttp session for HTTP connections.
        """
        self._session = session
        # Map profile names to pyhafas profile classes
        from pyhafas.profile import (
            KVBProfile,
            NASAProfile,
            NVVProfile,
            RKRPProfile,
            VSNProfile,
            VVVProfile,
        )

        profile_map: dict[str, type] = {
            "db": DBProfile,
            # "bvg": BVGProfile,  # Use VBB REST API for Berlin instead
            # "vbb": VBBProfile,  # Use VBB REST API for Berlin instead
            "kvb": KVBProfile,
            "nvv": NVVProfile,
            "vvv": VVVProfile,
            "vsn": VSNProfile,
            "rkrp": RKRPProfile,
            "nasa": NASAProfile,
            # Note: VVO (Verkehrsverbund Oberelbe) might use DB profile
            # The hafas-config tool will detect which profile works
            # Note: For Berlin stations, use api_provider = "vbb" (VBB REST API) instead of HAFAS
        }
        profile_class = profile_map.get(profile.lower(), DBProfile)
        # Create HafasClient with SSL verification disabled
        # (pyhafas may create connections during initialization)
        with hafas_ssl_context():
            self._client = HafasClient(profile_class())
        self._profile = profile.lower()

    async def find_station_by_name(self, name: str, place: str) -> Station | None:
        """Find a station by name and place."""
        try:
            query = f"{name}, {place}"
            # Use SSL context manager to disable verification only for this HAFAS call
            # Note: pyhafas methods are synchronous, run in thread pool to avoid blocking
            # Use run_with_ssl_disabled to ensure SSL patches are active in the thread
            import asyncio

            from mvg_departures.adapters.hafas_api.ssl_context import run_with_ssl_disabled

            results = await asyncio.to_thread(run_with_ssl_disabled, self._client.locations, query)
            if not results:
                return None
            # Take the first result
            result = results[0]
            location = getattr(result, "location", None)
            if not location:
                return None

            # Extract city/place - handle different attribute names
            city = getattr(location, "city", None) or getattr(location, "name", None) or place

            return Station(
                id=getattr(result, "id", "") or f"{name}_{place}",
                name=getattr(result, "name", None) or name,
                place=city,
                latitude=getattr(location, "latitude", 0.0),
                longitude=getattr(location, "longitude", 0.0),
            )
        except Exception as e:
            logger.warning(f"Error finding station by name '{name}, {place}': {e}")
            return None

    async def find_station_by_id(self, station_id: str) -> Station | None:
        """Find a station by its global identifier."""
        try:
            # HAFAS uses location IDs directly
            # Use SSL context manager to disable verification only for this HAFAS call
            # Note: pyhafas methods are synchronous, run in thread pool to avoid blocking
            # Use run_with_ssl_disabled to ensure SSL patches are active in the thread
            import asyncio

            from mvg_departures.adapters.hafas_api.ssl_context import run_with_ssl_disabled

            result = await asyncio.to_thread(
                run_with_ssl_disabled, self._client.location, station_id
            )
            if not result:
                return None
            location = getattr(result, "location", None)
            if not location:
                return None

            city = getattr(location, "city", None) or getattr(location, "name", None) or ""

            return Station(
                id=getattr(result, "id", None) or station_id,
                name=getattr(result, "name", None) or station_id,
                place=city,
                latitude=getattr(location, "latitude", 0.0),
                longitude=getattr(location, "longitude", 0.0),
            )
        except Exception as e:
            logger.warning(f"Error finding station by ID '{station_id}': {e}")
            return None

    async def find_nearby_station(self, latitude: float, longitude: float) -> Station | None:
        """Find the nearest station to given coordinates."""
        try:
            # Use SSL context manager to disable verification only for this HAFAS call
            # Note: pyhafas methods are synchronous, run in thread pool to avoid blocking
            # Use run_with_ssl_disabled to ensure SSL patches are active in the thread
            import asyncio

            from mvg_departures.adapters.hafas_api.ssl_context import run_with_ssl_disabled

            results = await asyncio.to_thread(
                run_with_ssl_disabled,
                self._client.nearby,
                latitude,
                longitude,
            )
            if not results:
                return None
            # Take the first (nearest) result
            result = results[0]
            location = getattr(result, "location", None)
            if not location:
                return None

            city = getattr(location, "city", None) or getattr(location, "name", None) or ""

            return Station(
                id=getattr(result, "id", "") or "",
                name=getattr(result, "name", None) or "",
                place=city,
                latitude=getattr(location, "latitude", latitude),
                longitude=getattr(location, "longitude", longitude),
            )
        except Exception as e:
            logger.warning(f"Error finding nearby station at ({latitude}, {longitude}): {e}")
            return None
