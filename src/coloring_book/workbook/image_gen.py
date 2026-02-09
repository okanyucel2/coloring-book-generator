"""Hybrid image generation for workbook items.

Strategy: AI-first (Genesis API) with SVG fallback.
Generates three versions of each item: colored, outline, dashed.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .models import WorkbookItem

logger = logging.getLogger(__name__)

# Clipart prompt template for AI generation
CLIPART_PROMPT = (
    "Simple flat-style cartoon {item_name} clipart for children's coloring book, "
    "white background, bright colors, cute style, no text, isolated object, "
    "clean edges, suitable for ages 3-5"
)


class WorkbookImageGenerator:
    """Generates colored + outline + dashed versions of workbook items."""

    def __init__(
        self,
        ai_base_url: str = "http://localhost:5000",
        ai_timeout: float = 30.0,
        ai_enabled: bool = True,
        image_size: tuple[int, int] = (512, 512),
    ):
        self.ai_base_url = ai_base_url
        self.ai_timeout = ai_timeout
        self.ai_enabled = ai_enabled
        self.image_size = image_size

    async def generate_item(self, name: str, category: str) -> WorkbookItem:
        """Generate all image variants for a workbook item.

        Args:
            name: Item identifier (e.g. "fire_truck")
            category: Item category (e.g. "vehicle")

        Returns:
            WorkbookItem with colored, outline, and dashed images
        """
        # 1. Get colored image (AI or fallback)
        colored = None
        if self.ai_enabled:
            colored = await self._generate_ai_colored(name, category)

        if colored is None:
            colored = self._generate_placeholder_colored(name)

        # 2. Convert colored → outline
        outline = self._image_to_outline(colored)

        # 3. Convert outline → dashed
        dashed = self._outline_to_dashed(outline)

        return WorkbookItem(
            name=name,
            category=category,
            colored_image=colored,
            outline_image=outline,
            dashed_image=dashed,
        )

    async def _generate_ai_colored(self, name: str, category: str) -> Optional[bytes]:
        """Try generating colored clipart via Genesis AI API."""
        try:
            import httpx

            display_name = name.replace("_", " ")
            prompt = CLIPART_PROMPT.format(item_name=display_name)

            url = f"{self.ai_base_url}/api/v1/image-generation/generate/raw"
            payload = {
                "animal": display_name,
                "style": "coloring_book",
                "difficulty": "easy",
                "model": "imagen",
            }

            async with httpx.AsyncClient(timeout=self.ai_timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

            image_bytes = response.content
            # Validate it's a real image
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()

            logger.info(f"AI generation succeeded for '{name}'")
            return image_bytes

        except Exception as e:
            logger.warning(f"AI generation failed for '{name}': {e}")
            return None

    def _generate_placeholder_colored(self, name: str) -> bytes:
        """Generate a simple colored placeholder image.

        Creates a colored shape with the item name - used as fallback
        when AI generation is unavailable.
        """
        width, height = self.image_size
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Draw a simple colored shape
        padding = 40
        # Use a nice color based on name hash
        hue = hash(name) % 360
        r, g, b = _hsl_to_rgb(hue, 0.7, 0.6)
        fill_color = (r, g, b, 255)
        outline_color = (max(r - 60, 0), max(g - 60, 0), max(b - 60, 0), 255)

        # Draw rounded rectangle as body
        draw.rounded_rectangle(
            [padding, padding, width - padding, height - padding],
            radius=30,
            fill=fill_color,
            outline=outline_color,
            width=3,
        )

        # Draw item name
        display_name = name.replace("_", " ").title()
        try:
            bbox = draw.textbbox((0, 0), display_name)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (width - text_width) // 2
            text_y = (height - text_height) // 2
            draw.text((text_x, text_y), display_name, fill=(255, 255, 255, 255))
        except Exception:
            draw.text((width // 4, height // 2), display_name, fill=(255, 255, 255, 255))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _image_to_outline(self, colored_png: bytes) -> bytes:
        """Convert colored image to black outline using edge detection.

        Uses Canny-style edge detection via PIL filters:
        1. Convert to grayscale
        2. Apply edge detection (FIND_EDGES)
        3. Threshold to clean binary outline
        4. Invert (black lines on white background)
        """
        img = Image.open(io.BytesIO(colored_png)).convert("L")

        # Apply edge detection
        edges = img.filter(ImageFilter.FIND_EDGES)

        # Convert to numpy for thresholding
        arr = np.array(edges)

        # Threshold: pixels above threshold become black lines
        threshold = 30
        binary = np.where(arr > threshold, 0, 255).astype(np.uint8)

        # Create output image (black lines on white)
        outline_img = Image.fromarray(binary, mode="L").convert("RGBA")

        # Make white areas transparent-ready but keep as white background
        result = Image.new("RGBA", outline_img.size, (255, 255, 255, 255))
        result.paste(outline_img, mask=None)

        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()

    def _outline_to_dashed(self, outline_png: bytes) -> bytes:
        """Convert solid outline to dashed tracing lines.

        Strategy: Sample the outline at intervals, creating dash-gap pattern.
        """
        img = Image.open(io.BytesIO(outline_png)).convert("L")
        arr = np.array(img)

        # Find black pixels (outline)
        is_line = arr < 128

        # Create dashed version: keep pixels in dash segments, remove in gaps
        dashed = np.full_like(arr, 255)  # Start white

        dash_len = 8  # pixels of dash
        gap_len = 6  # pixels of gap
        cycle = dash_len + gap_len

        # Apply dash pattern horizontally
        for y in range(arr.shape[0]):
            for x in range(arr.shape[1]):
                if is_line[y, x]:
                    # Determine if this pixel is in a dash or gap segment
                    pos_in_cycle = (x + y) % cycle  # diagonal dash for visual variety
                    if pos_in_cycle < dash_len:
                        dashed[y, x] = 0  # black (dash)

        # Convert back to image
        dashed_img = Image.fromarray(dashed, mode="L").convert("RGBA")
        result = Image.new("RGBA", dashed_img.size, (255, 255, 255, 255))
        result.paste(dashed_img, mask=None)

        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()

    async def generate_items_batch(
        self, items: list[tuple[str, str]]
    ) -> list[WorkbookItem]:
        """Generate multiple items.

        Args:
            items: List of (name, category) tuples

        Returns:
            List of WorkbookItem instances
        """
        results = []
        for name, category in items:
            try:
                item = await self.generate_item(name, category)
                results.append(item)
                logger.info(f"Generated item: {name}")
            except Exception as e:
                logger.error(f"Failed to generate item '{name}': {e}")
                # Create item with placeholder
                results.append(WorkbookItem(name=name, category=category))
        return results


def _hsl_to_rgb(h: int, s: float, l: float) -> tuple[int, int, int]:
    """Convert HSL to RGB. h: 0-360, s: 0-1, l: 0-1."""
    h = h / 360.0
    if s == 0:
        r = g = b = l
    else:
        def hue_to_rgb(p, q, t):
            if t < 0:
                t += 1
            if t > 1:
                t -= 1
            if t < 1 / 6:
                return p + (q - p) * 6 * t
            if t < 1 / 2:
                return q
            if t < 2 / 3:
                return p + (q - p) * (2 / 3 - t) * 6
            return p

        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hue_to_rgb(p, q, h + 1 / 3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1 / 3)

    return int(r * 255), int(g * 255), int(b * 255)
