"""Mock Inky display for testing without hardware."""

import logging
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)


class MockInkyDisplay:
    """Mock Inky display that saves images to file instead of displaying."""

    # Color constants matching Inky Impression Spectra (7 colors)
    # Order from Pimoroni library: black, white, green, blue, red, yellow, orange
    BLACK = 0
    WHITE = 1
    GREEN = 2
    BLUE = 3
    RED = 4
    YELLOW = 5
    ORANGE = 6

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

        # Create palette for Inky Impression Spectra (7 colors)
        # Order: black, white, green, blue, red, yellow, orange
        # Using web version colors for blue and green (less saturated)
        # Blue: #087BC4 (web banner color) -> RGB(8, 123, 196)
        # Green: #047857 (web realtime color, darker) -> RGB(4, 120, 87)
        self.palette = [
            0, 0, 0,        # 0: Black
            255, 255, 255,  # 1: White
            4, 120, 87,     # 2: Green (#047857 - darker green for realtime)
            8, 123, 196,    # 3: Blue (#087BC4 - less saturated blue for headers)
            255, 0, 0,      # 4: Red
            255, 255, 0,    # 5: Yellow
            255, 165, 0,    # 6: Orange
        ]
        # Fill remaining palette slots with white
        while len(self.palette) < 768:  # 256 colors * 3 RGB values
            self.palette.extend([255, 255, 255])

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

        # Convert palette mode to RGB for saving, preserving colors
        if self._current_image.mode == "P":
            # Convert to RGB, mapping palette indices to actual colors
            rgb_image = Image.new("RGB", self._current_image.size)
            pixels = self._current_image.load()
            rgb_pixels = rgb_image.load()
            palette = self._current_image.getpalette()
            
            # Map palette indices to RGB values
            for y in range(self._current_image.height):
                for x in range(self._current_image.width):
                    idx = pixels[x, y]
                    if palette and idx * 3 + 2 < len(palette):
                        r = palette[idx * 3]
                        g = palette[idx * 3 + 1]
                        b = palette[idx * 3 + 2]
                        rgb_pixels[x, y] = (r, g, b)
                    else:
                        rgb_pixels[x, y] = (255, 255, 255)  # Default to white
            
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
