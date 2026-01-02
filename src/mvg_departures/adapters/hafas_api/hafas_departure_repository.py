"""HAFAS departure repository adapter."""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from pyhafas import HafasClient
from pyhafas.profile import DBProfile

from mvg_departures.adapters.hafas_api.profile_detector import ProfileDetector
from mvg_departures.adapters.hafas_api.ssl_context import hafas_ssl_context
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

    async def _determine_profile(self, station_id: str) -> str:
        """Determine which HAFAS profile to use for a station.

        Args:
            station_id: The station ID.

        Returns:
            Profile name to use.
        """
        profile_to_use = self._profile

        if not profile_to_use:
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
                    profile_to_use = "db"
                    logger.warning(
                        f"Could not auto-detect profile for '{station_id}', using default 'db'"
                    )

        return profile_to_use

    def _get_profile_class(self, profile_name: str) -> type[Any]:
        """Get the profile class for a given profile name.

        Args:
            profile_name: The profile name (e.g., 'db', 'kvb').

        Returns:
            The profile class.
        """
        from pyhafas.profile import (
            KVBProfile,
            NASAProfile,
            NVVProfile,
            RKRPProfile,
            VSNProfile,
            VVVProfile,
        )

        profile_map: dict[str, type[Any]] = {
            "db": DBProfile,
            "kvb": KVBProfile,
            "nvv": NVVProfile,
            "vvv": VVVProfile,
            "vsn": VSNProfile,
            "rkrp": RKRPProfile,
            "nasa": NASAProfile,
        }
        profile_class: type[Any] = profile_map.get(profile_name.lower(), DBProfile)
        if profile_name.lower() not in profile_map:
            logger.warning(
                f"Profile '{profile_name}' not in known profiles, using 'db' as fallback"
            )
        return profile_class

    def _ensure_client_initialized(self, profile_to_use: str) -> None:
        """Ensure HAFAS client is initialized with the correct profile.

        Args:
            profile_to_use: The profile name to use.
        """
        if not self._client or self._initialized_profile != profile_to_use:
            profile_class = self._get_profile_class(profile_to_use)
            with hafas_ssl_context():
                self._client = HafasClient(profile_class())
            self._initialized_profile = profile_to_use

    async def _fetch_departures_data(
        self, station_id: str, departure_time: datetime, limit: int, profile_to_use: str
    ) -> list[Any]:
        """Fetch raw departure data from HAFAS API.

        Args:
            station_id: The station ID.
            departure_time: The departure time to query.
            limit: Maximum number of departures to fetch.
            profile_to_use: The profile name being used.

        Returns:
            List of raw departure data from HAFAS.

        Raises:
            Exception: If the API call fails.
        """
        import asyncio

        from mvg_departures.adapters.hafas_api.ssl_context import run_with_ssl_disabled_kwargs

        client = self._client
        if not client:
            raise RuntimeError("HAFAS client not initialized")

        try:
            departures_data_raw = await asyncio.to_thread(
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

        if departures_data_raw is None:
            logger.warning(
                f"HAFAS API returned None for station '{station_id}' with profile '{profile_to_use}'"
            )
            return []

        if len(departures_data_raw) == 0:
            logger.info(
                f"HAFAS API returned empty list for station '{station_id}' with profile '{profile_to_use}' "
                f"(this might be normal if there are no departures at this time)"
            )
            return []

        logger.debug(
            f"Got {len(departures_data_raw)} raw departures for station '{station_id}' with profile '{profile_to_use}'"
        )
        departures_data: list[Any] = list(departures_data_raw)
        return departures_data

    def _extract_departure_time(self, dep: Any) -> tuple[datetime | None, datetime | None]:
        """Extract departure time and planned time from HAFAS departure object.

        Args:
            dep: The HAFAS departure object.

        Returns:
            Tuple of (departure_time, planned_time), either may be None.
        """
        dep_time = getattr(dep, "when", None) or getattr(dep, "planned_when", None)
        if not dep_time:
            return None, None

        planned_time = getattr(dep, "planned_when", None) or dep_time

        # Ensure timezone awareness
        if dep_time.tzinfo is None:
            dep_time = dep_time.replace(tzinfo=UTC)
        if planned_time.tzinfo is None:
            planned_time = planned_time.replace(tzinfo=UTC)

        return dep_time, planned_time

    def _calculate_delay(self, dep: Any, planned_time: datetime) -> int | None:
        """Calculate delay in seconds from HAFAS departure object.

        Args:
            dep: The HAFAS departure object.
            planned_time: The planned departure time.

        Returns:
            Delay in seconds, or None if not available.
        """
        actual_when = getattr(dep, "when", None)
        if actual_when and planned_time:
            delay = actual_when - planned_time
            return int(delay.total_seconds())
        return None

    def _extract_line_info(self, dep: Any) -> tuple[str, str]:
        """Extract line name and transport type from HAFAS departure object.

        Args:
            dep: The HAFAS departure object.

        Returns:
            Tuple of (line_name, transport_type).
        """
        line_obj = getattr(dep, "line", None)
        transport_type = "Unknown"
        line_name = ""

        if line_obj:
            product = getattr(line_obj, "product", None) or getattr(line_obj, "mode", None)
            transport_type = self._map_transport_type(product)
            line_name = (
                getattr(line_obj, "name", None)
                or getattr(line_obj, "id", None)
                or getattr(line_obj, "fahrtNr", None)
                or ""
            )

        return line_name, transport_type

    def _extract_platform(self, dep: Any) -> int | None:
        """Extract platform number from HAFAS departure object.

        Args:
            dep: The HAFAS departure object.

        Returns:
            Platform number, or None if not available.
        """
        platform_attr = getattr(dep, "platform", None)
        if not platform_attr:
            return None

        try:
            return int(platform_attr) if isinstance(platform_attr, str) else platform_attr
        except (ValueError, TypeError):
            return None

    def _extract_destination(self, dep: Any) -> str:
        """Extract destination from HAFAS departure object.

        Args:
            dep: The HAFAS departure object.

        Returns:
            Destination name.
        """
        return getattr(dep, "direction", None) or getattr(dep, "destination", None) or ""

    def _extract_cancellation_status(self, dep: Any) -> bool:
        """Extract cancellation status from HAFAS departure object.

        Args:
            dep: The HAFAS departure object.

        Returns:
            True if cancelled, False otherwise.
        """
        return getattr(dep, "cancelled", False) or getattr(dep, "canceled", False)

    def _extract_messages(self, dep: Any) -> list[str]:
        """Extract messages/remarks from HAFAS departure object.

        Args:
            dep: The HAFAS departure object.

        Returns:
            List of message strings.
        """
        messages = getattr(dep, "remarks", None) or getattr(dep, "messages", None) or []
        if isinstance(messages, str):
            return [messages]
        return messages if isinstance(messages, list) else []

    def _convert_departure(self, dep: Any) -> Departure | None:
        """Convert a HAFAS departure object to our Departure model.

        Args:
            dep: The HAFAS departure object.

        Returns:
            Departure object, or None if conversion fails.
        """
        dep_time, planned_time = self._extract_departure_time(dep)
        if not dep_time or not planned_time:
            return None

        delay_seconds = self._calculate_delay(dep, planned_time)
        line_name, transport_type = self._extract_line_info(dep)
        platform = self._extract_platform(dep)
        destination = self._extract_destination(dep)
        is_cancelled = self._extract_cancellation_status(dep)
        messages = self._extract_messages(dep)

        actual_when = getattr(dep, "when", None)
        is_realtime = actual_when is not None or delay_seconds is not None

        return Departure(
            time=dep_time,
            planned_time=planned_time,
            delay_seconds=delay_seconds,
            platform=platform,
            is_realtime=is_realtime,
            line=line_name,
            destination=destination,
            transport_type=transport_type,
            icon="",  # HAFAS doesn't provide icons directly
            is_cancelled=is_cancelled,
            messages=messages,
        )

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,
        transport_types: list[str] | None = None,  # noqa: ARG002
        duration_minutes: int = 60,  # noqa: ARG002  # Not used by HAFAS API
    ) -> list[Departure]:
        """Get departures for a station.

        Note: transport_types parameter is kept for interface compatibility
        but is not currently implemented for HAFAS API.
        """
        try:
            profile_to_use = await self._determine_profile(station_id)
            self._ensure_client_initialized(profile_to_use)

            departure_time = datetime.now(UTC) + timedelta(minutes=offset_minutes)
            departures_data = await self._fetch_departures_data(
                station_id, departure_time, limit, profile_to_use
            )

            departures = []
            for dep in departures_data:
                try:
                    departure = self._convert_departure(dep)
                    if departure:
                        departures.append(departure)
                except Exception as e:
                    logger.warning(f"Error processing departure: {e}")
                    continue

            return departures
        except Exception as e:
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
