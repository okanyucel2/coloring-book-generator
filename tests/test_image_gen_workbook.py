"""Tests for workbook image generation pipeline."""

import io

import pytest
from PIL import Image

from coloring_book.workbook.image_gen import (
    CLIPART_PROMPT,
    WorkbookImageGenerator,
    _hsl_to_rgb,
)
from coloring_book.workbook.models import WorkbookItem


class TestHSLToRGB:
    def test_red(self):
        r, g, b = _hsl_to_rgb(0, 1.0, 0.5)
        assert r == 255
        assert g == 0
        assert b == 0

    def test_green(self):
        r, g, b = _hsl_to_rgb(120, 1.0, 0.5)
        assert g == 255

    def test_blue(self):
        r, g, b = _hsl_to_rgb(240, 1.0, 0.5)
        assert b == 255

    def test_white(self):
        r, g, b = _hsl_to_rgb(0, 0.0, 1.0)
        assert (r, g, b) == (255, 255, 255)

    def test_black(self):
        r, g, b = _hsl_to_rgb(0, 0.0, 0.0)
        assert (r, g, b) == (0, 0, 0)

    def test_gray(self):
        r, g, b = _hsl_to_rgb(0, 0.0, 0.5)
        assert r == g == b == 127


class TestWorkbookImageGenerator:
    @pytest.fixture
    def gen(self):
        return WorkbookImageGenerator(ai_enabled=False, image_size=(256, 256))

    def test_init_defaults(self):
        gen = WorkbookImageGenerator()
        assert gen.ai_enabled is True
        assert gen.image_size == (512, 512)

    def test_init_custom(self):
        gen = WorkbookImageGenerator(
            ai_enabled=False, image_size=(256, 256), ai_timeout=10.0,
        )
        assert gen.ai_enabled is False
        assert gen.image_size == (256, 256)
        assert gen.ai_timeout == 10.0

    def test_generate_placeholder_colored(self, gen):
        colored = gen._generate_placeholder_colored("fire_truck")
        assert isinstance(colored, bytes)
        assert len(colored) > 0

        # Verify it's a valid PNG
        img = Image.open(io.BytesIO(colored))
        assert img.format == "PNG"
        assert img.size == (256, 256)

    def test_generate_placeholder_different_items_different_colors(self, gen):
        img1 = gen._generate_placeholder_colored("fire_truck")
        img2 = gen._generate_placeholder_colored("ambulance")
        # Different items should produce different images
        assert img1 != img2

    def test_image_to_outline(self, gen):
        colored = gen._generate_placeholder_colored("cat")
        outline = gen._image_to_outline(colored)

        assert isinstance(outline, bytes)
        img = Image.open(io.BytesIO(outline))
        assert img.format == "PNG"
        assert img.size == (256, 256)

    def test_outline_is_mostly_white_and_black(self, gen):
        colored = gen._generate_placeholder_colored("dog")
        outline = gen._image_to_outline(colored)

        img = Image.open(io.BytesIO(outline)).convert("L")
        import numpy as np
        arr = np.array(img)
        # Most pixels should be white (255) or near-black
        white_pixels = (arr > 200).sum()
        total = arr.size
        assert white_pixels / total > 0.5, "Outline should be mostly white background"

    def test_outline_to_dashed(self, gen):
        colored = gen._generate_placeholder_colored("cat")
        outline = gen._image_to_outline(colored)
        dashed = gen._outline_to_dashed(outline)

        assert isinstance(dashed, bytes)
        img = Image.open(io.BytesIO(dashed))
        assert img.format == "PNG"
        assert img.size == (256, 256)

    def test_dashed_has_fewer_dark_pixels_than_outline(self, gen):
        colored = gen._generate_placeholder_colored("elephant")
        outline = gen._image_to_outline(colored)
        dashed = gen._outline_to_dashed(outline)

        import numpy as np
        outline_arr = np.array(Image.open(io.BytesIO(outline)).convert("L"))
        dashed_arr = np.array(Image.open(io.BytesIO(dashed)).convert("L"))

        outline_dark = (outline_arr < 128).sum()
        dashed_dark = (dashed_arr < 128).sum()

        # Dashed version should have fewer dark pixels (gaps in lines)
        assert dashed_dark <= outline_dark

    @pytest.mark.asyncio
    async def test_generate_item_no_ai(self, gen):
        item = await gen.generate_item("fire_truck", "vehicle")

        assert isinstance(item, WorkbookItem)
        assert item.name == "fire_truck"
        assert item.category == "vehicle"
        assert item.colored_image is not None
        assert item.outline_image is not None
        assert item.dashed_image is not None
        assert item.has_all_assets is True

    @pytest.mark.asyncio
    async def test_generate_items_batch(self, gen):
        items = [("cat", "animal"), ("dog", "animal"), ("fire_truck", "vehicle")]
        results = await gen.generate_items_batch(items)

        assert len(results) == 3
        for item in results:
            assert isinstance(item, WorkbookItem)
            assert item.has_all_assets is True

    @pytest.mark.asyncio
    async def test_generate_item_images_are_valid_pngs(self, gen):
        item = await gen.generate_item("cat", "animal")

        for img_bytes in [item.colored_image, item.outline_image, item.dashed_image]:
            img = Image.open(io.BytesIO(img_bytes))
            assert img.format == "PNG"


class TestClipartPromptTemplate:
    def test_prompt_contains_placeholder(self):
        assert "{item_name}" in CLIPART_PROMPT

    def test_prompt_formats_correctly(self):
        result = CLIPART_PROMPT.format(item_name="fire truck")
        assert "fire truck" in result
        assert "{" not in result
