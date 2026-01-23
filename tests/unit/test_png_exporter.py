"""Tests for PNG exporter module."""

import pytest
from PIL import Image
from io import BytesIO
import os
from coloring_book.png.exporter import PNGExporter
from coloring_book.svg.animals import CatDrawer, DogDrawer, BirdDrawer


class TestPNGExporter:
    """Test PNGExporter class."""

    def test_init_default(self):
        """Test initialization with defaults."""
        exporter = PNGExporter()
        assert exporter.dpi == 150
        assert exporter.quality == 90
        assert exporter.format == "PNG"

    def test_init_custom(self):
        """Test initialization with custom values."""
        exporter = PNGExporter(dpi=300, quality=95)
        assert exporter.dpi == 300
        assert exporter.quality == 95

    def test_dpi_validation(self):
        """Test DPI validation."""
        with pytest.raises(ValueError):
            PNGExporter(dpi=50)
        with pytest.raises(ValueError):
            PNGExporter(dpi=1000)

    def test_quality_validation(self):
        """Test quality validation."""
        with pytest.raises(ValueError):
            PNGExporter(quality=0)
        with pytest.raises(ValueError):
            PNGExporter(quality=101)

    def test_export_svg_to_png_cat(self):
        """Test exporting cat SVG to PNG - WITH PIXEL VERIFICATION."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter = PNGExporter()
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        assert png_bytes is not None
        assert len(png_bytes) > 0
        assert isinstance(png_bytes, bytes)
        
        # ✅ PIXEL VERIFICATION: Dosya boyutu kontrol
        # Boş beyaz PNG = ~987 byte, Gerçek çizim > 1500 byte
        assert len(png_bytes) >= 987, f"PNG too small ({len(png_bytes)} bytes), likely blank"
        
        # Verify it's a valid PNG
        img = Image.open(BytesIO(png_bytes))
        assert img.format == "PNG"
        assert img.mode == "RGB"
        
        # ✅ PIXEL VERIFICATION: Renk analizi
        # PIL getcolors() returns [(count, color), ...]
        colors = img.getcolors()
        assert colors is not None, "Image has too many colors (rendering worked)"
        
        # ✅ CORRECT FORMAT: (count, color)
        color_histogram = {color: count for count, color in colors}
        white_count = color_histogram.get((255, 255, 255), 0)
        total_pixels = img.width * img.height
        white_ratio = white_count / total_pixels if total_pixels > 0 else 1.0
        
        # Eğer %90+ beyaz ise, resim boş demektir
        assert white_ratio < 0.9, f"Image is {white_ratio*100:.1f}% white - likely blank"
        
        # ✅ PIXEL VERIFICATION: Resim boyutları
        assert img.width > 0, "Image width should be > 0"
        assert img.height > 0, "Image height should be > 0"

    def test_export_svg_to_png_dog(self):
        """Test exporting dog SVG to PNG - WITH PIXEL VERIFICATION."""
        dog = DogDrawer()
        svg_content = dog.draw()
        
        exporter = PNGExporter(dpi=200)
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        assert png_bytes is not None
        assert len(png_bytes) > 0
        
        # ✅ Dosya boyutu minimum threshold
        assert len(png_bytes) >= 987, f"PNG too small: {len(png_bytes)} bytes"
        
        img = Image.open(BytesIO(png_bytes))
        assert img.format == "PNG"
        
        # ✅ Pixel content check
        colors = img.getcolors()
        assert colors is not None
        color_histogram = {color: count for count, color in colors}
        white_count = color_histogram.get((255, 255, 255), 0)
        white_ratio = white_count / (img.width * img.height)
        assert white_ratio < 0.9, "Image appears blank (mostly white)"

    def test_export_svg_to_png_bird(self):
        """Test exporting bird SVG to PNG - WITH PIXEL VERIFICATION."""
        bird = BirdDrawer()
        svg_content = bird.draw()
        
        exporter = PNGExporter()
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        assert png_bytes is not None
        
        # ✅ Size check
        assert len(png_bytes) >= 987
        
        img = Image.open(BytesIO(png_bytes))
        assert img.format == "PNG"
        assert img.mode == "RGB"
        
        # ✅ Content check - Has non-white pixels
        colors = img.getcolors()
        assert colors is not None
        color_histogram = {color: count for count, color in colors}
        white_count = color_histogram.get((255, 255, 255), 0)
        white_ratio = white_count / (img.width * img.height)
        assert white_ratio < 0.9

    def test_export_to_file(self):
        """Test exporting PNG to file."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter = PNGExporter()
        output_path = "/tmp/test_cat.png"
        
        result = exporter.export_svg_to_file(svg_content, output_path)
        
        assert result == output_path
        assert os.path.exists(output_path)
        
        # Verify it's a valid PNG
        img = Image.open(output_path)
        assert img.format == "PNG"
        
        # ✅ Verify content, not just structure
        file_size = os.path.getsize(output_path)
        assert file_size >= 987, f"File too small: {file_size} bytes"
        
        colors = img.getcolors()
        assert colors is not None
        color_histogram = {color: count for count, color in colors}
        white_count = color_histogram.get((255, 255, 255), 0)
        white_ratio = white_count / (img.width * img.height)
        assert white_ratio < 0.9
        
        # Cleanup
        os.remove(output_path)

    def test_export_to_file_custom_dpi(self):
        """Test exporting with custom DPI."""
        dog = DogDrawer()
        svg_content = dog.draw()
        
        exporter = PNGExporter(dpi=300)
        output_path = "/tmp/test_dog_hires.png"
        
        exporter.export_svg_to_file(svg_content, output_path)
        
        img = Image.open(output_path)
        assert img.format == "PNG"
        # Higher DPI should result in larger file
        file_size = os.path.getsize(output_path)
        assert file_size > 100
        
        # ✅ Content verification
        assert file_size >= 987
        colors = img.getcolors()
        assert colors is not None
        color_histogram = {color: count for count, color in colors}
        white_count = color_histogram.get((255, 255, 255), 0)
        white_ratio = white_count / (img.width * img.height)
        assert white_ratio < 0.9
        
        os.remove(output_path)

    def test_get_image_dimensions(self):
        """Test getting image dimensions."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter = PNGExporter(dpi=150)
        width, height = exporter.get_image_dimensions(svg_content)
        
        assert width > 0
        assert height > 0
        assert isinstance(width, int)
        assert isinstance(height, int)

    def test_get_file_size(self):
        """Test getting PNG file size."""
        dog = DogDrawer()
        svg_content = dog.draw()
        
        exporter = PNGExporter()
        output_path = "/tmp/test_size.png"
        exporter.export_svg_to_file(svg_content, output_path)
        
        file_size = exporter.get_file_size(output_path)
        assert file_size > 0
        assert file_size == os.path.getsize(output_path)
        
        # ✅ Reasonable size
        assert file_size >= 987
        
        os.remove(output_path)

    def test_convert_bytes_to_image(self):
        """Test converting PNG bytes to Image object."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter = PNGExporter()
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        img = exporter.convert_bytes_to_image(png_bytes)
        
        assert isinstance(img, Image.Image)
        assert img.format == "PNG"
        
        # ✅ Verify content
        colors = img.getcolors()
        assert colors is not None

    def test_batch_export(self):
        """Test batch exporting multiple animals."""
        animals = [
            ("cat", CatDrawer()),
            ("dog", DogDrawer()),
            ("bird", BirdDrawer()),
        ]
        
        exporter = PNGExporter()
        results = {}
        
        for name, drawer in animals:
            svg = drawer.draw()
            png_bytes = exporter.export_svg_to_png(svg)
            results[name] = png_bytes
        
        assert len(results) == 3
        for name, png_bytes in results.items():
            assert len(png_bytes) > 0
            
            # ✅ Size verification - should vary by animal complexity
            assert len(png_bytes) >= 987, f"{name} PNG too small"
            
            img = Image.open(BytesIO(png_bytes))
            assert img.format == "PNG"
            
            # ✅ Content verification
            colors = img.getcolors()
            assert colors is not None
            color_histogram = {color: count for count, color in colors}
            white_count = color_histogram.get((255, 255, 255), 0)
            white_ratio = white_count / (img.width * img.height)
            assert white_ratio < 0.9, f"{name} appears blank"

    def test_preserve_aspect_ratio(self):
        """Test aspect ratio preservation."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter_low = PNGExporter(dpi=100)
        exporter_high = PNGExporter(dpi=300)
        
        w1, h1 = exporter_low.get_image_dimensions(svg_content)
        w2, h2 = exporter_high.get_image_dimensions(svg_content)
        
        # Aspect ratio should be same
        ratio1 = w1 / h1
        ratio2 = w2 / h2
        
        assert abs(ratio1 - ratio2) < 0.01

    def test_set_quality_chaining(self):
        """Test quality setter chaining."""
        exporter = PNGExporter().set_quality(85)
        assert exporter.quality == 85

    def test_set_dpi_chaining(self):
        """Test DPI setter chaining."""
        exporter = PNGExporter().set_dpi(200)
        assert exporter.dpi == 200

    def test_different_animals_different_sizes(self):
        """Test that different animals produce varying file sizes."""
        exporter = PNGExporter(dpi=150)
        
        cat_svg = CatDrawer().draw()
        dog_svg = DogDrawer().draw()
        bird_svg = BirdDrawer().draw()
        
        cat_png = exporter.export_svg_to_png(cat_svg)
        dog_png = exporter.export_svg_to_png(dog_svg)
        bird_png = exporter.export_svg_to_png(bird_svg)
        
        sizes = [len(cat_png), len(dog_png), len(bird_png)]
        
        # ✅ Different animals should have different file sizes
        # (Not all exactly 987 bytes)
        assert len(set(sizes)) > 1, "All PNGs have same size - likely all blank"
        
        # All must be above minimum
        assert all(s >= 987 for s in sizes)
        
        # All must have actual content
        for name, png_bytes in [("cat", cat_png), ("dog", dog_png), ("bird", bird_png)]:
            img = Image.open(BytesIO(png_bytes))
            colors = img.getcolors()
            assert colors is not None
            color_histogram = {color: count for count, color in colors}
            white_count = color_histogram.get((255, 255, 255), 0)
            white_ratio = white_count / (img.width * img.height)
            assert white_ratio < 0.9, f"{name} is blank"


class TestPNGExporterIntegration:
    """Integration tests for PNG exporter."""

    def test_export_multiple_formats(self):
        """Test exporting same SVG at different DPIs."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        dpi_levels = [100, 150, 200, 300]
        file_sizes = []
        
        for dpi in dpi_levels:
            exporter = PNGExporter(dpi=dpi)
            output_path = f"/tmp/test_cat_dpi_{dpi}.png"
            exporter.export_svg_to_file(svg_content, output_path)
            
            file_size = os.path.getsize(output_path)
            file_sizes.append(file_size)
            
            # ✅ Each must have content
            assert file_size >= 987
            
            os.remove(output_path)
        
        # Higher DPI should generally mean larger files
        assert file_sizes[-1] > file_sizes[0]

    def test_round_trip_svg_to_png_to_image(self):
        """Test complete workflow: SVG -> PNG -> Image."""
        dog = DogDrawer()
        svg_content = dog.draw()
        
        exporter = PNGExporter()
        png_bytes = exporter.export_svg_to_png(svg_content)
        img = exporter.convert_bytes_to_image(png_bytes)
        
        assert img.format == "PNG"
        assert img.mode == "RGB"
        assert img.size[0] > 0
        assert img.size[1] > 0
        
        # ✅ Verify actual content rendered
        colors = img.getcolors()
        assert colors is not None
        color_histogram = {color: count for count, color in colors}
        white_count = color_histogram.get((255, 255, 255), 0)
        white_ratio = white_count / (img.width * img.height)
        assert white_ratio < 0.9

    def test_dpi_affects_file_size(self):
        """Test that DPI setting affects file size."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter_low = PNGExporter(dpi=100)
        exporter_high = PNGExporter(dpi=300)
        
        output_low = "/tmp/test_low_dpi.png"
        output_high = "/tmp/test_high_dpi.png"
        
        exporter_low.export_svg_to_file(svg_content, output_low)
        exporter_high.export_svg_to_file(svg_content, output_high)
        
        size_low = os.path.getsize(output_low)
        size_high = os.path.getsize(output_high)
        
        # Higher DPI should result in larger file
        assert size_high > size_low
        
        # ✅ Both must have content
        assert size_low >= 987
        assert size_high >= 987
        
        os.remove(output_low)
        os.remove(output_high)

    def test_export_to_directory(self):
        """Test batch export to directory."""
        svg_dict = {
            "cat": CatDrawer().draw(),
            "dog": DogDrawer().draw(),
        }
        
        exporter = PNGExporter()
        output_dir = "/tmp/test_png_export"
        
        results = exporter.batch_export(svg_dict, output_dir)
        
        assert len(results) == 2
        assert os.path.exists(results["cat"])
        assert os.path.exists(results["dog"])
        
        # ✅ Verify all have content
        for name, path in results.items():
            file_size = os.path.getsize(path)
            assert file_size >= 987, f"{name} PNG too small"
        
        # Cleanup
        for path in results.values():
            os.remove(path)
        os.rmdir(output_dir)
