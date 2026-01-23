"""Test departure repository adapter with static mock data.

Provides various test scenarios:
- Canceled departures
- Departures beyond configured future
- Live departures (with real-time data)
- Planned departures (no real-time)
- Late departures (with delays)
- Various routes from one stop
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.ports.departure_repository import DepartureRepository

if TYPE_CHECKING:
    from aiohttp import ClientSession


class TestDepartureRepository(DepartureRepository):
    """Test adapter that returns static mock departure data."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        """Initialize test repository (session is ignored for mock data)."""
        self._session = session

    def _create_mock_departures(
        self, station_id: str, limit: int, offset_minutes: int
    ) -> list[Departure]:
        """Create mock departures with various test scenarios.

        Args:
            station_id: Station ID (used to vary scenarios)
            limit: Maximum number of departures to return
            offset_minutes: Offset from now

        Returns:
            List of mock Departure objects with various scenarios.
        """
        now = datetime.now(UTC) + timedelta(minutes=offset_minutes)
        departures: list[Departure] = []

        # Scenario 1: On-time real-time departure (in 2 minutes)
        departures.append(
            Departure(
                time=now + timedelta(minutes=2),
                planned_time=now + timedelta(minutes=2),
                delay_seconds=None,
                platform=1,
                is_realtime=True,
                line="U6",
                destination="Garching-Forschungszentrum",
                transport_type="U-Bahn",
                icon="mdi:subway",
                is_cancelled=False,
                messages=[],
                stop_point_global_id=f"{station_id}:1:1",
            )
        )

        # Scenario 2: Delayed real-time departure (5 minutes late)
        departures.append(
            Departure(
                time=now + timedelta(minutes=8),
                planned_time=now + timedelta(minutes=3),
                delay_seconds=300,  # 5 minutes
                platform=2,
                is_realtime=True,
                line="S1",
                destination="Freising",
                transport_type="S-Bahn",
                icon="mdi:subway-variant",
                is_cancelled=False,
                messages=["Verspätung aufgrund einer Störung"],
                stop_point_global_id=f"{station_id}:2:2",
            )
        )

        # Scenario 3: Canceled departure
        departures.append(
            Departure(
                time=now + timedelta(minutes=5),
                planned_time=now + timedelta(minutes=5),
                delay_seconds=None,
                platform=3,
                is_realtime=True,
                line="Tram 19",
                destination="St. Emmeram",
                transport_type="Tram",
                icon="mdi:tram",
                is_cancelled=True,
                messages=["Fahrt fällt aus"],
                stop_point_global_id=f"{station_id}:3:3",
            )
        )

        # Scenario 4: Planned-only departure (no real-time data)
        departures.append(
            Departure(
                time=now + timedelta(minutes=7),
                planned_time=now + timedelta(minutes=7),
                delay_seconds=None,
                platform=4,
                is_realtime=False,
                line="Bus 100",
                destination="Ostbahnhof",
                transport_type="Bus",
                icon="mdi:bus",
                is_cancelled=False,
                messages=[],
                stop_point_global_id=f"{station_id}:4:4",
            )
        )

        # Scenario 5: Departure beyond configured future (15 minutes)
        departures.append(
            Departure(
                time=now + timedelta(minutes=15),
                planned_time=now + timedelta(minutes=15),
                delay_seconds=None,
                platform=1,
                is_realtime=True,
                line="U3",
                destination="Moosach",
                transport_type="U-Bahn",
                icon="mdi:subway",
                is_cancelled=False,
                messages=[],
                stop_point_global_id=f"{station_id}:1:1",
            )
        )

        # Scenario 6: Multiple routes from same stop (different lines)
        departures.append(
            Departure(
                time=now + timedelta(minutes=4),
                planned_time=now + timedelta(minutes=4),
                delay_seconds=None,
                platform=5,
                is_realtime=True,
                line="U1",
                destination="Olympia-Einkaufszentrum",
                transport_type="U-Bahn",
                icon="mdi:subway",
                is_cancelled=False,
                messages=[],
                stop_point_global_id=f"{station_id}:5:5",
            )
        )

        departures.append(
            Departure(
                time=now + timedelta(minutes=6),
                planned_time=now + timedelta(minutes=6),
                delay_seconds=None,
                platform=6,
                is_realtime=True,
                line="U2",
                destination="Messestadt Ost",
                transport_type="U-Bahn",
                icon="mdi:subway",
                is_cancelled=False,
                messages=[],
                stop_point_global_id=f"{station_id}:6:6",
            )
        )

        # Scenario 7: Slightly delayed departure (2 minutes)
        departures.append(
            Departure(
                time=now + timedelta(minutes=10),
                planned_time=now + timedelta(minutes=8),
                delay_seconds=120,  # 2 minutes
                platform=2,
                is_realtime=True,
                line="S8",
                destination="Herrsching",
                transport_type="S-Bahn",
                icon="mdi:subway-variant",
                is_cancelled=False,
                messages=[],
                stop_point_global_id=f"{station_id}:2:2",
            )
        )

        # Scenario 8: Early departure (negative delay, rare but possible)
        departures.append(
            Departure(
                time=now + timedelta(minutes=9),
                planned_time=now + timedelta(minutes=10),
                delay_seconds=None,  # No delay shown for early departures
                platform=7,
                is_realtime=True,
                line="Bus 50",
                destination="Marienplatz",
                transport_type="Bus",
                icon="mdi:bus",
                is_cancelled=False,
                messages=[],
                stop_point_global_id=f"{station_id}:7:7",
            )
        )

        # Scenario 9: Departure with multiple messages
        departures.append(
            Departure(
                time=now + timedelta(minutes=12),
                planned_time=now + timedelta(minutes=12),
                delay_seconds=None,
                platform=8,
                is_realtime=True,
                line="Tram 20",
                destination="Bergmannstraße",
                transport_type="Tram",
                icon="mdi:tram",
                is_cancelled=False,
                messages=["Fahrzeugwechsel", "Barrierefrei"],
                stop_point_global_id=f"{station_id}:8:8",
            )
        )

        # Scenario 10: Departure far in future (30 minutes)
        departures.append(
            Departure(
                time=now + timedelta(minutes=30),
                planned_time=now + timedelta(minutes=30),
                delay_seconds=None,
                platform=1,
                is_realtime=False,
                line="U4",
                destination="Arabellapark",
                transport_type="U-Bahn",
                icon="mdi:subway",
                is_cancelled=False,
                messages=[],
                stop_point_global_id=f"{station_id}:1:1",
            )
        )

        # Apply limit and filter by transport types if specified
        # (Note: transport_types filtering would be applied here if needed)

        return departures[:limit]

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,
        transport_types: list[str] | None = None,  # noqa: ARG002
        duration_minutes: int = 60,  # noqa: ARG002
    ) -> list[Departure]:
        """Get mock departures for testing.

        Args:
            station_id: Station ID (used to vary scenarios)
            limit: Maximum number of departures to return
            offset_minutes: Offset in minutes from now
            transport_types: Ignored for test adapter
            duration_minutes: Ignored for test adapter

        Returns:
            List of mock Departure objects with various test scenarios.
        """
        return self._create_mock_departures(station_id, limit, offset_minutes)
