"""Inky display adapter."""

import asyncio
import logging
from typing import TYPE_CHECKING

from mvg_departures.domain.models.grouped_departures import GroupedDepartures
from mvg_departures.domain.ports.display_adapter import DisplayAdapter

from .config import InkyDisplayConfig
from .renderer import InkyRenderer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inky.inky_uc8159 import Inky as InkyDisplay  # type: ignore[import-untyped]


class InkyDisplayAdapter(DisplayAdapter):
    """Display adapter for Pimoroni Inky e-ink displays."""

    def __init__(self, config: InkyDisplayConfig | None = None) -> None:
        """Initialize Inky display adapter.

        Args:
            config: Optional display configuration. If None, uses defaults.
        """
        self.config = config or InkyDisplayConfig()
        self.display: InkyDisplay | None = None
        self.renderer: InkyRenderer | None = None
        self._update_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the display adapter."""
        try:
            from inky.auto import auto

            # Auto-detect Inky display
            self.display = auto()
            logger.info(
                f"Initialized Inky display: {self.display.width}x{self.display.height}, "
                f"colour: {self.display.colour}"
            )

            # Update config with actual display dimensions
            self.config.width = self.display.width
            self.config.height = self.display.height

            # Initialize renderer
            self.renderer = InkyRenderer(self.config, self.display)

            # Set border color
            try:
                self.display.set_border(self.display.WHITE)
            except Exception as e:
                logger.warning(f"Could not set border color: {e}")

            self._running = True
            logger.info("Inky display adapter started")
        except Exception as e:
            logger.error(f"Failed to initialize Inky display: {e}", exc_info=True)
            raise

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

    async def display_departures(self, direction_groups: list[GroupedDepartures]) -> None:
        """Display grouped departures on Inky display.

        Args:
            direction_groups: List of grouped departures to display.
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
            logger.debug("Updating Inky display...")
            self.display.show()
            logger.debug("Inky display updated")
        except Exception as e:
            logger.error(f"Failed to display departures: {e}", exc_info=True)
