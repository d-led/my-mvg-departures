"""KTEL Chania (Crete, Greece) departure repository. Server-side only (no CORS)."""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Robust UTC alias for Python < 3.11 and mypy
try:
    UTC = datetime.UTC  # type: ignore[attr-defined]
except AttributeError:
    from datetime import timezone

    UTC = timezone.utc  # noqa: UP017

from typing import TYPE_CHECKING, Any

import aiohttp

from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.ports.departure_repository import DepartureRepository

if TYPE_CHECKING:
    from aiohttp import ClientSession

# When it's this hour or later in Greece, show next day's schedule (no more buses today).
CHANIA_NEXT_DAY_CUTOFF_HOUR = 22
CHANIA_TIMEZONE = ZoneInfo("Europe/Athens")

logger = logging.getLogger(__name__)

KTEL_CHANIA_API_URL = (
    "https://www.e-ktel.com/index.php?option=com_imeticket&task=showScheduledRoutes"
    "&format=json&stationID={station_id}&departureDate={date}"
)

# API response data[] row: same order as the "Departures" table on e-ktel.com
# (https://www.e-ktel.com/en/services/live-departures). Table header:
# "Route ID | To | To | Bus number | Date | Time" plus a 7th value for platform.
# Index  Field (website)   Description
# -----  ----------------  --------------------------------------------------
#   0    Route ID          Trip/route identifier (we store as stop_point_global_id)
#   1    To                Destination name in Greek (e.g. "ΠΑΛΑΙΟΧΩΡΑ")
#   2    To                Destination name in English (e.g. "Paleochora"); we use for line/destination
#   3    Bus number        Route code (e.g. "A1", "54")
#   4    Date              Departure date YYYY-MM-DD
#   5    Time              Departure time HH:MM
#   6    (no column name)  Platform or gate number (integer or string in API)
CHANIA_API_ROW_ROUTE_ID = 0
CHANIA_API_ROW_TO_GREEK = 1
CHANIA_API_ROW_TO_EN = 2
CHANIA_API_ROW_BUS_NUMBER = 3
CHANIA_API_ROW_DATE = 4
CHANIA_API_ROW_TIME = 5
CHANIA_API_ROW_PLATFORM = 6


def _parse_platform(value: Any) -> int | None:
    """Parse platform from API (string or int) to int | None."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _effective_date_for_today() -> str:
    """Return YYYY-MM-DD to request: today, or tomorrow if it's late evening in Greece.

    After CHANIA_NEXT_DAY_CUTOFF_HOUR (22:00) Greece time, we request tomorrow's date
    so the dashboard shows the next day's first departures instead of an empty list.
    """
    now_greece = datetime.now(CHANIA_TIMEZONE)
    if now_greece.hour >= CHANIA_NEXT_DAY_CUTOFF_HOUR:
        return (now_greece + timedelta(days=1)).strftime("%Y-%m-%d")
    return now_greece.strftime("%Y-%m-%d")


class ChaniaDepartureRepository(DepartureRepository):
    """Fetches scheduled bus departures from KTEL Chania public API. Use on server only."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        self._session = session

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,  # noqa: ARG002 (protocol; Chania API has no offset)
        transport_types: list[str] | None = None,  # noqa: ARG002 (protocol; bus only)
        duration_minutes: int = 60,  # noqa: ARG002 (protocol; Chania uses date only)
        *,
        departure_date: str | None = None,  # YYYY-MM-DD; optional, for CLI one-time fetch
        after_time: (
            datetime | None
        ) = None,  # optional; only departures at or after this time (Athens tz)
    ) -> list[Departure]:
        # When no date given (dashboard): use tomorrow if it's late evening in Greece.
        date = _effective_date_for_today() if departure_date is None else departure_date
        use_own_session = self._session is None
        session = self._session if self._session is not None else aiohttp.ClientSession()
        try:
            departures = await self._fetch_for_date(
                session, station_id, date, limit, after_time=after_time
            )
            # If dashboard (no explicit date) and we got fewer than limit, fetch next calendar day
            # so we fill up to limit when today has few departures (e.g. evening).
            if departure_date is None and len(departures) < limit and len(departures) > 0:
                last_time = departures[-1].planned_time
                next_date_dt = last_time.date() + timedelta(days=1)
                next_date = next_date_dt.strftime("%Y-%m-%d")
                remainder = limit - len(departures)
                extra = await self._fetch_for_date(
                    session, station_id, next_date, remainder, after_time=None
                )
                departures = (departures + extra)[:limit]
            return departures
        finally:
            if use_own_session:
                await session.close()

    async def _fetch_for_date(
        self,
        session: "ClientSession",
        station_id: str,
        date: str,
        limit: int,
        *,
        after_time: datetime | None = None,
    ) -> list[Departure]:
        """Fetch and parse departures for a single date. Used by get_departures."""
        url = KTEL_CHANIA_API_URL.format(station_id=station_id, date=date)
        async with session.get(url) as resp:
            if not resp.ok:
                logger.warning(
                    "Chania API error: %s %s for %s",
                    resp.status,
                    resp.reason,
                    url,
                )
                return []
            try:
                data: dict[str, Any] = await resp.json()
            except (aiohttp.ContentTypeError, ValueError) as e:
                logger.warning("Chania API invalid JSON for %s: %s", url, e)
                return []
        return self._parse_departures(data, limit, after_time=after_time)

    def _parse_departures(
        self,
        data: dict[str, Any],
        limit: int,
        *,
        after_time: datetime | None = None,
    ) -> list[Departure]:
        raw = data.get("data")
        if not isinstance(raw, list):
            return []
        departures: list[Departure] = []
        for dep in raw:
            if not isinstance(dep, (list, tuple)) or len(dep) < 7:
                continue
            try:
                planned_time = datetime.strptime(
                    f"{dep[CHANIA_API_ROW_DATE]} {dep[CHANIA_API_ROW_TIME]}",
                    "%Y-%m-%d %H:%M",
                ).replace(tzinfo=CHANIA_TIMEZONE)
            except (TypeError, ValueError):
                continue
            if after_time is not None and planned_time < after_time:
                continue
            # Route ID as trip id; bus number (index 3) as line; English "To" as destination; platform from index 6
            bus_number = dep[CHANIA_API_ROW_BUS_NUMBER]
            to_en = dep[CHANIA_API_ROW_TO_EN]
            if bus_number in (None, "", "-", 0, "0") or str(bus_number).strip() == "":
                line_str = str(to_en) if to_en else ""
            else:
                line_str = str(bus_number).strip()
            destination_str = str(to_en) if to_en else ""
            departures.append(
                Departure(
                    stop_point_global_id=str(dep[CHANIA_API_ROW_ROUTE_ID]),
                    line=line_str,
                    destination=destination_str,
                    planned_time=planned_time,
                    time=planned_time,
                    platform=_parse_platform(dep[CHANIA_API_ROW_PLATFORM]),
                    transport_type="bus",
                    icon="bus",
                    is_cancelled=False,
                    is_realtime=False,
                    delay_seconds=None,
                    messages=[],
                )
            )
            if len(departures) >= limit:
                break
        return departures
