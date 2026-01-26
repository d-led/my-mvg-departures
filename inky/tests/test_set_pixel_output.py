"""Tests for writing solid colors via set_pixel.

This verifies that the adapter prefers `set_pixel()` (palette indices) over `set_image()`
when the display supports it, which avoids driver-side dithering/speckling.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image

from mvg_departures_inky.adapter import InkyDisplayAdapter
from mvg_departures_inky.config import InkyDisplayConfig


@dataclass
class FakeSetPixelDisplay:
    """Minimal display stub with the E673-like palette and API."""

    width: int = 2
    height: int = 2

    # E673 ("Spectra 6"/multi) constants
    BLACK: int = 0
    WHITE: int = 1
    YELLOW: int = 2
    RED: int = 3
    BLUE: int = 4
    GREEN: int = 5

    # Driver palette (index order must match constants above)
    DESATURATED_PALETTE: list[list[int]] = field(
        default_factory=lambda: [
            [0, 0, 0],  # black
            [255, 255, 255],  # white
            [255, 255, 0],  # yellow
            [255, 0, 0],  # red
            [0, 0, 255],  # blue
            [0, 255, 0],  # green
        ]
    )

    set_pixel_calls: list[tuple[int, int, int]] = field(default_factory=list)
    set_image_calls: int = 0
    show_calls: int = 0

    def set_pixel(self, x: int, y: int, v: int) -> None:  # noqa: D401 - simple stub
        self.set_pixel_calls.append((x, y, v))

    def set_image(self, _img: Image.Image, saturation: float = 0.5) -> None:
        self.set_image_calls += 1

    def show(self, *args: object, **kwargs: object) -> None:  # noqa: ANN401 - stub
        self.show_calls += 1


def test_when_display_supports_set_pixel_then_adapter_writes_palette_indices() -> None:
    display = FakeSetPixelDisplay()
    adapter = InkyDisplayAdapter(config=InkyDisplayConfig())
    adapter.display = display  # inject fake

    img = Image.new("RGB", (2, 2), (255, 255, 255))
    # Top-left blue, top-right red, bottom-left black, bottom-right white
    img.putpixel((0, 0), (0, 0, 255))
    img.putpixel((1, 0), (255, 0, 0))
    img.putpixel((0, 1), (0, 0, 0))
    img.putpixel((1, 1), (255, 255, 255))

    adapter._perform_full_update(img)

    # set_image should not be used when set_pixel is available
    assert display.set_image_calls == 0
    assert display.show_calls == 1

    # We should have exactly one call per pixel
    assert len(display.set_pixel_calls) == 4

    # Check that values are encoded as idx * 0x11
    expected = {
        (0, 0): display.BLUE * 0x11,
        (1, 0): display.RED * 0x11,
        (0, 1): display.BLACK * 0x11,
        (1, 1): display.WHITE * 0x11,
    }
    for x, y, v in display.set_pixel_calls:
        assert expected[(x, y)] == v


def test_when_image_is_palette_mode_then_adapter_writes_indices_directly() -> None:
    display = FakeSetPixelDisplay()
    adapter = InkyDisplayAdapter(config=InkyDisplayConfig())
    adapter.display = display  # inject fake

    # Palette image indices should be written directly as idx * 0x11.
    img = Image.new("P", (2, 2), display.WHITE)
    img.putpixel((0, 0), display.BLUE)
    img.putpixel((1, 0), display.RED)
    img.putpixel((0, 1), display.BLACK)
    img.putpixel((1, 1), display.WHITE)

    adapter._perform_full_update(img)

    assert display.set_image_calls == 0
    assert display.show_calls == 1
    assert len(display.set_pixel_calls) == 4

    expected = {
        (0, 0): display.BLUE * 0x11,
        (1, 0): display.RED * 0x11,
        (0, 1): display.BLACK * 0x11,
        (1, 1): display.WHITE * 0x11,
    }
    for x, y, v in display.set_pixel_calls:
        assert expected[(x, y)] == v

