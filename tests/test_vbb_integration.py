"""End-to-end integration tests for VBB API."""

import pytest

from mvg_departures.adapters.vbb_api import VbbDepartureRepository
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import StopConfiguration


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vbb_zoologischer_garten_bus249_matching() -> None:
    """Test that bus 249 departures from Zoologischer Garten match direction mappings."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        # Create VBB repository
        repo = VbbDepartureRepository(session=session)

        # Create stop configuration for Zoologischer Garten
        stop_config = StopConfiguration(
            station_id="900023201",  # S+U Zoologischer Garten Bhf
            station_name="Zoologischer Garten",
            direction_mappings={
                "->Uhlandstr.": ["249 Grunewald", "249 Schmargendorf", "249"],
            },
            max_departures_per_stop=15,
            max_departures_per_route=3,  # Should show up to 3 departures per route
            show_ungrouped=False,
            max_departures_fetch=50,
        )

        # Create grouping service
        grouping_service = DepartureGroupingService(repo)

        # Fetch and group departures
        grouped = await grouping_service.get_grouped_departures(stop_config)

        # Verify we got at least one group
        assert len(grouped) > 0, "Should have at least one direction group"

        # Find the Uhlandstr. group
        uhlandstr_group = None
        for direction_name, departures in grouped:
            if direction_name == "->Uhlandstr.":
                uhlandstr_group = departures
                break

        assert uhlandstr_group is not None, "Should have ->Uhlandstr. group"

        # Verify we have bus 249 departures
        bus249_deps = [d for d in uhlandstr_group if d.line == "249"]
        assert len(bus249_deps) > 0, "Should have at least one bus 249 departure"

        # Verify we have multiple departures (up to max_departures_per_route)
        print(f"Bus 249 departures found: {len(bus249_deps)} (max_departures_per_route=3)")
        assert (
            len(bus249_deps) >= 1
        ), f"Should have at least 1 bus 249 departure, got {len(bus249_deps)}"
        # Note: We might have fewer than 3 if there aren't enough in the time window
        # But we should have at least 1, and ideally more if available

        # Verify destinations match expected patterns
        destinations = {d.destination for d in bus249_deps}
        print(f"Bus 249 destinations found: {destinations}")

        # Should match either "Grunewald" or "Schmargendorf" in destination
        has_grunewald = any("Grunewald" in dest for dest in destinations)
        has_schmargendorf = any("Schmargendorf" in dest for dest in destinations)

        assert (
            has_grunewald or has_schmargendorf
        ), f"Should have Grunewald or Schmargendorf destinations, got: {destinations}"

        # Print all bus 249 departures for debugging
        print("\nAll bus 249 departures in ->Uhlandstr. group:")
        for dep in bus249_deps:
            print(f"  {dep.time.strftime('%H:%M')} - {dep.destination}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vbb_fetches_departures() -> None:
    """Test that VBB API can fetch departures from a real station."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        repo = VbbDepartureRepository(session=session)

        # Fetch departures from Zoologischer Garten
        departures = await repo.get_departures(
            station_id="900023201",  # S+U Zoologischer Garten Bhf
            limit=50,
        )

        assert len(departures) > 0, "Should fetch at least some departures"

        # Verify departures have required fields
        for dep in departures[:5]:  # Check first 5
            assert dep.line, f"Departure should have line, got: {dep}"
            assert dep.destination, f"Departure should have destination, got: {dep}"
            assert dep.time, f"Departure should have time, got: {dep}"

        # Check that we have bus 249
        bus249 = [d for d in departures if d.line == "249"]
        assert len(bus249) > 0, "Should have at least one bus 249 departure"

        # Verify bus 249 destinations include expected ones
        bus249_destinations = {d.destination for d in bus249}
        print(f"Bus 249 destinations: {bus249_destinations}")

        # Should have destinations with "Grunewald" or "Schmargendorf" or "Elsterplatz"
        has_expected = any(
            "Grunewald" in dest or "Schmargendorf" in dest or "Elsterplatz" in dest
            for dest in bus249_destinations
        )
        assert has_expected, f"Should have expected destinations, got: {bus249_destinations}"
