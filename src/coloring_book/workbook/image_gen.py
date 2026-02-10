"""Hybrid image generation for workbook items.

Strategy: AI-first (Genesis API) with PIL-drawn fallback.
Generates three versions of each item: colored, outline, dashed.

Fallback system draws recognizable shapes using PIL primitives:
- Vehicles: rectangles, circles for wheels, specific details per type
- Animals: ovals, circles, triangles for ears/tails/features
"""

from __future__ import annotations

import io
import logging
import math
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .models import WorkbookItem

logger = logging.getLogger(__name__)

# Clipart prompt template for AI generation
CLIPART_PROMPT = (
    "Simple flat-style cartoon {item_name} clipart for children's coloring book, "
    "white background, bright colors, cute style, no text, isolated object, "
    "clean edges, suitable for ages 3-5"
)

# ──────────────────────────────────────────────────────────────────────
# Color palettes for categories
# ──────────────────────────────────────────────────────────────────────
VEHICLE_COLORS: dict[str, tuple[int, int, int]] = {
    "fire_truck": (220, 40, 40),
    "police_car": (40, 80, 180),
    "ambulance": (255, 255, 255),
    "school_bus": (255, 200, 0),
    "helicopter": (80, 160, 80),
    "airplane": (100, 160, 230),
    "tractor": (0, 140, 60),
    "train": (60, 60, 60),
    "bicycle": (60, 180, 220),
    "taxi": (255, 220, 0),
    "bulldozer": (220, 180, 40),
    "crane": (255, 140, 0),
    "dump_truck": (180, 140, 60),
    "excavator": (230, 170, 30),
    "cement_mixer": (160, 160, 160),
    "garbage_truck": (60, 140, 60),
    "tow_truck": (180, 60, 60),
    "traffic_light": (80, 80, 80),
}

ANIMAL_COLORS: dict[str, tuple[int, int, int]] = {
    "cat": (255, 180, 100),
    "dog": (180, 130, 70),
    "bird": (255, 220, 60),
    "elephant": (160, 170, 190),
    "lion": (230, 180, 60),
    "giraffe": (240, 200, 80),
    "fish": (60, 160, 220),
    "butterfly": (200, 80, 200),
    "rabbit": (220, 200, 200),
    "turtle": (60, 160, 80),
    "horse": (160, 100, 60),
    "cow": (240, 240, 240),
    "pig": (255, 180, 180),
    "chicken": (255, 230, 150),
    "duck": (255, 220, 60),
    "frog": (60, 200, 60),
    "bear": (160, 110, 60),
    "monkey": (180, 130, 80),
}


def _get_item_color(name: str, category: str) -> tuple[int, int, int]:
    """Get the primary color for an item."""
    if category == "vehicle":
        return VEHICLE_COLORS.get(name, (150, 150, 200))
    if category == "animal":
        return ANIMAL_COLORS.get(name, (200, 180, 150))
    # Fallback based on name hash
    hue = hash(name) % 360
    r, g, b = _hsl_to_rgb(hue, 0.7, 0.6)
    return (r, g, b)


def _darker(color: tuple[int, int, int], amount: int = 60) -> tuple[int, int, int]:
    """Return a darker version of a color."""
    return (max(color[0] - amount, 0), max(color[1] - amount, 0), max(color[2] - amount, 0))


def _lighter(color: tuple[int, int, int], amount: int = 60) -> tuple[int, int, int]:
    """Return a lighter version of a color."""
    return (min(color[0] + amount, 255), min(color[1] + amount, 255), min(color[2] + amount, 255))


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
            colored = self._generate_placeholder_colored(name, category)

        # 2. Convert colored -> outline
        outline = self._image_to_outline(colored)

        # 3. Convert outline -> dashed
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

    # ──────────────────────────────────────────────────────────────
    # Placeholder generation (improved PIL drawing)
    # ──────────────────────────────────────────────────────────────

    def _generate_placeholder_colored(self, name: str, category: str = "generic") -> bytes:
        """Generate a visually appealing colored placeholder image.

        Uses category-specific drawing methods to create recognizable
        children's-book-style illustrations using PIL drawing primitives.
        """
        width, height = self.image_size

        # Dispatch to category-specific generators
        if category == "vehicle" and name in VEHICLE_COLORS:
            return self._generate_simple_vehicle(name, width, height)
        elif category == "animal" and name in ANIMAL_COLORS:
            return self._generate_simple_animal(name, width, height)
        else:
            return self._generate_generic_placeholder(name, category, width, height)

    def _generate_simple_vehicle(self, name: str, width: int, height: int) -> bytes:
        """Create a recognizable vehicle using PIL drawing primitives.

        Each vehicle type has a distinct shape: body, wheels, and
        type-specific details (ladder for fire truck, lights for police, etc.)
        """
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        color = VEHICLE_COLORS.get(name, (150, 150, 200))
        outline = _darker(color, 80)
        lw = max(2, width // 128)  # line width scales with image size

        # Scale factors
        cx, cy = width // 2, height // 2
        unit = min(width, height) // 10

        # ---- Per-vehicle shape dispatch ----
        if name == "fire_truck":
            self._draw_truck_body(draw, cx, cy, unit, color, outline, lw)
            # Ladder on top
            ladder_color = (200, 200, 200)
            draw.rectangle([cx - 4 * unit, cy - 3 * unit, cx + 2 * unit, cy - 2.5 * unit],
                           fill=ladder_color, outline=_darker(ladder_color), width=lw)
            # Rungs
            for i in range(-3, 2):
                x = cx + i * unit
                draw.line([x, cy - 3 * unit, x, cy - 2.5 * unit],
                          fill=_darker(ladder_color), width=lw)

        elif name == "police_car":
            self._draw_car_body(draw, cx, cy, unit, color, outline, lw)
            # Light bar on top
            draw.ellipse([cx - unit, cy - 3.5 * unit, cx - 0.2 * unit, cy - 2.5 * unit],
                         fill=(255, 0, 0), outline=(200, 0, 0), width=lw)
            draw.ellipse([cx + 0.2 * unit, cy - 3.5 * unit, cx + unit, cy - 2.5 * unit],
                         fill=(0, 0, 255), outline=(0, 0, 200), width=lw)

        elif name == "ambulance":
            self._draw_truck_body(draw, cx, cy, unit, color, outline, lw)
            # Red cross
            cross_c = (220, 40, 40)
            draw.rectangle([cx - 0.5 * unit, cy - 2 * unit, cx + 0.5 * unit, cy],
                           fill=cross_c, outline=cross_c)
            draw.rectangle([cx - 1.5 * unit, cy - 1.5 * unit, cx + 1.5 * unit, cy - 0.5 * unit],
                           fill=cross_c, outline=cross_c)

        elif name == "school_bus":
            self._draw_bus_body(draw, cx, cy, unit, color, outline, lw)

        elif name == "helicopter":
            self._draw_helicopter(draw, cx, cy, unit, color, outline, lw)

        elif name == "airplane":
            self._draw_airplane(draw, cx, cy, unit, color, outline, lw)

        elif name == "tractor":
            self._draw_tractor(draw, cx, cy, unit, color, outline, lw)

        elif name == "train":
            self._draw_train(draw, cx, cy, unit, color, outline, lw)

        elif name == "bicycle":
            self._draw_bicycle(draw, cx, cy, unit, color, outline, lw)

        elif name == "taxi":
            self._draw_car_body(draw, cx, cy, unit, color, outline, lw)
            # "TAXI" sign on top
            draw.rectangle([cx - 1.2 * unit, cy - 3.5 * unit, cx + 1.2 * unit, cy - 2.5 * unit],
                           fill=(255, 255, 200), outline=outline, width=lw)

        elif name == "bulldozer":
            self._draw_bulldozer(draw, cx, cy, unit, color, outline, lw)

        elif name == "crane":
            self._draw_crane(draw, cx, cy, unit, color, outline, lw)

        elif name == "dump_truck":
            self._draw_dump_truck(draw, cx, cy, unit, color, outline, lw)

        elif name == "excavator":
            self._draw_excavator(draw, cx, cy, unit, color, outline, lw)

        elif name == "cement_mixer":
            self._draw_cement_mixer(draw, cx, cy, unit, color, outline, lw)

        elif name == "garbage_truck":
            self._draw_garbage_truck(draw, cx, cy, unit, color, outline, lw)

        elif name == "tow_truck":
            self._draw_tow_truck(draw, cx, cy, unit, color, outline, lw)

        elif name == "traffic_light":
            self._draw_traffic_light(draw, cx, cy, unit, color, outline, lw)

        else:
            # Fallback: generic vehicle shape
            self._draw_car_body(draw, cx, cy, unit, color, outline, lw)

        # Draw item name at the bottom
        self._draw_label(draw, name, width, height)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _generate_simple_animal(self, name: str, width: int, height: int) -> bytes:
        """Create a recognizable animal using PIL drawing primitives.

        Each animal has a body shape, head, eyes, and distinguishing
        features (ears, tail, spots, etc.)
        """
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        color = ANIMAL_COLORS.get(name, (200, 180, 150))
        outline = _darker(color, 80)
        lw = max(2, width // 128)

        cx, cy = width // 2, height // 2
        unit = min(width, height) // 10

        if name == "cat":
            self._draw_cat(draw, cx, cy, unit, color, outline, lw)
        elif name == "dog":
            self._draw_dog(draw, cx, cy, unit, color, outline, lw)
        elif name == "bird":
            self._draw_bird(draw, cx, cy, unit, color, outline, lw)
        elif name == "elephant":
            self._draw_elephant(draw, cx, cy, unit, color, outline, lw)
        elif name == "lion":
            self._draw_lion(draw, cx, cy, unit, color, outline, lw)
        elif name == "giraffe":
            self._draw_giraffe(draw, cx, cy, unit, color, outline, lw)
        elif name == "fish":
            self._draw_fish(draw, cx, cy, unit, color, outline, lw)
        elif name == "butterfly":
            self._draw_butterfly(draw, cx, cy, unit, color, outline, lw)
        elif name == "rabbit":
            self._draw_rabbit(draw, cx, cy, unit, color, outline, lw)
        elif name == "turtle":
            self._draw_turtle(draw, cx, cy, unit, color, outline, lw)
        elif name == "horse":
            self._draw_horse(draw, cx, cy, unit, color, outline, lw)
        elif name == "cow":
            self._draw_cow(draw, cx, cy, unit, color, outline, lw)
        elif name == "pig":
            self._draw_pig(draw, cx, cy, unit, color, outline, lw)
        elif name == "chicken":
            self._draw_chicken(draw, cx, cy, unit, color, outline, lw)
        elif name == "duck":
            self._draw_duck(draw, cx, cy, unit, color, outline, lw)
        elif name == "frog":
            self._draw_frog(draw, cx, cy, unit, color, outline, lw)
        elif name == "bear":
            self._draw_bear(draw, cx, cy, unit, color, outline, lw)
        elif name == "monkey":
            self._draw_monkey(draw, cx, cy, unit, color, outline, lw)
        else:
            # Generic animal: oval body + round head
            self._draw_generic_animal(draw, cx, cy, unit, color, outline, lw)

        self._draw_label(draw, name, width, height)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _generate_generic_placeholder(
        self, name: str, category: str, width: int, height: int,
    ) -> bytes:
        """Generate a generic placeholder for unknown items.

        Draws a rounded shape with a gradient-like color fill and the item
        name in the center. Better than a plain rectangle.
        """
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)

        hue = hash(name) % 360
        r, g, b = _hsl_to_rgb(hue, 0.7, 0.6)
        fill_color = (r, g, b, 255)
        outline_color = (max(r - 60, 0), max(g - 60, 0), max(b - 60, 0), 255)

        cx, cy = width // 2, height // 2
        unit = min(width, height) // 10

        # Draw a large rounded rectangle as body
        padding = 2 * unit
        draw.rounded_rectangle(
            [padding, padding, width - padding, height - padding],
            radius=int(1.5 * unit),
            fill=fill_color,
            outline=outline_color,
            width=3,
        )

        # Add a decorative circle inside
        inner_r = int(2.5 * unit)
        draw.ellipse(
            [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
            fill=_lighter((r, g, b), 40) + (255,),
            outline=outline_color,
            width=2,
        )

        # Draw star in center
        self._draw_star(draw, cx, cy, unit, (255, 255, 255, 220))

        self._draw_label(draw, name, width, height)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # ──────────────────────────────────────────────────────────────
    # Vehicle drawing helpers
    # ──────────────────────────────────────────────────────────────

    def _draw_wheel(self, draw: ImageDraw.ImageDraw, x: int, y: int,
                    radius: int, lw: int) -> None:
        """Draw a wheel with hub at (x, y)."""
        draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                     fill=(50, 50, 50), outline=(30, 30, 30), width=lw)
        # Hub cap
        hub = radius // 3
        draw.ellipse([x - hub, y - hub, x + hub, y + hub],
                     fill=(180, 180, 180), outline=(120, 120, 120), width=max(1, lw // 2))

    def _draw_car_body(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                       unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a basic car body with cabin and wheels."""
        # Lower body
        draw.rounded_rectangle(
            [cx - 4 * unit, cy - unit, cx + 4 * unit, cy + 1.5 * unit],
            radius=unit // 2, fill=color, outline=outline, width=lw,
        )
        # Cabin (upper part)
        draw.rounded_rectangle(
            [cx - 2 * unit, cy - 2.5 * unit, cx + 2 * unit, cy - 0.5 * unit],
            radius=unit // 2, fill=color, outline=outline, width=lw,
        )
        # Windows
        win_color = (180, 220, 255)
        draw.rectangle([cx - 1.7 * unit, cy - 2.2 * unit, cx - 0.2 * unit, cy - 0.8 * unit],
                       fill=win_color, outline=outline, width=max(1, lw // 2))
        draw.rectangle([cx + 0.2 * unit, cy - 2.2 * unit, cx + 1.7 * unit, cy - 0.8 * unit],
                       fill=win_color, outline=outline, width=max(1, lw // 2))
        # Wheels
        wheel_r = int(0.9 * unit)
        self._draw_wheel(draw, int(cx - 2.5 * unit), int(cy + 1.5 * unit), wheel_r, lw)
        self._draw_wheel(draw, int(cx + 2.5 * unit), int(cy + 1.5 * unit), wheel_r, lw)
        # Headlights
        draw.ellipse([cx + 3.5 * unit, cy - 0.3 * unit, cx + 4.2 * unit, cy + 0.4 * unit],
                     fill=(255, 255, 180), outline=outline, width=lw)

    def _draw_truck_body(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a truck body (cab + cargo area)."""
        # Cargo area
        draw.rounded_rectangle(
            [cx - 4 * unit, cy - 2 * unit, cx + 2 * unit, cy + 1.5 * unit],
            radius=unit // 3, fill=color, outline=outline, width=lw,
        )
        # Cab
        draw.rounded_rectangle(
            [cx + 2 * unit, cy - 2.5 * unit, cx + 4.5 * unit, cy + 1.5 * unit],
            radius=unit // 3, fill=color, outline=outline, width=lw,
        )
        # Cab window
        draw.rectangle([cx + 2.5 * unit, cy - 2 * unit, cx + 4 * unit, cy - 0.5 * unit],
                       fill=(180, 220, 255), outline=outline, width=max(1, lw // 2))
        # Wheels
        wheel_r = int(0.9 * unit)
        self._draw_wheel(draw, int(cx - 2.5 * unit), int(cy + 1.5 * unit), wheel_r, lw)
        self._draw_wheel(draw, int(cx + 3.5 * unit), int(cy + 1.5 * unit), wheel_r, lw)

    def _draw_bus_body(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                       unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a school bus."""
        # Bus body
        draw.rounded_rectangle(
            [cx - 4.5 * unit, cy - 2 * unit, cx + 4.5 * unit, cy + 1.5 * unit],
            radius=unit // 2, fill=color, outline=outline, width=lw,
        )
        # Windows row
        win_color = (180, 220, 255)
        for i in range(-3, 4):
            wx = cx + i * 1.1 * unit
            draw.rectangle([wx - 0.4 * unit, cy - 1.5 * unit, wx + 0.4 * unit, cy - 0.3 * unit],
                           fill=win_color, outline=outline, width=max(1, lw // 2))
        # Wheels
        wheel_r = int(0.8 * unit)
        self._draw_wheel(draw, int(cx - 3 * unit), int(cy + 1.5 * unit), wheel_r, lw)
        self._draw_wheel(draw, int(cx + 3 * unit), int(cy + 1.5 * unit), wheel_r, lw)
        # Stop sign arm (left side)
        draw.rectangle([cx - 4.5 * unit - unit, cy - 1 * unit, cx - 4.5 * unit, cy - 0.3 * unit],
                       fill=(255, 0, 0), outline=_darker((255, 0, 0)), width=lw)

    def _draw_helicopter(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a helicopter."""
        # Body (oval)
        draw.ellipse([cx - 2.5 * unit, cy - 1.5 * unit, cx + 2 * unit, cy + 1.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Cockpit window
        draw.ellipse([cx + 0.5 * unit, cy - 1 * unit, cx + 2 * unit, cy + 0.5 * unit],
                     fill=(180, 220, 255), outline=outline, width=lw)
        # Tail boom
        draw.polygon([
            (cx - 2.5 * unit, cy - 0.3 * unit),
            (cx - 4.5 * unit, cy - 1.5 * unit),
            (cx - 4.5 * unit, cy - 0.5 * unit),
            (cx - 2.5 * unit, cy + 0.3 * unit),
        ], fill=color, outline=outline, width=lw)
        # Tail rotor
        draw.line([cx - 4.5 * unit, cy - 2 * unit, cx - 4.5 * unit, cy + 0.5 * unit],
                  fill=outline, width=lw * 2)
        # Main rotor blade
        draw.line([cx - 4 * unit, cy - 2 * unit, cx + 4 * unit, cy - 2 * unit],
                  fill=outline, width=lw * 2)
        # Rotor hub
        draw.ellipse([cx - 0.3 * unit, cy - 2.3 * unit, cx + 0.3 * unit, cy - 1.7 * unit],
                     fill=(100, 100, 100), outline=outline, width=lw)
        # Skids
        draw.line([cx - 2 * unit, cy + 1.5 * unit, cx - 2 * unit, cy + 2.2 * unit],
                  fill=outline, width=lw)
        draw.line([cx + 1 * unit, cy + 1.5 * unit, cx + 1 * unit, cy + 2.2 * unit],
                  fill=outline, width=lw)
        draw.line([cx - 2.5 * unit, cy + 2.2 * unit, cx + 1.5 * unit, cy + 2.2 * unit],
                  fill=outline, width=lw * 2)

    def _draw_airplane(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                       unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw an airplane."""
        # Fuselage
        draw.ellipse([cx - 4 * unit, cy - unit, cx + 4 * unit, cy + unit],
                     fill=color, outline=outline, width=lw)
        # Nose
        draw.polygon([
            (cx + 4 * unit, cy),
            (cx + 5 * unit, cy - 0.3 * unit),
            (cx + 5 * unit, cy + 0.3 * unit),
        ], fill=color, outline=outline, width=lw)
        # Wings
        draw.polygon([
            (cx - unit, cy),
            (cx - 0.5 * unit, cy + 3 * unit),
            (cx + 0.5 * unit, cy + 3 * unit),
            (cx + unit, cy),
        ], fill=_lighter(color, 30), outline=outline, width=lw)
        draw.polygon([
            (cx - unit, cy),
            (cx - 0.5 * unit, cy - 3 * unit),
            (cx + 0.5 * unit, cy - 3 * unit),
            (cx + unit, cy),
        ], fill=_lighter(color, 30), outline=outline, width=lw)
        # Tail
        draw.polygon([
            (cx - 3.5 * unit, cy),
            (cx - 4 * unit, cy - 2 * unit),
            (cx - 3 * unit, cy - 2 * unit),
            (cx - 2.5 * unit, cy),
        ], fill=_lighter(color, 20), outline=outline, width=lw)
        # Windows
        for i in range(-2, 3):
            wx = cx + i * unit
            draw.ellipse([wx - 0.15 * unit, cy - 0.4 * unit, wx + 0.15 * unit, cy - 0.1 * unit],
                         fill=(180, 220, 255), outline=outline)

    def _draw_tractor(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                      unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a tractor."""
        # Body
        draw.rounded_rectangle(
            [cx - 2 * unit, cy - 2 * unit, cx + 2 * unit, cy + unit],
            radius=unit // 3, fill=color, outline=outline, width=lw,
        )
        # Cab
        draw.rounded_rectangle(
            [cx - 0.5 * unit, cy - 3.5 * unit, cx + 2 * unit, cy - 1.5 * unit],
            radius=unit // 3, fill=color, outline=outline, width=lw,
        )
        # Cab window
        draw.rectangle([cx, cy - 3 * unit, cx + 1.5 * unit, cy - 2 * unit],
                       fill=(180, 220, 255), outline=outline, width=max(1, lw // 2))
        # Big rear wheel
        big_r = int(1.5 * unit)
        self._draw_wheel(draw, int(cx - 1.5 * unit), int(cy + unit), big_r, lw)
        # Small front wheel
        small_r = int(0.8 * unit)
        self._draw_wheel(draw, int(cx + 2.5 * unit), int(cy + unit), small_r, lw)
        # Exhaust pipe
        draw.rectangle([cx - 2 * unit, cy - 3.5 * unit, cx - 1.5 * unit, cy - 2 * unit],
                       fill=(80, 80, 80), outline=outline, width=lw)

    def _draw_train(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                    unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a train engine."""
        # Boiler (cylinder)
        draw.rounded_rectangle(
            [cx - 3 * unit, cy - 1.5 * unit, cx + 2 * unit, cy + 1.5 * unit],
            radius=unit, fill=color, outline=outline, width=lw,
        )
        # Cab
        draw.rectangle([cx + 2 * unit, cy - 2.5 * unit, cx + 4 * unit, cy + 1.5 * unit],
                       fill=_lighter(color, 30), outline=outline, width=lw)
        # Cab window
        draw.rectangle([cx + 2.5 * unit, cy - 2 * unit, cx + 3.5 * unit, cy - 0.5 * unit],
                       fill=(180, 220, 255), outline=outline, width=max(1, lw // 2))
        # Smokestack
        draw.rectangle([cx - 2 * unit, cy - 3 * unit, cx - 1.3 * unit, cy - 1.5 * unit],
                       fill=(80, 80, 80), outline=outline, width=lw)
        # Smoke puff
        draw.ellipse([cx - 2.5 * unit, cy - 4.5 * unit, cx - 1 * unit, cy - 3 * unit],
                     fill=(200, 200, 200, 180), outline=(180, 180, 180))
        # Wheels
        wheel_r = int(0.7 * unit)
        for wx in [-2, 0, 2, 3.5]:
            self._draw_wheel(draw, int(cx + wx * unit), int(cy + 1.5 * unit), wheel_r, lw)
        # Cowcatcher
        draw.polygon([
            (cx - 3 * unit, cy + 1.5 * unit),
            (cx - 4 * unit, cy + 2 * unit),
            (cx - 3 * unit, cy + 2 * unit),
        ], fill=outline, outline=outline, width=lw)

    def _draw_bicycle(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                      unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a bicycle."""
        wheel_r = int(1.5 * unit)
        # Rear wheel
        self._draw_wheel(draw, int(cx - 2 * unit), int(cy + unit), wheel_r, lw)
        # Front wheel
        self._draw_wheel(draw, int(cx + 2 * unit), int(cy + unit), wheel_r, lw)
        # Frame - triangle
        frame_color = color
        # Seat tube
        draw.line([cx - 0.5 * unit, cy - 1.5 * unit, cx - 2 * unit, cy + unit],
                  fill=frame_color, width=lw * 2)
        # Top tube
        draw.line([cx - 0.5 * unit, cy - 1.5 * unit, cx + unit, cy - unit],
                  fill=frame_color, width=lw * 2)
        # Down tube
        draw.line([cx + unit, cy - unit, cx - 2 * unit, cy + unit],
                  fill=frame_color, width=lw * 2)
        # Fork
        draw.line([cx + unit, cy - unit, cx + 2 * unit, cy + unit],
                  fill=frame_color, width=lw * 2)
        # Handlebars
        draw.line([cx + 0.5 * unit, cy - 2 * unit, cx + 1.5 * unit, cy - 1.5 * unit],
                  fill=outline, width=lw * 2)
        # Seat
        draw.ellipse([cx - unit, cy - 2 * unit, cx, cy - 1.5 * unit],
                     fill=(60, 60, 60), outline=outline, width=lw)
        # Pedal crank
        draw.ellipse([cx - 2.3 * unit, cy + 0.7 * unit, cx - 1.7 * unit, cy + 1.3 * unit],
                     fill=frame_color, outline=outline, width=lw)

    def _draw_bulldozer(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                        unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a bulldozer."""
        # Tracks
        draw.rounded_rectangle(
            [cx - 4 * unit, cy + 0.5 * unit, cx + 2 * unit, cy + 2.5 * unit],
            radius=unit, fill=(60, 60, 60), outline=(30, 30, 30), width=lw,
        )
        # Body
        draw.rounded_rectangle(
            [cx - 2.5 * unit, cy - 2 * unit, cx + 2 * unit, cy + 0.5 * unit],
            radius=unit // 3, fill=color, outline=outline, width=lw,
        )
        # Blade
        draw.rounded_rectangle(
            [cx - 4.5 * unit, cy - 1.5 * unit, cx - 3.5 * unit, cy + 1 * unit],
            radius=unit // 4, fill=(180, 180, 180), outline=_darker((180, 180, 180)), width=lw,
        )
        # Blade arm
        draw.line([cx - 3.5 * unit, cy - 0.5 * unit, cx - 2.5 * unit, cy - 0.5 * unit],
                  fill=outline, width=lw * 2)
        # Cab
        draw.rectangle([cx - 0.5 * unit, cy - 3 * unit, cx + 1.5 * unit, cy - 1.5 * unit],
                       fill=_lighter(color, 30), outline=outline, width=lw)
        # Cab window
        draw.rectangle([cx - 0.2 * unit, cy - 2.7 * unit, cx + 1.2 * unit, cy - 1.8 * unit],
                       fill=(180, 220, 255), outline=outline, width=max(1, lw // 2))

    def _draw_crane(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                    unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a crane."""
        # Base/truck
        draw.rounded_rectangle(
            [cx - 3 * unit, cy + unit, cx + 3 * unit, cy + 2.5 * unit],
            radius=unit // 3, fill=color, outline=outline, width=lw,
        )
        # Wheels
        wheel_r = int(0.7 * unit)
        for wx in [-2, 0, 2]:
            self._draw_wheel(draw, int(cx + wx * unit), int(cy + 2.5 * unit), wheel_r, lw)
        # Turret
        draw.rectangle([cx - unit, cy - unit, cx + unit, cy + unit],
                       fill=color, outline=outline, width=lw)
        # Boom (arm)
        draw.line([cx, cy - 0.5 * unit, cx + 3 * unit, cy - 4 * unit],
                  fill=color, width=lw * 3)
        draw.line([cx, cy - 0.5 * unit, cx + 3 * unit, cy - 4 * unit],
                  fill=outline, width=lw)
        # Hook
        draw.line([cx + 3 * unit, cy - 4 * unit, cx + 3 * unit, cy - 2 * unit],
                  fill=(100, 100, 100), width=lw)
        # Hook shape
        draw.arc([cx + 2.5 * unit, cy - 2.5 * unit, cx + 3.5 * unit, cy - 1.5 * unit],
                 0, 180, fill=(100, 100, 100), width=lw * 2)

    def _draw_dump_truck(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a dump truck."""
        # Dump bed (tilted)
        draw.polygon([
            (cx - 4 * unit, cy - 2 * unit),
            (cx + unit, cy - 2 * unit),
            (cx + unit, cy + 1.5 * unit),
            (cx - 3.5 * unit, cy + 1.5 * unit),
        ], fill=color, outline=outline, width=lw)
        # Cab
        draw.rounded_rectangle(
            [cx + 1.5 * unit, cy - 2 * unit, cx + 4 * unit, cy + 1.5 * unit],
            radius=unit // 3, fill=_lighter(color, 40), outline=outline, width=lw,
        )
        # Cab window
        draw.rectangle([cx + 2 * unit, cy - 1.5 * unit, cx + 3.5 * unit, cy - 0.3 * unit],
                       fill=(180, 220, 255), outline=outline, width=max(1, lw // 2))
        # Wheels
        wheel_r = int(0.8 * unit)
        self._draw_wheel(draw, int(cx - 2 * unit), int(cy + 1.5 * unit), wheel_r, lw)
        self._draw_wheel(draw, int(cx + 3 * unit), int(cy + 1.5 * unit), wheel_r, lw)

    def _draw_excavator(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                        unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw an excavator."""
        # Tracks
        draw.rounded_rectangle(
            [cx - 3 * unit, cy + unit, cx + 2 * unit, cy + 2.5 * unit],
            radius=unit, fill=(60, 60, 60), outline=(30, 30, 30), width=lw,
        )
        # Body
        draw.rounded_rectangle(
            [cx - 2 * unit, cy - 1.5 * unit, cx + 2 * unit, cy + unit],
            radius=unit // 3, fill=color, outline=outline, width=lw,
        )
        # Cab
        draw.rectangle([cx, cy - 2.5 * unit, cx + 2 * unit, cy - 1 * unit],
                       fill=_lighter(color, 30), outline=outline, width=lw)
        # Boom
        draw.line([cx - unit, cy - 1 * unit, cx - 3 * unit, cy - 4 * unit],
                  fill=color, width=lw * 3)
        # Arm
        draw.line([cx - 3 * unit, cy - 4 * unit, cx - 4.5 * unit, cy - 2 * unit],
                  fill=color, width=lw * 3)
        # Bucket
        draw.polygon([
            (cx - 4.5 * unit, cy - 2 * unit),
            (cx - 5 * unit, cy - 1 * unit),
            (cx - 4 * unit, cy - 0.5 * unit),
            (cx - 3.5 * unit, cy - 1.5 * unit),
        ], fill=(150, 150, 150), outline=_darker((150, 150, 150)), width=lw)

    def _draw_cement_mixer(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                           unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a cement mixer truck."""
        # Cab
        draw.rounded_rectangle(
            [cx + 1.5 * unit, cy - 1.5 * unit, cx + 4 * unit, cy + 1.5 * unit],
            radius=unit // 3, fill=_lighter(color, 40), outline=outline, width=lw,
        )
        # Cab window
        draw.rectangle([cx + 2 * unit, cy - 1 * unit, cx + 3.5 * unit, cy],
                       fill=(180, 220, 255), outline=outline, width=max(1, lw // 2))
        # Mixer drum (ellipse)
        draw.ellipse([cx - 4 * unit, cy - 2.5 * unit, cx + 2 * unit, cy + 1.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Drum stripes
        for i in range(-2, 2):
            x = cx + i * unit
            draw.line([x, cy - 2 * unit, x - 0.5 * unit, cy + unit],
                      fill=_lighter(color, 40), width=max(1, lw))
        # Wheels
        wheel_r = int(0.7 * unit)
        self._draw_wheel(draw, int(cx - 2 * unit), int(cy + 1.5 * unit), wheel_r, lw)
        self._draw_wheel(draw, int(cx + 3 * unit), int(cy + 1.5 * unit), wheel_r, lw)

    def _draw_garbage_truck(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                            unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a garbage truck."""
        # Compactor body
        draw.rounded_rectangle(
            [cx - 4 * unit, cy - 2 * unit, cx + unit, cy + 1.5 * unit],
            radius=unit // 3, fill=color, outline=outline, width=lw,
        )
        # Cab
        draw.rounded_rectangle(
            [cx + 1.5 * unit, cy - 1.5 * unit, cx + 4 * unit, cy + 1.5 * unit],
            radius=unit // 3, fill=_lighter(color, 40), outline=outline, width=lw,
        )
        # Cab window
        draw.rectangle([cx + 2 * unit, cy - 1 * unit, cx + 3.5 * unit, cy],
                       fill=(180, 220, 255), outline=outline, width=max(1, lw // 2))
        # Loading mechanism at back
        draw.rectangle([cx - 4.5 * unit, cy - 0.5 * unit, cx - 4 * unit, cy + 1.5 * unit],
                       fill=_darker(color, 30), outline=outline, width=lw)
        # Wheels
        wheel_r = int(0.7 * unit)
        self._draw_wheel(draw, int(cx - 2 * unit), int(cy + 1.5 * unit), wheel_r, lw)
        self._draw_wheel(draw, int(cx + 3 * unit), int(cy + 1.5 * unit), wheel_r, lw)

    def _draw_tow_truck(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                        unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a tow truck."""
        # Flatbed
        draw.rectangle([cx - 4 * unit, cy, cx + unit, cy + 1.5 * unit],
                       fill=_darker(color, 20), outline=outline, width=lw)
        # Cab
        draw.rounded_rectangle(
            [cx + 1.5 * unit, cy - 2 * unit, cx + 4 * unit, cy + 1.5 * unit],
            radius=unit // 3, fill=color, outline=outline, width=lw,
        )
        # Cab window
        draw.rectangle([cx + 2 * unit, cy - 1.5 * unit, cx + 3.5 * unit, cy - 0.3 * unit],
                       fill=(180, 220, 255), outline=outline, width=max(1, lw // 2))
        # Tow arm
        draw.line([cx - 2 * unit, cy, cx - 3 * unit, cy - 3 * unit],
                  fill=outline, width=lw * 2)
        draw.line([cx - 3 * unit, cy - 3 * unit, cx - 4 * unit, cy - 2 * unit],
                  fill=outline, width=lw * 2)
        # Hook
        draw.arc([cx - 4.5 * unit, cy - 2.5 * unit, cx - 3.5 * unit, cy - 1.5 * unit],
                 0, 180, fill=(100, 100, 100), width=lw * 2)
        # Wheels
        wheel_r = int(0.8 * unit)
        self._draw_wheel(draw, int(cx - 2 * unit), int(cy + 1.5 * unit), wheel_r, lw)
        self._draw_wheel(draw, int(cx + 3 * unit), int(cy + 1.5 * unit), wheel_r, lw)

    def _draw_traffic_light(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                            unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a traffic light."""
        # Pole
        draw.rectangle([cx - 0.4 * unit, cy + unit, cx + 0.4 * unit, cy + 4 * unit],
                       fill=(100, 100, 100), outline=outline, width=lw)
        # Base
        draw.rounded_rectangle(
            [cx - 1.5 * unit, cy + 3.5 * unit, cx + 1.5 * unit, cy + 4.5 * unit],
            radius=unit // 4, fill=(100, 100, 100), outline=outline, width=lw,
        )
        # Housing
        draw.rounded_rectangle(
            [cx - 1.2 * unit, cy - 3.5 * unit, cx + 1.2 * unit, cy + 1.2 * unit],
            radius=unit // 3, fill=color, outline=outline, width=lw,
        )
        # Red light
        light_r = int(0.6 * unit)
        draw.ellipse([cx - light_r, cy - 3 * unit, cx + light_r, cy - 3 * unit + 2 * light_r],
                     fill=(255, 50, 50), outline=outline, width=lw)
        # Yellow light
        draw.ellipse([cx - light_r, cy - 1.3 * unit, cx + light_r, cy - 1.3 * unit + 2 * light_r],
                     fill=(255, 220, 50), outline=outline, width=lw)
        # Green light
        draw.ellipse([cx - light_r, cy + 0.3 * unit, cx + light_r, cy + 0.3 * unit + 2 * light_r],
                     fill=(50, 220, 50), outline=outline, width=lw)

    # ──────────────────────────────────────────────────────────────
    # Animal drawing helpers
    # ──────────────────────────────────────────────────────────────

    def _draw_eyes(self, draw: ImageDraw.ImageDraw, x: int, y: int,
                   spacing: int, size: int, lw: int) -> None:
        """Draw a pair of cute cartoon eyes."""
        for dx in [-spacing, spacing]:
            # White
            draw.ellipse([x + dx - size, y - size, x + dx + size, y + size],
                         fill=(255, 255, 255), outline=(0, 0, 0), width=max(1, lw))
            # Pupil
            ps = size // 2
            draw.ellipse([x + dx - ps, y - ps, x + dx + ps, y + ps],
                         fill=(0, 0, 0))

    def _draw_cat(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                  unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a cat."""
        # Body (oval)
        draw.ellipse([cx - 2.5 * unit, cy - unit, cx + 2.5 * unit, cy + 3 * unit],
                     fill=color, outline=outline, width=lw)
        # Head (circle)
        head_r = int(1.8 * unit)
        head_y = cy - 1.5 * unit
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Ears (triangles)
        ear_size = int(1.2 * unit)
        for dx in [-1, 1]:
            ear_x = cx + dx * int(1.2 * unit)
            draw.polygon([
                (ear_x, head_y - head_r - ear_size),
                (ear_x - int(0.6 * unit), head_y - head_r + int(0.3 * unit)),
                (ear_x + int(0.6 * unit), head_y - head_r + int(0.3 * unit)),
            ], fill=color, outline=outline, width=lw)
            # Inner ear
            draw.polygon([
                (ear_x, head_y - head_r - ear_size + int(0.3 * unit)),
                (ear_x - int(0.3 * unit), head_y - head_r + int(0.2 * unit)),
                (ear_x + int(0.3 * unit), head_y - head_r + int(0.2 * unit)),
            ], fill=(255, 180, 180))
        # Eyes
        self._draw_eyes(draw, cx, int(head_y - 0.2 * unit), int(0.7 * unit), int(0.35 * unit), lw)
        # Nose (triangle)
        draw.polygon([
            (cx, int(head_y + 0.3 * unit)),
            (cx - int(0.25 * unit), int(head_y + 0.6 * unit)),
            (cx + int(0.25 * unit), int(head_y + 0.6 * unit)),
        ], fill=(255, 130, 130))
        # Whiskers
        for dy in [0, int(0.3 * unit)]:
            draw.line([cx - int(0.3 * unit), int(head_y + 0.5 * unit + dy),
                       cx - int(1.5 * unit), int(head_y + 0.3 * unit + dy)],
                      fill=outline, width=max(1, lw))
            draw.line([cx + int(0.3 * unit), int(head_y + 0.5 * unit + dy),
                       cx + int(1.5 * unit), int(head_y + 0.3 * unit + dy)],
                      fill=outline, width=max(1, lw))
        # Tail
        draw.arc([cx + unit, cy, cx + 4 * unit, cy + 3 * unit],
                 180, 360, fill=color, width=lw * 3)
        draw.arc([cx + unit, cy, cx + 4 * unit, cy + 3 * unit],
                 180, 360, fill=outline, width=lw)

    def _draw_dog(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                  unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a dog."""
        # Body
        draw.ellipse([cx - 2.5 * unit, cy - unit, cx + 2.5 * unit, cy + 3 * unit],
                     fill=color, outline=outline, width=lw)
        # Head
        head_r = int(1.8 * unit)
        head_y = cy - 1.5 * unit
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Floppy ears
        for dx in [-1, 1]:
            ear_x = cx + dx * int(1.5 * unit)
            draw.ellipse([ear_x - int(0.6 * unit), head_y - int(0.5 * unit),
                          ear_x + int(0.6 * unit), head_y + int(1.5 * unit)],
                         fill=_darker(color, 30), outline=outline, width=lw)
        # Eyes
        self._draw_eyes(draw, cx, int(head_y - 0.2 * unit), int(0.7 * unit), int(0.35 * unit), lw)
        # Nose
        draw.ellipse([cx - int(0.3 * unit), int(head_y + 0.4 * unit),
                      cx + int(0.3 * unit), int(head_y + 0.8 * unit)],
                     fill=(30, 30, 30))
        # Tongue
        draw.ellipse([cx - int(0.2 * unit), int(head_y + 0.8 * unit),
                      cx + int(0.2 * unit), int(head_y + 1.3 * unit)],
                     fill=(255, 130, 130), outline=(200, 80, 80), width=max(1, lw))
        # Tail (wagging arc)
        draw.arc([cx + unit, cy - unit, cx + 4 * unit, cy + 2 * unit],
                 220, 340, fill=color, width=lw * 3)

    def _draw_bird(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                   unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a bird."""
        # Body
        draw.ellipse([cx - 2 * unit, cy - unit, cx + 2 * unit, cy + 2 * unit],
                     fill=color, outline=outline, width=lw)
        # Head
        head_r = int(1.2 * unit)
        head_y = cy - 1.5 * unit
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Eye
        self._draw_eyes(draw, cx, int(head_y), int(0.4 * unit), int(0.25 * unit), lw)
        # Beak
        draw.polygon([
            (cx + head_r - int(0.2 * unit), head_y),
            (cx + head_r + int(unit), int(head_y + 0.3 * unit)),
            (cx + head_r - int(0.2 * unit), int(head_y + 0.5 * unit)),
        ], fill=(255, 140, 0), outline=_darker((255, 140, 0)), width=lw)
        # Wing
        draw.ellipse([cx - int(1.5 * unit), cy - int(0.5 * unit),
                      cx + int(1.5 * unit), cy + int(1.5 * unit)],
                     fill=_darker(color, 20), outline=outline, width=lw)
        # Tail feathers
        for dy in [-0.3, 0, 0.3]:
            draw.polygon([
                (cx - 2 * unit, int(cy + 0.5 * unit + dy * unit)),
                (cx - 3.5 * unit, int(cy - unit + dy * unit)),
                (cx - 2 * unit, int(cy + dy * unit)),
            ], fill=_darker(color, 15), outline=outline, width=max(1, lw))
        # Legs
        for dx in [-0.5, 0.5]:
            lx = cx + int(dx * unit)
            draw.line([lx, cy + 2 * unit, lx, cy + 3 * unit],
                      fill=(200, 140, 0), width=lw)
            # Toes
            draw.line([lx - int(0.3 * unit), cy + 3 * unit, lx + int(0.3 * unit), cy + 3 * unit],
                      fill=(200, 140, 0), width=lw)

    def _draw_elephant(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                       unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw an elephant."""
        # Body
        draw.ellipse([cx - 3 * unit, cy - 1.5 * unit, cx + 3 * unit, cy + 2.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Head
        head_r = int(2 * unit)
        head_x = cx + int(2 * unit)
        head_y = cy - unit
        draw.ellipse([head_x - head_r, head_y - head_r, head_x + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Ears
        ear_r = int(1.5 * unit)
        draw.ellipse([head_x + int(0.5 * unit), head_y - int(1.5 * unit),
                      head_x + int(0.5 * unit) + 2 * ear_r, head_y + int(1 * unit)],
                     fill=_lighter(color, 20), outline=outline, width=lw)
        # Trunk
        draw.arc([head_x - int(0.5 * unit), head_y, head_x + int(1.5 * unit), head_y + 4 * unit],
                 180, 360, fill=color, width=lw * 4)
        draw.arc([head_x - int(0.5 * unit), head_y, head_x + int(1.5 * unit), head_y + 4 * unit],
                 180, 360, fill=outline, width=lw)
        # Eye
        eye_x = head_x - int(0.3 * unit)
        eye_y = head_y - int(0.3 * unit)
        draw.ellipse([eye_x - int(0.3 * unit), eye_y - int(0.3 * unit),
                      eye_x + int(0.3 * unit), eye_y + int(0.3 * unit)],
                     fill=(255, 255, 255), outline=(0, 0, 0), width=lw)
        draw.ellipse([eye_x - int(0.15 * unit), eye_y - int(0.15 * unit),
                      eye_x + int(0.15 * unit), eye_y + int(0.15 * unit)],
                     fill=(0, 0, 0))
        # Legs
        for lx in [-2, -0.5, 1, 2.5]:
            x = cx + int(lx * unit)
            draw.rectangle([x - int(0.5 * unit), cy + 2 * unit, x + int(0.5 * unit), cy + 3.5 * unit],
                           fill=color, outline=outline, width=lw)
        # Tail
        draw.line([cx - 3 * unit, cy, cx - 4 * unit, cy - unit], fill=outline, width=lw * 2)

    def _draw_lion(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                   unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a lion."""
        # Body
        draw.ellipse([cx - 2.5 * unit, cy, cx + 2.5 * unit, cy + 3 * unit],
                     fill=color, outline=outline, width=lw)
        # Mane (large circle behind head)
        mane_r = int(2.5 * unit)
        head_y = cy - unit
        draw.ellipse([cx - mane_r, head_y - mane_r, cx + mane_r, head_y + mane_r],
                     fill=_darker(color, 30), outline=outline, width=lw)
        # Head
        head_r = int(1.8 * unit)
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Eyes
        self._draw_eyes(draw, cx, int(head_y - 0.2 * unit), int(0.6 * unit), int(0.3 * unit), lw)
        # Nose
        draw.polygon([
            (cx, int(head_y + 0.3 * unit)),
            (cx - int(0.3 * unit), int(head_y + 0.7 * unit)),
            (cx + int(0.3 * unit), int(head_y + 0.7 * unit)),
        ], fill=(80, 50, 30))
        # Mouth
        draw.arc([cx - int(0.3 * unit), int(head_y + 0.5 * unit),
                  cx + int(0.3 * unit), int(head_y + 1 * unit)],
                 0, 180, fill=outline, width=max(1, lw))
        # Legs
        for lx in [-1.5, 1.5]:
            x = cx + int(lx * unit)
            draw.rectangle([x - int(0.4 * unit), cy + 2.5 * unit, x + int(0.4 * unit), cy + 4 * unit],
                           fill=color, outline=outline, width=lw)
        # Tail with tuft
        draw.arc([cx + unit, cy, cx + 4 * unit, cy + 2 * unit],
                 200, 340, fill=color, width=lw * 3)
        draw.ellipse([cx + 3.5 * unit, cy - int(0.3 * unit),
                      cx + 4.5 * unit, cy + int(0.5 * unit)],
                     fill=_darker(color, 30), outline=outline, width=lw)

    def _draw_giraffe(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                      unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a giraffe."""
        # Body
        draw.ellipse([cx - 2 * unit, cy + unit, cx + 2 * unit, cy + 3.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Neck
        draw.rectangle([cx - int(0.6 * unit), cy - 3 * unit, cx + int(0.6 * unit), cy + 2 * unit],
                       fill=color, outline=outline, width=lw)
        # Head
        head_r = int(1.2 * unit)
        head_y = cy - 3.5 * unit
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Horns
        for dx in [-0.5, 0.5]:
            hx = cx + int(dx * unit)
            draw.line([hx, head_y - head_r, hx, head_y - head_r - int(0.8 * unit)],
                      fill=outline, width=lw * 2)
            draw.ellipse([hx - int(0.15 * unit), head_y - head_r - unit,
                          hx + int(0.15 * unit), head_y - head_r - int(0.7 * unit)],
                         fill=_darker(color, 40))
        # Eyes
        self._draw_eyes(draw, cx, int(head_y), int(0.5 * unit), int(0.25 * unit), lw)
        # Spots on neck
        spot_color = _darker(color, 50)
        for sy in range(-2, 2):
            for sx in [-0.3, 0.3]:
                spot_x = cx + int(sx * unit)
                spot_y = cy + int(sy * unit) - unit
                draw.ellipse([spot_x - int(0.2 * unit), spot_y - int(0.2 * unit),
                              spot_x + int(0.2 * unit), spot_y + int(0.2 * unit)],
                             fill=spot_color)
        # Legs
        for lx in [-1.2, 1.2]:
            x = cx + int(lx * unit)
            draw.rectangle([x - int(0.3 * unit), cy + 3 * unit, x + int(0.3 * unit), cy + 4.5 * unit],
                           fill=color, outline=outline, width=lw)

    def _draw_fish(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                   unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a fish."""
        # Body (oval)
        draw.ellipse([cx - 3 * unit, cy - 1.5 * unit, cx + 2 * unit, cy + 1.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Tail
        draw.polygon([
            (cx - 2.5 * unit, cy),
            (cx - 4 * unit, cy - 2 * unit),
            (cx - 4 * unit, cy + 2 * unit),
        ], fill=_darker(color, 20), outline=outline, width=lw)
        # Fin on top
        draw.polygon([
            (cx - unit, cy - 1.5 * unit),
            (cx - 0.5 * unit, cy - 3 * unit),
            (cx + unit, cy - 1.5 * unit),
        ], fill=_lighter(color, 30), outline=outline, width=lw)
        # Eye
        eye_x = cx + int(0.8 * unit)
        self._draw_eyes(draw, eye_x, cy, 0, int(0.4 * unit), lw)
        # Mouth
        draw.arc([cx + int(1.5 * unit), cy - int(0.3 * unit),
                  cx + int(2.5 * unit), cy + int(0.5 * unit)],
                 140, 220, fill=outline, width=lw * 2)
        # Scales (arcs)
        scale_color = _lighter(color, 20)
        for sx in range(-2, 1):
            for sy in [-0.5, 0.5]:
                draw.arc([cx + int(sx * unit), int(cy + sy * unit - 0.3 * unit),
                          cx + int((sx + 1) * unit), int(cy + sy * unit + 0.3 * unit)],
                         0, 180, fill=scale_color, width=max(1, lw))

    def _draw_butterfly(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                        unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a butterfly."""
        # Upper wings
        for dx in [-1, 1]:
            wing_cx = cx + dx * int(2.2 * unit)
            draw.ellipse([wing_cx - int(2 * unit), cy - 3 * unit,
                          wing_cx + int(2 * unit), cy + int(0.5 * unit)],
                         fill=color, outline=outline, width=lw)
            # Wing pattern
            draw.ellipse([wing_cx - int(0.8 * unit), cy - int(2 * unit),
                          wing_cx + int(0.8 * unit), cy - int(0.5 * unit)],
                         fill=_lighter(color, 40), outline=outline, width=max(1, lw))
        # Lower wings
        for dx in [-1, 1]:
            wing_cx = cx + dx * int(1.8 * unit)
            draw.ellipse([wing_cx - int(1.5 * unit), cy - int(0.5 * unit),
                          wing_cx + int(1.5 * unit), cy + 2.5 * unit],
                         fill=_lighter(color, 20), outline=outline, width=lw)
        # Body
        draw.ellipse([cx - int(0.3 * unit), cy - 2 * unit, cx + int(0.3 * unit), cy + 2 * unit],
                     fill=(60, 40, 20), outline=outline, width=lw)
        # Head
        draw.ellipse([cx - int(0.4 * unit), cy - 2.7 * unit, cx + int(0.4 * unit), cy - 1.8 * unit],
                     fill=(60, 40, 20), outline=outline, width=lw)
        # Antennae
        for dx in [-1, 1]:
            draw.line([cx, cy - 2.7 * unit,
                       cx + dx * int(1.2 * unit), cy - 3.8 * unit],
                      fill=outline, width=lw)
            draw.ellipse([cx + dx * int(1.2 * unit) - int(0.15 * unit), cy - 4 * unit,
                          cx + dx * int(1.2 * unit) + int(0.15 * unit), cy - 3.7 * unit],
                         fill=outline)

    def _draw_rabbit(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                     unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a rabbit."""
        # Body
        draw.ellipse([cx - 2 * unit, cy, cx + 2 * unit, cy + 3 * unit],
                     fill=color, outline=outline, width=lw)
        # Head
        head_r = int(1.5 * unit)
        head_y = cy - unit
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Long ears
        for dx in [-0.6, 0.6]:
            ear_x = cx + int(dx * unit)
            draw.ellipse([ear_x - int(0.4 * unit), head_y - head_r - int(2.5 * unit),
                          ear_x + int(0.4 * unit), head_y - head_r + int(0.5 * unit)],
                         fill=color, outline=outline, width=lw)
            # Inner ear
            draw.ellipse([ear_x - int(0.2 * unit), head_y - head_r - int(2 * unit),
                          ear_x + int(0.2 * unit), head_y - head_r],
                         fill=(255, 200, 200))
        # Eyes
        self._draw_eyes(draw, cx, int(head_y - 0.2 * unit), int(0.5 * unit), int(0.25 * unit), lw)
        # Nose
        draw.polygon([
            (cx, int(head_y + 0.3 * unit)),
            (cx - int(0.2 * unit), int(head_y + 0.55 * unit)),
            (cx + int(0.2 * unit), int(head_y + 0.55 * unit)),
        ], fill=(255, 150, 150))
        # Whiskers
        for dy in [0, int(0.2 * unit)]:
            for dx_sign in [-1, 1]:
                draw.line([cx + dx_sign * int(0.3 * unit), int(head_y + 0.5 * unit + dy),
                           cx + dx_sign * int(1.5 * unit), int(head_y + 0.4 * unit + dy)],
                          fill=outline, width=max(1, lw))
        # Fluffy tail
        draw.ellipse([cx + int(1.5 * unit), cy + int(1.5 * unit),
                      cx + int(2.5 * unit), cy + int(2.5 * unit)],
                     fill=(255, 255, 255), outline=outline, width=lw)

    def _draw_turtle(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                     unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a turtle."""
        # Shell (dome shape)
        draw.ellipse([cx - 2.5 * unit, cy - 2 * unit, cx + 2.5 * unit, cy + 2 * unit],
                     fill=color, outline=outline, width=lw)
        # Shell pattern (hexagonal segments)
        pattern_color = _darker(color, 30)
        draw.ellipse([cx - int(1.2 * unit), cy - int(1 * unit), cx + int(1.2 * unit), cy + int(1 * unit)],
                     fill=_lighter(color, 15), outline=pattern_color, width=max(1, lw))
        # Shell rim patterns
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            px = cx + int(1.6 * unit * math.cos(rad))
            py = cy + int(1.3 * unit * math.sin(rad))
            draw.ellipse([px - int(0.4 * unit), py - int(0.3 * unit),
                          px + int(0.4 * unit), py + int(0.3 * unit)],
                         fill=_lighter(color, 15), outline=pattern_color, width=max(1, lw))
        # Head
        head_r = int(0.8 * unit)
        head_x = cx + int(3 * unit)
        draw.ellipse([head_x - head_r, cy - head_r, head_x + head_r, cy + head_r],
                     fill=_lighter(color, 30), outline=outline, width=lw)
        # Eye
        draw.ellipse([head_x + int(0.1 * unit), cy - int(0.3 * unit),
                      head_x + int(0.4 * unit), cy],
                     fill=(255, 255, 255), outline=(0, 0, 0), width=max(1, lw))
        draw.ellipse([head_x + int(0.2 * unit), cy - int(0.2 * unit),
                      head_x + int(0.35 * unit), cy - int(0.05 * unit)],
                     fill=(0, 0, 0))
        # Legs
        for pos in [(-2, 1.5), (-1, 1.8), (1, 1.8), (2, 1.5)]:
            lx = cx + int(pos[0] * unit)
            ly = cy + int(pos[1] * unit)
            draw.ellipse([lx - int(0.4 * unit), ly - int(0.3 * unit),
                          lx + int(0.4 * unit), ly + int(0.3 * unit)],
                         fill=_lighter(color, 30), outline=outline, width=lw)
        # Tail
        draw.polygon([
            (cx - 2.5 * unit, cy),
            (cx - 3.2 * unit, cy - int(0.2 * unit)),
            (cx - 3.2 * unit, cy + int(0.2 * unit)),
        ], fill=_lighter(color, 30), outline=outline, width=lw)

    def _draw_horse(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                    unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a horse."""
        # Body
        draw.ellipse([cx - 3 * unit, cy - unit, cx + 2 * unit, cy + 2.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Neck
        draw.polygon([
            (cx + unit, cy - unit),
            (cx + 2 * unit, cy - 3 * unit),
            (cx + 3 * unit, cy - 3 * unit),
            (cx + 2.5 * unit, cy),
        ], fill=color, outline=outline, width=lw)
        # Head
        head_r = int(1.2 * unit)
        head_x = cx + int(3 * unit)
        head_y = cy - int(3 * unit)
        draw.ellipse([head_x - head_r, head_y - head_r, head_x + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Ears
        for dx in [-0.3, 0.3]:
            ear_x = head_x + int(dx * unit)
            draw.polygon([
                (ear_x, head_y - head_r),
                (ear_x - int(0.2 * unit), head_y - head_r - int(0.8 * unit)),
                (ear_x + int(0.2 * unit), head_y - head_r - int(0.8 * unit)),
            ], fill=color, outline=outline, width=lw)
        # Eye
        draw.ellipse([head_x + int(0.2 * unit), head_y - int(0.3 * unit),
                      head_x + int(0.6 * unit), head_y + int(0.1 * unit)],
                     fill=(255, 255, 255), outline=(0, 0, 0), width=lw)
        draw.ellipse([head_x + int(0.3 * unit), head_y - int(0.2 * unit),
                      head_x + int(0.5 * unit), head_y],
                     fill=(0, 0, 0))
        # Mane
        for my in range(-3, 0):
            mx = cx + int(2 * unit) + int(0.3 * my * unit)
            draw.ellipse([mx - int(0.3 * unit), cy + int(my * unit) - int(0.5 * unit),
                          mx + int(0.5 * unit), cy + int(my * unit) + int(0.3 * unit)],
                         fill=_darker(color, 40))
        # Legs
        for lx_pos in [-2, -0.5, 0.5, 1.5]:
            x = cx + int(lx_pos * unit)
            draw.rectangle([x - int(0.3 * unit), cy + 2 * unit, x + int(0.3 * unit), cy + 4 * unit],
                           fill=color, outline=outline, width=lw)
            # Hooves
            draw.rectangle([x - int(0.35 * unit), cy + int(3.7 * unit),
                            x + int(0.35 * unit), cy + 4 * unit],
                           fill=(50, 40, 30), outline=outline, width=max(1, lw))
        # Tail
        draw.arc([cx - 4 * unit, cy - unit, cx - 2 * unit, cy + 2 * unit],
                 150, 330, fill=_darker(color, 40), width=lw * 3)

    def _draw_cow(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                  unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a cow."""
        # Body
        draw.ellipse([cx - 3 * unit, cy - unit, cx + 2 * unit, cy + 2.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Spots
        for pos in [(-1.5, 0), (0.5, 0.5), (-0.5, 1.5)]:
            sx = cx + int(pos[0] * unit)
            sy = cy + int(pos[1] * unit)
            draw.ellipse([sx - int(0.6 * unit), sy - int(0.5 * unit),
                          sx + int(0.6 * unit), sy + int(0.5 * unit)],
                         fill=(60, 60, 60))
        # Head
        head_r = int(1.5 * unit)
        head_x = cx + int(2.5 * unit)
        head_y = cy - int(0.5 * unit)
        draw.ellipse([head_x - head_r, head_y - head_r, head_x + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Horns
        for dx in [-0.5, 0.5]:
            hx = head_x + int(dx * unit)
            draw.polygon([
                (hx, head_y - head_r),
                (hx - int(0.15 * unit), head_y - head_r - int(0.8 * unit)),
                (hx + int(0.15 * unit), head_y - head_r - int(0.8 * unit)),
            ], fill=(220, 200, 150), outline=outline, width=lw)
        # Eyes
        self._draw_eyes(draw, head_x, int(head_y - 0.2 * unit), int(0.5 * unit), int(0.25 * unit), lw)
        # Nose/muzzle
        draw.ellipse([head_x - int(0.6 * unit), head_y + int(0.3 * unit),
                      head_x + int(0.6 * unit), head_y + int(1 * unit)],
                     fill=(255, 200, 180), outline=outline, width=lw)
        # Nostrils
        for ndx in [-0.2, 0.2]:
            draw.ellipse([head_x + int(ndx * unit) - int(0.1 * unit),
                          head_y + int(0.5 * unit),
                          head_x + int(ndx * unit) + int(0.1 * unit),
                          head_y + int(0.7 * unit)],
                         fill=(60, 40, 30))
        # Legs
        for lx_pos in [-2, -0.5, 0.5, 1.5]:
            x = cx + int(lx_pos * unit)
            draw.rectangle([x - int(0.3 * unit), cy + 2 * unit, x + int(0.3 * unit), cy + 3.5 * unit],
                           fill=color, outline=outline, width=lw)

    def _draw_pig(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                  unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a pig."""
        # Body
        draw.ellipse([cx - 2.5 * unit, cy - unit, cx + 2.5 * unit, cy + 2.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Head
        head_r = int(1.5 * unit)
        head_y = cy - unit
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Ears
        for dx in [-1, 1]:
            ear_x = cx + dx * int(1 * unit)
            draw.polygon([
                (ear_x, head_y - head_r + int(0.2 * unit)),
                (ear_x - dx * int(0.3 * unit), head_y - head_r - int(0.8 * unit)),
                (ear_x + dx * int(0.5 * unit), head_y - head_r - int(0.3 * unit)),
            ], fill=_darker(color, 20), outline=outline, width=lw)
        # Eyes
        self._draw_eyes(draw, cx, int(head_y - 0.2 * unit), int(0.5 * unit), int(0.25 * unit), lw)
        # Snout
        draw.ellipse([cx - int(0.6 * unit), head_y + int(0.2 * unit),
                      cx + int(0.6 * unit), head_y + int(0.8 * unit)],
                     fill=_darker(color, 15), outline=outline, width=lw)
        # Nostrils
        for ndx in [-0.2, 0.2]:
            draw.ellipse([cx + int(ndx * unit) - int(0.1 * unit),
                          head_y + int(0.4 * unit),
                          cx + int(ndx * unit) + int(0.1 * unit),
                          head_y + int(0.6 * unit)],
                         fill=_darker(color, 40))
        # Legs
        for lx in [-1.5, -0.5, 0.5, 1.5]:
            x = cx + int(lx * unit)
            draw.rectangle([x - int(0.3 * unit), cy + 2 * unit, x + int(0.3 * unit), cy + 3 * unit],
                           fill=color, outline=outline, width=lw)
        # Curly tail
        draw.arc([cx + 2 * unit, cy - int(0.5 * unit), cx + 3.5 * unit, cy + unit],
                 0, 270, fill=_darker(color, 20), width=lw * 2)

    def _draw_chicken(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                      unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a chicken."""
        # Body
        draw.ellipse([cx - 2 * unit, cy - unit, cx + 2 * unit, cy + 2.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Wing
        draw.ellipse([cx - unit, cy - int(0.5 * unit), cx + int(1.5 * unit), cy + int(1.5 * unit)],
                     fill=_darker(color, 15), outline=outline, width=lw)
        # Head
        head_r = int(1 * unit)
        head_y = cy - 1.5 * unit
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Comb
        for dx in [-0.3, 0, 0.3]:
            comb_x = cx + int(dx * unit)
            draw.ellipse([comb_x - int(0.2 * unit), head_y - head_r - int(0.5 * unit),
                          comb_x + int(0.2 * unit), head_y - head_r + int(0.2 * unit)],
                         fill=(255, 50, 50), outline=(200, 30, 30), width=max(1, lw))
        # Eye
        self._draw_eyes(draw, cx, int(head_y), int(0.3 * unit), int(0.2 * unit), lw)
        # Beak
        draw.polygon([
            (cx + head_r - int(0.2 * unit), head_y + int(0.1 * unit)),
            (cx + head_r + int(0.6 * unit), head_y + int(0.3 * unit)),
            (cx + head_r - int(0.2 * unit), head_y + int(0.5 * unit)),
        ], fill=(255, 180, 0), outline=_darker((255, 180, 0)), width=lw)
        # Wattle
        draw.ellipse([cx + int(0.3 * unit), head_y + int(0.5 * unit),
                      cx + int(0.6 * unit), head_y + int(1 * unit)],
                     fill=(255, 50, 50), outline=(200, 30, 30), width=max(1, lw))
        # Legs
        for dx in [-0.5, 0.5]:
            lx = cx + int(dx * unit)
            draw.line([lx, cy + 2.5 * unit, lx, cy + 3.5 * unit],
                      fill=(200, 160, 0), width=lw * 2)
            draw.line([lx - int(0.3 * unit), cy + 3.5 * unit,
                       lx + int(0.3 * unit), cy + 3.5 * unit],
                      fill=(200, 160, 0), width=lw)
        # Tail feathers
        for angle_offset in [-15, 0, 15]:
            rad = math.radians(160 + angle_offset)
            tx = cx - 2 * unit + int(1.5 * unit * math.cos(rad))
            ty = cy + int(1 * unit * math.sin(rad))
            draw.polygon([
                (cx - 2 * unit, cy + int(0.5 * unit)),
                (tx, ty),
                (cx - int(1.8 * unit), cy + int(0.8 * unit)),
            ], fill=_darker(color, 20), outline=outline, width=max(1, lw))

    def _draw_duck(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                   unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a duck."""
        # Body
        draw.ellipse([cx - 2.5 * unit, cy - unit, cx + 2 * unit, cy + 2.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Head
        head_r = int(1.2 * unit)
        head_x = cx + int(1.5 * unit)
        head_y = cy - int(1.5 * unit)
        draw.ellipse([head_x - head_r, head_y - head_r, head_x + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Eye
        self._draw_eyes(draw, head_x, int(head_y - 0.2 * unit), int(0.3 * unit), int(0.2 * unit), lw)
        # Bill
        draw.polygon([
            (head_x + head_r - int(0.3 * unit), head_y + int(0.1 * unit)),
            (head_x + head_r + int(unit), head_y + int(0.2 * unit)),
            (head_x + head_r + int(unit), head_y + int(0.6 * unit)),
            (head_x + head_r - int(0.3 * unit), head_y + int(0.5 * unit)),
        ], fill=(255, 160, 0), outline=_darker((255, 160, 0)), width=lw)
        # Wing
        draw.ellipse([cx - int(1.5 * unit), cy - int(0.5 * unit),
                      cx + int(1.5 * unit), cy + int(1.5 * unit)],
                     fill=_darker(color, 15), outline=outline, width=lw)
        # Tail
        draw.polygon([
            (cx - 2.5 * unit, cy + unit),
            (cx - 3.5 * unit, cy - int(0.5 * unit)),
            (cx - 3 * unit, cy + int(1.2 * unit)),
        ], fill=_darker(color, 20), outline=outline, width=lw)

    def _draw_frog(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                   unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a frog."""
        # Body
        draw.ellipse([cx - 2.5 * unit, cy - unit, cx + 2.5 * unit, cy + 2 * unit],
                     fill=color, outline=outline, width=lw)
        # Belly
        draw.ellipse([cx - int(1.5 * unit), cy - int(0.3 * unit),
                      cx + int(1.5 * unit), cy + int(1.5 * unit)],
                     fill=_lighter(color, 50), outline=outline, width=max(1, lw))
        # Head
        head_r = int(1.5 * unit)
        head_y = cy - int(1.5 * unit)
        draw.ellipse([cx - head_r, head_y - int(0.8 * head_r), cx + head_r, head_y + int(0.8 * head_r)],
                     fill=color, outline=outline, width=lw)
        # Bulging eyes
        for dx in [-1, 1]:
            eye_x = cx + dx * int(0.8 * unit)
            eye_y = head_y - int(0.5 * unit)
            eye_r = int(0.5 * unit)
            draw.ellipse([eye_x - eye_r, eye_y - eye_r, eye_x + eye_r, eye_y + eye_r],
                         fill=(255, 255, 255), outline=outline, width=lw)
            draw.ellipse([eye_x - int(0.2 * unit), eye_y - int(0.2 * unit),
                          eye_x + int(0.2 * unit), eye_y + int(0.2 * unit)],
                         fill=(0, 0, 0))
        # Mouth (wide smile)
        draw.arc([cx - int(0.8 * unit), head_y, cx + int(0.8 * unit), head_y + int(0.8 * unit)],
                 0, 180, fill=outline, width=lw * 2)
        # Front legs
        for dx in [-1, 1]:
            lx = cx + dx * int(2 * unit)
            draw.ellipse([lx - int(0.5 * unit), cy + int(1.5 * unit),
                          lx + int(0.5 * unit), cy + int(2 * unit)],
                         fill=color, outline=outline, width=lw)
        # Back legs (bent)
        for dx in [-1, 1]:
            lx = cx + dx * int(2.5 * unit)
            draw.ellipse([lx - int(0.8 * unit), cy + unit,
                          lx + int(0.8 * unit), cy + int(2.5 * unit)],
                         fill=color, outline=outline, width=lw)

    def _draw_bear(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                   unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a bear."""
        # Body
        draw.ellipse([cx - 2.5 * unit, cy - unit, cx + 2.5 * unit, cy + 3 * unit],
                     fill=color, outline=outline, width=lw)
        # Head
        head_r = int(1.8 * unit)
        head_y = cy - int(1.5 * unit)
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Round ears
        for dx in [-1, 1]:
            ear_x = cx + dx * int(1.3 * unit)
            ear_y = head_y - int(1.3 * unit)
            ear_r = int(0.6 * unit)
            draw.ellipse([ear_x - ear_r, ear_y - ear_r, ear_x + ear_r, ear_y + ear_r],
                         fill=color, outline=outline, width=lw)
            # Inner ear
            inner_r = int(0.35 * unit)
            draw.ellipse([ear_x - inner_r, ear_y - inner_r, ear_x + inner_r, ear_y + inner_r],
                         fill=_lighter(color, 40))
        # Eyes
        self._draw_eyes(draw, cx, int(head_y - 0.2 * unit), int(0.6 * unit), int(0.3 * unit), lw)
        # Snout area
        draw.ellipse([cx - int(0.7 * unit), head_y + int(0.2 * unit),
                      cx + int(0.7 * unit), head_y + int(1 * unit)],
                     fill=_lighter(color, 40), outline=outline, width=max(1, lw))
        # Nose
        draw.ellipse([cx - int(0.25 * unit), head_y + int(0.3 * unit),
                      cx + int(0.25 * unit), head_y + int(0.55 * unit)],
                     fill=(30, 30, 30))
        # Belly patch
        draw.ellipse([cx - int(1.5 * unit), cy + int(0.3 * unit),
                      cx + int(1.5 * unit), cy + int(2.2 * unit)],
                     fill=_lighter(color, 30), outline=outline, width=max(1, lw))
        # Arms
        for dx in [-1, 1]:
            x0 = cx + dx * int(2 * unit)
            x1 = cx + dx * int(3 * unit)
            draw.ellipse([min(x0, x1), cy - int(0.5 * unit),
                          max(x0, x1), cy + int(1.5 * unit)],
                         fill=color, outline=outline, width=lw)
        # Legs
        for dx in [-1, 1]:
            x0 = cx + dx * int(0.8 * unit)
            x1 = cx + dx * int(2 * unit)
            draw.ellipse([min(x0, x1), cy + int(2.5 * unit),
                          max(x0, x1), cy + int(3.8 * unit)],
                         fill=color, outline=outline, width=lw)

    def _draw_monkey(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                     unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a monkey."""
        # Body
        draw.ellipse([cx - 2 * unit, cy - unit, cx + 2 * unit, cy + 2.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Head
        head_r = int(1.6 * unit)
        head_y = cy - int(1.5 * unit)
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Face area (lighter)
        face_r = int(1.1 * unit)
        draw.ellipse([cx - face_r, head_y - int(0.5 * face_r), cx + face_r, head_y + face_r],
                     fill=_lighter(color, 50), outline=outline, width=max(1, lw))
        # Ears
        for dx in [-1, 1]:
            ear_x = cx + dx * int(1.5 * unit)
            ear_r = int(0.5 * unit)
            draw.ellipse([ear_x - ear_r, head_y - ear_r, ear_x + ear_r, head_y + ear_r],
                         fill=color, outline=outline, width=lw)
            # Inner ear
            inner_r = int(0.3 * unit)
            draw.ellipse([ear_x - inner_r, head_y - inner_r, ear_x + inner_r, head_y + inner_r],
                         fill=_lighter(color, 50))
        # Eyes
        self._draw_eyes(draw, cx, int(head_y - 0.1 * unit), int(0.5 * unit), int(0.25 * unit), lw)
        # Nose
        draw.ellipse([cx - int(0.15 * unit), head_y + int(0.3 * unit),
                      cx + int(0.15 * unit), head_y + int(0.5 * unit)],
                     fill=(60, 40, 30))
        # Mouth
        draw.arc([cx - int(0.4 * unit), head_y + int(0.4 * unit),
                  cx + int(0.4 * unit), head_y + int(0.8 * unit)],
                 0, 180, fill=outline, width=max(1, lw))
        # Belly
        draw.ellipse([cx - int(1.2 * unit), cy, cx + int(1.2 * unit), cy + int(2 * unit)],
                     fill=_lighter(color, 40), outline=outline, width=max(1, lw))
        # Arms
        for dx in [-1, 1]:
            draw.line([cx + dx * int(2 * unit), cy, cx + dx * int(3 * unit), cy + int(1.5 * unit)],
                      fill=color, width=lw * 3)
        # Tail (curly)
        draw.arc([cx - 3 * unit, cy, cx - unit, cy + 3 * unit],
                 90, 360, fill=color, width=lw * 3)
        draw.arc([cx - 3 * unit, cy, cx - unit, cy + 3 * unit],
                 90, 360, fill=outline, width=lw)

    def _draw_generic_animal(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                             unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a generic animal (oval body + round head)."""
        # Body
        draw.ellipse([cx - 2.5 * unit, cy, cx + 2.5 * unit, cy + 3 * unit],
                     fill=color, outline=outline, width=lw)
        # Head
        head_r = int(1.5 * unit)
        head_y = cy - unit
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Eyes
        self._draw_eyes(draw, cx, int(head_y), int(0.5 * unit), int(0.25 * unit), lw)
        # Legs
        for lx in [-1.5, -0.5, 0.5, 1.5]:
            x = cx + int(lx * unit)
            draw.rectangle([x - int(0.3 * unit), cy + 2.5 * unit,
                            x + int(0.3 * unit), cy + 3.5 * unit],
                           fill=color, outline=outline, width=lw)

    # ──────────────────────────────────────────────────────────────
    # Shared helpers
    # ──────────────────────────────────────────────────────────────

    def _draw_label(self, draw: ImageDraw.ImageDraw, name: str,
                    width: int, height: int) -> None:
        """Draw item name label at the bottom of the image."""
        display_name = name.replace("_", " ").title()
        try:
            bbox = draw.textbbox((0, 0), display_name)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (width - text_width) // 2
            text_y = height - text_height - max(8, height // 20)
            # Background for readability
            pad = 4
            draw.rounded_rectangle(
                [text_x - pad, text_y - pad, text_x + text_width + pad, text_y + text_height + pad],
                radius=4, fill=(255, 255, 255, 200),
            )
            draw.text((text_x, text_y), display_name, fill=(60, 60, 60, 255))
        except Exception:
            draw.text((width // 4, height - 20), display_name, fill=(60, 60, 60, 255))

    def _draw_star(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                   unit: int, color: tuple) -> None:
        """Draw a decorative star."""
        points = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r = unit if i % 2 == 0 else unit * 0.4
            points.append((cx + int(r * math.cos(angle)), cy + int(r * math.sin(angle))))
        draw.polygon(points, fill=color)

    # ──────────────────────────────────────────────────────────────
    # Image conversion (outline / dashed)
    # ──────────────────────────────────────────────────────────────

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
