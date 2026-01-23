#!/usr/bin/env python3
"""Generate example cat coloring page PNG.

Usage:
    python -m scripts.generate_example          # SVG pipeline
    python -m scripts.generate_example --ai     # AI generation (with SVG fallback)
"""

import argparse
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def generate_svg_example():
    """Generate cat PNG via SVG pipeline."""
    from coloring_book.svg.factory import AnimalFactory
    from coloring_book.png.exporter import PNGExporter

    print("📐 Creating cat drawer...")
    cat_drawer = AnimalFactory.create("cat", width=312, height=312)

    print("🎨 Drawing cat SVG...")
    svg_content = cat_drawer.draw()

    print("📸 Converting to PNG with 6x stroke multiplier...")
    exporter = PNGExporter(dpi=150, quality=90)
    png_bytes = exporter.export_svg_to_png(svg_content)

    output_dir = project_root / "docs" / "examples"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "cat_example.png"
    output_file.write_bytes(png_bytes)

    print(f"✅ Saved: {output_file}")
    print(f"📊 File size: {len(png_bytes)} bytes")
    return output_file


def generate_ai_example():
    """Generate cat PNG via AI, with SVG fallback."""
    from coloring_book.ai import AIColoringGenerator

    output_dir = project_root / "docs" / "examples"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "cat_ai_example.png"

    print("🤖 Generating via AI (Nano Banana)...")
    generator = AIColoringGenerator()
    image_bytes = generator.generate("cat", output_path=output_file)

    if image_bytes:
        print(f"✅ AI-generated: {output_file}")
        print(f"📊 File size: {len(image_bytes)} bytes")
        return output_file

    print("⚠️  AI generation failed, falling back to SVG pipeline...")
    return generate_svg_example()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate example coloring page")
    parser.add_argument("--ai", action="store_true", help="Use AI generation (with SVG fallback)")
    args = parser.parse_args()

    if args.ai:
        output_path = generate_ai_example()
    else:
        output_path = generate_svg_example()

    print(f"🎉 Done! Example PNG ready at: {output_path}")
