"""Integration tests for PNG export functionality."""

import pytest
from coloring_book.png.exporter import PNGExporter
from coloring_book.png.watermark import WatermarkGenerator, PreviewGenerator, ListingImageGenerator
from coloring_book.svg.animals import CatDrawer, DogDrawer, BirdDrawer
from PIL import Image
from io import BytesIO
import os


class TestPNGExportIntegration:
    """Integration tests for complete PNG export pipeline."""

    def test_complete_pipeline_cat(self):
        """Test complete SVG to PNG to watermark pipeline for cat."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        # Export SVG to PNG
        exporter = PNGExporter(dpi=150)
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        # Add watermark
        wm_gen = WatermarkGenerator(text="Preview", opacity=0.3)
        watermarked = wm_gen.add_watermark(png_bytes)
        
        # Create preview
        preview_gen = PreviewGenerator(size=(200, 200))
        thumbnail = preview_gen.create_thumbnail(watermarked)
        
        assert thumbnail is not None
        img = Image.open(BytesIO(thumbnail))
        assert img.format == "PNG"

    def test_complete_pipeline_dog(self):
        """Test complete pipeline for dog."""
        dog = DogDrawer()
        svg_content = dog.draw()
        
        exporter = PNGExporter(dpi=200, quality=95)
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        wm_gen = WatermarkGenerator(text="© 2024", opacity=0.25, position="bottom-right")
        watermarked = wm_gen.add_watermark(png_bytes)
        
        listing_gen = ListingImageGenerator()
        listing_img = listing_gen.generate(watermarked, title="Dog Drawing")
        
        assert listing_img is not None
        img = Image.open(BytesIO(listing_img))
        assert img.format == "PNG"

    def test_batch_export_with_watermarks(self):
        """Test batch exporting multiple animals with watermarks."""
        animals = {
            "cat": CatDrawer().draw(),
            "dog": DogDrawer().draw(),
            "bird": BirdDrawer().draw(),
        }
        
        exporter = PNGExporter(dpi=150)
        wm_gen = WatermarkGenerator(opacity=0.3)
        preview_gen = PreviewGenerator()
        
        results = {}
        for name, svg_content in animals.items():
            # Export to PNG
            png_bytes = exporter.export_svg_to_png(svg_content)
            
            # Add watermark
            watermarked = wm_gen.add_watermark(png_bytes)
            
            # Create preview
            preview = preview_gen.create_thumbnail(watermarked)
            
            results[name] = preview
        
        assert len(results) == 3
        for name, preview_bytes in results.items():
            img = Image.open(BytesIO(preview_bytes))
            assert img.format == "PNG"

    def test_export_to_file_with_watermark(self):
        """Test exporting to file with watermark."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter = PNGExporter()
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        wm_gen = WatermarkGenerator(text="Demo", opacity=0.4)
        watermarked = wm_gen.add_watermark(png_bytes)
        
        output_path = "/tmp/test_watermarked.png"
        with open(output_path, "wb") as f:
            f.write(watermarked)
        
        assert os.path.exists(output_path)
        file_size = os.path.getsize(output_path)
        assert file_size > 0
        
        img = Image.open(output_path)
        assert img.format == "PNG"
        
        os.remove(output_path)

    def test_high_dpi_export(self):
        """Test exporting at high DPI for print quality."""
        dog = DogDrawer()
        svg_content = dog.draw()
        
        # High DPI for print
        exporter = PNGExporter(dpi=300, quality=95)
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        img = Image.open(BytesIO(png_bytes))
        # Should have reasonable size for print
        assert img.size[0] >= 600
        assert img.size[1] >= 400

    def test_preview_generation_pipeline(self):
        """Test generating previews at different sizes."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter = PNGExporter()
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        sizes = [(100, 100), (200, 200), (400, 400)]
        previews = {}
        
        for size in sizes:
            preview_gen = PreviewGenerator(size=size)
            previews[str(size)] = preview_gen.create_thumbnail(png_bytes)
        
        # Verify all previews are valid
        for size_str, preview_bytes in previews.items():
            img = Image.open(BytesIO(preview_bytes))
            assert img.format == "PNG"

    def test_listing_image_generation(self):
        """Test generating Etsy listing images."""
        bird = BirdDrawer()
        svg_content = bird.draw()
        
        exporter = PNGExporter(dpi=150)
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        listing_gen = ListingImageGenerator(size=(1200, 1200))
        listing_img = listing_gen.generate(png_bytes, title="Beautiful Bird Drawing")
        
        img = Image.open(BytesIO(listing_img))
        assert img.format == "PNG"
        assert img.size == (1200, 1200)

    def test_export_and_save_multiple(self):
        """Test exporting and saving multiple animals to directory."""
        animals = {
            "cat": CatDrawer().draw(),
            "dog": DogDrawer().draw(),
            "bird": BirdDrawer().draw(),
        }
        
        exporter = PNGExporter()
        output_dir = "/tmp/test_animals"
        
        saved_files = {}
        for name, svg_content in animals.items():
            png_bytes = exporter.export_svg_to_png(svg_content)
            output_path = os.path.join(output_dir, f"{name}.png")
            os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, "wb") as f:
                f.write(png_bytes)
            
            saved_files[name] = output_path
        
        # Verify all files exist and are valid PNGs
        assert len(saved_files) == 3
        for name, path in saved_files.items():
            assert os.path.exists(path)
            img = Image.open(path)
            assert img.format == "PNG"
            os.remove(path)
        
        os.rmdir(output_dir)

    def test_watermark_with_different_opacities(self):
        """Test watermarking at different opacity levels."""
        cat = CatDrawer()
        svg_content = cat.draw()
        
        exporter = PNGExporter()
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        opacities = [0.1, 0.3, 0.5, 0.7, 0.9]
        results = {}
        
        for opacity in opacities:
            wm_gen = WatermarkGenerator(opacity=opacity)
            watermarked = wm_gen.add_watermark(png_bytes)
            results[opacity] = watermarked
        
        # Verify all watermarked images are valid
        for opacity, watermarked_bytes in results.items():
            img = Image.open(BytesIO(watermarked_bytes))
            assert img.format == "PNG"

    def test_chaining_operations(self):
        """Test chaining PNG operations."""
        dog = DogDrawer()
        svg_content = dog.draw()
        
        # Chain operations
        exporter = PNGExporter().set_dpi(200).set_quality(90)
        png_bytes = exporter.export_svg_to_png(svg_content)
        
        wm_gen = WatermarkGenerator().set_opacity(0.4)
        watermarked = wm_gen.add_watermark(png_bytes)
        
        preview_gen = PreviewGenerator(size=(250, 250))
        preview = preview_gen.create_thumbnail(watermarked)
        
        assert preview is not None
        img = Image.open(BytesIO(preview))
        assert img.format == "PNG"
