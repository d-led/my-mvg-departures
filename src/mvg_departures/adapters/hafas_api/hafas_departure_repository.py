"""HAFAS departure repository adapter."""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from pyhafas import HafasClient
from pyhafas.profile import DBProfile

from mvg_departures.adapters.hafas_api.bvg_profile import BVGProfile
from mvg_departures.adapters.hafas_api.profile_detector import ProfileDetector
from mvg_departures.adapters.hafas_api.ssl_context import hafas_ssl_context
from mvg_departures.adapters.hafas_api.vbb_profile import VBBProfile
from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.ports.departure_repository import DepartureRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession


class HafasDepartureRepository(DepartureRepository):
    """Adapter for HAFAS departure repository."""

    def __init__(
        self,
        profile: str | None = None,
        session: "ClientSession | None" = None,
        profile_detector: ProfileDetector | None = None,
    ) -> None:
        """Initialize with HAFAS profile and optional aiohttp session.

        Args:
            profile: HAFAS profile name (e.g., 'db', 'vvo'). If None, will auto-detect.
            session: Optional aiohttp session for HTTP connections.
            profile_detector: Optional profile detector instance (for sharing cache).
        """
        self._session = session
        self._profile = profile.lower() if profile else None
        self._profile_detector = profile_detector or ProfileDetector(session=session)
        # Will be initialized on first use
        self._client: HafasClient | None = None
        self._initialized_profile: str | None = None
        # Cache for station_id -> profile mapping (for auto-detection)
        self._station_profiles: dict[str, str] = {}

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,
        transport_types: list[str] | None = None,  # noqa: ARG002
    ) -> list[Departure]:
        """Get departures for a station.

        Note: transport_types parameter is kept for interface compatibility
        but is not currently implemented for HAFAS API.
        """
        try:
            # Determine which profile to use
            profile_to_use = self._profile

            # Auto-detect profile if not specified
            if not profile_to_use:
                # Check cache first
                if station_id in self._station_profiles:
                    profile_to_use = self._station_profiles[station_id]
                else:
                    detected_profile = await self._profile_detector.detect_profile(station_id)
                    if detected_profile:
                        profile_to_use = detected_profile
                        self._station_profiles[station_id] = detected_profile
                        logger.info(
                            f"Auto-detected profile '{detected_profile}' for station '{station_id}'"
                        )
                    else:
                        # Fallback to DB profile
                        profile_to_use = "db"
                        logger.warning(
                            f"Could not auto-detect profile for '{station_id}', using default 'db'"
                        )

            # Get or create client with the correct profile
            if not self._client or self._initialized_profile != profile_to_use:
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
                    "bvg": BVGProfile,
                    "vbb": VBBProfile,
                    "kvb": KVBProfile,
                    "nvv": NVVProfile,
                    "vvv": VVVProfile,
                    "vsn": VSNProfile,
                    "rkrp": RKRPProfile,
                    "nasa": NASAProfile,
                    # Note: VVO (Verkehrsverbund Oberelbe) might use DB profile
                    # The hafas-config tool will detect which profile works
                }
                profile_class = profile_map.get(profile_to_use.lower(), DBProfile)
                if profile_to_use.lower() not in profile_map:
                    logger.warning(
                        f"Profile '{profile_to_use}' not in known profiles, using 'db' as fallback"
                    )
                # Create HafasClient with SSL verification disabled
                # (pyhafas may create connections during initialization)
                with hafas_ssl_context():
                    self._client = HafasClient(profile_class())
                self._initialized_profile = profile_to_use

            client = self._client

            # Calculate departure time with offset
            departure_time = datetime.now(UTC) + timedelta(minutes=offset_minutes)

            # Get departures from HAFAS with SSL verification disabled
            # Note: pyhafas methods are synchronous, run in thread pool to avoid blocking
            # Use run_with_ssl_disabled_kwargs to ensure SSL patches are active in the thread
            import asyncio

            from mvg_departures.adapters.hafas_api.ssl_context import run_with_ssl_disabled_kwargs

            try:
                departures_data = await asyncio.to_thread(
                    run_with_ssl_disabled_kwargs,
                    (
                        client.departures,
                        {
                            "station": station_id,
                            "date": departure_time,
                            "max_trips": limit,
                        },
                    ),
                )
            except Exception as e:
                logger.error(
                    f"Error calling HAFAS departures API for station '{station_id}' with profile '{profile_to_use}': {e}"
                )
                raise

            if departures_data is None:
                logger.warning(
                    f"HAFAS API returned None for station '{station_id}' with profile '{profile_to_use}'"
                )
                return []

            if len(departures_data) == 0:
                logger.info(
                    f"HAFAS API returned empty list for station '{station_id}' with profile '{profile_to_use}' "
                    f"(this might be normal if there are no departures at this time)"
                )
                return []

            logger.debug(
                f"Got {len(departures_data)} raw departures for station '{station_id}' with profile '{profile_to_use}'"
            )

            departures = []
            for dep in departures_data:
                try:
                    # Extract departure time - handle different attribute names
                    dep_time = getattr(dep, "when", None) or getattr(dep, "planned_when", None)
                    if not dep_time:
                        continue

                    # Get planned time
                    planned_time = getattr(dep, "planned_when", None) or dep_time

                    # Calculate delay
                    delay_seconds = None
                    actual_when = getattr(dep, "when", None)
                    if actual_when and planned_time:
                        delay = actual_when - planned_time
                        delay_seconds = int(delay.total_seconds())

                    # Map transport type - handle different line structures
                    line_obj = getattr(dep, "line", None)
                    transport_type = "Unknown"
                    line_name = ""
                    if line_obj:
                        product = getattr(line_obj, "product", None) or getattr(
                            line_obj, "mode", None
                        )
                        transport_type = self._map_transport_type(product)
                        line_name = (
                            getattr(line_obj, "name", None)
                            or getattr(line_obj, "id", None)
                            or getattr(line_obj, "fahrtNr", None)
                            or ""
                        )

                    # Extract platform
                    platform = None
                    platform_attr = getattr(dep, "platform", None)
                    if platform_attr:
                        try:
                            platform = (
                                int(platform_attr)
                                if isinstance(platform_attr, str)
                                else platform_attr
                            )
                        except (ValueError, TypeError):
                            platform = None

                    # Get destination
                    destination = (
                        getattr(dep, "direction", None) or getattr(dep, "destination", None) or ""
                    )

                    # Get cancellation status
                    is_cancelled = getattr(dep, "cancelled", False) or getattr(
                        dep, "canceled", False
                    )

                    # Get messages/remarks
                    messages = getattr(dep, "remarks", None) or getattr(dep, "messages", None) or []
                    if isinstance(messages, str):
                        messages = [messages]

                    # Ensure timezone awareness
                    if dep_time.tzinfo is None:
                        dep_time = dep_time.replace(tzinfo=UTC)
                    if planned_time.tzinfo is None:
                        planned_time = planned_time.replace(tzinfo=UTC)

                    departure = Departure(
                        time=dep_time,
                        planned_time=planned_time,
                        delay_seconds=delay_seconds,
                        platform=platform,
                        is_realtime=actual_when is not None or delay_seconds is not None,
                        line=line_name,
                        destination=destination,
                        transport_type=transport_type,
                        icon="",  # HAFAS doesn't provide icons directly
                        is_cancelled=is_cancelled,
                        messages=messages if isinstance(messages, list) else [],
                    )
                    departures.append(departure)
                except Exception as e:
                    logger.warning(f"Error processing departure: {e}")
                    continue

            return departures
        except Exception as e:
            # Don't hide errors - let them propagate
            logger.error(f"Error getting departures for station '{station_id}': {e}")
            raise

    def _map_transport_type(self, product: str | None) -> str:
        """Map HAFAS product type to our transport type string."""
        if not product:
            return "Unknown"
        product_lower = product.lower()
        # Map common HAFAS product types
        type_map: dict[str, str] = {
            "bus": "Bus",
            "tram": "Tram",
            "subway": "U-Bahn",
            "suburban": "S-Bahn",
            "train": "Train",
            "ferry": "Ferry",
        }
        # Check for partial matches
        for key, value in type_map.items():
            if key in product_lower:
                return value
        return product.capitalize() if product else "Unknown"
