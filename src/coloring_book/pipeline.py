"""
Unified Coloring Book Generation Pipeline
==========================================

Orchestrates AI-first generation with SVG fallback.
"""

import logging
from pathlib import Path
from typing import Optional

from .ai.generator import AIColoringGenerator
from .svg.factory import AnimalFactory
from .png.exporter import PNGExporter

logger = logging.getLogger(__name__)

# Valid styles and difficulties (lists for consistent ordering in CLI help)
VALID_STYLES = ["coloring_book", "kawaii", "realistic"]
VALID_DIFFICULTIES = ["easy", "medium", "hard"]


class ColoringBookPipeline:
    """Generate coloring book pages with AI-first, SVG-fallback strategy."""

    def __init__(
        self,
        ai_enabled: bool = True,
        ai_base_url: str = "http://localhost:5000",
        png_dpi: int = 150,
    ):
        """Initialize pipeline.

        Args:
            ai_enabled: Try AI generation first
            ai_base_url: Genesis API base URL
            png_dpi: PNG export DPI
        """
        self.ai_enabled = ai_enabled
        self.ai_generator = AIColoringGenerator(base_url=ai_base_url) if ai_enabled else None
        self.png_dpi = png_dpi

    def generate(
        self,
        animal: str,
        style: str = "coloring_book",
        difficulty: str = "medium",
        output_path: Optional[Path] = None,
    ) -> bytes:
        """Generate coloring book page.

        Strategy:
        1. Try AI generation if enabled
        2. Fallback to SVG pipeline if AI fails
        3. Export to PNG

        Args:
            animal: Animal name (any string, not limited to registry)
            style: Image style (coloring_book, kawaii, realistic)
            difficulty: Detail level (easy, medium, hard)
            output_path: Optional save path

        Returns:
            PNG image bytes

        Raises:
            ValueError: If invalid style/difficulty
        """
        # Validate inputs
        if style not in VALID_STYLES:
            raise ValueError(f"Invalid style '{style}'. Must be one of: {VALID_STYLES}")
        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(f"Invalid difficulty '{difficulty}'. Must be one of: {VALID_DIFFICULTIES}")

        # Try AI generation first
        if self.ai_enabled:
            logger.info(f"Attempting AI generation: {animal} ({style}, {difficulty})")
            ai_png = self.ai_generator.generate(
                animal=animal,
                style=style,
                difficulty=difficulty,
                output_path=None,  # Don't save yet
            )

            if ai_png:
                logger.info(f"✅ AI generation succeeded for '{animal}'")
                if output_path:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(ai_png)
                return ai_png

            logger.warning(f"AI generation failed for '{animal}', falling back to SVG")

        # Fallback: SVG pipeline
        logger.info(f"Generating SVG for '{animal}'")
        svg_png = self._svg_pipeline(animal, output_path)
        return svg_png

    def _svg_pipeline(self, animal: str, output_path: Optional[Path] = None) -> bytes:
        """Generate PNG via SVG pipeline.

        Args:
            animal: Animal name
            output_path: Optional save path

        Returns:
            PNG image bytes
        """
        try:
            # Create SVG using factory (only registered animals)
            drawer = AnimalFactory.create(animal)
            svg_content = drawer.draw()

            # Export to PNG
            exporter = PNGExporter(dpi=self.png_dpi)
            png_bytes = exporter.export_svg_to_png(svg_content)

            # Save if path provided
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(png_bytes)
                logger.info(f"Saved SVG-generated PNG: {output_path}")

            return png_bytes

        except Exception as e:
            logger.error(f"SVG pipeline failed for '{animal}': {e}")
            raise RuntimeError(f"Generation failed for '{animal}': {e}") from e

    def batch_generate(
        self,
        animals: list[str],
        style: str = "coloring_book",
        difficulty: str = "medium",
        output_dir: Optional[Path] = None,
    ) -> dict[str, Optional[bytes]]:
        """Generate multiple coloring pages.

        Args:
            animals: List of animal names
            style: Image style
            difficulty: Detail level
            output_dir: Directory to save PNGs

        Returns:
            Dictionary of {animal: png_bytes or None}
        """
        results = {}

        for animal in animals:
            output_path = None
            if output_dir:
                output_path = output_dir / f"{animal}.png"

            try:
                png_bytes = self.generate(
                    animal=animal,
                    style=style,
                    difficulty=difficulty,
                    output_path=output_path,
                )
                results[animal] = png_bytes
                logger.info(f"✅ Generated: {animal}")

            except Exception as e:
                logger.error(f"❌ Failed: {animal} - {e}")
                results[animal] = None

        return results
