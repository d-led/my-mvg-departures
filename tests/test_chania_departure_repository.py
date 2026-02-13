"""Behavior-focused tests for ChaniaDepartureRepository and Chania stations list."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from mvg_departures.adapters.chania_api.chania_departure_repository import (
    ChaniaDepartureRepository,
    _effective_date_for_today,
)
from mvg_departures.adapters.chania_api.chania_stations import list_chania_stations

ATHENS = ZoneInfo("Europe/Athens")


@pytest.mark.asyncio
async def test_get_departures_parses_api_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given a valid API response, when get_departures is called, then returns parsed departures."""

    class MockResponse:
        ok = True

        async def json(self) -> object:
            return {
                "success": True,
                "data": [["1", "Γραμμή 1", "Line 1", "A1", "2026-02-08", "12:34", "3"]],
            }

        async def __aenter__(self) -> "MockResponse":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

    class MockSession:
        def get(self, _url: str) -> MockResponse:
            return MockResponse()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("aiohttp.ClientSession", lambda: MockSession())

    repo = ChaniaDepartureRepository()
    # Explicit date: single-date fetch (e.g. CLI), no next-day fill
    departures = await repo.get_departures("1", limit=10, departure_date="2026-02-08")

    assert len(departures) == 1
    dep = departures[0]
    assert dep.stop_point_global_id == "1"
    assert dep.line == "A1"  # bus number from API index 3
    assert dep.destination == "Line 1"  # English "To" from API index 2
    assert dep.planned_time == datetime(2026, 2, 8, 12, 34, tzinfo=ATHENS)
    assert dep.time == datetime(2026, 2, 8, 12, 34, tzinfo=ATHENS)
    assert dep.platform == 3
    assert dep.transport_type == "bus"
    assert dep.icon == "bus"
    assert dep.is_cancelled is False
    assert dep.is_realtime is False
    assert dep.delay_seconds is None
    assert dep.messages == []


@pytest.mark.asyncio
async def test_get_departures_filters_by_after_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given API returns rows at 10:00, 10:15, 10:30, when get_departures is called with after_time 10:15, then returns only 10:15 and 10:30."""

    class MockResponse:
        ok = True

        async def json(self) -> object:
            return {
                "data": [
                    ["1", "", "L1", "", "2026-02-08", "10:00", "1"],
                    ["2", "", "L2", "", "2026-02-08", "10:15", "1"],
                    ["3", "", "L3", "", "2026-02-08", "10:30", "1"],
                ],
            }

        async def __aenter__(self) -> "MockResponse":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

    class MockSession:
        def get(self, _url: str) -> MockResponse:
            return MockResponse()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("aiohttp.ClientSession", lambda: MockSession())

    after = datetime(2026, 2, 8, 10, 15, tzinfo=ATHENS)
    repo = ChaniaDepartureRepository()
    departures = await repo.get_departures(
        "11", limit=10, departure_date="2026-02-08", after_time=after
    )

    assert len(departures) == 2
    assert departures[0].planned_time == datetime(2026, 2, 8, 10, 15, tzinfo=ATHENS)
    assert departures[1].planned_time == datetime(2026, 2, 8, 10, 30, tzinfo=ATHENS)


@pytest.mark.asyncio
async def test_get_departures_respects_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given API returns many rows, when get_departures is called with limit=2, then returns at most 2."""

    class MockResponse:
        ok = True

        async def json(self) -> object:
            return {
                "data": [
                    ["1", "", "L1", "", "2026-02-08", "10:00", "1"],
                    ["2", "", "L2", "", "2026-02-08", "10:15", "1"],
                    ["3", "", "L3", "", "2026-02-08", "10:30", "1"],
                ],
            }

        async def __aenter__(self) -> "MockResponse":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

    class MockSession:
        def get(self, _url: str) -> MockResponse:
            return MockResponse()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("aiohttp.ClientSession", lambda: MockSession())

    repo = ChaniaDepartureRepository()
    departures = await repo.get_departures("11", limit=2)

    assert len(departures) == 2
    # Bus number (index 3) empty in mock, so line falls back to To (index 2)
    assert departures[0].line == "L1"
    assert departures[1].line == "L2"


@pytest.mark.asyncio
async def test_get_departures_fetches_next_day_when_fewer_than_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Given dashboard (no explicit date), when first date returns fewer than limit, then next day is fetched and merged."""
    call_count = 0

    class MockResponse:
        ok = True

        async def json(self) -> object:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "data": [["1", "", "Today", "", "2026-02-08", "20:00", "1"]],
                }
            return {
                "data": [
                    ["2", "", "Tomorrow1", "", "2026-02-09", "08:00", "1"],
                    ["3", "", "Tomorrow2", "", "2026-02-09", "09:00", "1"],
                ],
            }

        async def __aenter__(self) -> "MockResponse":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

    class MockSession:
        def get(self, _url: str) -> MockResponse:
            return MockResponse()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("aiohttp.ClientSession", lambda: MockSession())
    monkeypatch.setattr(
        "mvg_departures.adapters.chania_api.chania_departure_repository._effective_date_for_today",
        lambda: "2026-02-08",
    )

    repo = ChaniaDepartureRepository()
    departures = await repo.get_departures("11", limit=10)

    assert call_count == 2
    assert len(departures) == 3
    assert departures[0].planned_time == datetime(2026, 2, 8, 20, 0, tzinfo=ATHENS)
    assert departures[1].planned_time == datetime(2026, 2, 9, 8, 0, tzinfo=ATHENS)
    assert departures[2].planned_time == datetime(2026, 2, 9, 9, 0, tzinfo=ATHENS)


@pytest.mark.asyncio
async def test_get_departures_on_http_error_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Given API returns 500, when get_departures is called, then returns empty list."""

    class MockResponse:
        @property
        def ok(self) -> bool:
            return False

        @property
        def status(self) -> int:
            return 500

        @property
        def reason(self) -> str:
            return "Internal Server Error"

        async def __aenter__(self) -> "MockResponse":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

    class MockSession:
        def get(self, _url: str) -> MockResponse:
            return MockResponse()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("aiohttp.ClientSession", lambda: MockSession())

    repo = ChaniaDepartureRepository()
    departures = await repo.get_departures("11")

    assert departures == []


def test_effective_date_after_cutoff_returns_tomorrow(monkeypatch: pytest.MonkeyPatch) -> None:
    """When it's 23:00 Greece time, effective date for 'today' is tomorrow."""
    import datetime as dt

    greece = ZoneInfo("Europe/Athens")
    late = datetime(2026, 2, 12, 23, 0, 0, tzinfo=greece)

    class FakeDatetime:
        @staticmethod
        def now(_tz: ZoneInfo | None = None):
            return late

        strptime = dt.datetime.strptime
        replace = dt.datetime.replace

        def __getattr__(self, name: str):
            return getattr(dt.datetime, name)

    monkeypatch.setattr(
        "mvg_departures.adapters.chania_api.chania_departure_repository.datetime",
        FakeDatetime(),
    )
    assert _effective_date_for_today() == "2026-02-13"


def test_effective_date_before_cutoff_returns_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """When it's 21:00 Greece time, effective date for 'today' is today."""
    import datetime as dt

    greece = ZoneInfo("Europe/Athens")
    evening = datetime(2026, 2, 12, 21, 0, 0, tzinfo=greece)

    class FakeDatetime:
        @staticmethod
        def now(_tz: ZoneInfo | None = None):
            return evening

        strptime = dt.datetime.strptime
        replace = dt.datetime.replace

        def __getattr__(self, name: str):
            return getattr(dt.datetime, name)

    monkeypatch.setattr(
        "mvg_departures.adapters.chania_api.chania_departure_repository.datetime",
        FakeDatetime(),
    )
    assert _effective_date_for_today() == "2026-02-12"


def test_list_chania_stations_returns_id_name_pairs() -> None:
    """Given the Chania stations list, it contains known stations with (id, name) pairs."""
    stations = list_chania_stations()
    assert len(stations) >= 2
    ids_and_names = dict(stations)
    assert ids_and_names["11"] == "CHANIA"
    assert ids_and_names["14"] == "PALAIOCHORA"
    for sid, name in stations:
        assert isinstance(sid, str)
        assert sid.isdigit()
        assert isinstance(name, str)
        assert len(name) > 0
