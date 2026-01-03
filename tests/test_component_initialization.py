"""Behavior tests for component initialization configuration and method."""

import pytest

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.builders import HeaderDisplaySettings
from mvg_departures.adapters.web.views.departures.departures import (
    ComponentInitializationConfig,
)
from mvg_departures.domain.models import StopConfiguration
from tests.test_departures_liveview_helpers import _create_test_view


class TestComponentInitializationConfig:
    """Behavior tests for ComponentInitializationConfig dataclass."""

    def test_when_created_then_holds_all_configuration_values(self) -> None:
        """Given configuration values, when creating config, then holds all values correctly."""
        stop_configs = [
            StopConfiguration(
                station_id="de:09162:70",
                station_name="Universität",
                direction_mappings={},
            )
        ]
        config = AppConfig.for_testing(config_file=None)
        header_display = HeaderDisplaySettings(
            random_header_colors=True,
            header_background_brightness=0.8,
            random_color_salt=42,
        )

        init_config = ComponentInitializationConfig(
            stop_configs=stop_configs,
            config=config,
            header_display=header_display,
        )

        assert init_config.stop_configs == stop_configs
        assert init_config.config is config
        assert init_config.header_display is header_display

    def test_when_created_then_is_immutable(self) -> None:
        """Given a config instance, when trying to modify it, then raises FrozenInstanceError."""
        stop_configs = [
            StopConfiguration(
                station_id="de:09162:70",
                station_name="Universität",
                direction_mappings={},
            )
        ]
        config = AppConfig.for_testing(config_file=None)
        header_display = HeaderDisplaySettings()

        init_config = ComponentInitializationConfig(
            stop_configs=stop_configs,
            config=config,
            header_display=header_display,
        )

        with pytest.raises(
            (AttributeError, TypeError)
        ):  # FrozenInstanceError raises AttributeError
            init_config.stop_configs = []  # type: ignore[misc]


class TestInitializeComponents:
    """Behavior tests for _initialize_components method."""

    def test_when_initialized_then_creates_formatter_with_config(self) -> None:
        """Given initialization config, when initializing components, then creates formatter with correct config."""
        view = _create_test_view()
        stop_configs = [
            StopConfiguration(
                station_id="de:09162:70",
                station_name="Universität",
                direction_mappings={},
            )
        ]
        config = AppConfig.for_testing(config_file=None)
        header_display = HeaderDisplaySettings()

        init_config = ComponentInitializationConfig(
            stop_configs=stop_configs,
            config=config,
            header_display=header_display,
        )

        view._initialize_components(init_config)

        assert view.formatter is not None
        # Formatter should be initialized with the config from init_config
        assert hasattr(view.formatter, "format_departure_time")

    def test_when_initialized_then_creates_presence_broadcaster(self) -> None:
        """Given initialization config, when initializing components, then creates presence broadcaster."""
        view = _create_test_view()
        stop_configs = [
            StopConfiguration(
                station_id="de:09162:70",
                station_name="Universität",
                direction_mappings={},
            )
        ]
        config = AppConfig.for_testing(config_file=None)
        header_display = HeaderDisplaySettings()

        init_config = ComponentInitializationConfig(
            stop_configs=stop_configs,
            config=config,
            header_display=header_display,
        )

        view._initialize_components(init_config)

        assert view.presence_broadcaster is not None
        assert hasattr(view.presence_broadcaster, "broadcast_join")

    def test_when_initialized_then_creates_calculator_with_correct_config(self) -> None:
        """Given initialization config, when initializing components, then creates calculator with header display settings."""
        view = _create_test_view()
        stop_configs = [
            StopConfiguration(
                station_id="de:09162:70",
                station_name="Universität",
                direction_mappings={},
            )
        ]
        config = AppConfig.for_testing(config_file=None)
        header_display = HeaderDisplaySettings(
            random_header_colors=True,
            header_background_brightness=0.9,
            random_color_salt=123,
        )

        init_config = ComponentInitializationConfig(
            stop_configs=stop_configs,
            config=config,
            header_display=header_display,
        )

        view._initialize_components(init_config)

        assert view.departure_grouping_calculator is not None
        # Calculator should use the header display settings from init_config
        assert view.departure_grouping_calculator.random_header_colors is True
        assert view.departure_grouping_calculator.header_background_brightness == 0.9
        assert view.departure_grouping_calculator.random_color_salt == 123

    def test_when_initialized_with_different_header_settings_then_uses_those_settings(
        self,
    ) -> None:
        """Given different header display settings, when initializing, then calculator uses those specific settings."""
        view = _create_test_view()
        stop_configs = [
            StopConfiguration(
                station_id="de:09162:70",
                station_name="Universität",
                direction_mappings={},
            )
        ]
        config = AppConfig.for_testing(config_file=None)
        header_display = HeaderDisplaySettings(
            random_header_colors=False,
            header_background_brightness=0.5,
            random_color_salt=999,
        )

        init_config = ComponentInitializationConfig(
            stop_configs=stop_configs,
            config=config,
            header_display=header_display,
        )

        view._initialize_components(init_config)

        assert view.departure_grouping_calculator.random_header_colors is False
        assert view.departure_grouping_calculator.header_background_brightness == 0.5
        assert view.departure_grouping_calculator.random_color_salt == 999

    def test_when_initialized_then_calculator_uses_correct_stop_configs(self) -> None:
        """Given stop configs, when initializing, then calculator is configured with those stop configs."""
        view = _create_test_view()
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
        config = AppConfig.for_testing(config_file=None)
        header_display = HeaderDisplaySettings()

        init_config = ComponentInitializationConfig(
            stop_configs=stop_configs,
            config=config,
            header_display=header_display,
        )

        view._initialize_components(init_config)

        assert view.departure_grouping_calculator.stop_configs == stop_configs
        assert len(view.departure_grouping_calculator.stop_configs) == 2
