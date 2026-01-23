"""
AI Coloring Book Generator
============================

Client for Genesis Image Generation API (Nano Banana).
Falls back to SVG pipeline if API is unavailable.
"""

import logging
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

GENESIS_BASE_URL = "http://localhost:5000"
GENERATE_ENDPOINT = "/api/v1/image-generation/generate/raw"


class AIColoringGenerator:
    """Generate coloring book pages via Genesis AI Image Generation API."""

    def __init__(self, base_url: str = GENESIS_BASE_URL, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout

    def generate(
        self,
        animal: str,
        output_path: Optional[Path] = None,
        style: str = "coloring_book",
        difficulty: str = "medium",
    ) -> Optional[bytes]:
        """Generate a coloring book image via the Genesis API.

        Args:
            animal: Animal to generate (e.g. 'cat', 'elephant')
            output_path: If provided, save PNG to this path
            style: Image style (coloring_book, kawaii, realistic)
            difficulty: Detail level (easy, medium, hard)

        Returns:
            PNG image bytes, or None if generation failed
        """
        url = f"{self.base_url}{GENERATE_ENDPOINT}"
        payload = {"animal": animal, "style": style, "difficulty": difficulty}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning(f"AI generation failed for '{animal}': {e}")
            return None

        image_bytes = response.content

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(image_bytes)
            logger.info(f"Saved AI-generated image: {output_path} ({len(image_bytes)} bytes)")

        return image_bytes
