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
    "owl": (160, 120, 80),
    "dolphin": (120, 170, 210),
    "penguin": (40, 40, 50),
    "panda": (240, 240, 240),
}

DINOSAUR_COLORS: dict[str, tuple[int, int, int]] = {
    "t_rex": (100, 160, 60),
    "triceratops": (180, 140, 80),
    "stegosaurus": (140, 180, 80),
    "brontosaurus": (120, 160, 120),
    "pterodactyl": (160, 130, 100),
    "velociraptor": (80, 140, 80),
    "ankylosaurus": (160, 150, 100),
    "spinosaurus": (60, 130, 100),
    "parasaurolophus": (100, 170, 140),
    "diplodocus": (140, 170, 130),
    "iguanodon": (120, 150, 70),
    "pachycephalosaurus": (170, 140, 100),
    "brachiosaurus": (130, 160, 100),
    "allosaurus": (130, 100, 70),
    "dimetrodon": (180, 120, 60),
    "plesiosaurus": (80, 140, 180),
    "mosasaurus": (60, 120, 160),
    "archaeopteryx": (180, 160, 100),
}

OCEAN_COLORS: dict[str, tuple[int, int, int]] = {
    "dolphin": (120, 170, 210),
    "whale": (80, 120, 170),
    "shark": (140, 150, 160),
    "octopus": (180, 80, 140),
    "seahorse": (255, 180, 60),
    "jellyfish": (200, 160, 220),
    "starfish": (255, 160, 60),
    "crab": (220, 100, 60),
    "lobster": (200, 60, 40),
    "sea_turtle": (80, 160, 100),
    "clownfish": (255, 140, 40),
    "pufferfish": (240, 220, 120),
    "manta_ray": (80, 100, 140),
    "seal": (160, 150, 140),
    "penguin": (40, 40, 50),
    "orca": (30, 30, 40),
    "narwhal": (140, 170, 200),
    "squid": (200, 120, 140),
}

SPACE_COLORS: dict[str, tuple[int, int, int]] = {
    "rocket": (220, 60, 40),
    "astronaut": (240, 240, 240),
    "planet": (60, 140, 200),
    "star": (255, 220, 60),
    "moon": (220, 220, 200),
    "sun": (255, 200, 40),
    "satellite": (180, 180, 190),
    "ufo": (120, 200, 120),
    "space_shuttle": (230, 230, 240),
    "mars_rover": (180, 140, 100),
    "telescope": (140, 100, 70),
    "comet": (200, 220, 255),
    "asteroid": (160, 140, 120),
    "space_station": (200, 200, 210),
    "lunar_module": (200, 190, 160),
    "meteor": (200, 100, 40),
    "galaxy": (120, 80, 180),
    "constellation": (200, 200, 255),
}

FOOD_COLORS: dict[str, tuple[int, int, int]] = {
    "pizza": (240, 180, 60),
    "hamburger": (180, 120, 60),
    "ice_cream": (255, 200, 220),
    "cupcake": (255, 160, 200),
    "donut": (220, 160, 100),
    "apple": (220, 40, 40),
    "banana": (255, 230, 80),
    "watermelon": (60, 180, 60),
    "cookie": (200, 160, 100),
    "cake": (255, 200, 220),
    "taco": (240, 200, 100),
    "hotdog": (200, 140, 80),
    "french_fries": (255, 220, 80),
    "lollipop": (220, 60, 160),
    "chocolate": (100, 60, 30),
    "sandwich": (220, 190, 130),
    "sushi": (240, 240, 240),
    "pancake": (230, 190, 120),
}


def _get_item_color(name: str, category: str) -> tuple[int, int, int]:
    """Get the primary color for an item."""
    if category == "vehicle":
        return VEHICLE_COLORS.get(name, (150, 150, 200))
    if category == "animal":
        # Check all animal-like color dicts
        if name in ANIMAL_COLORS:
            return ANIMAL_COLORS[name]
        if name in DINOSAUR_COLORS:
            return DINOSAUR_COLORS[name]
        if name in OCEAN_COLORS:
            return OCEAN_COLORS[name]
        return (200, 180, 150)
    if category == "science":
        return SPACE_COLORS.get(name, (140, 140, 180))
    if category == "food":
        return FOOD_COLORS.get(name, (220, 180, 140))
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
        if category == "vehicle":
            return self._generate_simple_vehicle(name, width, height)
        elif category == "animal":
            # Dinosaurs and ocean animals are also category="animal"
            if name in DINOSAUR_COLORS:
                return self._generate_simple_dinosaur(name, width, height)
            elif name in OCEAN_COLORS:
                return self._generate_simple_ocean(name, width, height)
            else:
                return self._generate_simple_animal(name, width, height)
        elif category == "science":
            return self._generate_simple_space(name, width, height)
        elif category == "food":
            return self._generate_simple_food(name, width, height)
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
        elif name == "owl":
            self._draw_owl(draw, cx, cy, unit, color, outline, lw)
        elif name == "dolphin":
            self._draw_dolphin(draw, cx, cy, unit, color, outline, lw)
        elif name == "penguin":
            self._draw_penguin(draw, cx, cy, unit, color, outline, lw)
        elif name == "panda":
            self._draw_panda(draw, cx, cy, unit, color, outline, lw)
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
    # Missing animal draw methods (owl, dolphin, penguin, panda)
    # ──────────────────────────────────────────────────────────────

    def _draw_owl(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                  unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw an owl."""
        # Body
        draw.ellipse([cx - 2 * unit, cy - unit, cx + 2 * unit, cy + 3 * unit],
                     fill=color, outline=outline, width=lw)
        # Head (large round)
        head_r = int(2 * unit)
        head_y = cy - int(1.5 * unit)
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Ear tufts
        for dx in [-1, 1]:
            tx = cx + dx * int(1.3 * unit)
            draw.polygon([(tx, head_y - int(2 * unit)),
                          (tx - int(0.5 * unit), head_y - int(0.8 * unit)),
                          (tx + int(0.5 * unit), head_y - int(0.8 * unit))],
                         fill=_darker(color, 30), outline=outline, width=lw)
        # Large eyes
        for dx in [-1, 1]:
            ex = cx + dx * int(0.8 * unit)
            er = int(0.7 * unit)
            draw.ellipse([ex - er, head_y - er, ex + er, head_y + er],
                         fill=(255, 255, 255), outline=outline, width=lw)
            pr = int(0.35 * unit)
            draw.ellipse([ex - pr, head_y - pr, ex + pr, head_y + pr],
                         fill=(30, 30, 30))
        # Beak
        draw.polygon([(cx, head_y + int(0.3 * unit)),
                      (cx - int(0.4 * unit), head_y + int(0.8 * unit)),
                      (cx + int(0.4 * unit), head_y + int(0.8 * unit))],
                     fill=(255, 180, 40), outline=outline, width=lw)
        # Belly
        draw.ellipse([cx - int(1.2 * unit), cy, cx + int(1.2 * unit), cy + int(2.2 * unit)],
                     fill=_lighter(color, 40), outline=outline, width=max(1, lw))
        # Wings
        for dx in [-1, 1]:
            wx = cx + dx * int(2 * unit)
            draw.ellipse([min(cx, wx), cy - int(0.5 * unit),
                          max(cx, wx), cy + int(2 * unit)],
                         fill=_darker(color, 20), outline=outline, width=lw)

    def _draw_dolphin(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                      unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a dolphin."""
        # Body (curved ellipse)
        draw.ellipse([cx - 4 * unit, cy - 1.5 * unit, cx + 3 * unit, cy + 1.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Belly
        draw.ellipse([cx - 3 * unit, cy - 0.3 * unit, cx + 2.5 * unit, cy + 1.5 * unit],
                     fill=_lighter(color, 60), outline=outline, width=max(1, lw))
        # Snout
        draw.polygon([(cx + 3 * unit, cy), (cx + 5 * unit, cy - int(0.3 * unit)),
                      (cx + 5 * unit, cy + int(0.3 * unit))],
                     fill=color, outline=outline, width=lw)
        # Eye
        draw.ellipse([cx + int(1.5 * unit), cy - int(0.5 * unit),
                      cx + int(2.1 * unit), cy + int(0.1 * unit)],
                     fill=(30, 30, 30))
        # Dorsal fin
        draw.polygon([(cx - int(0.5 * unit), cy - int(1.5 * unit)),
                      (cx + int(0.5 * unit), cy - int(3 * unit)),
                      (cx + int(1.5 * unit), cy - int(1.5 * unit))],
                     fill=_darker(color, 20), outline=outline, width=lw)
        # Tail flukes
        draw.polygon([(cx - 4 * unit, cy),
                      (cx - 5 * unit, cy - int(1.5 * unit)),
                      (cx - 5 * unit, cy + int(1.5 * unit))],
                     fill=color, outline=outline, width=lw)
        # Flipper
        draw.ellipse([cx + int(0.5 * unit), cy + int(0.5 * unit),
                      cx + int(2 * unit), cy + int(2 * unit)],
                     fill=_darker(color, 20), outline=outline, width=lw)

    def _draw_penguin(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                      unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a penguin."""
        # Body (black oval)
        draw.ellipse([cx - 2 * unit, cy - 2 * unit, cx + 2 * unit, cy + 3 * unit],
                     fill=color, outline=outline, width=lw)
        # White belly
        draw.ellipse([cx - int(1.3 * unit), cy - unit, cx + int(1.3 * unit), cy + int(2.5 * unit)],
                     fill=(240, 240, 245), outline=outline, width=max(1, lw))
        # Head
        head_r = int(1.5 * unit)
        head_y = cy - int(2.5 * unit)
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=color, outline=outline, width=lw)
        # Eyes
        for dx in [-1, 1]:
            ex = cx + dx * int(0.5 * unit)
            draw.ellipse([ex - int(0.25 * unit), head_y - int(0.25 * unit),
                          ex + int(0.25 * unit), head_y + int(0.25 * unit)],
                         fill=(255, 255, 255), outline=(30, 30, 30), width=max(1, lw))
        # Beak
        draw.polygon([(cx, head_y + int(0.3 * unit)),
                      (cx - int(0.5 * unit), head_y + int(0.8 * unit)),
                      (cx + int(0.5 * unit), head_y + int(0.8 * unit))],
                     fill=(255, 180, 40), outline=outline, width=lw)
        # Wings/flippers
        for dx in [-1, 1]:
            x0 = cx + dx * int(2 * unit)
            x1 = cx + dx * int(3 * unit)
            draw.ellipse([min(x0, x1), cy - unit, max(x0, x1), cy + int(1.5 * unit)],
                         fill=color, outline=outline, width=lw)
        # Feet
        for dx in [-1, 1]:
            fx = cx + dx * int(0.7 * unit)
            draw.ellipse([fx - int(0.5 * unit), cy + int(2.8 * unit),
                          fx + int(0.5 * unit), cy + int(3.4 * unit)],
                         fill=(255, 180, 40), outline=outline, width=lw)

    def _draw_panda(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                    unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a panda."""
        # Body (white)
        draw.ellipse([cx - 2.5 * unit, cy - unit, cx + 2.5 * unit, cy + 3 * unit],
                     fill=(250, 250, 250), outline=outline, width=lw)
        # Head (white)
        head_r = int(2 * unit)
        head_y = cy - int(1.5 * unit)
        draw.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r],
                     fill=(250, 250, 250), outline=outline, width=lw)
        # Black ears
        for dx in [-1, 1]:
            ear_x = cx + dx * int(1.5 * unit)
            ear_y = head_y - int(1.5 * unit)
            ear_r = int(0.7 * unit)
            draw.ellipse([ear_x - ear_r, ear_y - ear_r, ear_x + ear_r, ear_y + ear_r],
                         fill=(30, 30, 30), outline=outline, width=lw)
        # Black eye patches
        for dx in [-1, 1]:
            ex = cx + dx * int(0.7 * unit)
            draw.ellipse([ex - int(0.6 * unit), head_y - int(0.6 * unit),
                          ex + int(0.6 * unit), head_y + int(0.4 * unit)],
                         fill=(30, 30, 30))
            # White eye highlight
            draw.ellipse([ex - int(0.2 * unit), head_y - int(0.2 * unit),
                          ex + int(0.2 * unit), head_y + int(0.1 * unit)],
                         fill=(255, 255, 255))
        # Nose
        draw.ellipse([cx - int(0.25 * unit), head_y + int(0.4 * unit),
                      cx + int(0.25 * unit), head_y + int(0.65 * unit)],
                     fill=(30, 30, 30))
        # Black arms
        for dx in [-1, 1]:
            x0 = cx + dx * int(2 * unit)
            x1 = cx + dx * int(3.2 * unit)
            draw.ellipse([min(x0, x1), cy - int(0.5 * unit), max(x0, x1), cy + int(1.5 * unit)],
                         fill=(30, 30, 30), outline=outline, width=lw)
        # Black legs
        for dx in [-1, 1]:
            x0 = cx + dx * int(0.8 * unit)
            x1 = cx + dx * int(2 * unit)
            draw.ellipse([min(x0, x1), cy + int(2.5 * unit), max(x0, x1), cy + int(3.6 * unit)],
                         fill=(30, 30, 30), outline=outline, width=lw)

    # ──────────────────────────────────────────────────────────────
    # Dinosaur drawing
    # ──────────────────────────────────────────────────────────────

    def _generate_simple_dinosaur(self, name: str, width: int, height: int) -> bytes:
        """Create a recognizable dinosaur using PIL drawing primitives."""
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        color = DINOSAUR_COLORS.get(name, (120, 160, 100))
        outline = _darker(color, 80)
        lw = max(2, width // 128)
        cx, cy = width // 2, height // 2
        unit = min(width, height) // 10

        # Dispatch to shape templates
        if name == "t_rex":
            self._draw_dino_bipedal(draw, cx, cy, unit, color, outline, lw, arms_tiny=True, head_large=True)
        elif name == "velociraptor":
            self._draw_dino_bipedal(draw, cx, cy, unit, color, outline, lw, arms_tiny=False, head_large=False)
        elif name == "allosaurus":
            self._draw_dino_bipedal(draw, cx, cy, unit, color, outline, lw, arms_tiny=True, head_large=True)
            # Crest
            draw.polygon([(cx + int(2 * unit), cy - int(3.5 * unit)),
                          (cx + int(2.5 * unit), cy - int(4.5 * unit)),
                          (cx + int(3 * unit), cy - int(3 * unit))],
                         fill=_darker(color, 20), outline=outline, width=lw)
        elif name == "triceratops":
            self._draw_dino_quadruped(draw, cx, cy, unit, color, outline, lw)
            # Frill
            draw.ellipse([cx + int(2 * unit), cy - int(4.5 * unit),
                          cx + int(5 * unit), cy - int(1.5 * unit)],
                         fill=_lighter(color, 30), outline=outline, width=lw)
            # Three horns
            draw.polygon([(cx + int(3.5 * unit), cy - int(2.5 * unit)),
                          (cx + int(3.2 * unit), cy - int(4.5 * unit)),
                          (cx + int(3.8 * unit), cy - int(4.5 * unit))],
                         fill=(240, 230, 200), outline=outline, width=lw)
            for dy in [-1, 1]:
                draw.polygon([(cx + int(4 * unit), cy - int(2.2 * unit) + dy * int(0.5 * unit)),
                              (cx + int(5.5 * unit), cy - int(3 * unit) + dy * int(0.3 * unit)),
                              (cx + int(4.2 * unit), cy - int(1.8 * unit) + dy * int(0.5 * unit))],
                             fill=(240, 230, 200), outline=outline, width=lw)
        elif name in ("stegosaurus", "iguanodon"):
            self._draw_dino_quadruped(draw, cx, cy, unit, color, outline, lw)
            # Back plates
            for i in range(-3, 3):
                px = cx + i * int(1.2 * unit)
                ph = int(1.2 * unit) + abs(i) * int(0.2 * unit)
                draw.polygon([(px, cy - int(2 * unit)),
                              (px - int(0.4 * unit), cy - int(2 * unit) - ph),
                              (px + int(0.4 * unit), cy - int(2 * unit) - ph)],
                             fill=_darker(color, 20), outline=outline, width=lw)
        elif name in ("brontosaurus", "diplodocus", "brachiosaurus"):
            self._draw_dino_longneck(draw, cx, cy, unit, color, outline, lw)
        elif name == "pterodactyl":
            self._draw_dino_flying(draw, cx, cy, unit, color, outline, lw)
        elif name == "archaeopteryx":
            self._draw_dino_flying(draw, cx, cy, unit, color, outline, lw)
            # Feathered tail
            for i in range(3):
                fx = cx - int(3 * unit) - i * int(0.5 * unit)
                draw.ellipse([fx - int(0.6 * unit), cy + i * int(0.4 * unit),
                              fx + int(0.3 * unit), cy + int(1.5 * unit) + i * int(0.3 * unit)],
                             fill=_lighter(color, 20 + i * 10), outline=outline, width=max(1, lw))
        elif name == "ankylosaurus":
            self._draw_dino_quadruped(draw, cx, cy, unit, color, outline, lw)
            # Armor bumps
            for i in range(-2, 3):
                for j in range(-1, 1):
                    bx = cx + i * int(1.2 * unit)
                    by = cy - int(1.5 * unit) + j * int(0.8 * unit)
                    draw.ellipse([bx - int(0.3 * unit), by - int(0.3 * unit),
                                  bx + int(0.3 * unit), by + int(0.3 * unit)],
                                 fill=_darker(color, 30), outline=outline, width=max(1, lw))
            # Club tail
            draw.ellipse([cx - int(5 * unit), cy - int(0.8 * unit),
                          cx - int(3.5 * unit), cy + int(0.8 * unit)],
                         fill=_darker(color, 30), outline=outline, width=lw)
        elif name in ("spinosaurus", "dimetrodon"):
            self._draw_dino_bipedal(draw, cx, cy, unit, color, outline, lw, arms_tiny=True, head_large=True)
            # Sail on back
            points = []
            for i in range(-3, 4):
                px = cx + i * int(0.8 * unit)
                top_h = int(2.5 * unit) - abs(i) * int(0.3 * unit)
                points.append((px, cy - int(2 * unit) - top_h))
            # Close the sail along the back line
            for i in range(3, -4, -1):
                px = cx + i * int(0.8 * unit)
                points.append((px, cy - int(2 * unit)))
            draw.polygon(points, fill=_lighter(color, 30), outline=outline, width=lw)
        elif name == "parasaurolophus":
            self._draw_dino_bipedal(draw, cx, cy, unit, color, outline, lw, arms_tiny=False, head_large=False)
            # Crest
            draw.polygon([(cx + int(2.5 * unit), cy - int(3 * unit)),
                          (cx + int(1 * unit), cy - int(5 * unit)),
                          (cx + int(3 * unit), cy - int(4.5 * unit))],
                         fill=_lighter(color, 20), outline=outline, width=lw)
        elif name == "pachycephalosaurus":
            self._draw_dino_bipedal(draw, cx, cy, unit, color, outline, lw, arms_tiny=False, head_large=True)
            # Dome head
            draw.ellipse([cx + int(1.5 * unit), cy - int(5 * unit),
                          cx + int(4 * unit), cy - int(3 * unit)],
                         fill=_darker(color, 20), outline=outline, width=lw)
        elif name in ("plesiosaurus", "mosasaurus"):
            self._draw_dino_marine(draw, cx, cy, unit, color, outline, lw)
        else:
            # Generic dinosaur
            self._draw_dino_quadruped(draw, cx, cy, unit, color, outline, lw)

        self._draw_label(draw, name, width, height)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _draw_dino_bipedal(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                           unit: int, color: tuple, outline: tuple, lw: int,
                           arms_tiny: bool = True, head_large: bool = True) -> None:
        """Draw a bipedal dinosaur (T-Rex style)."""
        # Body
        draw.ellipse([cx - 3 * unit, cy - 2 * unit, cx + 2 * unit, cy + 2 * unit],
                     fill=color, outline=outline, width=lw)
        # Belly
        draw.ellipse([cx - 2 * unit, cy - unit, cx + unit, cy + 2 * unit],
                     fill=_lighter(color, 30), outline=outline, width=max(1, lw))
        # Head
        hr = int(1.8 * unit) if head_large else int(1.3 * unit)
        hx = cx + int(2.5 * unit)
        hy = cy - int(2 * unit)
        draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                     fill=color, outline=outline, width=lw)
        # Jaw
        draw.ellipse([hx, hy, hx + int(2 * unit), hy + int(1.2 * unit)],
                     fill=color, outline=outline, width=lw)
        # Eye
        draw.ellipse([hx + int(0.3 * unit), hy - int(0.5 * unit),
                      hx + int(0.8 * unit), hy],
                     fill=(255, 255, 255), outline=(30, 30, 30), width=max(1, lw))
        draw.ellipse([hx + int(0.5 * unit), hy - int(0.35 * unit),
                      hx + int(0.7 * unit), hy - int(0.15 * unit)],
                     fill=(30, 30, 30))
        # Teeth
        for i in range(3):
            tx = hx + int(0.8 * unit) + i * int(0.4 * unit)
            draw.polygon([(tx, hy + int(0.4 * unit)),
                          (tx + int(0.15 * unit), hy + int(0.9 * unit)),
                          (tx - int(0.15 * unit), hy + int(0.9 * unit))],
                         fill=(255, 255, 255), outline=outline, width=max(1, lw))
        # Arms
        arm_len = int(0.8 * unit) if arms_tiny else int(1.5 * unit)
        draw.line([cx + unit, cy - unit, cx + unit + arm_len, cy],
                  fill=color, width=lw * 3)
        draw.line([cx + unit, cy - unit, cx + unit + arm_len, cy],
                  fill=outline, width=lw)
        # Legs
        for dx in [-1.5, 0.5]:
            lx = cx + int(dx * unit)
            draw.rectangle([lx - int(0.6 * unit), cy + int(1.5 * unit),
                            lx + int(0.6 * unit), cy + int(3.5 * unit)],
                           fill=color, outline=outline, width=lw)
            # Feet
            draw.ellipse([lx - int(0.8 * unit), cy + int(3 * unit),
                          lx + int(0.8 * unit), cy + int(3.8 * unit)],
                         fill=color, outline=outline, width=lw)
        # Tail
        draw.polygon([(cx - 3 * unit, cy - unit),
                      (cx - 5 * unit, cy - int(0.5 * unit)),
                      (cx - 5 * unit, cy + int(0.5 * unit)),
                      (cx - 3 * unit, cy + unit)],
                     fill=color, outline=outline, width=lw)

    def _draw_dino_quadruped(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                             unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a quadruped dinosaur (triceratops/stegosaurus style)."""
        # Body
        draw.ellipse([cx - 3 * unit, cy - 2 * unit, cx + 3 * unit, cy + unit],
                     fill=color, outline=outline, width=lw)
        # Belly
        draw.ellipse([cx - 2 * unit, cy - unit, cx + 2 * unit, cy + unit],
                     fill=_lighter(color, 30), outline=outline, width=max(1, lw))
        # Head
        hx = cx + int(3.5 * unit)
        hy = cy - int(1.5 * unit)
        draw.ellipse([hx - int(1.2 * unit), hy - int(1.2 * unit),
                      hx + int(1.2 * unit), hy + int(1.2 * unit)],
                     fill=color, outline=outline, width=lw)
        # Eye
        draw.ellipse([hx + int(0.2 * unit), hy - int(0.4 * unit),
                      hx + int(0.6 * unit), hy],
                     fill=(255, 255, 255), outline=(30, 30, 30), width=max(1, lw))
        # Four legs
        legs = [-2, -0.5, 1, 2.5]
        for lx_off in legs:
            lx = cx + int(lx_off * unit)
            draw.rectangle([lx - int(0.5 * unit), cy + int(0.5 * unit),
                            lx + int(0.5 * unit), cy + int(2.8 * unit)],
                           fill=color, outline=outline, width=lw)
        # Tail
        draw.polygon([(cx - 3 * unit, cy - unit),
                      (cx - 5 * unit, cy - int(0.5 * unit)),
                      (cx - 5 * unit, cy),
                      (cx - 3 * unit, cy)],
                     fill=color, outline=outline, width=lw)

    def _draw_dino_longneck(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                            unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a long-neck dinosaur (brontosaurus style)."""
        # Large body
        draw.ellipse([cx - 3 * unit, cy - unit, cx + 3 * unit, cy + 2.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Long neck
        draw.polygon([(cx + int(2 * unit), cy - unit),
                      (cx + int(3 * unit), cy - int(4.5 * unit)),
                      (cx + int(4 * unit), cy - int(4.5 * unit)),
                      (cx + int(3 * unit), cy)],
                     fill=color, outline=outline, width=lw)
        # Small head
        hx = cx + int(3.5 * unit)
        hy = cy - int(5 * unit)
        draw.ellipse([hx - int(0.8 * unit), hy - int(0.6 * unit),
                      hx + int(0.8 * unit), hy + int(0.6 * unit)],
                     fill=color, outline=outline, width=lw)
        # Eye
        draw.ellipse([hx + int(0.2 * unit), hy - int(0.3 * unit),
                      hx + int(0.5 * unit), hy],
                     fill=(255, 255, 255), outline=(30, 30, 30), width=max(1, lw))
        # Legs
        for lx_off in [-2, -0.5, 1, 2.5]:
            lx = cx + int(lx_off * unit)
            draw.rectangle([lx - int(0.6 * unit), cy + int(2 * unit),
                            lx + int(0.6 * unit), cy + int(3.8 * unit)],
                           fill=color, outline=outline, width=lw)
        # Tail
        draw.polygon([(cx - 3 * unit, cy),
                      (cx - 5 * unit, cy + int(0.5 * unit)),
                      (cx - 5.5 * unit, cy),
                      (cx - 3 * unit, cy - unit)],
                     fill=color, outline=outline, width=lw)

    def _draw_dino_flying(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                          unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a flying dinosaur (pterodactyl style)."""
        # Body
        draw.ellipse([cx - unit, cy - unit, cx + 2 * unit, cy + unit],
                     fill=color, outline=outline, width=lw)
        # Head with beak
        draw.ellipse([cx + int(1.5 * unit), cy - int(1.5 * unit),
                      cx + int(3 * unit), cy - int(0.3 * unit)],
                     fill=color, outline=outline, width=lw)
        # Beak
        draw.polygon([(cx + int(3 * unit), cy - int(0.9 * unit)),
                      (cx + int(4.5 * unit), cy - int(0.5 * unit)),
                      (cx + int(3 * unit), cy - int(0.5 * unit))],
                     fill=_darker(color, 30), outline=outline, width=lw)
        # Crest
        draw.polygon([(cx + int(2 * unit), cy - int(1.5 * unit)),
                      (cx + int(1.5 * unit), cy - int(3 * unit)),
                      (cx + int(3 * unit), cy - int(1.5 * unit))],
                     fill=_lighter(color, 20), outline=outline, width=lw)
        # Eye
        draw.ellipse([cx + int(2.2 * unit), cy - int(1.2 * unit),
                      cx + int(2.6 * unit), cy - int(0.8 * unit)],
                     fill=(255, 255, 255), outline=(30, 30, 30), width=max(1, lw))
        # Wings
        draw.polygon([(cx - unit, cy), (cx - 4 * unit, cy - 3 * unit),
                      (cx - 5 * unit, cy - unit), (cx - unit, cy + int(0.5 * unit))],
                     fill=_lighter(color, 20), outline=outline, width=lw)
        draw.polygon([(cx + unit, cy), (cx + unit, cy - 3 * unit),
                      (cx - unit, cy - 3.5 * unit), (cx - unit, cy)],
                     fill=_lighter(color, 20), outline=outline, width=lw)
        # Legs
        for dx in [0, 1]:
            draw.line([cx + int(dx * unit), cy + unit,
                       cx + int(dx * unit), cy + int(2 * unit)],
                      fill=color, width=lw * 2)

    def _draw_dino_marine(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                          unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a marine dinosaur (plesiosaurus style)."""
        # Body
        draw.ellipse([cx - 3 * unit, cy - 1.5 * unit, cx + 2 * unit, cy + 1.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Belly
        draw.ellipse([cx - 2.5 * unit, cy - int(0.3 * unit), cx + 1.5 * unit, cy + 1.5 * unit],
                     fill=_lighter(color, 50), outline=outline, width=max(1, lw))
        # Long neck
        draw.polygon([(cx + int(1.5 * unit), cy - unit),
                      (cx + int(3 * unit), cy - int(4 * unit)),
                      (cx + int(3.8 * unit), cy - int(3.8 * unit)),
                      (cx + int(2.5 * unit), cy)],
                     fill=color, outline=outline, width=lw)
        # Small head
        hx = cx + int(3.4 * unit)
        hy = cy - int(4.5 * unit)
        draw.ellipse([hx - int(0.8 * unit), hy - int(0.5 * unit),
                      hx + int(0.8 * unit), hy + int(0.5 * unit)],
                     fill=color, outline=outline, width=lw)
        # Eye
        draw.ellipse([hx + int(0.2 * unit), hy - int(0.2 * unit),
                      hx + int(0.5 * unit), hy + int(0.1 * unit)],
                     fill=(30, 30, 30))
        # Flippers
        for dy in [-1, 1]:
            y0 = cy + min(dy * int(0.5 * unit), dy * int(2.5 * unit))
            y1 = cy + max(dy * int(0.5 * unit), dy * int(2.5 * unit))
            draw.ellipse([cx - 2 * unit, y0, cx, y1],
                         fill=_darker(color, 20), outline=outline, width=lw)
        # Tail
        draw.polygon([(cx - 3 * unit, cy),
                      (cx - 4.5 * unit, cy - unit),
                      (cx - 4.5 * unit, cy + unit)],
                     fill=color, outline=outline, width=lw)

    # ──────────────────────────────────────────────────────────────
    # Ocean animal drawing
    # ──────────────────────────────────────────────────────────────

    def _generate_simple_ocean(self, name: str, width: int, height: int) -> bytes:
        """Create a recognizable ocean animal using PIL drawing primitives."""
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        color = OCEAN_COLORS.get(name, (80, 140, 200))
        outline = _darker(color, 80)
        lw = max(2, width // 128)
        cx, cy = width // 2, height // 2
        unit = min(width, height) // 10

        if name == "dolphin":
            self._draw_dolphin(draw, cx, cy, unit, color, outline, lw)
        elif name == "whale":
            self._draw_ocean_whale(draw, cx, cy, unit, color, outline, lw)
        elif name == "shark":
            self._draw_ocean_shark(draw, cx, cy, unit, color, outline, lw)
        elif name == "octopus":
            self._draw_ocean_octopus(draw, cx, cy, unit, color, outline, lw)
        elif name == "seahorse":
            self._draw_ocean_seahorse(draw, cx, cy, unit, color, outline, lw)
        elif name == "jellyfish":
            self._draw_ocean_jellyfish(draw, cx, cy, unit, color, outline, lw)
        elif name == "starfish":
            self._draw_ocean_starfish(draw, cx, cy, unit, color, outline, lw)
        elif name in ("crab", "lobster"):
            self._draw_ocean_crab(draw, cx, cy, unit, color, outline, lw)
        elif name == "sea_turtle":
            self._draw_turtle(draw, cx, cy, unit, color, outline, lw)
        elif name in ("clownfish", "pufferfish"):
            self._draw_fish(draw, cx, cy, unit, color, outline, lw)
        elif name == "manta_ray":
            self._draw_ocean_ray(draw, cx, cy, unit, color, outline, lw)
        elif name == "seal":
            self._draw_ocean_seal(draw, cx, cy, unit, color, outline, lw)
        elif name == "penguin":
            self._draw_penguin(draw, cx, cy, unit, color, outline, lw)
        elif name == "orca":
            self._draw_ocean_whale(draw, cx, cy, unit, color, outline, lw)
        elif name == "narwhal":
            self._draw_ocean_whale(draw, cx, cy, unit, color, outline, lw)
            # Horn
            draw.polygon([(cx + int(3.5 * unit), cy - int(0.5 * unit)),
                          (cx + int(6 * unit), cy - int(1.5 * unit)),
                          (cx + int(3.5 * unit), cy + int(0.2 * unit))],
                         fill=(240, 230, 200), outline=outline, width=lw)
        elif name == "squid":
            self._draw_ocean_octopus(draw, cx, cy, unit, color, outline, lw)
        else:
            self._draw_fish(draw, cx, cy, unit, color, outline, lw)

        self._draw_label(draw, name, width, height)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _draw_ocean_whale(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                          unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a whale."""
        draw.ellipse([cx - 4 * unit, cy - 2 * unit, cx + 3 * unit, cy + 2 * unit],
                     fill=color, outline=outline, width=lw)
        # Belly
        draw.ellipse([cx - 3 * unit, cy - int(0.5 * unit), cx + 2 * unit, cy + 2 * unit],
                     fill=_lighter(color, 60), outline=outline, width=max(1, lw))
        # Eye
        draw.ellipse([cx + int(1.5 * unit), cy - int(0.8 * unit),
                      cx + int(2.1 * unit), cy - int(0.2 * unit)],
                     fill=(30, 30, 30))
        # Mouth
        draw.arc([cx + unit, cy, cx + int(3 * unit), cy + unit],
                 0, 180, fill=outline, width=lw)
        # Tail
        draw.polygon([(cx - 4 * unit, cy),
                      (cx - 5.5 * unit, cy - int(1.8 * unit)),
                      (cx - 5.5 * unit, cy + int(1.8 * unit))],
                     fill=color, outline=outline, width=lw)
        # Flipper
        draw.ellipse([cx, cy + int(0.5 * unit), cx + int(2 * unit), cy + int(2.5 * unit)],
                     fill=_darker(color, 20), outline=outline, width=lw)
        # Water spout
        draw.line([cx, cy - int(2 * unit), cx, cy - int(3.5 * unit)],
                  fill=(100, 180, 240), width=lw * 2)
        draw.ellipse([cx - int(0.8 * unit), cy - int(4.5 * unit),
                      cx + int(0.8 * unit), cy - int(3.5 * unit)],
                     fill=(140, 200, 255), outline=(100, 180, 240), width=lw)

    def _draw_ocean_shark(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                          unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a shark."""
        # Body
        draw.ellipse([cx - 4 * unit, cy - 1.5 * unit, cx + 3 * unit, cy + 1.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Belly
        draw.ellipse([cx - 3 * unit, cy - int(0.2 * unit), cx + 2 * unit, cy + 1.5 * unit],
                     fill=_lighter(color, 80), outline=outline, width=max(1, lw))
        # Snout
        draw.polygon([(cx + 3 * unit, cy), (cx + int(4.5 * unit), cy),
                      (cx + 3 * unit, cy + int(0.5 * unit))],
                     fill=color, outline=outline, width=lw)
        # Dorsal fin (tall triangle)
        draw.polygon([(cx - int(0.5 * unit), cy - int(1.5 * unit)),
                      (cx + int(0.3 * unit), cy - int(3.5 * unit)),
                      (cx + int(1.5 * unit), cy - int(1.5 * unit))],
                     fill=_darker(color, 20), outline=outline, width=lw)
        # Eye
        draw.ellipse([cx + int(1.8 * unit), cy - int(0.6 * unit),
                      cx + int(2.3 * unit), cy - int(0.1 * unit)],
                     fill=(30, 30, 30))
        # Tail
        draw.polygon([(cx - 4 * unit, cy),
                      (cx - 5 * unit, cy - int(2 * unit)),
                      (cx - 5 * unit, cy + int(1.5 * unit))],
                     fill=color, outline=outline, width=lw)
        # Teeth
        for i in range(4):
            tx = cx + int(2.5 * unit) + i * int(0.3 * unit)
            draw.polygon([(tx, cy + int(0.3 * unit)),
                          (tx + int(0.1 * unit), cy + int(0.7 * unit)),
                          (tx - int(0.1 * unit), cy + int(0.7 * unit))],
                         fill=(255, 255, 255))

    def _draw_ocean_octopus(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                            unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw an octopus."""
        # Head
        draw.ellipse([cx - 2 * unit, cy - 3 * unit, cx + 2 * unit, cy],
                     fill=color, outline=outline, width=lw)
        # Eyes
        for dx in [-1, 1]:
            ex = cx + dx * int(0.7 * unit)
            draw.ellipse([ex - int(0.5 * unit), cy - int(2.2 * unit),
                          ex + int(0.5 * unit), cy - int(1.4 * unit)],
                         fill=(255, 255, 255), outline=(30, 30, 30), width=max(1, lw))
            draw.ellipse([ex - int(0.2 * unit), cy - int(2 * unit),
                          ex + int(0.2 * unit), cy - int(1.6 * unit)],
                         fill=(30, 30, 30))
        # Tentacles (8)
        import math as _m
        for i in range(8):
            angle = _m.radians(180 + i * 22.5)
            x1 = cx + int(1.5 * unit * _m.cos(angle))
            y1 = cy
            x2 = cx + int(3.5 * unit * _m.cos(angle + 0.3))
            y2 = cy + int(3.5 * unit)
            draw.line([x1, y1, x2, y2], fill=color, width=lw * 3)
            draw.line([x1, y1, x2, y2], fill=outline, width=lw)
            # Sucker dots
            mx, my = (x1 + x2) // 2, (y1 + y2) // 2
            draw.ellipse([mx - 3, my - 3, mx + 3, my + 3],
                         fill=_lighter(color, 40))

    def _draw_ocean_seahorse(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                             unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a seahorse."""
        # Body curve (series of overlapping circles)
        for i in range(7):
            r = int((2 - i * 0.15) * unit)
            by = cy - int(2 * unit) + i * int(0.9 * unit)
            draw.ellipse([cx - r, by - r // 2, cx + r, by + r // 2],
                         fill=color, outline=outline, width=lw)
        # Head
        draw.ellipse([cx - int(1.2 * unit), cy - int(3.5 * unit),
                      cx + int(1.2 * unit), cy - int(1.5 * unit)],
                     fill=color, outline=outline, width=lw)
        # Snout
        draw.rectangle([cx + int(0.5 * unit), cy - int(2.8 * unit),
                        cx + int(2 * unit), cy - int(2.2 * unit)],
                       fill=color, outline=outline, width=lw)
        # Eye
        draw.ellipse([cx - int(0.1 * unit), cy - int(3 * unit),
                      cx + int(0.5 * unit), cy - int(2.4 * unit)],
                     fill=(30, 30, 30))
        # Crown spikes
        for i in range(3):
            sx = cx - int(0.3 * unit) + i * int(0.4 * unit)
            draw.polygon([(sx, cy - int(3.5 * unit)),
                          (sx + int(0.2 * unit), cy - int(4.2 * unit)),
                          (sx + int(0.4 * unit), cy - int(3.5 * unit))],
                         fill=_darker(color, 20), outline=outline, width=max(1, lw))
        # Curly tail
        draw.arc([cx - int(1.5 * unit), cy + int(2 * unit),
                  cx + int(1.5 * unit), cy + int(4.5 * unit)],
                 0, 270, fill=color, width=lw * 3)

    def _draw_ocean_jellyfish(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                              unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a jellyfish."""
        # Bell/dome
        draw.ellipse([cx - 2.5 * unit, cy - 3 * unit, cx + 2.5 * unit, cy],
                     fill=color, outline=outline, width=lw)
        # Inner bell
        draw.ellipse([cx - int(1.5 * unit), cy - int(2 * unit),
                      cx + int(1.5 * unit), cy - int(0.5 * unit)],
                     fill=_lighter(color, 40), outline=outline, width=max(1, lw))
        # Eyes
        for dx in [-1, 1]:
            ex = cx + dx * int(0.5 * unit)
            draw.ellipse([ex - int(0.2 * unit), cy - int(1.5 * unit),
                          ex + int(0.2 * unit), cy - int(1.1 * unit)],
                         fill=(30, 30, 30))
        # Tentacles (wavy lines)
        import math as _m
        for i in range(7):
            tx = cx - int(2 * unit) + i * int(0.7 * unit)
            for j in range(8):
                y1 = cy + j * int(0.6 * unit)
                y2 = y1 + int(0.6 * unit)
                wobble = int(0.3 * unit * _m.sin(j + i))
                draw.line([tx + wobble, y1, tx - wobble, y2],
                          fill=color, width=max(2, lw))

    def _draw_ocean_starfish(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                             unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a starfish."""
        import math as _m
        # Star shape with 5 arms
        points = []
        for i in range(10):
            angle = _m.radians(i * 36 - 90)
            r = int(3.5 * unit) if i % 2 == 0 else int(1.5 * unit)
            points.append((cx + int(r * _m.cos(angle)), cy + int(r * _m.sin(angle))))
        draw.polygon(points, fill=color, outline=outline, width=lw)
        # Inner pattern
        inner_pts = []
        for i in range(10):
            angle = _m.radians(i * 36 - 90)
            r = int(2.5 * unit) if i % 2 == 0 else int(1.2 * unit)
            inner_pts.append((cx + int(r * _m.cos(angle)), cy + int(r * _m.sin(angle))))
        draw.polygon(inner_pts, fill=_lighter(color, 30), outline=outline, width=max(1, lw))
        # Eyes
        self._draw_eyes(draw, cx, cy - int(0.5 * unit), int(0.4 * unit), int(0.2 * unit), lw)
        # Smile
        draw.arc([cx - int(0.3 * unit), cy, cx + int(0.3 * unit), cy + int(0.5 * unit)],
                 0, 180, fill=outline, width=lw)
        # Spots on arms
        for i in range(5):
            angle = _m.radians(i * 72 - 90)
            sx = cx + int(2.2 * unit * _m.cos(angle))
            sy = cy + int(2.2 * unit * _m.sin(angle))
            draw.ellipse([sx - int(0.2 * unit), sy - int(0.2 * unit),
                          sx + int(0.2 * unit), sy + int(0.2 * unit)],
                         fill=_lighter(color, 50))

    def _draw_ocean_crab(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a crab."""
        # Body (wide oval)
        draw.ellipse([cx - 2.5 * unit, cy - 1.5 * unit, cx + 2.5 * unit, cy + 1.5 * unit],
                     fill=color, outline=outline, width=lw)
        # Eyes on stalks
        for dx in [-1, 1]:
            ex = cx + dx * int(1.5 * unit)
            draw.line([ex, cy - int(1.5 * unit), ex, cy - int(2.5 * unit)],
                      fill=color, width=lw * 2)
            draw.ellipse([ex - int(0.3 * unit), cy - int(3 * unit),
                          ex + int(0.3 * unit), cy - int(2.3 * unit)],
                         fill=(255, 255, 255), outline=(30, 30, 30), width=max(1, lw))
        # Claws
        for dx in [-1, 1]:
            claw_x = cx + dx * int(3.5 * unit)
            draw.ellipse([claw_x - int(1.2 * unit), cy - int(1.5 * unit),
                          claw_x + int(1.2 * unit), cy + int(0.5 * unit)],
                         fill=color, outline=outline, width=lw)
            # Claw opening
            draw.line([claw_x, cy - int(0.5 * unit),
                       claw_x + dx * int(1 * unit), cy - int(1.5 * unit)],
                      fill=outline, width=lw * 2)
        # Legs (3 pairs)
        for i in range(3):
            for dx in [-1, 1]:
                lx = cx + dx * int((1.5 + i * 0.8) * unit)
                draw.line([lx, cy + unit, lx + dx * int(1.5 * unit), cy + int(2.5 * unit)],
                          fill=color, width=lw * 2)

    def _draw_ocean_ray(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                        unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a manta ray."""
        # Wings (large diamond)
        draw.polygon([(cx, cy - int(0.5 * unit)),
                      (cx - 5 * unit, cy - int(2 * unit)),
                      (cx, cy + int(1.5 * unit)),
                      (cx + 5 * unit, cy - int(2 * unit))],
                     fill=color, outline=outline, width=lw)
        # Body center
        draw.ellipse([cx - int(1.5 * unit), cy - int(1.5 * unit),
                      cx + int(1.5 * unit), cy + int(1.5 * unit)],
                     fill=color, outline=outline, width=lw)
        # Belly
        draw.ellipse([cx - unit, cy - int(0.5 * unit), cx + unit, cy + unit],
                     fill=_lighter(color, 60), outline=outline, width=max(1, lw))
        # Eyes
        for dx in [-1, 1]:
            draw.ellipse([cx + dx * int(1.2 * unit) - int(0.2 * unit), cy - int(0.8 * unit),
                          cx + dx * int(1.2 * unit) + int(0.2 * unit), cy - int(0.4 * unit)],
                         fill=(30, 30, 30))
        # Tail
        draw.line([cx, cy + int(1.5 * unit), cx, cy + int(4 * unit)],
                  fill=color, width=lw * 2)

    def _draw_ocean_seal(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a seal."""
        # Body
        draw.ellipse([cx - 3 * unit, cy - 1.5 * unit, cx + 2 * unit, cy + 2 * unit],
                     fill=color, outline=outline, width=lw)
        # Head
        draw.ellipse([cx + unit, cy - int(2.5 * unit), cx + int(3.5 * unit), cy],
                     fill=color, outline=outline, width=lw)
        # Eyes
        draw.ellipse([cx + int(2 * unit), cy - int(1.8 * unit),
                      cx + int(2.5 * unit), cy - int(1.3 * unit)],
                     fill=(30, 30, 30))
        # Nose
        draw.ellipse([cx + int(2.8 * unit), cy - int(1.2 * unit),
                      cx + int(3.2 * unit), cy - int(0.8 * unit)],
                     fill=(30, 30, 30))
        # Whiskers
        for dy in [-1, 0, 1]:
            draw.line([cx + int(2.8 * unit), cy - unit + dy * int(0.2 * unit),
                       cx + int(4 * unit), cy - unit + dy * int(0.4 * unit)],
                      fill=outline, width=max(1, lw))
        # Flippers
        draw.ellipse([cx + int(0.5 * unit), cy + unit,
                      cx + int(2.5 * unit), cy + int(2.5 * unit)],
                     fill=_darker(color, 20), outline=outline, width=lw)
        # Tail
        draw.polygon([(cx - 3 * unit, cy), (cx - 4 * unit, cy - unit),
                      (cx - 4 * unit, cy + unit)],
                     fill=color, outline=outline, width=lw)

    # ──────────────────────────────────────────────────────────────
    # Space object drawing
    # ──────────────────────────────────────────────────────────────

    def _generate_simple_space(self, name: str, width: int, height: int) -> bytes:
        """Create a recognizable space object using PIL drawing primitives."""
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        color = SPACE_COLORS.get(name, (140, 140, 180))
        outline = _darker(color, 80)
        lw = max(2, width // 128)
        cx, cy = width // 2, height // 2
        unit = min(width, height) // 10

        if name == "rocket":
            self._draw_space_rocket(draw, cx, cy, unit, color, outline, lw)
        elif name == "astronaut":
            self._draw_space_astronaut(draw, cx, cy, unit, color, outline, lw)
        elif name == "planet":
            self._draw_space_planet(draw, cx, cy, unit, color, outline, lw)
        elif name == "star":
            self._draw_star(draw, cx, cy, int(3 * unit), color)
            draw.polygon(self._star_points(cx, cy, int(3 * unit)), outline=outline, width=lw)
        elif name == "moon":
            self._draw_space_moon(draw, cx, cy, unit, color, outline, lw)
        elif name == "sun":
            self._draw_space_sun(draw, cx, cy, unit, color, outline, lw)
        elif name in ("satellite", "space_station"):
            self._draw_space_satellite(draw, cx, cy, unit, color, outline, lw)
        elif name == "ufo":
            self._draw_space_ufo(draw, cx, cy, unit, color, outline, lw)
        elif name == "space_shuttle":
            self._draw_space_rocket(draw, cx, cy, unit, color, outline, lw)
        elif name == "mars_rover":
            self._draw_space_rover(draw, cx, cy, unit, color, outline, lw)
        elif name == "telescope":
            self._draw_space_telescope(draw, cx, cy, unit, color, outline, lw)
        elif name in ("comet", "meteor", "asteroid"):
            self._draw_space_comet(draw, cx, cy, unit, color, outline, lw)
        elif name in ("galaxy", "constellation"):
            self._draw_space_galaxy(draw, cx, cy, unit, color, outline, lw)
        elif name == "lunar_module":
            self._draw_space_satellite(draw, cx, cy, unit, color, outline, lw)
        else:
            self._draw_space_planet(draw, cx, cy, unit, color, outline, lw)

        self._draw_label(draw, name, width, height)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _star_points(self, cx: int, cy: int, r: int) -> list:
        """Helper: return star polygon points."""
        pts = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            radius = r if i % 2 == 0 else int(r * 0.4)
            pts.append((cx + int(radius * math.cos(angle)), cy + int(radius * math.sin(angle))))
        return pts

    def _draw_space_rocket(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                           unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a rocket."""
        # Body
        draw.rounded_rectangle([cx - unit, cy - 3 * unit, cx + unit, cy + 2 * unit],
                               radius=int(0.5 * unit), fill=(240, 240, 245), outline=outline, width=lw)
        # Nose cone
        draw.polygon([(cx, cy - int(4.5 * unit)),
                      (cx - unit, cy - 3 * unit),
                      (cx + unit, cy - 3 * unit)],
                     fill=color, outline=outline, width=lw)
        # Window
        draw.ellipse([cx - int(0.5 * unit), cy - int(2 * unit),
                      cx + int(0.5 * unit), cy - unit],
                     fill=(100, 180, 240), outline=outline, width=lw)
        # Stripe
        draw.rectangle([cx - unit, cy - int(0.5 * unit), cx + unit, cy + int(0.5 * unit)],
                       fill=color, outline=outline, width=lw)
        # Fins
        for dx in [-1, 1]:
            draw.polygon([(cx + dx * unit, cy + unit),
                          (cx + dx * int(2.5 * unit), cy + int(3 * unit)),
                          (cx + dx * unit, cy + 2 * unit)],
                         fill=color, outline=outline, width=lw)
        # Flame
        draw.polygon([(cx - int(0.6 * unit), cy + 2 * unit),
                      (cx, cy + int(3.5 * unit)),
                      (cx + int(0.6 * unit), cy + 2 * unit)],
                     fill=(255, 160, 40), outline=(255, 100, 20), width=lw)
        draw.polygon([(cx - int(0.3 * unit), cy + 2 * unit),
                      (cx, cy + int(3 * unit)),
                      (cx + int(0.3 * unit), cy + 2 * unit)],
                     fill=(255, 240, 80))

    def _draw_space_astronaut(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                              unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw an astronaut."""
        # Body (suit)
        draw.rounded_rectangle([cx - int(1.5 * unit), cy - unit, cx + int(1.5 * unit), cy + 3 * unit],
                               radius=int(0.5 * unit), fill=color, outline=outline, width=lw)
        # Helmet
        draw.ellipse([cx - int(1.8 * unit), cy - int(3.5 * unit),
                      cx + int(1.8 * unit), cy - int(0.2 * unit)],
                     fill=color, outline=outline, width=lw)
        # Visor
        draw.ellipse([cx - int(1.2 * unit), cy - int(2.8 * unit),
                      cx + int(1.2 * unit), cy - int(0.8 * unit)],
                     fill=(80, 140, 200), outline=outline, width=lw)
        # Backpack
        draw.rounded_rectangle([cx - int(2 * unit), cy - int(0.5 * unit),
                                cx - int(1.5 * unit), cy + int(2.5 * unit)],
                               radius=3, fill=(180, 180, 190), outline=outline, width=lw)
        # Arms
        for dx in [-1, 1]:
            draw.rounded_rectangle([cx + dx * int(1.5 * unit), cy,
                                    cx + dx * int(2.5 * unit), cy + int(2 * unit)],
                                   radius=int(0.3 * unit), fill=color, outline=outline, width=lw)
        # Legs
        for dx in [-1, 1]:
            draw.rounded_rectangle([cx + dx * int(0.5 * unit), cy + int(2.5 * unit),
                                    cx + dx * int(1.3 * unit), cy + int(4 * unit)],
                                   radius=int(0.3 * unit), fill=color, outline=outline, width=lw)

    def _draw_space_planet(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                           unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a planet with ring."""
        r = int(3 * unit)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=color, outline=outline, width=lw)
        # Stripes
        for i in range(-2, 3):
            sy = cy + i * int(0.8 * unit)
            sw = int(0.3 * unit)
            draw.ellipse([cx - r + int(0.5 * unit), sy - sw, cx + r - int(0.5 * unit), sy + sw],
                         fill=_lighter(color, 20 + abs(i) * 10), outline=None)
        # Ring
        draw.ellipse([cx - int(4.5 * unit), cy - int(0.8 * unit),
                      cx + int(4.5 * unit), cy + int(0.8 * unit)],
                     fill=None, outline=_lighter(color, 40), width=lw * 2)

    def _draw_space_moon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a moon with craters."""
        r = int(3 * unit)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=color, outline=outline, width=lw)
        # Craters
        craters = [(-1, -1, 0.8), (1.2, 0.5, 0.6), (-0.5, 1.5, 0.5), (1.5, -1.5, 0.4)]
        for crx, cry, cr_size in craters:
            cr = int(cr_size * unit)
            draw.ellipse([cx + int(crx * unit) - cr, cy + int(cry * unit) - cr,
                          cx + int(crx * unit) + cr, cy + int(cry * unit) + cr],
                         fill=_darker(color, 20), outline=_darker(color, 40), width=max(1, lw))

    def _draw_space_sun(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                        unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a sun with rays."""
        r = int(2.5 * unit)
        # Rays
        for i in range(12):
            angle = math.radians(i * 30)
            x1 = cx + int((r + int(0.5 * unit)) * math.cos(angle))
            y1 = cy + int((r + int(0.5 * unit)) * math.sin(angle))
            x2 = cx + int((r + int(2 * unit)) * math.cos(angle))
            y2 = cy + int((r + int(2 * unit)) * math.sin(angle))
            draw.line([x1, y1, x2, y2], fill=color, width=lw * 3)
        # Circle
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=color, outline=outline, width=lw)
        # Face
        self._draw_eyes(draw, cx, cy - int(0.3 * unit), int(0.5 * unit), int(0.25 * unit), lw)
        draw.arc([cx - int(0.5 * unit), cy + int(0.2 * unit),
                  cx + int(0.5 * unit), cy + int(0.8 * unit)],
                 0, 180, fill=(200, 100, 20), width=lw)

    def _draw_space_satellite(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                              unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a satellite."""
        # Body
        draw.rounded_rectangle([cx - unit, cy - unit, cx + unit, cy + unit],
                               radius=int(0.3 * unit), fill=color, outline=outline, width=lw)
        # Solar panels
        for dx in [-1, 1]:
            draw.rectangle([cx + dx * int(1.5 * unit), cy - int(1.5 * unit),
                            cx + dx * int(4 * unit), cy + int(1.5 * unit)],
                           fill=(60, 80, 140), outline=outline, width=lw)
            # Panel lines
            for i in range(3):
                px = cx + dx * int((2 + i * 0.7) * unit)
                draw.line([px, cy - int(1.5 * unit), px, cy + int(1.5 * unit)],
                          fill=outline, width=max(1, lw))
        # Antenna
        draw.line([cx, cy - unit, cx, cy - int(2.5 * unit)],
                  fill=outline, width=lw * 2)
        draw.ellipse([cx - int(0.2 * unit), cy - int(2.8 * unit),
                      cx + int(0.2 * unit), cy - int(2.4 * unit)],
                     fill=(255, 40, 40), outline=outline, width=lw)

    def _draw_space_ufo(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                        unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a UFO."""
        # Saucer bottom
        draw.ellipse([cx - 4 * unit, cy - int(0.5 * unit), cx + 4 * unit, cy + int(1.5 * unit)],
                     fill=_darker(color, 20), outline=outline, width=lw)
        # Saucer top
        draw.ellipse([cx - 3 * unit, cy - int(1.5 * unit), cx + 3 * unit, cy + int(0.5 * unit)],
                     fill=color, outline=outline, width=lw)
        # Dome
        draw.ellipse([cx - int(1.5 * unit), cy - int(3 * unit),
                      cx + int(1.5 * unit), cy - int(0.5 * unit)],
                     fill=(180, 220, 255), outline=outline, width=lw)
        # Lights
        for i in range(-3, 4):
            lx = cx + i * int(0.9 * unit)
            colors = [(255, 255, 100), (100, 255, 100), (255, 100, 100)]
            draw.ellipse([lx - int(0.2 * unit), cy + int(0.2 * unit),
                          lx + int(0.2 * unit), cy + int(0.6 * unit)],
                         fill=colors[i % 3])

    def _draw_space_rover(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                          unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a Mars rover."""
        # Body
        draw.rounded_rectangle([cx - 2 * unit, cy - unit, cx + 2 * unit, cy + unit],
                               radius=int(0.3 * unit), fill=color, outline=outline, width=lw)
        # Top instruments
        draw.rectangle([cx - unit, cy - int(2 * unit), cx + unit, cy - unit],
                       fill=_lighter(color, 20), outline=outline, width=lw)
        # Camera mast
        draw.line([cx + int(0.5 * unit), cy - int(2 * unit),
                   cx + int(0.5 * unit), cy - int(3.5 * unit)],
                  fill=outline, width=lw * 2)
        draw.rectangle([cx, cy - int(4 * unit), cx + unit, cy - int(3.5 * unit)],
                       fill=(180, 180, 190), outline=outline, width=lw)
        # Wheels (6)
        for i, wx in enumerate([-1.5, -0.5, 0.5, 1.5]):
            self._draw_wheel(draw, int(cx + wx * unit), int(cy + int(1.2 * unit)),
                             int(0.5 * unit), lw)
        # Solar panel
        draw.rectangle([cx - int(1.5 * unit), cy - int(2.5 * unit),
                        cx + int(1.5 * unit), cy - int(2 * unit)],
                       fill=(60, 80, 140), outline=outline, width=lw)

    def _draw_space_telescope(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                              unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a telescope."""
        # Tube
        draw.rounded_rectangle([cx - int(0.8 * unit), cy - 3 * unit,
                                cx + int(0.8 * unit), cy + 2 * unit],
                               radius=int(0.3 * unit), fill=color, outline=outline, width=lw)
        # Lens end (wider)
        draw.ellipse([cx - int(1.2 * unit), cy - int(3.5 * unit),
                      cx + int(1.2 * unit), cy - int(2.5 * unit)],
                     fill=_lighter(color, 30), outline=outline, width=lw)
        # Lens glass
        draw.ellipse([cx - int(0.8 * unit), cy - int(3.2 * unit),
                      cx + int(0.8 * unit), cy - int(2.8 * unit)],
                     fill=(100, 160, 220), outline=outline, width=lw)
        # Tripod
        for dx in [-1, 0, 1]:
            draw.line([cx, cy + 2 * unit,
                       cx + dx * int(2 * unit), cy + int(4 * unit)],
                      fill=_darker(color, 30), width=lw * 2)

    def _draw_space_comet(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                          unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a comet/meteor."""
        # Tail (fading)
        for i in range(5):
            alpha = 200 - i * 40
            tw = int((1 + i * 0.8) * unit)
            draw.ellipse([cx - int(3 * unit) - i * int(1.5 * unit), cy - tw // 2,
                          cx - int(1 * unit) - i * int(0.5 * unit), cy + tw // 2],
                         fill=_lighter(color, 20 + i * 15))
        # Core
        r = int(1.5 * unit)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=color, outline=outline, width=lw)
        # Inner glow
        ir = int(0.8 * unit)
        draw.ellipse([cx - ir, cy - ir, cx + ir, cy + ir],
                     fill=_lighter(color, 40))

    def _draw_space_galaxy(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                           unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a spiral galaxy."""
        # Outer glow
        for i in range(3, 0, -1):
            r = int((2 + i) * unit)
            draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2],
                         fill=_lighter(color, 30 + i * 15))
        # Center bulge
        r = int(1.5 * unit)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=color, outline=outline, width=lw)
        # Spiral arms (approximated with arcs)
        for offset in [0, 180]:
            for i in range(4):
                ar = int((1.5 + i * 0.8) * unit)
                start = offset + i * 30
                draw.arc([cx - ar, cy - ar // 2, cx + ar, cy + ar // 2],
                         start, start + 120, fill=_lighter(color, 20), width=lw * 2)
        # Stars (dots)
        import random
        rng = random.Random(42)
        for _ in range(15):
            sx = cx + rng.randint(-int(3 * unit), int(3 * unit))
            sy = cy + rng.randint(-int(2 * unit), int(2 * unit))
            draw.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(255, 255, 220))

    # ──────────────────────────────────────────────────────────────
    # Food drawing
    # ──────────────────────────────────────────────────────────────

    def _generate_simple_food(self, name: str, width: int, height: int) -> bytes:
        """Create a recognizable food item using PIL drawing primitives."""
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        color = FOOD_COLORS.get(name, (220, 180, 140))
        outline = _darker(color, 80)
        lw = max(2, width // 128)
        cx, cy = width // 2, height // 2
        unit = min(width, height) // 10

        if name == "pizza":
            self._draw_food_pizza(draw, cx, cy, unit, color, outline, lw)
        elif name == "hamburger":
            self._draw_food_burger(draw, cx, cy, unit, color, outline, lw)
        elif name == "ice_cream":
            self._draw_food_icecream(draw, cx, cy, unit, color, outline, lw)
        elif name == "cupcake":
            self._draw_food_cupcake(draw, cx, cy, unit, color, outline, lw)
        elif name == "donut":
            self._draw_food_donut(draw, cx, cy, unit, color, outline, lw)
        elif name in ("apple", "banana", "watermelon"):
            self._draw_food_fruit(draw, cx, cy, unit, color, outline, lw, name)
        elif name == "cookie":
            self._draw_food_cookie(draw, cx, cy, unit, color, outline, lw)
        elif name == "cake":
            self._draw_food_cake(draw, cx, cy, unit, color, outline, lw)
        elif name == "taco":
            self._draw_food_taco(draw, cx, cy, unit, color, outline, lw)
        elif name == "hotdog":
            self._draw_food_hotdog(draw, cx, cy, unit, color, outline, lw)
        elif name == "french_fries":
            self._draw_food_fries(draw, cx, cy, unit, color, outline, lw)
        elif name == "lollipop":
            self._draw_food_lollipop(draw, cx, cy, unit, color, outline, lw)
        elif name == "chocolate":
            self._draw_food_chocolate(draw, cx, cy, unit, color, outline, lw)
        elif name == "sandwich":
            self._draw_food_burger(draw, cx, cy, unit, color, outline, lw)
        elif name == "sushi":
            self._draw_food_sushi(draw, cx, cy, unit, color, outline, lw)
        elif name == "pancake":
            self._draw_food_pancake(draw, cx, cy, unit, color, outline, lw)
        else:
            # Generic food: rounded rectangle
            r = int(2.5 * unit)
            draw.rounded_rectangle([cx - r, cy - r, cx + r, cy + r],
                                   radius=unit, fill=color, outline=outline, width=lw)

        self._draw_label(draw, name, width, height)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _draw_food_pizza(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a pizza slice."""
        draw.polygon([(cx, cy - 3 * unit), (cx - int(2.5 * unit), cy + 2 * unit),
                      (cx + int(2.5 * unit), cy + 2 * unit)],
                     fill=color, outline=outline, width=lw)
        # Crust
        draw.arc([cx - int(2.5 * unit), cy + unit, cx + int(2.5 * unit), cy + int(3 * unit)],
                 0, 180, fill=_darker(color, 30), width=lw * 3)
        # Pepperoni
        spots = [(-0.5, -1), (0.5, 0), (-0.3, 0.8), (0.8, -0.5)]
        for sx, sy in spots:
            draw.ellipse([cx + int(sx * unit) - int(0.35 * unit), cy + int(sy * unit) - int(0.35 * unit),
                          cx + int(sx * unit) + int(0.35 * unit), cy + int(sy * unit) + int(0.35 * unit)],
                         fill=(200, 40, 40), outline=_darker((200, 40, 40)), width=max(1, lw))

    def _draw_food_burger(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                          unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a hamburger."""
        # Top bun
        draw.ellipse([cx - 3 * unit, cy - 3 * unit, cx + 3 * unit, cy - int(0.5 * unit)],
                     fill=(210, 170, 80), outline=outline, width=lw)
        # Sesame seeds
        for sx in [-1, 0, 1]:
            draw.ellipse([cx + int(sx * unit) - 4, cy - int(2.2 * unit) - 3,
                          cx + int(sx * unit) + 4, cy - int(2.2 * unit) + 3],
                         fill=(240, 230, 200))
        # Lettuce
        draw.rounded_rectangle([cx - int(3.2 * unit), cy - unit, cx + int(3.2 * unit), cy - int(0.3 * unit)],
                               radius=3, fill=(80, 180, 60), outline=_darker((80, 180, 60)), width=lw)
        # Patty
        draw.rounded_rectangle([cx - int(2.8 * unit), cy - int(0.3 * unit),
                                cx + int(2.8 * unit), cy + int(0.8 * unit)],
                               radius=int(0.2 * unit), fill=color, outline=outline, width=lw)
        # Cheese
        draw.polygon([(cx - int(2.8 * unit), cy + int(0.5 * unit)),
                      (cx - int(3 * unit), cy + int(1.2 * unit)),
                      (cx - int(1.5 * unit), cy + int(0.8 * unit)),
                      (cx, cy + int(1.3 * unit)),
                      (cx + int(1.5 * unit), cy + int(0.8 * unit)),
                      (cx + int(3 * unit), cy + int(1.2 * unit)),
                      (cx + int(2.8 * unit), cy + int(0.5 * unit))],
                     fill=(255, 210, 60), outline=_darker((255, 210, 60)), width=max(1, lw))
        # Bottom bun
        draw.rounded_rectangle([cx - 3 * unit, cy + unit, cx + 3 * unit, cy + int(2.5 * unit)],
                               radius=int(0.3 * unit), fill=(210, 170, 80), outline=outline, width=lw)

    def _draw_food_icecream(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                            unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw an ice cream cone."""
        # Cone
        draw.polygon([(cx - int(1.5 * unit), cy), (cx, cy + int(3.5 * unit)),
                      (cx + int(1.5 * unit), cy)],
                     fill=(220, 180, 100), outline=_darker((220, 180, 100)), width=lw)
        # Waffle pattern
        for i in range(4):
            y = cy + int(0.5 * unit) + i * int(0.7 * unit)
            draw.line([cx - int((1.3 - i * 0.3) * unit), y,
                       cx + int((1.3 - i * 0.3) * unit), y],
                      fill=_darker((220, 180, 100), 30), width=max(1, lw))
        # Scoops
        scoops = [(cx, cy - int(0.5 * unit), color),
                  (cx - int(0.8 * unit), cy - int(1.8 * unit), _lighter(color, 30)),
                  (cx + int(0.8 * unit), cy - int(1.8 * unit), (255, 240, 200))]
        for sx, sy, sc in scoops:
            r = int(1.2 * unit)
            draw.ellipse([sx - r, sy - r, sx + r, sy + r],
                         fill=sc, outline=outline, width=lw)

    def _draw_food_cupcake(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                           unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a cupcake."""
        # Wrapper
        draw.polygon([(cx - int(1.5 * unit), cy), (cx - int(2 * unit), cy + int(2.5 * unit)),
                      (cx + int(2 * unit), cy + int(2.5 * unit)), (cx + int(1.5 * unit), cy)],
                     fill=(200, 160, 100), outline=outline, width=lw)
        # Wrapper lines
        for i in range(-2, 3):
            wx = cx + int(i * 0.7 * unit)
            draw.line([wx, cy, wx + int(i * 0.1 * unit), cy + int(2.5 * unit)],
                      fill=_darker((200, 160, 100), 30), width=max(1, lw))
        # Frosting swirl
        draw.ellipse([cx - int(1.8 * unit), cy - int(2 * unit), cx + int(1.8 * unit), cy + int(0.5 * unit)],
                     fill=color, outline=outline, width=lw)
        draw.ellipse([cx - int(1.2 * unit), cy - int(2.8 * unit), cx + int(1.2 * unit), cy - int(1 * unit)],
                     fill=_lighter(color, 20), outline=outline, width=lw)
        # Cherry on top
        draw.ellipse([cx - int(0.4 * unit), cy - int(3.5 * unit),
                      cx + int(0.4 * unit), cy - int(2.7 * unit)],
                     fill=(220, 30, 30), outline=_darker((220, 30, 30)), width=lw)

    def _draw_food_donut(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a donut."""
        r = int(2.5 * unit)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=color, outline=outline, width=lw)
        # Icing
        draw.ellipse([cx - r, cy - r, cx + r, cy + int(0.3 * unit)],
                     fill=(255, 120, 160), outline=outline, width=lw)
        # Hole
        hr = int(0.8 * unit)
        draw.ellipse([cx - hr, cy - hr, cx + hr, cy + hr],
                     fill=(255, 255, 255), outline=outline, width=lw)
        # Sprinkles
        import random
        rng = random.Random(42)
        sprinkle_colors = [(255, 80, 80), (80, 200, 80), (80, 80, 255), (255, 255, 80)]
        for _ in range(12):
            sx = cx + rng.randint(-int(2 * unit), int(2 * unit))
            sy = cy + rng.randint(-int(2 * unit), int(0.2 * unit))
            dist = ((sx - cx) ** 2 + (sy - cy) ** 2) ** 0.5
            if hr + int(0.3 * unit) < dist < r - int(0.3 * unit):
                draw.rectangle([sx - 3, sy - 1, sx + 3, sy + 1],
                               fill=rng.choice(sprinkle_colors))

    def _draw_food_fruit(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int, name: str) -> None:
        """Draw a fruit (apple, banana, watermelon)."""
        if name == "apple":
            r = int(2.5 * unit)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         fill=color, outline=outline, width=lw)
            # Highlight
            draw.ellipse([cx - int(1.5 * unit), cy - int(1.8 * unit),
                          cx - int(0.3 * unit), cy - int(0.5 * unit)],
                         fill=_lighter(color, 40))
            # Stem
            draw.rectangle([cx - 2, cy - r - int(0.8 * unit), cx + 2, cy - r + int(0.3 * unit)],
                           fill=(100, 60, 30))
            # Leaf
            draw.ellipse([cx, cy - r - int(0.5 * unit), cx + int(1.2 * unit), cy - r + int(0.2 * unit)],
                         fill=(80, 180, 60))
        elif name == "banana":
            draw.arc([cx - 3 * unit, cy - 2 * unit, cx + 3 * unit, cy + 4 * unit],
                     200, 340, fill=color, width=int(2 * unit))
            draw.arc([cx - 3 * unit, cy - 2 * unit, cx + 3 * unit, cy + 4 * unit],
                     200, 340, fill=outline, width=lw)
        elif name == "watermelon":
            # Half slice
            draw.pieslice([cx - 3 * unit, cy - 3 * unit, cx + 3 * unit, cy + 3 * unit],
                          0, 180, fill=color, outline=outline, width=lw)
            # Red inside
            draw.pieslice([cx - int(2.5 * unit), cy - int(2.5 * unit),
                           cx + int(2.5 * unit), cy + int(2.5 * unit)],
                          0, 180, fill=(220, 40, 40), outline=outline, width=lw)
            # Seeds
            for sx, sy in [(-1, 0.5), (0, 0.3), (1, 0.5), (-0.5, 1), (0.5, 1)]:
                draw.ellipse([cx + int(sx * unit) - 3, cy + int(sy * unit) - 5,
                              cx + int(sx * unit) + 3, cy + int(sy * unit) + 2],
                             fill=(30, 30, 30))

    def _draw_food_cookie(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                          unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a cookie."""
        r = int(2.5 * unit)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=color, outline=outline, width=lw)
        # Chocolate chips
        chips = [(-1, -1), (0.8, -0.5), (-0.5, 0.8), (1, 0.8), (0, -0.2), (-1.2, 0)]
        for sx, sy in chips:
            draw.ellipse([cx + int(sx * unit) - int(0.25 * unit), cy + int(sy * unit) - int(0.2 * unit),
                          cx + int(sx * unit) + int(0.25 * unit), cy + int(sy * unit) + int(0.2 * unit)],
                         fill=(60, 30, 10), outline=(40, 20, 5))

    def _draw_food_cake(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                        unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a birthday cake."""
        # Bottom layer
        draw.rounded_rectangle([cx - 3 * unit, cy, cx + 3 * unit, cy + int(2.5 * unit)],
                               radius=int(0.3 * unit), fill=(240, 200, 160), outline=outline, width=lw)
        # Top layer
        draw.rounded_rectangle([cx - int(2.5 * unit), cy - int(1.5 * unit),
                                cx + int(2.5 * unit), cy + int(0.3 * unit)],
                               radius=int(0.3 * unit), fill=(240, 200, 160), outline=outline, width=lw)
        # Frosting
        draw.rounded_rectangle([cx - int(2.7 * unit), cy - int(0.3 * unit),
                                cx + int(2.7 * unit), cy + int(0.3 * unit)],
                               radius=3, fill=color, outline=outline, width=lw)
        draw.rounded_rectangle([cx - 3 * unit, cy + int(0.8 * unit),
                                cx + 3 * unit, cy + int(1.3 * unit)],
                               radius=3, fill=color, outline=outline, width=lw)
        # Candles
        for i in range(-2, 3):
            candle_x = cx + i * int(0.8 * unit)
            draw.rectangle([candle_x - 3, cy - int(2.8 * unit), candle_x + 3, cy - int(1.5 * unit)],
                           fill=(255, 255, 200), outline=outline, width=max(1, lw))
            # Flame
            draw.ellipse([candle_x - 4, cy - int(3.3 * unit), candle_x + 4, cy - int(2.8 * unit)],
                         fill=(255, 180, 40))

    def _draw_food_taco(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                        unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a taco."""
        # Shell
        draw.pieslice([cx - 3 * unit, cy - 2 * unit, cx + 3 * unit, cy + 4 * unit],
                      200, 340, fill=color, outline=outline, width=lw)
        # Filling: lettuce
        draw.pieslice([cx - int(2.5 * unit), cy - int(1.5 * unit),
                       cx + int(2.5 * unit), cy + int(3.5 * unit)],
                      210, 330, fill=(80, 180, 60), outline=None)
        # Filling: meat
        draw.pieslice([cx - 2 * unit, cy - unit, cx + 2 * unit, cy + 3 * unit],
                      215, 325, fill=(180, 100, 60), outline=None)
        # Cheese
        draw.pieslice([cx - int(1.5 * unit), cy - int(0.5 * unit),
                       cx + int(1.5 * unit), cy + int(2.5 * unit)],
                      220, 320, fill=(255, 210, 60), outline=None)

    def _draw_food_hotdog(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                          unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a hotdog."""
        # Bun bottom
        draw.rounded_rectangle([cx - 3 * unit, cy - int(0.5 * unit), cx + 3 * unit, cy + int(1.5 * unit)],
                               radius=int(0.5 * unit), fill=(220, 180, 100), outline=outline, width=lw)
        # Bun top
        draw.rounded_rectangle([cx - 3 * unit, cy - int(1.5 * unit), cx + 3 * unit, cy + int(0.2 * unit)],
                               radius=int(0.5 * unit), fill=(230, 190, 110), outline=outline, width=lw)
        # Sausage
        draw.rounded_rectangle([cx - int(3.2 * unit), cy - int(0.5 * unit),
                                cx + int(3.2 * unit), cy + int(0.5 * unit)],
                               radius=int(0.3 * unit), fill=color, outline=outline, width=lw)
        # Mustard zigzag
        for i in range(-3, 3):
            x1 = cx + int(i * 0.9 * unit)
            x2 = cx + int((i + 0.5) * 0.9 * unit)
            draw.line([x1, cy - int(0.2 * unit), x2, cy + int(0.2 * unit)],
                      fill=(255, 220, 40), width=lw * 2)

    def _draw_food_fries(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw french fries."""
        # Container
        draw.polygon([(cx - int(1.5 * unit), cy - int(0.5 * unit)),
                      (cx - int(2 * unit), cy + int(2.5 * unit)),
                      (cx + int(2 * unit), cy + int(2.5 * unit)),
                      (cx + int(1.5 * unit), cy - int(0.5 * unit))],
                     fill=(220, 40, 40), outline=outline, width=lw)
        # Fries sticking out
        fry_positions = [-1.2, -0.6, 0, 0.6, 1.2]
        for fx in fry_positions:
            x = cx + int(fx * unit)
            fh = int(2 * unit) + int(abs(fx) * 0.5 * unit)
            draw.rounded_rectangle([x - int(0.2 * unit), cy - fh,
                                    x + int(0.2 * unit), cy],
                                   radius=2, fill=color, outline=outline, width=max(1, lw))

    def _draw_food_lollipop(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                            unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a lollipop."""
        # Stick
        draw.rectangle([cx - 3, cy, cx + 3, cy + int(3.5 * unit)],
                       fill=(200, 180, 140), outline=outline, width=max(1, lw))
        # Candy
        r = int(2.5 * unit)
        draw.ellipse([cx - r, cy - int(2.5 * unit) - r, cx + r, cy - int(2.5 * unit) + r],
                     fill=color, outline=outline, width=lw)
        # Spiral pattern
        for i in range(3):
            ir = r - i * int(0.6 * unit)
            if ir > 0:
                draw.arc([cx - ir, cy - int(2.5 * unit) - ir, cx + ir, cy - int(2.5 * unit) + ir],
                         i * 60, i * 60 + 180, fill=_lighter(color, 40 + i * 20), width=lw * 2)

    def _draw_food_chocolate(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                             unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a chocolate bar."""
        draw.rounded_rectangle([cx - 3 * unit, cy - 2 * unit, cx + 3 * unit, cy + 2 * unit],
                               radius=int(0.3 * unit), fill=color, outline=outline, width=lw)
        # Grid lines
        for i in range(-2, 3):
            draw.line([cx + int(i * 1.2 * unit), cy - 2 * unit,
                       cx + int(i * 1.2 * unit), cy + 2 * unit],
                      fill=outline, width=max(1, lw))
        for i in range(-1, 2):
            draw.line([cx - 3 * unit, cy + int(i * 1.3 * unit),
                       cx + 3 * unit, cy + int(i * 1.3 * unit)],
                      fill=outline, width=max(1, lw))

    def _draw_food_sushi(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw sushi."""
        # Nori wrap
        draw.rounded_rectangle([cx - int(1.8 * unit), cy - int(1.5 * unit),
                                cx + int(1.8 * unit), cy + int(1.5 * unit)],
                               radius=int(0.5 * unit), fill=(30, 60, 30), outline=outline, width=lw)
        # Rice
        draw.rounded_rectangle([cx - int(1.5 * unit), cy - int(1.2 * unit),
                                cx + int(1.5 * unit), cy + int(1.2 * unit)],
                               radius=int(0.4 * unit), fill=color, outline=outline, width=lw)
        # Fish on top
        draw.ellipse([cx - int(1.2 * unit), cy - int(0.8 * unit),
                      cx + int(1.2 * unit), cy + int(0.4 * unit)],
                     fill=(240, 120, 80), outline=outline, width=lw)

    def _draw_food_pancake(self, draw: ImageDraw.ImageDraw, cx: int, cy: int,
                           unit: int, color: tuple, outline: tuple, lw: int) -> None:
        """Draw a pancake stack."""
        # Stack of 3 pancakes
        for i in range(3):
            py = cy + int((2 - i) * 0.8 * unit)
            draw.ellipse([cx - int(2.5 * unit), py - int(0.4 * unit),
                          cx + int(2.5 * unit), py + int(0.4 * unit)],
                         fill=color, outline=outline, width=lw)
        # Butter
        draw.rectangle([cx - int(0.5 * unit), cy - int(0.5 * unit),
                        cx + int(0.5 * unit), cy + int(0.1 * unit)],
                       fill=(255, 240, 150), outline=_darker((255, 240, 150)), width=lw)
        # Syrup drip
        draw.ellipse([cx - int(2 * unit), cy - int(0.8 * unit),
                      cx + int(2 * unit), cy + int(0.3 * unit)],
                     fill=(160, 100, 40), outline=None)
        # Drips
        for dx in [-1.5, 0.5, 1.8]:
            x = cx + int(dx * unit)
            draw.rectangle([x - 3, cy + int(0.3 * unit), x + 3, cy + int(1.2 * unit)],
                           fill=(160, 100, 40))

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
