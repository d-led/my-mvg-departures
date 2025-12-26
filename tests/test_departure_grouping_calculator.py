"""Specification tests for departure display calculation."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.builders import (
    DepartureGroupingCalculator,
    generate_pastel_color_from_text,
)
from mvg_departures.adapters.web.formatters import DepartureFormatter
from mvg_departures.domain.models import (
    Departure,
    DirectionGroupWithMetadata,
    StopConfiguration,
)


def _create_calculator() -> DepartureGroupingCalculator:
    """Create a test DepartureGroupingCalculator instance."""
    with patch.dict(os.environ, {}, clear=True):
        stop_configs = [
            StopConfiguration(
                station_id="de:09162:70",
                station_name="Universität",
                direction_mappings={},
            ),
            StopConfiguration(
                station_id="de:09162:71",
                station_name="Marienplatz",
                direction_mappings={},
            ),
        ]
        config = AppConfig(config_file=None, _env_file=None)
        formatter = DepartureFormatter(config)
        return DepartureGroupingCalculator(stop_configs, config, formatter)


def test_when_no_departures_available_then_shows_no_departures() -> None:
    """Given no departures at any stop, when displaying, then shows no departures available."""
    calculator = _create_calculator()
    result = calculator.calculate_display_data([])

    assert result["has_departures"] is False
    assert len(result["groups_with_departures"]) == 0
    assert len(result["stops_without_departures"]) == 2
    assert "Universität" in result["stops_without_departures"]
    assert "Marienplatz" in result["stops_without_departures"]


def test_when_single_departure_exists_then_displays_it() -> None:
    """Given a single departure at a stop, when displaying, then shows the departure."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    assert result["has_departures"] is True
    assert len(result["groups_with_departures"]) == 1
    assert len(result["groups_with_departures"][0]["departures"]) == 1
    assert "Marienplatz" in result["stops_without_departures"]


def test_when_departure_exists_then_displays_line_and_destination() -> None:
    """Given a departure, when displaying, then shows the line number and destination station."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    assert departure_display["line"] == "U3"
    assert departure_display["destination"] == "Giesing"


def test_when_departure_is_cancelled_then_shows_cancelled_status() -> None:
    """Given a cancelled departure, when displaying, then marks it as cancelled."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=True,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    assert departure_display["cancelled"] is True


def test_when_departure_is_delayed_then_shows_delay_information() -> None:
    """Given a delayed departure, when displaying, then shows the delay amount."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=3),
        delay_seconds=120,  # 2 minutes
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    assert departure_display["has_delay"] is True
    assert departure_display["delay_display"] is not None
    assert "2m" in departure_display["delay_display"]


def test_when_delay_is_under_one_minute_then_does_not_show_delay() -> None:
    """Given a departure delayed less than one minute, when displaying, then does not show delay."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=4, seconds=59),
        delay_seconds=59,  # Below threshold
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    assert departure_display["has_delay"] is False
    assert departure_display["delay_display"] is None


def test_when_departure_has_realtime_data_then_shows_realtime_indicator() -> None:
    """Given a departure with real-time tracking, when displaying, then marks it as real-time."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=True,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    assert departure_display["is_realtime"] is True


def test_when_departure_has_platform_then_shows_platform_number() -> None:
    """Given a departure with a platform assignment, when displaying, then shows the platform number."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=1,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    assert departure_display["platform"] == "1"


def test_when_departure_has_no_platform_then_does_not_show_platform() -> None:
    """Given a departure without platform information, when displaying, then does not show platform."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    assert departure_display["platform"] is None


def test_when_multiple_departures_exist_then_displays_all() -> None:
    """Given multiple departures at stops, when displaying, then shows all departures."""
    now = datetime.now(UTC)
    departure1 = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )
    departure2 = Departure(
        time=now + timedelta(minutes=10),
        planned_time=now + timedelta(minutes=10),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U6",
        destination="Klinikum Großhadern",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure1],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        ),
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Klinikum Großhadern",
            departures=[departure2],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        ),
    ]
    result = calculator.calculate_display_data(direction_groups)

    assert result["has_departures"] is True
    assert len(result["groups_with_departures"]) == 2
    assert len(result["groups_with_departures"][0]["departures"]) == 1
    assert len(result["groups_with_departures"][1]["departures"]) == 1


def test_when_stop_has_no_departures_then_lists_it_as_empty() -> None:
    """Given a configured stop with no departures, when displaying, then lists it as having no departures."""
    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    assert result["has_departures"] is False
    assert "Universität" in result["stops_without_departures"]
    assert "Marienplatz" in result["stops_without_departures"]


def test_when_departures_exist_then_first_group_is_marked_as_first() -> None:
    """Given departures to display, when displaying, then marks the first group as the first."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    group = result["groups_with_departures"][0]
    assert group["is_first_header"] is True
    assert group["is_first_group"] is True
    assert group["is_last_group"] is True


def test_when_multiple_groups_exist_then_first_and_last_are_marked() -> None:
    """Given multiple departure groups, when displaying, then marks first and last groups correctly."""
    now = datetime.now(UTC)
    departure1 = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )
    departure2 = Departure(
        time=now + timedelta(minutes=10),
        planned_time=now + timedelta(minutes=10),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U6",
        destination="Klinikum Großhadern",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure1],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        ),
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Klinikum Großhadern",
            departures=[departure2],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        ),
    ]
    result = calculator.calculate_display_data(direction_groups)

    assert len(result["groups_with_departures"]) == 2
    first_group = result["groups_with_departures"][0]
    last_group = result["groups_with_departures"][1]

    assert first_group["is_first_header"] is True
    assert first_group["is_first_group"] is True
    assert first_group["is_last_group"] is False

    assert last_group["is_first_header"] is False
    assert last_group["is_first_group"] is False
    assert last_group["is_last_group"] is True


def test_when_departures_from_different_stops_then_each_stop_is_marked_as_new() -> None:
    """Given departures from different stops, when displaying, then marks each stop as a new stop."""
    now = datetime.now(UTC)
    departure1 = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )
    departure2 = Departure(
        time=now + timedelta(minutes=10),
        planned_time=now + timedelta(minutes=10),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U6",
        destination="Klinikum Großhadern",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure1],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        ),
        DirectionGroupWithMetadata(
            station_id="de:09162:71",
            stop_name="Marienplatz",
            direction_name="->Klinikum Großhadern",
            departures=[departure2],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        ),
    ]
    result = calculator.calculate_display_data(direction_groups)

    assert result["groups_with_departures"][0]["is_new_stop"] is True
    assert result["groups_with_departures"][1]["is_new_stop"] is True


def test_when_departures_from_same_stop_then_second_is_not_marked_as_new() -> None:
    """Given multiple departures from the same stop, when displaying, then only first is marked as new stop."""
    now = datetime.now(UTC)
    departure1 = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )
    departure2 = Departure(
        time=now + timedelta(minutes=10),
        planned_time=now + timedelta(minutes=10),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U6",
        destination="Klinikum Großhadern",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure1],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        ),
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Klinikum Großhadern",
            departures=[departure2],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        ),
    ]
    result = calculator.calculate_display_data(direction_groups)

    assert result["groups_with_departures"][0]["is_new_stop"] is True
    assert result["groups_with_departures"][1]["is_new_stop"] is False


def test_when_departures_are_unsorted_then_displays_them_sorted_by_time() -> None:
    """Given unsorted departures, when displaying, then shows them sorted by departure time."""
    now = datetime.now(UTC)
    later_departure = Departure(
        time=now + timedelta(minutes=10),
        planned_time=now + timedelta(minutes=10),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )
    earlier_departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U6",
        destination="Klinikum Großhadern",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    # Add in reverse order
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[later_departure, earlier_departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departures = result["groups_with_departures"][0]["departures"]
    assert len(departures) == 2
    # Should be sorted: earlier (5 min) comes before later (10 min)
    assert departures[0]["line"] == "U6"
    assert departures[1]["line"] == "U3"


def test_when_departure_exists_then_includes_accessibility_label() -> None:
    """Given a departure, when displaying, then includes complete accessibility label with all information."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=3),
        delay_seconds=120,  # 2 minutes
        platform=1,
        is_realtime=True,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    aria_label = departure_display["aria_label"]
    assert "Line U3" in aria_label
    assert "Giesing" in aria_label
    assert "Platform 1" in aria_label
    assert "delayed by 2 minutes" in aria_label
    assert "real-time" in aria_label


def test_when_departure_is_cancelled_then_accessibility_label_includes_cancelled() -> None:
    """Given a cancelled departure, when displaying, then accessibility label includes cancelled status."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=True,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    aria_label = departure_display["aria_label"]
    assert "cancelled" in aria_label


def test_when_departure_is_scheduled_then_accessibility_label_says_scheduled() -> None:
    """Given a scheduled (not real-time) departure, when displaying, then accessibility label indicates scheduled."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    aria_label = departure_display["aria_label"]
    assert "scheduled" in aria_label


def test_when_departures_exist_then_header_shows_stop_and_direction() -> None:
    """Given departures grouped by stop and direction, when displaying, then header shows stop name and direction."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    group = result["groups_with_departures"][0]
    assert group["header"] == "Universität → Giesing"
    assert group["stop_name"] == "Universität"


def test_when_direction_has_arrow_prefix_then_header_removes_it() -> None:
    """Given a direction name with arrow prefix, when displaying, then header removes prefix and uses arrow symbol."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    group = result["groups_with_departures"][0]
    # Should remove "->" prefix and add "→" in header
    assert "->" not in group["header"]
    assert "→" in group["header"]


def test_when_departure_exists_then_includes_all_time_formats() -> None:
    """Given a departure, when displaying, then includes relative, absolute, and configured time formats."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    assert "time_str" in departure_display
    assert "time_str_relative" in departure_display
    assert "time_str_absolute" in departure_display
    assert departure_display["time_str"] is not None
    assert departure_display["time_str_relative"] is not None
    assert departure_display["time_str_absolute"] is not None


def test_when_no_departures_then_includes_font_size_configuration() -> None:
    """Given no departures available, when displaying, then includes font size configuration for empty message."""
    calculator = _create_calculator()
    result = calculator.calculate_display_data([])

    assert "font_size_no_departures" in result
    assert result["font_size_no_departures"] is not None


def test_when_some_stops_have_departures_and_others_dont_then_lists_both() -> None:
    """Given some stops with departures and some without, when displaying, then shows departures and lists empty stops."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        ),
        DirectionGroupWithMetadata(
            station_id="de:09162:71",
            stop_name="Marienplatz",
            direction_name="->Ostbahnhof",
            departures=[],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        ),
    ]
    result = calculator.calculate_display_data(direction_groups)

    assert result["has_departures"] is True
    assert len(result["groups_with_departures"]) == 1
    assert "Marienplatz" in result["stops_without_departures"]
    assert "Universität" not in result["stops_without_departures"]


def test_when_departure_has_large_delay_then_shows_delay_correctly() -> None:
    """Given a departure with significant delay, when displaying, then shows delay amount in minutes."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=10),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=300,  # 5 minutes
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    assert departure_display["has_delay"] is True
    assert "5m" in departure_display["delay_display"]


def test_when_departure_has_platform_zero_then_shows_platform_zero() -> None:
    """Given a departure at platform 0, when displaying, then shows platform as zero."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=0,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    calculator = _create_calculator()
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )
    ]
    result = calculator.calculate_display_data(direction_groups)

    departure_display = result["groups_with_departures"][0]["departures"][0]
    assert departure_display["platform"] == "0"


def test_when_stops_have_same_name_different_ids_then_uses_correct_config() -> None:
    """Given stops with same name but different IDs, when displaying, then uses correct config per station_id."""
    now = datetime.now(UTC)
    departure1 = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )
    departure2 = Departure(
        time=now + timedelta(minutes=6),
        planned_time=now + timedelta(minutes=6),
        delay_seconds=None,
        platform=None,
        is_realtime=False,
        line="54",
        destination="Lorettoplatz",
        transport_type="Bus",
        icon="mdi:bus",
        is_cancelled=False,
        messages=[],
    )

    # Create calculator with two stops that have the same name but different IDs
    with patch.dict(os.environ, {}, clear=True):
        stop_configs = [
            StopConfiguration(
                station_id="de:09162:1110",
                station_name="Giesing",
                direction_mappings={},
                random_header_colors=False,  # First stop: no random colors
            ),
            StopConfiguration(
                station_id="de:09162:1110:4:4",
                station_name="Giesing",
                direction_mappings={},
                random_header_colors=True,  # Second stop: random colors
            ),
        ]
        config = AppConfig(config_file=None, _env_file=None)
        formatter = DepartureFormatter(config)
        calculator = DepartureGroupingCalculator(
            stop_configs, config, formatter, random_header_colors=False
        )

    # Create direction groups with station_id, stop_name, direction_name, departures, random_header_colors, header_background_brightness, random_color_salt
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:1110",
            stop_name="Giesing",
            direction_name="->City",
            departures=[departure1],
            random_header_colors=False,
            header_background_brightness=None,
            random_color_salt=None,
        ),  # First stop: random_header_colors=False
        DirectionGroupWithMetadata(
            station_id="de:09162:1110:4:4",
            stop_name="Giesing",
            direction_name="->Tegernseer Str.",
            departures=[departure2],
            random_header_colors=True,
            header_background_brightness=None,
            random_color_salt=None,
        ),  # Second stop: random_header_colors=True
    ]
    result = calculator.calculate_display_data(direction_groups)

    # Should have 2 groups
    assert len(result["groups_with_departures"]) == 2

    # First group (de:09162:1110) should NOT have header_color (random_header_colors=False)
    first_group = result["groups_with_departures"][0]
    assert first_group["station_id"] == "de:09162:1110"
    assert first_group["stop_name"] == "Giesing"
    assert "header_color" not in first_group

    # Second group (de:09162:1110:4:4) SHOULD have header_color (random_header_colors=True)
    second_group = result["groups_with_departures"][1]
    assert second_group["station_id"] == "de:09162:1110:4:4"
    assert second_group["stop_name"] == "Giesing"
    assert "header_color" in second_group


def test_when_same_text_and_salt_then_same_color() -> None:
    """Given the same text and salt, when generating colors, then produces the same color."""
    text = "Giesing → Tegernseer Str."
    brightness = 0.7
    salt = 0

    color1 = generate_pastel_color_from_text(text, brightness, 0, salt)
    color2 = generate_pastel_color_from_text(text, brightness, 0, salt)

    assert color1 == color2
    assert color1.startswith("#")
    assert len(color1) == 7  # #RRGGBB format


def test_when_different_salt_then_different_color() -> None:
    """Given the same text but different salt, when generating colors, then produces different colors."""
    text = "Giesing → Tegernseer Str."
    brightness = 0.7

    color_with_salt_0 = generate_pastel_color_from_text(text, brightness, 0, salt=0)
    color_with_salt_1 = generate_pastel_color_from_text(text, brightness, 0, salt=1)
    color_with_salt_2 = generate_pastel_color_from_text(text, brightness, 0, salt=2)

    # All should be valid hex colors
    assert color_with_salt_0.startswith("#")
    assert color_with_salt_1.startswith("#")
    assert color_with_salt_2.startswith("#")
    assert len(color_with_salt_0) == 7
    assert len(color_with_salt_1) == 7
    assert len(color_with_salt_2) == 7

    # Different salts should produce different colors
    assert color_with_salt_0 != color_with_salt_1, "Salt 0 and 1 should produce different colors"
    assert color_with_salt_0 != color_with_salt_2, "Salt 0 and 2 should produce different colors"
    assert color_with_salt_1 != color_with_salt_2, "Salt 1 and 2 should produce different colors"


def test_when_salt_used_in_calculator_then_affects_color() -> None:
    """Given direction groups with different salt values, when calculating display data, then produces different colors."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        line="U2",
        destination="Tegernseer Str.",
        is_cancelled=False,
        delay_seconds=None,
        is_realtime=True,
        platform=None,
        transport_type="U-Bahn",
        icon="mdi:subway",
        messages=[],
    )

    with patch.dict(os.environ, {}, clear=True):
        stop_configs = [
            StopConfiguration(
                station_id="de:09162:1110",
                station_name="Giesing",
                direction_mappings={},
                random_header_colors=True,
                random_color_salt=0,
            ),
            StopConfiguration(
                station_id="de:09162:1110:4:4",
                station_name="Giesing",
                direction_mappings={},
                random_header_colors=True,
                random_color_salt=1,
            ),
        ]
        config = AppConfig(config_file=None, _env_file=None)
        formatter = DepartureFormatter(config)
        calculator = DepartureGroupingCalculator(
            stop_configs, config, formatter, random_header_colors=True, random_color_salt=0
        )

    # Create direction groups with same header text but different salt values
    direction_groups = [
        DirectionGroupWithMetadata(
            station_id="de:09162:1110",
            stop_name="Giesing",
            direction_name="->Tegernseer Str.",
            departures=[departure],
            random_header_colors=True,
            header_background_brightness=None,
            random_color_salt=0,  # salt = 0
        ),
        DirectionGroupWithMetadata(
            station_id="de:09162:1110:4:4",
            stop_name="Giesing",
            direction_name="->Tegernseer Str.",
            departures=[departure],
            random_header_colors=True,
            header_background_brightness=None,
            random_color_salt=1,  # salt = 1
        ),
    ]
    result = calculator.calculate_display_data(direction_groups)

    # Should have 2 groups (first header uses banner_color, second uses random color)
    assert len(result["groups_with_departures"]) == 2

    # First group is the first header, so it won't have header_color (uses banner_color)
    first_group = result["groups_with_departures"][0]
    assert first_group["is_first_header"] is True
    assert "header_color" not in first_group

    # Second group should have header_color with salt=1
    second_group = result["groups_with_departures"][1]
    assert second_group["is_first_header"] is False
    assert "header_color" in second_group
    color_with_salt_1 = second_group["header_color"]

    # Now test with salt=0 for the second group
    direction_groups_salt_0 = [
        DirectionGroupWithMetadata(
            station_id="de:09162:1110",
            stop_name="Giesing",
            direction_name="->Tegernseer Str.",
            departures=[departure],
            random_header_colors=True,
            header_background_brightness=None,
            random_color_salt=0,  # salt = 0
        ),
        DirectionGroupWithMetadata(
            station_id="de:09162:1110:4:4",
            stop_name="Giesing",
            direction_name="->Tegernseer Str.",
            departures=[departure],
            random_header_colors=True,
            header_background_brightness=None,
            random_color_salt=0,  # salt = 0 (same as first)
        ),
    ]
    result_salt_0 = calculator.calculate_display_data(direction_groups_salt_0)
    second_group_salt_0 = result_salt_0["groups_with_departures"][1]

    # Colors should be different because salt is different
    assert (
        color_with_salt_1 != second_group_salt_0["header_color"]
    ), "Different salt values should produce different colors for the same header text"
