"""Tests for PNG watermark/preview generation."""

import pytest
from PIL import Image
from io import BytesIO
import os
from coloring_book.png.watermark import WatermarkGenerator, PreviewGenerator, ListingImageGenerator
from coloring_book.svg.animals import CatDrawer, DogDrawer


class TestWatermarkGenerator:
    """Test watermark generator."""

    def test_init_default(self):
        """Test initialization with defaults."""
        gen = WatermarkGenerator()
        assert gen.text == "© Coloring Book"
        assert gen.opacity == 0.3
        assert gen.position == "center"

    def test_init_custom(self):
        """Test custom initialization."""
        gen = WatermarkGenerator(text="My Watermark", opacity=0.5, position="bottom-right")
        assert gen.text == "My Watermark"
        assert gen.opacity == 0.5
        assert gen.position == "bottom-right"

    def test_opacity_validation(self):
        """Test opacity validation."""
        with pytest.raises(ValueError):
            WatermarkGenerator(opacity=-0.1)
        with pytest.raises(ValueError):
            WatermarkGenerator(opacity=1.5)

    def test_position_validation(self):
        """Test position validation."""
        with pytest.raises(ValueError):
            WatermarkGenerator(position="invalid")

    def test_add_watermark_to_png(self):
        """Test adding watermark to PNG."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        # Create simple PNG
        img = Image.new("RGB", (400, 300), "white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        
        gen = WatermarkGenerator(text="Preview", opacity=0.4)
        watermarked = gen.add_watermark(png_bytes)
        
        assert watermarked is not None
        assert len(watermarked) > 0
        
        # Verify it's still a valid PNG
        watermarked_img = Image.open(BytesIO(watermarked))
        assert watermarked_img.format == "PNG"

    def test_watermark_positions(self):
        """Test watermark at different positions."""
        img = Image.new("RGB", (400, 300), "white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        
        positions = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]
        
        for pos in positions:
            gen = WatermarkGenerator(position=pos)
            watermarked = gen.add_watermark(png_bytes)
            assert watermarked is not None
            assert len(watermarked) > 0

    def test_watermark_opacity_levels(self):
        """Test watermark at different opacity levels."""
        img = Image.new("RGB", (400, 300), "white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        
        opacities = [0.1, 0.3, 0.5, 0.7, 0.9]
        
        for opacity in opacities:
            gen = WatermarkGenerator(opacity=opacity)
            watermarked = gen.add_watermark(png_bytes)
            assert watermarked is not None


class TestPreviewGenerator:
    """Test preview/thumbnail generation."""

    def test_init_default(self):
        """Test initialization with defaults."""
        gen = PreviewGenerator()
        assert gen.size == (200, 200)
        assert gen.format == "PNG"

    def test_init_custom(self):
        """Test custom initialization."""
        gen = PreviewGenerator(size=(300, 300))
        assert gen.size == (300, 300)

    def test_create_thumbnail(self):
        """Test thumbnail creation."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        # Create simple PNG
        img = Image.new("RGB", (800, 600), "white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        
        gen = PreviewGenerator(size=(200, 150))
        thumbnail = gen.create_thumbnail(png_bytes)
        
        assert thumbnail is not None
        assert len(thumbnail) > 0
        
        # Verify dimensions
        thumb_img = Image.open(BytesIO(thumbnail))
        assert thumb_img.size == (200, 150)

    def test_create_thumbnail_maintains_aspect(self):
        """Test that thumbnail maintains aspect ratio."""
        img = Image.new("RGB", (800, 400), "white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        
        gen = PreviewGenerator(size=(200, 200))
        thumbnail = gen.create_thumbnail(png_bytes)
        
        thumb_img = Image.open(BytesIO(thumbnail))
        # Should fit within bounds
        assert thumb_img.size[0] <= 200
        assert thumb_img.size[1] <= 200

    def test_batch_thumbnail(self):
        """Test batch thumbnail generation."""
        cat = CatDrawer()
        dog = DogDrawer()
        
        img1 = Image.new("RGB", (800, 600), "white")
        buffer1 = BytesIO()
        img1.save(buffer1, format="PNG")
        
        img2 = Image.new("RGB", (800, 600), "white")
        buffer2 = BytesIO()
        img2.save(buffer2, format="PNG")
        
        png_dict = {
            "cat": buffer1.getvalue(),
            "dog": buffer2.getvalue(),
        }
        
        gen = PreviewGenerator(size=(150, 150))
        thumbnails = gen.batch_thumbnail(png_dict)
        
        assert len(thumbnails) == 2
        assert "cat" in thumbnails
        assert "dog" in thumbnails


class TestListingImageGenerator:
    """Test listing image generation (combines preview + metadata)."""

    def test_init_default(self):
        """Test initialization."""
        gen = ListingImageGenerator()
        assert gen.size == (1000, 1000)

    def test_generate_listing_image(self):
        """Test generating Etsy listing image."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        # Create simple PNG
        img = Image.new("RGB", (800, 600), "white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        
        gen = ListingImageGenerator()
        listing_img = gen.generate(png_bytes, title="My Cat Drawing")
        
        assert listing_img is not None
        assert len(listing_img) > 0
        
        # Verify it's a PNG
        result_img = Image.open(BytesIO(listing_img))
        assert result_img.format == "PNG"

    def test_listing_image_with_metadata(self):
        """Test listing image with metadata text."""
        img = Image.new("RGB", (800, 600), "white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        
        metadata = {
            "title": "Coloring Book Page",
            "category": "Animals",
            "difficulty": "Easy",
        }
        
        gen = ListingImageGenerator()
        listing_img = gen.generate_with_metadata(png_bytes, metadata)
        
        assert listing_img is not None
        result_img = Image.open(BytesIO(listing_img))
        assert result_img.format == "PNG"


class TestWatermarkIntegration:
    """Integration tests for watermark + preview."""

    def test_watermark_then_preview(self):
        """Test applying watermark then creating preview."""
        img = Image.new("RGB", (800, 600), "white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        
        # Add watermark
        wm_gen = WatermarkGenerator(text="Preview", opacity=0.3)
        watermarked = wm_gen.add_watermark(png_bytes)
        
        # Create thumbnail
        preview_gen = PreviewGenerator(size=(200, 150))
        thumbnail = preview_gen.create_thumbnail(watermarked)
        
        assert thumbnail is not None
        thumb_img = Image.open(BytesIO(thumbnail))
        assert thumb_img.format == "PNG"
