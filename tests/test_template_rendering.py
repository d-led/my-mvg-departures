"""Tests for template rendering in pyview_app."""

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.presence import PresenceTracker
from mvg_departures.adapters.web.state import State
from mvg_departures.adapters.web.views.departures.departures import (
    DeparturesLiveView,
    LiveViewDependencies,
)
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import (
    Departure,
    DirectionGroupWithMetadata,
    StopConfiguration,
)


def _create_test_view() -> DeparturesLiveView:
    """Create a test DeparturesLiveView instance."""
    with patch.dict(os.environ, {}, clear=True):
        state_manager = State()
        grouping_service = MagicMock(spec=DepartureGroupingService)
        stop_configs = [
            StopConfiguration(
                station_id="de:09162:70",
                station_name="Universität",
                direction_mappings={},
            )
        ]
        config = AppConfig.for_testing(config_file=None)
        presence_tracker = PresenceTracker()
        dependencies = LiveViewDependencies(
            state_manager=state_manager,
            grouping_service=grouping_service,
            stop_configs=stop_configs,
            config=config,
            presence_tracker=presence_tracker,
        )
        return DeparturesLiveView(dependencies)


def test_prepare_template_data_includes_line_and_destination() -> None:
    """Given a departure, when preparing template data, then line and destination are included."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    assert len(template_data["groups_with_departures"]) == 1
    group = template_data["groups_with_departures"][0]
    assert len(group["departures"]) == 1
    dep_data = group["departures"][0]
    assert dep_data["line"] == "U3"
    assert dep_data["destination"] == "Giesing"


def test_prepare_template_data_cancelled_sets_flag() -> None:
    """Given a cancelled departure, when preparing template data, then cancelled flag is set."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    dep_data = template_data["groups_with_departures"][0]["departures"][0]
    assert dep_data["cancelled"] is True


def test_prepare_template_data_delay_sets_flag() -> None:
    """Given a delayed departure, when preparing template data, then delay flag and display are set."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    dep_data = template_data["groups_with_departures"][0]["departures"][0]
    assert dep_data["has_delay"] is True
    assert dep_data["delay_display"] is not None
    assert "2m" in dep_data["delay_display"]


def test_prepare_template_data_realtime_sets_flag() -> None:
    """Given a realtime departure, when preparing template data, then realtime flag is set."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    dep_data = template_data["groups_with_departures"][0]["departures"][0]
    assert dep_data["is_realtime"] is True


def test_prepare_template_data_platform_when_present() -> None:
    """Given a departure with platform, when preparing template data, then platform is included."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    dep_data = template_data["groups_with_departures"][0]["departures"][0]
    assert dep_data["platform"] == "1"


def test_prepare_template_data_platform_when_missing() -> None:
    """Given a departure without platform, when preparing template data, then platform is None."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    dep_data = template_data["groups_with_departures"][0]["departures"][0]
    assert dep_data["platform"] is None


def test_prepare_template_data_empty_list() -> None:
    """Given empty direction groups, when preparing template data, then has_departures is False."""
    view = _create_test_view()
    template_data = view.departure_grouping_calculator.calculate_display_data([])

    assert template_data["has_departures"] is False
    assert len(template_data["groups_with_departures"]) == 0


def test_prepare_template_data_single_departure() -> None:
    """Given a single departure, when preparing template data, then it is included."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    assert template_data["has_departures"] is True
    assert len(template_data["groups_with_departures"]) == 1
    assert len(template_data["groups_with_departures"][0]["departures"]) == 1


def test_prepare_template_data_multiple_departures() -> None:
    """Given multiple departures, when preparing template data, then all are included."""
    now = datetime.now(UTC)
    departure1 = Departure(
        time=now,
        planned_time=now,
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
        time=now,
        planned_time=now,
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

    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    assert template_data["has_departures"] is True
    assert len(template_data["groups_with_departures"]) == 2


def test_prepare_template_data_stop_without_departures() -> None:
    """Given a stop with no departures, when preparing template data, then it is in stops_without_departures."""
    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    assert template_data["has_departures"] is False
    assert "Universität" in template_data["stops_without_departures"]


def test_prepare_template_data_first_header_flag() -> None:
    """Given departures, when preparing template data, then first header is marked."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    group = template_data["groups_with_departures"][0]
    assert group["is_first_header"] is True
    assert group["is_first_group"] is True
    assert group["is_last_group"] is True


def test_prepare_template_data_new_stop_flag() -> None:
    """Given departures from different stops, when preparing template data, then is_new_stop is set correctly."""
    now = datetime.now(UTC)
    departure1 = Departure(
        time=now,
        planned_time=now,
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
        time=now,
        planned_time=now,
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

    view = _create_test_view()
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
    template_data = view.departure_grouping_calculator.calculate_display_data(direction_groups)

    assert template_data["groups_with_departures"][0]["is_new_stop"] is True
    assert template_data["groups_with_departures"][1]["is_new_stop"] is True


# Template rendering tests - these actually render the template and check HTML output


async def test_render_includes_line_and_destination() -> None:
    """Given a departure, when rendering, then line and destination are in HTML."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
    from mvg_departures.adapters.web.state import DeparturesState

    state = DeparturesState(
        direction_groups=[
            DirectionGroupWithMetadata(
                station_id="de:09162:70",
                stop_name="Universität",
                direction_name="->Giesing",
                departures=[departure],
                random_header_colors=None,
                header_background_brightness=None,
                random_color_salt=None,
            )
        ],
        last_update=now,
        api_status="success",
    )
    result = await view.render(state, {})
    html = result.text() if hasattr(result, "text") else str(result)

    assert "U3" in html
    assert "Giesing" in html


async def test_render_cancelled_applies_class() -> None:
    """Given a cancelled departure, when rendering, then cancelled class is in HTML."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
    from mvg_departures.adapters.web.state import DeparturesState

    state = DeparturesState(
        direction_groups=[
            DirectionGroupWithMetadata(
                station_id="de:09162:70",
                stop_name="Universität",
                direction_name="->Giesing",
                departures=[departure],
                random_header_colors=None,
                header_background_brightness=None,
                random_color_salt=None,
            )
        ],
        last_update=now,
        api_status="success",
    )
    result = await view.render(state, {})
    html = result.text() if hasattr(result, "text") else str(result)

    assert 'class="departure-row cancelled"' in html or 'class="departure-row  cancelled"' in html


async def test_render_delay_applies_class() -> None:
    """Given a delayed departure, when rendering, then delay class is in HTML."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
    from mvg_departures.adapters.web.state import DeparturesState

    state = DeparturesState(
        direction_groups=[
            DirectionGroupWithMetadata(
                station_id="de:09162:70",
                stop_name="Universität",
                direction_name="->Giesing",
                departures=[departure],
                random_header_colors=None,
                header_background_brightness=None,
                random_color_salt=None,
            )
        ],
        last_update=now,
        api_status="success",
    )
    result = await view.render(state, {})
    html = result.text() if hasattr(result, "text") else str(result)

    assert 'class="time delay' in html
    assert "2m" in html


async def test_render_realtime_applies_class() -> None:
    """Given a realtime departure, when rendering, then realtime class is in HTML."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
    from mvg_departures.adapters.web.state import DeparturesState

    state = DeparturesState(
        direction_groups=[
            DirectionGroupWithMetadata(
                station_id="de:09162:70",
                stop_name="Universität",
                direction_name="->Giesing",
                departures=[departure],
                random_header_colors=None,
                header_background_brightness=None,
                random_color_salt=None,
            )
        ],
        last_update=now,
        api_status="success",
    )
    result = await view.render(state, {})
    html = result.text() if hasattr(result, "text") else str(result)

    assert 'class="time realtime' in html or 'class="time  realtime' in html


async def test_render_platform_when_present() -> None:
    """Given a departure with platform, when rendering, then platform is in HTML."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
    from mvg_departures.adapters.web.state import DeparturesState

    state = DeparturesState(
        direction_groups=[
            DirectionGroupWithMetadata(
                station_id="de:09162:70",
                stop_name="Universität",
                direction_name="->Giesing",
                departures=[departure],
                random_header_colors=None,
                header_background_brightness=None,
                random_color_salt=None,
            )
        ],
        last_update=now,
        api_status="success",
    )
    result = await view.render(state, {})
    html = result.text() if hasattr(result, "text") else str(result)

    assert "1" in html
    assert 'class="platform"' in html


async def test_render_empty_list() -> None:
    """Given empty direction groups, when rendering, then no departures message is in HTML."""
    now = datetime.now(UTC)
    view = _create_test_view()
    from mvg_departures.adapters.web.state import DeparturesState

    state = DeparturesState(
        direction_groups=[],
        last_update=now,
        api_status="success",
    )
    result = await view.render(state, {})
    html = result.text() if hasattr(result, "text") else str(result)

    assert "No departures available" in html


async def test_render_stop_without_departures() -> None:
    """Given a stop with departures and another without, when rendering, then empty stop is shown."""
    now = datetime.now(UTC)
    departure = Departure(
        time=now,
        planned_time=now,
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

    view = _create_test_view()
    # Add another stop config so we can test stops without departures
    view.stop_configs.append(
        StopConfiguration(
            station_id="de:09162:71",
            station_name="Marienplatz",
            direction_mappings={},
        )
    )
    from mvg_departures.adapters.web.state import DeparturesState

    # One stop has departures, one doesn't
    state = DeparturesState(
        direction_groups=[
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
        ],
        last_update=now,
        api_status="success",
    )
    result = await view.render(state, {})
    html = result.text() if hasattr(result, "text") else str(result)

    assert "No departures" in html
    assert "Marienplatz" in html
