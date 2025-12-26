"""HAFAS profile auto-detection."""

import logging
from typing import TYPE_CHECKING

from pyhafas import HafasClient
from pyhafas.profile import (
    DBProfile,
    KVBProfile,
    NASAProfile,
    NVVProfile,
    RKRPProfile,
    VSNProfile,
    VVVProfile,
)

from mvg_departures.adapters.hafas_api.ssl_context import hafas_ssl_context

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession

# List of profiles to try in order (most common first)
# Note: BVG and VBB are not included because Berlin stations should use
# the VBB REST API (api_provider = "vbb") instead of HAFAS
PROFILE_ORDER = ["db", "kvb", "nvv", "vvv", "vsn", "rkrp", "nasa"]


class ProfileDetector:
    """Detects the correct HAFAS profile for a station ID."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        """Initialize with optional aiohttp session."""
        self._session = session
        self._profile_cache: dict[str, str] = {}  # station_id -> profile

    async def detect_profile(self, station_id: str) -> str | None:
        """Detect the correct HAFAS profile for a station ID.

        Tries common profiles until one successfully returns departures.
        Caches the result for future use.

        Args:
            station_id: The station ID to test.

        Returns:
            The detected profile name, or None if no profile works.
        """
        # Check cache first
        if station_id in self._profile_cache:
            return self._profile_cache[station_id]

        # Try each profile until one works
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

        # Track profiles that return empty results (might be valid but no departures at this time)
        empty_results_profiles: list[str] = []

        for profile_name in PROFILE_ORDER:
            if profile_name not in profile_map:
                continue

            try:
                profile_class = profile_map[profile_name]
                # Create client and make request with SSL verification disabled
                # (pyhafas may create connections during initialization)
                from datetime import UTC, datetime

                with hafas_ssl_context():
                    client = HafasClient(profile_class())

                # Try to get a single departure to test if this profile works
                # Note: pyhafas methods are synchronous, run in thread pool to avoid blocking
                # Use run_with_ssl_disabled_kwargs to ensure SSL patches are active in the thread
                import asyncio

                from mvg_departures.adapters.hafas_api.ssl_context import (
                    run_with_ssl_disabled_kwargs,
                )

                departures = await asyncio.to_thread(
                    run_with_ssl_disabled_kwargs,
                    (
                        client.departures,
                        {
                            "station": station_id,
                            "date": datetime.now(UTC),
                            "max_trips": 1,
                        },
                    ),
                )

                # Check if we got actual results (not None and not empty)
                # An empty list might mean the station exists but has no departures,
                # but for detection we want to be more strict - we need actual departures
                # to confirm the profile works for this station
                if departures is not None and len(departures) > 0:
                    logger.info(
                        f"Detected HAFAS profile '{profile_name}' for station '{station_id}'"
                    )
                    self._profile_cache[station_id] = profile_name
                    return profile_name
                if departures is not None:
                    # Got empty list - station might exist but no departures
                    # This could be a valid profile, but we'll continue trying others first
                    # Only use this as fallback if no other profile returns results
                    logger.debug(
                        f"Profile '{profile_name}' returned empty results for station '{station_id}'"
                    )
                    empty_results_profiles.append(profile_name)
            except Exception as e:
                logger.debug(f"Profile '{profile_name}' failed for station '{station_id}': {e}")
                continue

        # If no profile returned actual departures, but some returned empty lists,
        # use the first one that returned an empty list (prefer earlier in PROFILE_ORDER)
        if empty_results_profiles:
            fallback_profile = empty_results_profiles[0]
            logger.warning(
                f"No profile returned departures for station '{station_id}', "
                f"using '{fallback_profile}' as fallback (returned empty list)"
            )
            self._profile_cache[station_id] = fallback_profile
            return fallback_profile

        logger.warning(f"Could not detect HAFAS profile for station '{station_id}'")
        return None
