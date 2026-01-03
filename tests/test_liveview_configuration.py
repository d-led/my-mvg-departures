"""Tests for LiveView configuration types and initialization."""

import os
from unittest.mock import MagicMock, patch

import pytest

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.presence import PresenceTracker
from mvg_departures.adapters.web.state import State
from mvg_departures.adapters.web.views.departures.departures import (
    DeparturesLiveView,
    DisplayConfiguration,
    LiveViewConfiguration,
    LiveViewDependencies,
    RouteDisplaySettings,
    create_departures_live_view,
)
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import StopConfiguration


def test_live_view_dependencies_creation() -> None:
    """Given all required dependencies, when creating LiveViewDependencies, then all fields are set."""
    state_manager = State()
    grouping_service = MagicMock(spec=DepartureGroupingService)
    stop_configs = [
        StopConfiguration(station_id="de:09162:70", station_name="Test", direction_mappings={})
    ]
    config = AppConfig.for_testing()
    presence_tracker = PresenceTracker()

    dependencies = LiveViewDependencies(
        state_manager=state_manager,
        grouping_service=grouping_service,
        stop_configs=stop_configs,
        config=config,
        presence_tracker=presence_tracker,
    )

    assert dependencies.state_manager is state_manager
    assert dependencies.grouping_service is grouping_service
    assert dependencies.stop_configs == stop_configs
    assert dependencies.config is config
    assert dependencies.presence_tracker is presence_tracker


def test_live_view_dependencies_is_frozen() -> None:
    """Given LiveViewDependencies, when trying to modify, then raises AttributeError."""
    dependencies = LiveViewDependencies(
        state_manager=State(),
        grouping_service=MagicMock(spec=DepartureGroupingService),
        stop_configs=[],
        config=AppConfig.for_testing(),
        presence_tracker=PresenceTracker(),
    )

    with pytest.raises(AttributeError):
        dependencies.state_manager = State()


def test_route_display_settings_defaults() -> None:
    """Given no parameters, when creating RouteDisplaySettings, then defaults to None."""
    settings = RouteDisplaySettings()

    assert settings.title is None
    assert settings.theme is None


def test_route_display_settings_with_values() -> None:
    """Given title and theme, when creating RouteDisplaySettings, then values are set."""
    settings = RouteDisplaySettings(title="Custom Title", theme="dark")

    assert settings.title == "Custom Title"
    assert settings.theme == "dark"


def test_route_display_settings_is_frozen() -> None:
    """Given RouteDisplaySettings, when trying to modify, then raises AttributeError."""
    settings = RouteDisplaySettings(title="Test")

    with pytest.raises(AttributeError):
        settings.title = "Modified"


def test_display_configuration_defaults() -> None:
    """Given no parameters, when creating DisplayConfiguration, then uses sensible defaults."""
    config = DisplayConfiguration()

    assert config.fill_vertical_space is False
    assert config.font_scaling_factor_when_filling == 1.0
    assert config.random_header_colors is False
    assert config.header_background_brightness == 0.7
    assert config.random_color_salt == 0


def test_display_configuration_with_custom_values() -> None:
    """Given custom values, when creating DisplayConfiguration, then values are set."""
    config = DisplayConfiguration(
        fill_vertical_space=True,
        font_scaling_factor_when_filling=1.5,
        random_header_colors=True,
        header_background_brightness=0.8,
        random_color_salt=42,
    )

    assert config.fill_vertical_space is True
    assert config.font_scaling_factor_when_filling == 1.5
    assert config.random_header_colors is True
    assert config.header_background_brightness == 0.8
    assert config.random_color_salt == 42


def test_display_configuration_is_frozen() -> None:
    """Given DisplayConfiguration, when trying to modify, then raises AttributeError."""
    config = DisplayConfiguration(fill_vertical_space=True)

    with pytest.raises(AttributeError):
        config.fill_vertical_space = False


def test_live_view_configuration_creation() -> None:
    """Given all components, when creating LiveViewConfiguration, then all fields are set."""
    dependencies = LiveViewDependencies(
        state_manager=State(),
        grouping_service=MagicMock(spec=DepartureGroupingService),
        stop_configs=[],
        config=AppConfig.for_testing(),
        presence_tracker=PresenceTracker(),
    )
    route_display = RouteDisplaySettings(title="Test")
    display_config = DisplayConfiguration(fill_vertical_space=True)

    config = LiveViewConfiguration(
        dependencies=dependencies,
        route_display=route_display,
        display_config=display_config,
    )

    assert config.dependencies is dependencies
    assert config.route_display is route_display
    assert config.display_config is display_config


def test_live_view_configuration_is_frozen() -> None:
    """Given LiveViewConfiguration, when trying to modify, then raises AttributeError."""
    config = LiveViewConfiguration(
        dependencies=LiveViewDependencies(
            state_manager=State(),
            grouping_service=MagicMock(spec=DepartureGroupingService),
            stop_configs=[],
            config=AppConfig.for_testing(),
            presence_tracker=PresenceTracker(),
        ),
        route_display=RouteDisplaySettings(),
        display_config=DisplayConfiguration(),
    )

    with pytest.raises(AttributeError):
        config.dependencies = LiveViewDependencies(
            state_manager=State(),
            grouping_service=MagicMock(spec=DepartureGroupingService),
            stop_configs=[],
            config=AppConfig.for_testing(),
            presence_tracker=PresenceTracker(),
        )


def test_departures_live_view_init_with_dependencies_only() -> None:
    """Given only dependencies, when initializing DeparturesLiveView, then uses default display settings."""
    with patch.dict(os.environ, {}, clear=True):
        dependencies = LiveViewDependencies(
            state_manager=State(),
            grouping_service=MagicMock(spec=DepartureGroupingService),
            stop_configs=[
                StopConfiguration(
                    station_id="de:09162:70", station_name="Test", direction_mappings={}
                )
            ],
            config=AppConfig.for_testing(),
            presence_tracker=PresenceTracker(),
        )

        view = DeparturesLiveView(dependencies)

        assert view.state_manager is dependencies.state_manager
        assert view.grouping_service is dependencies.grouping_service
        assert view.stop_configs == dependencies.stop_configs
        assert view.config is dependencies.config
        assert view.presence_tracker is dependencies.presence_tracker
        assert view.route_title is None
        assert view.route_theme is None
        assert view.fill_vertical_space is False
        assert view.font_scaling_factor_when_filling == 1.0
        assert view.random_header_colors is False
        assert view.header_background_brightness == 0.7
        assert view.random_color_salt == 0


def test_departures_live_view_init_with_all_config() -> None:
    """Given all configuration, when initializing DeparturesLiveView, then all settings are applied."""
    with patch.dict(os.environ, {}, clear=True):
        dependencies = LiveViewDependencies(
            state_manager=State(),
            grouping_service=MagicMock(spec=DepartureGroupingService),
            stop_configs=[
                StopConfiguration(
                    station_id="de:09162:70", station_name="Test", direction_mappings={}
                )
            ],
            config=AppConfig.for_testing(),
            presence_tracker=PresenceTracker(),
        )
        route_display = RouteDisplaySettings(title="Custom Title", theme="dark")
        display_config = DisplayConfiguration(
            fill_vertical_space=True,
            font_scaling_factor_when_filling=1.5,
            random_header_colors=True,
            header_background_brightness=0.8,
            random_color_salt=42,
        )

        view = DeparturesLiveView(dependencies, route_display, display_config)

        assert view.route_title == "Custom Title"
        assert view.route_theme == "dark"
        assert view.fill_vertical_space is True
        assert view.font_scaling_factor_when_filling == 1.5
        assert view.random_header_colors is True
        assert view.header_background_brightness == 0.8
        assert view.random_color_salt == 42


def test_assign_instance_variables() -> None:
    """Given configuration objects, when assigning instance variables, then all fields are set correctly."""
    with patch.dict(os.environ, {}, clear=True):
        dependencies = LiveViewDependencies(
            state_manager=State(),
            grouping_service=MagicMock(spec=DepartureGroupingService),
            stop_configs=[
                StopConfiguration(
                    station_id="de:09162:70", station_name="Test", direction_mappings={}
                )
            ],
            config=AppConfig.for_testing(),
            presence_tracker=PresenceTracker(),
        )
        route_display = RouteDisplaySettings(title="Test Title")
        display_config = DisplayConfiguration(fill_vertical_space=True)

        view = DeparturesLiveView(dependencies, route_display, display_config)

        # Verify _assign_instance_variables was called correctly
        assert view.state_manager is dependencies.state_manager
        assert view.route_title == "Test Title"
        assert view.fill_vertical_space is True


def test_create_departures_live_view_factory() -> None:
    """Given LiveViewConfiguration, when creating LiveView via factory, then returns configured class."""
    with patch.dict(os.environ, {}, clear=True):
        state_manager = State()
        grouping_service = MagicMock(spec=DepartureGroupingService)
        stop_configs = [
            StopConfiguration(station_id="de:09162:70", station_name="Test", direction_mappings={})
        ]
        config = AppConfig.for_testing()
        presence_tracker = PresenceTracker()

        dependencies = LiveViewDependencies(
            state_manager=state_manager,
            grouping_service=grouping_service,
            stop_configs=stop_configs,
            config=config,
            presence_tracker=presence_tracker,
        )
        route_display = RouteDisplaySettings(title="Factory Title", theme="light")
        display_config = DisplayConfiguration(
            fill_vertical_space=True,
            font_scaling_factor_when_filling=1.2,
            random_header_colors=True,
            header_background_brightness=0.9,
            random_color_salt=10,
        )
        live_view_config = LiveViewConfiguration(
            dependencies=dependencies,
            route_display=route_display,
            display_config=display_config,
        )

        live_view_class = create_departures_live_view(live_view_config)

        assert issubclass(live_view_class, DeparturesLiveView)

        # Create an instance and verify it has the correct configuration
        instance = live_view_class()
        assert instance.route_title == "Factory Title"
        assert instance.route_theme == "light"
        assert instance.fill_vertical_space is True
        assert instance.font_scaling_factor_when_filling == 1.2
        assert instance.random_header_colors is True
        assert instance.header_background_brightness == 0.9
        assert instance.random_color_salt == 10


def test_create_departures_live_view_with_defaults() -> None:
    """Given minimal parameters, when creating LiveView via factory, then uses defaults."""
    with patch.dict(os.environ, {}, clear=True):
        state_manager = State()
        grouping_service = MagicMock(spec=DepartureGroupingService)
        stop_configs = [
            StopConfiguration(station_id="de:09162:70", station_name="Test", direction_mappings={})
        ]
        config = AppConfig.for_testing()
        presence_tracker = PresenceTracker()

        dependencies = LiveViewDependencies(
            state_manager=state_manager,
            grouping_service=grouping_service,
            stop_configs=stop_configs,
            config=config,
            presence_tracker=presence_tracker,
        )
        route_display = RouteDisplaySettings()  # Defaults: title=None, theme=None
        display_config = DisplayConfiguration()  # All defaults
        live_view_config = LiveViewConfiguration(
            dependencies=dependencies,
            route_display=route_display,
            display_config=display_config,
        )

        live_view_class = create_departures_live_view(live_view_config)

        instance = live_view_class()
        assert instance.route_title is None
        assert instance.route_theme is None
        assert instance.fill_vertical_space is False
        assert instance.font_scaling_factor_when_filling == 1.0
        assert instance.random_header_colors is False
        assert instance.header_background_brightness == 0.7
        assert instance.random_color_salt == 0


def test_create_departures_live_view_creates_unique_classes() -> None:
    """Given different configurations, when creating LiveViews, then each has unique class with correct config."""
    with patch.dict(os.environ, {}, clear=True):
        state_manager = State()
        grouping_service = MagicMock(spec=DepartureGroupingService)
        stop_configs = [
            StopConfiguration(station_id="de:09162:70", station_name="Test", direction_mappings={})
        ]
        config = AppConfig.for_testing()
        presence_tracker = PresenceTracker()

        dependencies = LiveViewDependencies(
            state_manager=state_manager,
            grouping_service=grouping_service,
            stop_configs=stop_configs,
            config=config,
            presence_tracker=presence_tracker,
        )

        config1 = LiveViewConfiguration(
            dependencies=dependencies,
            route_display=RouteDisplaySettings(title="Title 1"),
            display_config=DisplayConfiguration(),
        )
        class1 = create_departures_live_view(config1)

        config2 = LiveViewConfiguration(
            dependencies=dependencies,
            route_display=RouteDisplaySettings(title="Title 2"),
            display_config=DisplayConfiguration(),
        )
        class2 = create_departures_live_view(config2)

        # Each factory call creates a new class (even if names might be similar)
        assert class1 is not class2

        # Create instances and verify they have different configurations
        instance1 = class1()
        instance2 = class2()

        assert instance1.route_title == "Title 1"
        assert instance2.route_title == "Title 2"


def test_when_creating_live_view_with_config_then_returns_configured_class() -> None:
    """Given LiveViewConfiguration, when creating LiveView, then returns a class that can be instantiated."""
    with patch.dict(os.environ, {}, clear=True):
        state_manager = State()
        grouping_service = MagicMock(spec=DepartureGroupingService)
        stop_configs = [
            StopConfiguration(station_id="de:09162:70", station_name="Test", direction_mappings={})
        ]
        config = AppConfig.for_testing()
        presence_tracker = PresenceTracker()

        dependencies = LiveViewDependencies(
            state_manager=state_manager,
            grouping_service=grouping_service,
            stop_configs=stop_configs,
            config=config,
            presence_tracker=presence_tracker,
        )
        live_view_config = LiveViewConfiguration(
            dependencies=dependencies,
            route_display=RouteDisplaySettings(),
            display_config=DisplayConfiguration(),
        )

        live_view_class = create_departures_live_view(live_view_config)

        assert issubclass(live_view_class, DeparturesLiveView)
        # Should be able to instantiate the class
        instance = live_view_class()
        assert instance is not None


def test_when_creating_live_view_then_instance_has_correct_dependencies() -> None:
    """Given LiveViewConfiguration with dependencies, when creating instance, then has access to all dependencies."""
    with patch.dict(os.environ, {}, clear=True):
        state_manager = State()
        grouping_service = MagicMock(spec=DepartureGroupingService)
        stop_configs = [
            StopConfiguration(station_id="de:09162:70", station_name="Test", direction_mappings={})
        ]
        config = AppConfig.for_testing()
        presence_tracker = PresenceTracker()

        dependencies = LiveViewDependencies(
            state_manager=state_manager,
            grouping_service=grouping_service,
            stop_configs=stop_configs,
            config=config,
            presence_tracker=presence_tracker,
        )
        live_view_config = LiveViewConfiguration(
            dependencies=dependencies,
            route_display=RouteDisplaySettings(),
            display_config=DisplayConfiguration(),
        )

        live_view_class = create_departures_live_view(live_view_config)
        instance = live_view_class()

        # Verify instance has access to dependencies through state_manager
        assert instance.state_manager is state_manager
        assert instance.grouping_service is grouping_service
        assert instance.stop_configs == stop_configs
