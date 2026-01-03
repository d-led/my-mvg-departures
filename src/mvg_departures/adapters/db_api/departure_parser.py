"""Parser for DB API departure responses (v6.db.transport.rest format)."""

import logging
from datetime import datetime
from typing import Any

from mvg_departures.domain.models.departure import Departure

logger = logging.getLogger(__name__)

# Icon mapping for transport modes
ICON_MAP = {
    "nationalExpress": "mdi:train",
    "national": "mdi:train",
    "regionalExpress": "mdi:train",
    "regional": "mdi:train",
    "suburban": "mdi:subway-variant",
    "subway": "mdi:subway",
    "tram": "mdi:tram",
    "bus": "mdi:bus",
    "ferry": "mdi:ferry",
    "taxi": "mdi:taxi",
}

# Display names for transport modes
MODE_DISPLAY_NAMES = {
    "nationalExpress": "ICE",
    "national": "IC/EC",
    "regionalExpress": "RE",
    "regional": "RB",
    "suburban": "S-Bahn",
    "subway": "U-Bahn",
    "tram": "Tram",
    "bus": "Bus",
    "ferry": "Ferry",
    "taxi": "Taxi",
}


class DepartureParser:
    """Parses v6.db.transport.rest departure responses into Departure objects."""

    @staticmethod
    def parse_departures(departures: list[dict[str, Any]], limit: int) -> list[Departure]:
        """Parse departures from v6 API response.

        Args:
            departures: List of departure dictionaries from API.
            limit: Maximum number of departures to parse.

        Returns:
            List of Departure objects.
        """
        results = []

        for dep in departures[:limit]:
            departure = DepartureParser._parse_departure(dep)
            if departure:
                results.append(departure)

        return results

    @staticmethod
    @staticmethod
    def _parse_departure_times(
        dep: dict[str, Any],
    ) -> tuple[datetime | None, datetime | None, datetime | None]:
        """Parse departure times. Returns (planned_time, real_time, effective_time)."""
        when_str = dep.get("when") or dep.get("plannedWhen", "")
        planned_when_str = dep.get("plannedWhen", "")

        planned_time = DepartureParser._parse_time(planned_when_str)
        real_time = DepartureParser._parse_time(when_str)

        if not planned_time and not real_time:
            return None, None, None

        effective_time = real_time or planned_time
        return planned_time, real_time, effective_time

    @staticmethod
    def _calculate_delay(
        dep: dict[str, Any], planned_time: datetime | None, real_time: datetime | None
    ) -> int | None:
        """Calculate delay in seconds."""
        delay_seconds = dep.get("delay")
        if delay_seconds is None and planned_time and real_time:
            delay_seconds = int((real_time - planned_time).total_seconds())
        return delay_seconds if delay_seconds and delay_seconds > 0 else None

    @staticmethod
    def _extract_line_info(dep: dict[str, Any]) -> tuple[str, str, str, str]:
        """Extract line information. Returns (line_name, mode, product, transport_type)."""
        line_data = dep.get("line", {})
        line_name = line_data.get("name", "") if line_data else ""
        mode = line_data.get("mode", "") if line_data else ""
        product = line_data.get("product", "") if line_data else ""
        transport_type = DepartureParser._get_transport_type(mode, product, line_name)
        return line_name, mode, product, transport_type

    @staticmethod
    def _extract_stop_point_id(dep: dict[str, Any]) -> str | None:
        """Extract stop point ID if available."""
        stop = dep.get("stop", {})
        return str(stop.get("id", "")) if stop else None

    @staticmethod
    def _parse_departure(dep: dict[str, Any]) -> Departure | None:
        """Parse a single departure into a Departure object."""
        try:
            planned_time, real_time, effective_time = DepartureParser._parse_departure_times(dep)
            if not effective_time:
                return None

            delay = DepartureParser._calculate_delay(dep, planned_time, real_time)
            line_name, mode, _product, transport_type = DepartureParser._extract_line_info(dep)
            destination = dep.get("direction", "")
            platform = DepartureParser._parse_platform(dep.get("platform"))
            is_cancelled = dep.get("cancelled", False)
            messages = DepartureParser._extract_messages(dep.get("remarks", []))
            stop_point_id = DepartureParser._extract_stop_point_id(dep)

            return Departure(
                time=effective_time,
                planned_time=planned_time or effective_time,
                delay_seconds=delay,
                platform=platform,
                is_realtime=real_time is not None,
                line=line_name,
                destination=destination,
                transport_type=transport_type,
                icon=ICON_MAP.get(mode, "mdi:train"),
                is_cancelled=is_cancelled,
                messages=messages,
                stop_point_global_id=stop_point_id,
            )
        except Exception as e:
            logger.warning(f"Error parsing departure: {e}")
            return None

    @staticmethod
    def _parse_time(time_str: str) -> datetime | None:
        """Parse ISO 8601 time string."""
        if not time_str:
            return None

        try:
            return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except Exception:
            return None

    @staticmethod
    def _get_transport_type(mode: str, product: str, line_name: str) -> str:
        """Determine transport type from mode, product, and line name."""
        # Use mode if available
        if mode and mode in MODE_DISPLAY_NAMES:
            return MODE_DISPLAY_NAMES[mode]

        # Use product as fallback
        if product and product in MODE_DISPLAY_NAMES:
            return MODE_DISPLAY_NAMES[product]

        # Infer from line name
        line_upper = line_name.upper()
        if "ICE" in line_upper:
            return "ICE"
        if "IC" in line_upper or "EC" in line_upper:
            return "IC/EC"
        if line_upper.startswith("RE"):
            return "RE"
        if line_upper.startswith("RB"):
            return "RB"
        if line_upper.startswith("S"):
            return "S-Bahn"
        if "BUS" in line_upper:
            return "Bus"
        if "TRAM" in line_upper:
            return "Tram"
        if line_upper.startswith("U"):
            return "U-Bahn"

        return "Train"

    @staticmethod
    def _parse_platform(platform: str | int | None) -> int | None:
        """Parse platform value to integer."""
        if platform is None:
            return None

        try:
            # Remove non-numeric characters (e.g., "12a" -> 12)
            platform_str = str(platform).strip()
            numeric = "".join(c for c in platform_str if c.isdigit())
            return int(numeric) if numeric else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    @staticmethod
    def _extract_message_from_dict(remark: dict[str, Any]) -> str | None:
        """Extract message text from dictionary remark."""
        text = remark.get("text", "")
        return str(text) if text else None

    @staticmethod
    def _extract_messages(remarks: list[Any]) -> list[str]:
        """Extract message texts from remarks."""
        messages = []
        if not isinstance(remarks, list):
            return messages

        for remark in remarks:
            if isinstance(remark, dict):
                message = DepartureParser._extract_message_from_dict(remark)
                if message:
                    messages.append(message)
            elif isinstance(remark, str):
                messages.append(remark)

        return messages
