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
        self._needs_rotation = False  # Whether to rotate image to match hardware orientation
        self._previous_direction_groups: list[DirectionGroupWithMetadata] | None = (
            None  # Previous direction groups for input-level change detection
        )

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

            # Input-level change detection: compare departure data instead of images
            # This avoids false positives from dithering and is more efficient
            changed_sections = self._detect_input_changes(
                self._previous_direction_groups, direction_groups_with_metadata
            )

            # If row count changed, we need a full refresh (layout changes)
            total_previous_rows = self._count_total_rows(self._previous_direction_groups)
            total_current_rows = self._count_total_rows(direction_groups_with_metadata)
            row_count_changed = total_previous_rows != total_current_rows

            if row_count_changed:
                logger.info(
                    f"Row count changed: {total_previous_rows} -> {total_current_rows}, "
                    "performing full refresh (layout changed)"
                )
                # Render full image
                img = self.renderer.render(direction_groups_with_metadata)
            elif not changed_sections:
                # No changes at input level - skip update
                logger.info("No changes detected at input level, skipping display update.")
                # Still store the current data for next comparison
                self._previous_direction_groups = direction_groups_with_metadata.copy()
                return
            else:
                # Some sections changed - render only changed sections
                logger.info(
                    f"Input-level changes detected: {len(changed_sections)} section(s) changed. "
                    f"Changed sections: {changed_sections}"
                )
                # Render full image
                img = self.renderer.render(direction_groups_with_metadata)

            # Store current data for next comparison
            self._previous_direction_groups = direction_groups_with_metadata.copy()

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

            # Always perform full update (Inky Impression doesn't support partial updates)
            # Input-level change detection is used to skip updates when nothing changed
            if isinstance(self.display, MockInkyDisplay):
                # Mock display: log input-level changes
                logger.info(
                    f"Mock display: Input-level changes detected: {len(changed_sections)} section(s). "
                    f"Changed sections: {changed_sections}. Performing full update for visualization."
                )
            else:
                logger.debug(
                    f"Input-level changes detected: {len(changed_sections)} section(s) changed. "
                    "Performing full refresh."
                )

            self._perform_full_update(img)
            logger.debug("Inky display updated")
        except Exception as e:
            logger.error(f"Failed to display departures: {e}", exc_info=True)

    def _perform_full_update(self, img: Image.Image) -> None:
        """Perform a full display update."""
        if self.display is None:
            logger.error("Display not initialized, cannot perform update")
            return

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

    def _detect_input_changes(
        self,
        previous_groups: list[DirectionGroupWithMetadata] | None,
        current_groups: list[DirectionGroupWithMetadata],
    ) -> list[int]:
        """Detect which sections changed by comparing input data.

        Args:
            previous_groups: Previous direction groups (None if first render).
            current_groups: Current direction groups.

        Returns:
            List of section indices (0-based) that changed. Empty list if no changes.
        """
        if previous_groups is None:
            # First render: all sections are "changed" (need to render everything)
            return list(range(len(current_groups)))

        if len(previous_groups) != len(current_groups):
            # Number of groups changed: return all indices (full refresh needed)
            return list(range(len(current_groups)))

        changed_sections: list[int] = []
        for i, (prev_group, curr_group) in enumerate(
            zip(previous_groups, current_groups, strict=True)
        ):
            # Compare group metadata
            if (
                prev_group.station_id != curr_group.station_id
                or prev_group.stop_name != curr_group.stop_name
                or prev_group.direction_name != curr_group.direction_name
            ):
                changed_sections.append(i)
                continue

            # Compare departures
            if len(prev_group.departures) != len(curr_group.departures):
                changed_sections.append(i)
                continue

            # Compare each departure (compare key fields that affect display)
            for prev_dep, curr_dep in zip(
                prev_group.departures, curr_group.departures, strict=True
            ):
                # Compare fields that affect rendering
                if (
                    prev_dep.time != curr_dep.time
                    or prev_dep.planned_time != curr_dep.planned_time
                    or prev_dep.delay_seconds != curr_dep.delay_seconds
                    or prev_dep.platform != curr_dep.platform
                    or prev_dep.is_realtime != curr_dep.is_realtime
                    or prev_dep.line != curr_dep.line
                    or prev_dep.destination != curr_dep.destination
                    or prev_dep.transport_type != curr_dep.transport_type
                    or prev_dep.is_cancelled != curr_dep.is_cancelled
                ):
                    changed_sections.append(i)
                    break  # This section changed, no need to check more departures

        return changed_sections

    def _count_total_rows(self, groups: list[DirectionGroupWithMetadata] | None) -> int:
        """Count total number of rows (headers + departures).

        Args:
            groups: List of direction groups (None if empty).

        Returns:
            Total number of rows.
        """
        if not groups:
            return 0

        total = 0
        for group in groups:
            total += 1  # Header
            total += len(group.departures)  # Departure rows
        return total
