"""Tests for improved image generation with category-specific placeholders.

Validates that the enhanced PIL-drawn placeholders produce valid PNGs
at the correct size, and that outline/dashed conversions work properly
for both vehicle and animal categories.
"""

import io

import numpy as np
import pytest
from PIL import Image

from coloring_book.workbook.image_gen import (
    ANIMAL_COLORS,
    VEHICLE_COLORS,
    WorkbookImageGenerator,
    _darker,
    _hsl_to_rgb,
    _lighter,
)
from coloring_book.workbook.models import WorkbookItem


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def gen_256():
    """Generator with AI disabled and 256x256 images."""
    return WorkbookImageGenerator(ai_enabled=False, image_size=(256, 256))


@pytest.fixture
def gen_512():
    """Generator with AI disabled and 512x512 images."""
    return WorkbookImageGenerator(ai_enabled=False, image_size=(512, 512))


# ──────────────────────────────────────────────────────────────────────
# Helper to validate PNG bytes
# ──────────────────────────────────────────────────────────────────────

def _assert_valid_png(data: bytes, expected_size: tuple[int, int]) -> Image.Image:
    """Assert that data is a valid PNG with the expected dimensions."""
    assert isinstance(data, bytes), "Image data must be bytes"
    assert len(data) > 100, "Image data too small to be a valid PNG"

    img = Image.open(io.BytesIO(data))
    assert img.format == "PNG", f"Expected PNG format, got {img.format}"
    assert img.size == expected_size, f"Expected size {expected_size}, got {img.size}"
    return img


# ──────────────────────────────────────────────────────────────────────
# Core placeholder tests
# ──────────────────────────────────────────────────────────────────────

class TestPlaceholderGeneratesValidPNG:
    """Test that placeholder images are valid PNGs."""

    def test_vehicle_placeholder_is_valid_png(self, gen_256):
        colored = gen_256._generate_placeholder_colored("fire_truck", "vehicle")
        _assert_valid_png(colored, (256, 256))

    def test_animal_placeholder_is_valid_png(self, gen_256):
        colored = gen_256._generate_placeholder_colored("cat", "animal")
        _assert_valid_png(colored, (256, 256))

    def test_generic_placeholder_is_valid_png(self, gen_256):
        colored = gen_256._generate_placeholder_colored("unknown_item", "other")
        _assert_valid_png(colored, (256, 256))

    def test_placeholder_512_is_valid(self, gen_512):
        colored = gen_512._generate_placeholder_colored("fire_truck", "vehicle")
        _assert_valid_png(colored, (512, 512))


class TestPlaceholderCorrectSize:
    """Test that placeholders respect the configured image_size."""

    def test_256x256(self, gen_256):
        colored = gen_256._generate_placeholder_colored("dog", "animal")
        img = _assert_valid_png(colored, (256, 256))
        assert img.size == (256, 256)

    def test_512x512(self, gen_512):
        colored = gen_512._generate_placeholder_colored("cat", "animal")
        img = _assert_valid_png(colored, (512, 512))
        assert img.size == (512, 512)

    def test_custom_size(self):
        gen = WorkbookImageGenerator(ai_enabled=False, image_size=(320, 320))
        colored = gen._generate_placeholder_colored("elephant", "animal")
        img = _assert_valid_png(colored, (320, 320))
        assert img.size == (320, 320)


# ──────────────────────────────────────────────────────────────────────
# Outline conversion tests
# ──────────────────────────────────────────────────────────────────────

class TestOutlineFromColored:
    """Test colored -> outline conversion."""

    def test_outline_is_valid_png(self, gen_256):
        colored = gen_256._generate_placeholder_colored("fire_truck", "vehicle")
        outline = gen_256._image_to_outline(colored)
        _assert_valid_png(outline, (256, 256))

    def test_outline_is_mostly_white(self, gen_256):
        colored = gen_256._generate_placeholder_colored("cat", "animal")
        outline = gen_256._image_to_outline(colored)

        img = Image.open(io.BytesIO(outline)).convert("L")
        arr = np.array(img)
        white_ratio = (arr > 200).sum() / arr.size
        assert white_ratio > 0.5, f"Outline should be mostly white, got {white_ratio:.2%}"

    def test_outline_has_dark_lines(self, gen_256):
        colored = gen_256._generate_placeholder_colored("elephant", "animal")
        outline = gen_256._image_to_outline(colored)

        img = Image.open(io.BytesIO(outline)).convert("L")
        arr = np.array(img)
        dark_pixels = (arr < 128).sum()
        assert dark_pixels > 0, "Outline should have some dark pixels (lines)"

    def test_outline_from_vehicle(self, gen_256):
        colored = gen_256._generate_placeholder_colored("police_car", "vehicle")
        outline = gen_256._image_to_outline(colored)
        _assert_valid_png(outline, (256, 256))

    def test_outline_from_generic(self, gen_256):
        colored = gen_256._generate_placeholder_colored("spaceship", "other")
        outline = gen_256._image_to_outline(colored)
        _assert_valid_png(outline, (256, 256))


# ──────────────────────────────────────────────────────────────────────
# Dashed conversion tests
# ──────────────────────────────────────────────────────────────────────

class TestDashedFromOutline:
    """Test outline -> dashed conversion."""

    def test_dashed_is_valid_png(self, gen_256):
        colored = gen_256._generate_placeholder_colored("fire_truck", "vehicle")
        outline = gen_256._image_to_outline(colored)
        dashed = gen_256._outline_to_dashed(outline)
        _assert_valid_png(dashed, (256, 256))

    def test_dashed_has_fewer_dark_pixels_than_outline(self, gen_256):
        colored = gen_256._generate_placeholder_colored("dog", "animal")
        outline = gen_256._image_to_outline(colored)
        dashed = gen_256._outline_to_dashed(outline)

        outline_arr = np.array(Image.open(io.BytesIO(outline)).convert("L"))
        dashed_arr = np.array(Image.open(io.BytesIO(dashed)).convert("L"))

        outline_dark = (outline_arr < 128).sum()
        dashed_dark = (dashed_arr < 128).sum()

        assert dashed_dark <= outline_dark, (
            f"Dashed ({dashed_dark}) should have <= dark pixels than outline ({outline_dark})"
        )

    def test_dashed_is_mostly_white(self, gen_256):
        colored = gen_256._generate_placeholder_colored("cat", "animal")
        outline = gen_256._image_to_outline(colored)
        dashed = gen_256._outline_to_dashed(outline)

        img = Image.open(io.BytesIO(dashed)).convert("L")
        arr = np.array(img)
        white_ratio = (arr > 200).sum() / arr.size
        assert white_ratio > 0.5, f"Dashed should be mostly white, got {white_ratio:.2%}"


# ──────────────────────────────────────────────────────────────────────
# Vehicle-specific placeholder tests
# ──────────────────────────────────────────────────────────────────────

class TestVehicleSpecificPlaceholder:
    """Test that each vehicle type generates a unique, valid image."""

    VEHICLE_NAMES = list(VEHICLE_COLORS.keys())

    @pytest.mark.parametrize("vehicle_name", VEHICLE_NAMES)
    def test_vehicle_produces_valid_png(self, gen_256, vehicle_name):
        colored = gen_256._generate_placeholder_colored(vehicle_name, "vehicle")
        _assert_valid_png(colored, (256, 256))

    def test_different_vehicles_produce_different_images(self, gen_256):
        fire_truck = gen_256._generate_placeholder_colored("fire_truck", "vehicle")
        police_car = gen_256._generate_placeholder_colored("police_car", "vehicle")
        assert fire_truck != police_car, "Different vehicles should produce different images"

    @pytest.mark.parametrize("vehicle_name", VEHICLE_NAMES)
    def test_vehicle_has_non_white_content(self, gen_256, vehicle_name):
        colored = gen_256._generate_placeholder_colored(vehicle_name, "vehicle")
        img = Image.open(io.BytesIO(colored)).convert("L")
        arr = np.array(img)
        non_white = (arr < 250).sum()
        assert non_white > 100, (
            f"Vehicle '{vehicle_name}' should have drawn content, not just white"
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_fire_truck(self, gen_256):
        item = await gen_256.generate_item("fire_truck", "vehicle")
        assert isinstance(item, WorkbookItem)
        assert item.has_all_assets is True
        for img_bytes in [item.colored_image, item.outline_image, item.dashed_image]:
            _assert_valid_png(img_bytes, (256, 256))

    @pytest.mark.asyncio
    async def test_full_pipeline_traffic_light(self, gen_256):
        item = await gen_256.generate_item("traffic_light", "vehicle")
        assert isinstance(item, WorkbookItem)
        assert item.has_all_assets is True


# ──────────────────────────────────────────────────────────────────────
# Animal-specific placeholder tests
# ──────────────────────────────────────────────────────────────────────

class TestAnimalSpecificPlaceholder:
    """Test that each animal type generates a unique, valid image."""

    ANIMAL_NAMES = list(ANIMAL_COLORS.keys())

    @pytest.mark.parametrize("animal_name", ANIMAL_NAMES)
    def test_animal_produces_valid_png(self, gen_256, animal_name):
        colored = gen_256._generate_placeholder_colored(animal_name, "animal")
        _assert_valid_png(colored, (256, 256))

    def test_different_animals_produce_different_images(self, gen_256):
        cat = gen_256._generate_placeholder_colored("cat", "animal")
        dog = gen_256._generate_placeholder_colored("dog", "animal")
        assert cat != dog, "Different animals should produce different images"

    @pytest.mark.parametrize("animal_name", ANIMAL_NAMES)
    def test_animal_has_non_white_content(self, gen_256, animal_name):
        colored = gen_256._generate_placeholder_colored(animal_name, "animal")
        img = Image.open(io.BytesIO(colored)).convert("L")
        arr = np.array(img)
        non_white = (arr < 250).sum()
        assert non_white > 100, (
            f"Animal '{animal_name}' should have drawn content, not just white"
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_cat(self, gen_256):
        item = await gen_256.generate_item("cat", "animal")
        assert isinstance(item, WorkbookItem)
        assert item.has_all_assets is True
        for img_bytes in [item.colored_image, item.outline_image, item.dashed_image]:
            _assert_valid_png(img_bytes, (256, 256))

    @pytest.mark.asyncio
    async def test_full_pipeline_butterfly(self, gen_256):
        item = await gen_256.generate_item("butterfly", "animal")
        assert isinstance(item, WorkbookItem)
        assert item.has_all_assets is True


# ──────────────────────────────────────────────────────────────────────
# Color utility tests
# ──────────────────────────────────────────────────────────────────────

class TestColorUtilities:
    """Test helper color functions."""

    def test_darker_reduces_values(self):
        result = _darker((200, 150, 100), 50)
        assert result == (150, 100, 50)

    def test_darker_clamps_to_zero(self):
        result = _darker((20, 10, 5), 30)
        assert result == (0, 0, 0)

    def test_lighter_increases_values(self):
        result = _lighter((100, 150, 200), 50)
        assert result == (150, 200, 250)

    def test_lighter_clamps_to_255(self):
        result = _lighter((240, 250, 255), 30)
        assert result == (255, 255, 255)


# ──────────────────────────────────────────────────────────────────────
# Batch generation test
# ──────────────────────────────────────────────────────────────────────

class TestBatchGeneration:
    """Test batch generation with mixed categories."""

    @pytest.mark.asyncio
    async def test_mixed_batch(self, gen_256):
        items = [
            ("fire_truck", "vehicle"),
            ("cat", "animal"),
            ("school_bus", "vehicle"),
            ("elephant", "animal"),
        ]
        results = await gen_256.generate_items_batch(items)
        assert len(results) == 4
        for item in results:
            assert isinstance(item, WorkbookItem)
            assert item.has_all_assets is True

    @pytest.mark.asyncio
    async def test_unknown_category_still_works(self, gen_256):
        item = await gen_256.generate_item("alien_spaceship", "sci_fi")
        assert isinstance(item, WorkbookItem)
        assert item.has_all_assets is True
        _assert_valid_png(item.colored_image, (256, 256))
