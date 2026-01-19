"""Inky display adapter."""

import asyncio
import contextlib
import logging
import os
from typing import TYPE_CHECKING

from mvg_departures.adapters.web.builders.departure_grouping_calculator import (
    DepartureGroupingCalculator,
)
from mvg_departures.domain.models.direction_group_with_metadata import (
    DirectionGroupWithMetadata,
)
from mvg_departures.domain.models.grouped_departures import GroupedDepartures
from mvg_departures.domain.models.stop_configuration import StopConfiguration
from mvg_departures.domain.ports.display_adapter import DisplayAdapter
from PIL import Image

from .config import InkyDisplayConfig
from .mock_display import MockInkyDisplay, create_mock_display
from .renderer import InkyRenderer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inky.inky_uc8159 import Inky as InkyDisplay  # Optional hardware dependency


class InkyDisplayAdapter(DisplayAdapter):
    """Display adapter for Pimoroni Inky e-ink displays."""

    def __init__(
        self,
        config: InkyDisplayConfig | None = None,
        grouping_calculator: DepartureGroupingCalculator | None = None,
        stop_configs: list[StopConfiguration] | None = None,
    ) -> None:
        """Initialize Inky display adapter.

        Args:
            config: Optional display configuration. If None, uses defaults.
            grouping_calculator: Departure grouping calculator (same as web version).
            stop_configs: List of stop configurations for converting GroupedDepartures to
                         DirectionGroupWithMetadata. Required if display_departures will be
                         called with GroupedDepartures.
        """
        self.config = config or InkyDisplayConfig()
        self.grouping_calculator = grouping_calculator
        self.stop_configs = stop_configs or []
        self.display: InkyDisplay | None = None
        self.renderer: InkyRenderer | None = None
        self._update_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the display adapter."""
        # Check if we should use mock mode
        use_mock = os.getenv("INKY_MOCK_MODE", "false").lower() in ("true", "1", "yes")
        output_dir = os.getenv("INKY_MOCK_OUTPUT_DIR", None)

        if use_mock:
            logger.info("Using mock Inky display (INKY_MOCK_MODE=true)")
            # Use "red" color mode to support colored headers
            self.display = create_mock_display(
                width=self.config.width,
                height=self.config.height,
                colour="red",  # Use red color mode (Spectra supports all 6 colors: white, black, red, yellow, green, blue)
                output_dir=output_dir,
            )
            # Update config with actual display dimensions (even for mock)
            self.config.width = self.display.width
            self.config.height = self.display.height
        else:
            try:
                from inky.auto import auto  # Optional hardware dependency

                # Auto-detect Inky display
                self.display = auto()
                logger.info(
                    f"Initialized Inky display: {self.display.width}x{self.display.height}, "
                    f"colour: {self.display.colour}"
                )

                # Real hardware returns dimensions in landscape mode, but we need portrait mode
                # Swap width and height for real hardware (mock is already correct)
                # For 7.5" Inky Impression Spectra: hardware returns 800x480 (landscape), we need 480x800 (portrait)
                display_width = self.display.width
                display_height = self.display.height
                
                # Swap for portrait mode on real hardware
                self.config.width = display_height  # Use height as width (portrait)
                self.config.height = display_width  # Use width as height (portrait)
                logger.info(
                    f"Swapped dimensions for portrait mode: {display_width}x{display_height} -> "
                    f"{self.config.width}x{self.config.height}"
                )
            except ImportError as e:
                logger.warning(
                    f"Inky library not available (likely on non-Linux platform): {e}. "
                    "Falling back to mock mode. "
                    "To use real hardware, install with: pip install -e '.[hardware]' "
                    "or set INKY_MOCK_MODE=true to suppress this warning."
                )
                # Fall back to mock mode
                self.display = create_mock_display(
                    width=self.config.width,
                    height=self.config.height,
                    colour="red",  # Use red color mode (Spectra supports all 6 colors: white, black, red, yellow, green, blue)
                    output_dir=output_dir,
                )
                # Update config with actual display dimensions
                self.config.width = self.display.width
                self.config.height = self.display.height
            except Exception as e:
                logger.warning(
                    f"Failed to initialize real Inky display: {e}. "
                    "Falling back to mock mode. Set INKY_MOCK_MODE=true to suppress this warning."
                )
                # Fall back to mock mode
                self.display = create_mock_display(
                    width=self.config.width,
                    height=self.config.height,
                    colour="red",  # Use red color mode (Spectra supports all 6 colors: white, black, red, yellow, green, blue)
                    output_dir=output_dir,
                )
                # Update config with actual display dimensions
                self.config.width = self.display.width
                self.config.height = self.display.height

        # Initialize renderer with grouping calculator
        if not self.grouping_calculator:
            raise ValueError("grouping_calculator is required")
        self.renderer = InkyRenderer(self.config, self.display, self.grouping_calculator)

        # Set border color
        try:
            self.display.set_border(self.display.WHITE)
        except Exception as e:
            logger.warning(f"Could not set border color: {e}")

        self._running = True
        logger.info("Inky display adapter started")

    async def stop(self) -> None:
        """Stop the display adapter."""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._update_task
        logger.info("Inky display adapter stopped")

    async def display_departures(
        self,
        direction_groups: (
            list[GroupedDepartures] | list[tuple[GroupedDepartures, StopConfiguration]]
        ),
    ) -> None:
        """Display grouped departures on Inky display.

        Args:
            direction_groups: List of grouped departures, or list of tuples (group, stop_config).
                            If tuples are provided, uses the stop_config directly.
                            Otherwise, tries to match groups to stop configs.
        """
        if not self.renderer or not self.display:
            logger.warning("Display not initialized, skipping render")
            return

        try:
            # Convert GroupedDepartures to DirectionGroupWithMetadata
            # If direction_groups contains tuples, use the stop_config directly
            # Otherwise, try to match groups to stop configs
            direction_groups_with_metadata: list[DirectionGroupWithMetadata] = []
            for item in direction_groups:
                # Check if item is a tuple (group, stop_config) or just a group
                if isinstance(item, tuple) and len(item) == 2:
                    group, stop_config = item
                else:
                    # Legacy: item is just a GroupedDepartures, try to match
                    group = item
                    stop_config = None

                if not group.departures:
                    continue

                # If stop_config not provided, try to find matching stop config
                if not stop_config:
                    # Try matching by direction_name in direction_mappings
                    for stop_cfg in self.stop_configs:
                        # Check if this direction_name matches any pattern in this stop's direction_mappings
                        if group.direction_name in stop_cfg.direction_mappings:
                            stop_config = stop_cfg
                            break

                    # If no match found, use the first stop config as fallback
                    if not stop_config and self.stop_configs:
                        stop_config = self.stop_configs[0]
                        logger.debug(
                            f"Could not match direction '{group.direction_name}' to a stop config, "
                            f"using first stop config '{stop_config.station_name}' as fallback"
                        )

                if not stop_config:
                    logger.warning(
                        f"No stop config available for direction '{group.direction_name}', skipping"
                    )
                    continue

                direction_groups_with_metadata.append(
                    DirectionGroupWithMetadata(
                        station_id=stop_config.station_id,
                        stop_name=stop_config.station_name,
                        direction_name=group.direction_name,
                        departures=group.departures,
                        random_header_colors=stop_config.random_header_colors,
                        header_background_brightness=stop_config.header_background_brightness,
                        random_color_salt=stop_config.random_color_salt,
                    )
                )

            # Render to PIL Image
            # The renderer uses config.width and config.height which are already swapped for portrait mode
            # on real hardware (480x800), or correct for mock (480x800)
            img = self.renderer.render(direction_groups_with_metadata)

            # Resize image to display resolution if needed (as per Pimoroni examples)
            # Note: For real hardware, the image is rendered in portrait (480x800) but display is landscape (800x480)
            # The display.set_image() should handle the orientation, so we don't rotate/transpose here
            if hasattr(self.display, "resolution") and img.size != self.display.resolution:
                # Only resize if dimensions don't match - but be careful not to stretch
                # For portrait rendering on landscape display, this should not be needed
                logger.debug(
                    f"Image size {img.size}, display resolution {self.display.resolution}"
                )

            # Set image on display (with optional saturation parameter for Spectra)
            # Per Pimoroni examples: inky.set_image(resizedimage, saturation=saturation)
            if hasattr(self.display, "set_image"):
                try:
                    # Try with saturation parameter (for Spectra displays)
                    self.display.set_image(img, saturation=0.5)
                except TypeError:
                    # Fallback if saturation parameter not supported
                    self.display.set_image(img)
            else:
                # For mock display, use set_image method
                self.display.set_image(img)

            # Update display (this is the slow part for e-ink)
            # In mock mode, this saves to file instead
            logger.debug("Updating Inky display...")
            if isinstance(self.display, MockInkyDisplay):
                # Generate filename with timestamp for mock mode
                import time

                filename = f"departures_{int(time.time())}.png"
                self.display.show(filename)
            else:
                self.display.show()
            logger.debug("Inky display updated")
        except Exception as e:
            logger.error(f"Failed to display departures: {e}", exc_info=True)
