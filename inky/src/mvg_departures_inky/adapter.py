"""Inky display adapter."""

import asyncio
import logging
import os
from typing import TYPE_CHECKING

from mvg_departures.adapters.web.builders.departure_grouping_calculator import (
    DepartureGroupingCalculator,
)
from mvg_departures.domain.models.direction_group_with_metadata import (
    DirectionGroupWithMetadata,
)
from mvg_departures.domain.ports.display_adapter import DisplayAdapter

from .config import InkyDisplayConfig
from .mock_display import MockInkyDisplay, create_mock_display
from .renderer import InkyRenderer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inky.inky_uc8159 import Inky as InkyDisplay  # type: ignore[import-untyped]


class InkyDisplayAdapter(DisplayAdapter):
    """Display adapter for Pimoroni Inky e-ink displays."""

    def __init__(
        self,
        config: InkyDisplayConfig | None = None,
        grouping_calculator: DepartureGroupingCalculator | None = None,
    ) -> None:
        """Initialize Inky display adapter.

        Args:
            config: Optional display configuration. If None, uses defaults.
            grouping_calculator: Departure grouping calculator (same as web version).
        """
        self.config = config or InkyDisplayConfig()
        self.grouping_calculator = grouping_calculator
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
            self.display = create_mock_display(
                width=self.config.width,
                height=self.config.height,
                colour="black",
                output_dir=output_dir,
            )
        else:
            try:
                from inky.auto import auto  # type: ignore[import-untyped]

                # Auto-detect Inky display
                self.display = auto()
                logger.info(
                    f"Initialized Inky display: {self.display.width}x{self.display.height}, "
                    f"colour: {self.display.colour}"
                )

                # Update config with actual display dimensions
                self.config.width = self.display.width
                self.config.height = self.display.height
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
                    colour="black",
                    output_dir=output_dir,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize real Inky display: {e}. "
                    "Falling back to mock mode. Set INKY_MOCK_MODE=true to suppress this warning."
                )
                # Fall back to mock mode
                self.display = create_mock_display(
                    width=self.config.width,
                    height=self.config.height,
                    colour="black",
                    output_dir=output_dir,
                )

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
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        logger.info("Inky display adapter stopped")

    async def display_departures(
        self, direction_groups: list[DirectionGroupWithMetadata]
    ) -> None:
        """Display grouped departures on Inky display.

        Args:
            direction_groups: List of direction groups with metadata (same as web version).
        """
        if not self.renderer or not self.display:
            logger.warning("Display not initialized, skipping render")
            return

        try:
            # Render to PIL Image
            img = self.renderer.render(direction_groups)

            # Set image on display
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
