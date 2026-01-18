"""Mock Inky display for testing without hardware."""

import logging
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)


class MockInkyDisplay:
    """Mock Inky display that saves images to file instead of displaying."""

    # Color constants matching Inky display
    WHITE = 0
    BLACK = 1
    RED = 2
    YELLOW = 3

    def __init__(
        self,
        width: int = 480,
        height: int = 800,
        colour: str = "black",
        output_dir: Path | str | None = None,
    ) -> None:
        """Initialize mock display.

        Args:
            width: Display width in pixels.
            height: Display height in pixels.
            colour: Display color mode ('black', 'red', 'yellow').
            output_dir: Directory to save output images. Defaults to current directory.
        """
        self.width = width
        self.height = height
        self.colour = colour
        self._current_image: Image.Image | None = None
        self._output_dir = Path(output_dir) if output_dir else Path.cwd()
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._image_counter = 0

        # Create palette for color mode
        if colour == "black":
            self.palette = [255, 255, 255, 0, 0, 0]  # White, Black
        elif colour == "red":
            self.palette = [255, 255, 255, 0, 0, 0, 255, 0, 0]  # White, Black, Red
        elif colour == "yellow":
            self.palette = [255, 255, 255, 0, 0, 0, 255, 255, 0]  # White, Black, Yellow
        else:
            self.palette = [255, 255, 255, 0, 0, 0]  # Default to black/white

        logger.info(
            f"Initialized MockInkyDisplay: {width}x{height}, colour={colour}, "
            f"output_dir={self._output_dir}"
        )

    def set_image(self, image: Image.Image) -> None:
        """Set the image to display.

        Args:
            image: PIL Image to display.
        """
        self._current_image = image.copy()
        logger.debug(f"Image set: {image.size}, mode={image.mode}")

    def set_border(self, color: int) -> None:
        """Set border color (mock implementation - does nothing visually).

        Args:
            color: Border color (WHITE, BLACK, RED, or YELLOW).
        """
        logger.debug(f"Border color set to {color}")

    def show(self, filename: str | None = None) -> None:
        """Show the image by saving it to disk.

        Args:
            filename: Optional filename. If not provided, generates one automatically.
        """
        if self._current_image is None:
            logger.warning("No image set, cannot show")
            return

        if filename is None:
            self._image_counter += 1
            filename = f"inky_mock_output_{self._image_counter:04d}.png"

        output_path = self._output_dir / filename

        # Convert palette mode to RGB for saving
        if self._current_image.mode == "P":
            # Create RGB version for better viewing
            rgb_image = self._current_image.convert("RGB")
            rgb_image.save(output_path)
        else:
            self._current_image.save(output_path)

        logger.info(f"Mock display output saved to: {output_path}")
        print(f"📺 Mock Inky display: Image saved to {output_path}")

    def get_palette(self) -> list[int]:
        """Get the color palette for this display.

        Returns:
            List of RGB values for the palette.
        """
        return self.palette


def create_mock_display(
    width: int = 480,
    height: int = 800,
    colour: str = "black",
    output_dir: Path | str | None = None,
) -> MockInkyDisplay:
    """Create a mock Inky display for testing.

    Args:
        width: Display width in pixels.
        height: Display height in pixels.
        colour: Display color mode.
        output_dir: Directory to save output images.

    Returns:
        MockInkyDisplay instance.
    """
    return MockInkyDisplay(width=width, height=height, colour=colour, output_dir=output_dir)
