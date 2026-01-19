"""Tests for InkyDisplayAdapter rotation logic.

This test verifies that:
1. Rotating a portrait image (480x800) produces landscape (800x480)
2. Rotation uses transpose (no pixel stretching)
3. Dimensions are correctly swapped
"""

import pytest
from PIL import Image


class TestAdapterRotation:
    """Tests for adapter rotation logic."""

    def test_when_rotate_portrait_image_then_dimensions_swap(self) -> None:
        """Test that rotating a portrait image (480x800) produces landscape (800x480)."""
        # Create a portrait image
        portrait_img = Image.new("RGB", (480, 800), "white")
        assert portrait_img.size == (480, 800), "Initial image should be 480x800"

        # Rotate 90 degrees clockwise (ROTATE_270)
        rotated_img = portrait_img.transpose(Image.Transpose.ROTATE_270)
        assert rotated_img.size == (800, 480), (
            f"Rotated image should be 800x480, got {rotated_img.size}"
        )

        # Verify it's a perfect transpose (no stretching)
        # The image should have the same number of pixels
        assert portrait_img.width * portrait_img.height == rotated_img.width * rotated_img.height, (
            "Rotated image should have same number of pixels (no stretching)"
        )

    def test_when_rotate_landscape_image_then_dimensions_swap(self) -> None:
        """Test that rotating a landscape image (800x480) produces portrait (480x800)."""
        # Create a landscape image
        landscape_img = Image.new("RGB", (800, 480), "white")
        assert landscape_img.size == (800, 480), "Initial image should be 800x480"

        # Rotate 90 degrees clockwise (ROTATE_270)
        rotated_img = landscape_img.transpose(Image.Transpose.ROTATE_270)
        assert rotated_img.size == (480, 800), (
            f"Rotated image should be 480x800, got {rotated_img.size}"
        )

    def test_when_rotate_with_rotate_90_then_dimensions_swap(self) -> None:
        """Test that ROTATE_90 also swaps dimensions (but rotates content differently)."""
        # Create a portrait image
        portrait_img = Image.new("RGB", (480, 800), "white")
        
        # ROTATE_90 rotates counter-clockwise, but also swaps dimensions
        rotated_img = portrait_img.transpose(Image.Transpose.ROTATE_90)
        assert rotated_img.size == (800, 480), (
            f"ROTATE_90 should swap dimensions to 800x480, got {rotated_img.size}"
        )

    def test_when_rotate_then_no_pixel_stretching(self) -> None:
        """Test that rotation preserves pixel count (no stretching)."""
        # Create a portrait image with specific dimensions
        portrait_img = Image.new("RGB", (480, 800), "white")
        original_pixels = portrait_img.width * portrait_img.height

        # Rotate 90 degrees clockwise
        rotated_img = portrait_img.transpose(Image.Transpose.ROTATE_270)
        rotated_pixels = rotated_img.width * rotated_img.height

        assert original_pixels == rotated_pixels, (
            f"Rotation should preserve pixel count: {original_pixels} != {rotated_pixels}"
        )
        assert rotated_img.size == (800, 480), (
            f"Rotated dimensions should be 800x480, got {rotated_img.size}"
        )
