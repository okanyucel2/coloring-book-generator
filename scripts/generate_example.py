#!/usr/bin/env python3
"""Generate example cat coloring page PNG."""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from coloring_book.svg.factory import AnimalFactory
from coloring_book.png.exporter import PNGExporter


def generate_cat_example():
    """Generate and save example cat PNG."""
    
    # Create cat drawer using factory
    print("📐 Creating cat drawer...")
    cat_drawer = AnimalFactory.create("cat", width=312, height=312)
    
    # Draw SVG
    print("🎨 Drawing cat SVG...")
    svg_content = cat_drawer.draw()
    
    # Convert to PNG with updated exporter
    print("📸 Converting to PNG with 6x stroke multiplier...")
    exporter = PNGExporter(dpi=150, quality=90)
    png_bytes = exporter.export_svg_to_png(svg_content)
    
    # Create output directory
    output_dir = project_root / "docs" / "examples"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save PNG
    output_file = output_dir / "cat_example.png"
    output_file.write_bytes(png_bytes)
    
    print(f"✅ Saved: {output_file}")
    print(f"📊 File size: {len(png_bytes)} bytes")
    
    return output_file


if __name__ == "__main__":
    output_path = generate_cat_example()
    print(f"🎉 Done! Example PNG ready at: {output_path}")
