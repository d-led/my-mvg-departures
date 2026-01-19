"""Inky display adapter."""

import asyncio
import contextlib
import logging
import os
from typing import TYPE_CHECKING

import numpy as np
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
        self._needs_rotation = False  # Whether to rotate image to match hardware orientation
        self._previous_image: Image.Image | None = (
            None  # Previous rendered image for partial updates
        )
        self._partial_update_count = 0  # Count of partial updates (for periodic full refresh)

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
                display_width = self.display.width
                display_height = self.display.height
                logger.info(
                    f"Initialized Inky display: {display_width}x{display_height}, "
                    f"colour: {self.display.colour}"
                )

                # For hardware, we want text to run along the shortest side (portrait orientation)
                # If hardware is landscape (width > height), swap dimensions for rendering
                # This makes the renderer think it's portrait, so text flows along the short side
                if display_width > display_height:
                    # Landscape hardware: render as portrait (text along short side)
                    self.config.width = display_height  # Use height as width for rendering
                    self.config.height = display_width  # Use width as height for rendering
                    self._needs_rotation = True  # Mark that we need to rotate the final image
                    logger.info(
                        f"Hardware is landscape ({display_width}x{display_height}), "
                        f"rendering as portrait ({self.config.width}x{self.config.height}) "
                        f"for text along short side"
                    )
                else:
                    # Already portrait or square: use as-is
                    self.config.width = display_width
                    self.config.height = display_height
                    self._needs_rotation = False
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
            # The renderer uses config.width and config.height which may be swapped for portrait mode
            # on real hardware (e.g., 480x800) so text runs along the short side
            img = self.renderer.render(direction_groups_with_metadata)

            # If hardware is landscape but we rendered as portrait, rotate the image to match hardware
            # Use transpose (not rotate) to avoid pixel stretching - it's a perfect 90-degree swap
            if self._needs_rotation:
                # Rotate 90 degrees clockwise: portrait (480x800) -> landscape (800x480)
                # ROTATE_270 = 270° counter-clockwise = 90° clockwise (perfect pixel swap, no interpolation)
                original_size = img.size
                img = img.transpose(Image.Transpose.ROTATE_270)
                logger.info(
                    f"Rotated rendered image: {original_size} -> {img.size} "
                    f"(portrait -> landscape, no stretching)"
                )

            # Verify image matches display resolution (should match after rotation if needed)
            expected_size = (self.display.width, self.display.height)
            if img.size != expected_size:
                logger.error(
                    f"Image size {img.size} doesn't match display resolution {expected_size}. "
                    f"Rotation flag: {self._needs_rotation}"
                )
                raise ValueError(
                    f"Image size {img.size} doesn't match expected display size {expected_size}"
                )

            # Mock display always does full updates (for easier debugging/visualization)
            # Real e-paper display uses partial updates when enabled (to reduce flicker)
            if isinstance(self.display, MockInkyDisplay):
                # Mock display: always perform full update to show complete image
                logger.debug("Mock display: performing full update (always shows complete image).")
                self._perform_full_update(img)
            elif self.config.partial_update_enabled:
                # Real e-paper: use partial updates when enabled
                changed_regions = self._find_changed_regions(self._previous_image, img)

                if not changed_regions:
                    logger.debug("No changes detected, skipping display update.")
                    return

                # Check for forced full refresh
                if (
                    self.config.full_refresh_interval > 0
                    and self._partial_update_count >= self.config.full_refresh_interval
                ):
                    logger.info(
                        f"Forcing full refresh after {self._partial_update_count} partial updates."
                    )
                    self._partial_update_count = 0
                    self._perform_full_update(img)
                elif len(changed_regions) == 1 and changed_regions[0] == (
                    0,
                    0,
                    img.width,
                    img.height,
                ):
                    # If the entire image changed (e.g., first render or major layout change)
                    logger.info("Full image changed, performing full refresh.")
                    self._partial_update_count = 0
                    self._perform_full_update(img)
                else:
                    # Perform partial update
                    logger.debug(f"Performing partial update for {len(changed_regions)} regions.")
                    self._partial_update_count += 1
                    self._perform_partial_update(img, changed_regions)
            else:
                # Partial updates disabled, always perform full update
                logger.debug("Partial updates disabled, performing full refresh.")
                self._perform_full_update(img)

            self._previous_image = img.copy()  # Store current image for next comparison
            logger.debug("Inky display updated")
        except Exception as e:
            logger.error(f"Failed to display departures: {e}", exc_info=True)

    def _perform_full_update(self, img: Image.Image) -> None:
        """Perform a full display update."""
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
        logger.debug("Performing full display update...")
        if isinstance(self.display, MockInkyDisplay):
            # Generate filename with timestamp for mock mode
            import time

            filename = f"departures_{int(time.time())}.png"
            self.display.show(filename)
        else:
            self.display.show()

    def _perform_partial_update(
        self, img: Image.Image, regions: list[tuple[int, int, int, int]]
    ) -> None:
        """Perform a partial display update for specified regions.

        Args:
            img: Full image to display.
            regions: List of (x, y, width, height) tuples for changed regions.
        """
        # Set image on display first (required before partial update)
        if hasattr(self.display, "set_image"):
            try:
                self.display.set_image(img, saturation=0.5)
            except TypeError:
                self.display.set_image(img)
        else:
            self.display.set_image(img)

        # Try to use partial update if supported
        # Note: Mock display should never reach here (it always does full updates)
        if isinstance(self.display, MockInkyDisplay):
            # This shouldn't happen, but if it does, do a full update
            logger.warning("Mock display reached partial update path, falling back to full update.")
            self._perform_full_update(img)
            return
        if hasattr(self.display, "show_partial"):
            # Some Inky displays might have show_partial (e.g., older versions or specific models)
            for x, y, w, h in regions:
                self.display.show_partial(x, y, w, h)
        elif hasattr(self.display, "partial_update"):
            # Newer Inky libraries might have a partial_update method
            for x, y, w, h in regions:
                self.display.partial_update(x, y, w, h)
        else:
            # Partial update not supported, fall back to full update
            logger.warning(
                "Partial update not supported by Inky library, falling back to full update."
            )
            self._perform_full_update(img)

    def _find_changed_regions(
        self, previous_img: Image.Image | None, current_img: Image.Image
    ) -> list[tuple[int, int, int, int]]:
        """Find changed regions between two images.

        Args:
            previous_img: Previous image (None if first render).
            current_img: Current image.

        Returns:
            List of (x, y, width, height) tuples for changed regions.
            Returns empty list if no previous image or if images are identical.
        """
        if previous_img is None:
            # First render: return full image region
            return [(0, 0, current_img.width, current_img.height)]

        if previous_img.size != current_img.size:
            # Size changed: return full image region
            return [(0, 0, current_img.width, current_img.height)]

        # Convert images to numpy arrays for comparison
        # Convert to RGB if needed for comparison
        prev_array = np.array(previous_img.convert("RGB"))
        curr_array = np.array(current_img.convert("RGB"))

        # Find pixels that changed
        diff = np.any(prev_array != curr_array, axis=2)

        if not np.any(diff):
            # No changes
            return []

        # Find bounding box of changed region
        changed_y, changed_x = np.where(diff)
        if len(changed_y) == 0:
            return []

        min_y, max_y = int(changed_y.min()), int(changed_y.max())
        min_x, max_x = int(changed_x.min()), int(changed_x.max())

        # Add some padding to ensure we update edges properly
        padding = 2
        x = max(0, min_x - padding)
        y = max(0, min_y - padding)
        width = min(current_img.width - x, max_x - min_x + 1 + 2 * padding)
        height = min(current_img.height - y, max_y - min_y + 1 + 2 * padding)

        # If changed region is too large (>50% of image), just return full region
        # This avoids partial update overhead when most of the screen changed
        if width * height > 0.5 * current_img.width * current_img.height:
            return [(0, 0, current_img.width, current_img.height)]

        return [(x, y, width, height)]
