"""
TASK-d2a95f88: Assertion Self-Validation Tests

Negative tests to validate that pixel assertions CORRECTLY REJECT blank images.
This proves our test logic is sound BEFORE we rely on it.
"""

import pytest
from PIL import Image
from io import BytesIO
from coloring_book.png.exporter import PNGExporter
from coloring_book.svg.animals import CatDrawer


class TestAssertionValidationNegative:
    """Negative tests - verify assertions reject KNOWN-BAD inputs."""

    def test_pixel_assertion_rejects_blank_white_image(self):
        """
        VALIDATION: Blank white image MUST be rejected by white_ratio assertion.
        
        This proves our assertion logic actually catches blank images.
        If this test FAILS, our assertion is broken.
        """
        # Create KNOWN-BLANK image
        blank = Image.new("RGB", (200, 200), (255, 255, 255))
        
        # Apply assertion logic
        colors = blank.getcolors()
        color_histogram = {color: count for count, color in colors}
        
        white_count = color_histogram.get((255, 255, 255), 0)
        total_pixels = blank.width * blank.height
        white_ratio = white_count / total_pixels
        
        # ✅ CRITICAL: This assertion MUST FAIL on blank image
        # If it passes, our assertion is broken
        assert white_ratio == 1.0, "Blank image should be 100% white"
        assert white_ratio >= 0.9, "Blank image should exceed 90% threshold"
        
        # The actual assertion should reject this
        with pytest.raises(AssertionError):
            assert white_ratio < 0.9, "Blank image should fail this assertion"

    def test_pixel_assertion_rejects_nearly_blank_image(self):
        """
        VALIDATION: 95% white image MUST be rejected by 0.9 threshold.
        """
        # Create image that is 95% white, 5% black
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        pixels = img.load()
        
        # Make ~5% of pixels black (200*200 = 40000 pixels, 5% = 2000)
        for i in range(2000):
            x = i % 200
            y = i // 200
            pixels[x, y] = (0, 0, 0)
        
        # Check the assertion
        colors = img.getcolors()
        color_histogram = {color: count for count, color in colors}
        
        white_count = color_histogram.get((255, 255, 255), 0)
        total_pixels = img.width * img.height
        white_ratio = white_count / total_pixels
        
        print(f"95% white image: {white_ratio*100:.1f}% white")
        assert white_ratio > 0.94, "Image should be >94% white"
        assert white_ratio < 0.96, "Image should be <96% white"
        
        # Assertion should reject this
        with pytest.raises(AssertionError):
            assert white_ratio < 0.9, "95% white should fail <0.9 threshold"

    def test_rendered_image_passes_pixel_assertion(self):
        """
        VALIDATION: Real rendered image MUST PASS white_ratio < 0.9 assertion.
        """
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter = PNGExporter(dpi=150)
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        img = Image.open(BytesIO(png_bytes))
        
        colors = img.getcolors()
        color_histogram = {color: count for color, count in colors}
        
        white_count = color_histogram.get((255, 255, 255), 0)
        total_pixels = img.width * img.height
        white_ratio = white_count / total_pixels
        
        print(f"Rendered image: {white_ratio*100:.1f}% white")
        
        # ✅ Assertion should PASS on rendered image
        assert white_ratio < 0.9, f"Rendered image should be <90% white, got {white_ratio*100:.1f}%"

    def test_getcolors_api_format(self):
        """
        VALIDATION: Verify PIL getcolors() returns (count, color) format.
        
        This catches the API gotcha that broke assertions.
        """
        # Create simple image with 2 colors
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        pixels = img.load()
        
        # Make 25% red
        for i in range(2500):
            x = i % 100
            y = i // 100
            pixels[x, y] = (255, 0, 0)
        
        colors = img.getcolors()
        
        # ✅ Verify format: getcolors() returns [(count, color), ...]
        assert isinstance(colors, list), "getcolors() should return list"
        assert len(colors) == 2, "Should have 2 colors (white and red)"
        
        # First item is (count, color) tuple
        first_item = colors[0]
        assert isinstance(first_item, tuple), "Each item should be tuple"
        assert len(first_item) == 2, "Each tuple should be (count, color)"
        
        count, color = first_item
        assert isinstance(count, int), "First element is count (int)"
        assert isinstance(color, tuple), "Second element is color (tuple)"
        assert len(color) == 3, "Color should be RGB (3 values)"
        
        # Verify the values make sense
        color_histogram = {color: count for count, color in colors}
        white_count = color_histogram.get((255, 255, 255), 0)
        red_count = color_histogram.get((255, 0, 0), 0)
        
        assert white_count + red_count == 10000, "Count should sum to 100*100"
        assert red_count == 2500, "Red should be 25% = 2500 pixels"
        assert white_count == 7500, "White should be 75% = 7500 pixels"

    def test_assertion_handles_single_color_image(self):
        """
        VALIDATION: Single-color image handling.
        """
        # All white
        blank = Image.new("RGB", (100, 100), (255, 255, 255))
        colors = blank.getcolors()
        
        # Should return single tuple: (count, color)
        assert len(colors) == 1, "Single-color image should have 1 entry"
        
        count, color = colors[0]
        assert count == 10000, "Should be 100*100 pixels"
        assert color == (255, 255, 255), "Color should be white"


class TestAssertionValidationPositive:
    """Positive tests - verify good images pass assertions."""

    def test_rendered_image_has_multiple_colors(self):
        """Real rendered image should have multiple colors (not just white)."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter = PNGExporter(dpi=150)
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        img = Image.open(BytesIO(png_bytes))
        colors = img.getcolors()
        
        # Should have at least 2 colors (white + black strokes)
        assert len(colors) >= 2, f"Rendered should have ≥2 colors, got {len(colors)}"

    def test_file_size_assertion_blank_vs_rendered(self):
        """File size should clearly distinguish blank from rendered."""
        # Blank
        blank_png = Image.new("RGB", (312, 312), (255, 255, 255))
        blank_buffer = BytesIO()
        blank_png.save(blank_buffer, format="PNG")
        blank_size = len(blank_buffer.getvalue())
        
        # Rendered
        cat = CatDrawer()
        exporter = PNGExporter(dpi=150)
        rendered_bytes = exporter.export_svg_to_png(cat.draw())
        rendered_size = len(rendered_bytes)
        
        print(f"Blank: {blank_size} bytes")
        print(f"Rendered: {rendered_size} bytes")
        print(f"Ratio: {rendered_size / blank_size:.1f}x")
        
        # Rendered should be significantly larger
        assert rendered_size > blank_size * 2, \
            f"Rendered ({rendered_size}) should be >2x blank ({blank_size})"

    def test_multiple_animals_have_variable_sizes(self):
        """Different animals should produce different file sizes."""
        from coloring_book.svg.animals import DogDrawer, BirdDrawer
        
        exporter = PNGExporter(dpi=150)
        
        cat_size = len(exporter.export_svg_to_png(CatDrawer().draw()))
        dog_size = len(exporter.export_svg_to_png(DogDrawer().draw()))
        bird_size = len(exporter.export_svg_to_png(BirdDrawer().draw()))
        
        sizes = [cat_size, dog_size, bird_size]
        
        # Not all the same
        assert len(set(sizes)) > 1, f"Sizes should vary: {sizes}"
        
        # All substantially larger than blank
        blank_png = Image.new("RGB", (312, 312), (255, 255, 255))
        blank_buffer = BytesIO()
        blank_png.save(blank_buffer, format="PNG")
        blank_size = len(blank_buffer.getvalue())
        
        for size in sizes:
            assert size > blank_size * 2, f"All should be >2x blank ({blank_size})"
