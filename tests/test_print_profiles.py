"""Tests for PrintProfile and presets."""

import pytest
from coloring_book.pdf.profiles import PrintProfile, PROFILES, get_profile


class TestPrintProfile:
    def test_home_preset_values(self):
        p = PROFILES["home"]
        assert p.dpi == 150
        assert p.color_space == "rgb"
        assert p.bleed_mm == 0
        assert p.show_crop_marks is False
        assert p.jpeg_quality == 85
        assert p.max_file_size_mb == 0

    def test_etsy_standard_preset_values(self):
        p = PROFILES["etsy_standard"]
        assert p.dpi == 300
        assert p.color_space == "grayscale"
        assert p.bleed_mm == 0
        assert p.show_crop_marks is False
        assert p.jpeg_quality == 90
        assert p.max_file_size_mb == 20

    def test_pro_print_preset_values(self):
        p = PROFILES["pro_print"]
        assert p.dpi == 300
        assert p.color_space == "rgb"
        assert p.bleed_mm == 3
        assert p.show_crop_marks is True
        assert p.jpeg_quality == 95

    def test_poster_preset_values(self):
        p = PROFILES["poster"]
        assert p.dpi == 300
        assert p.bleed_mm == 5
        assert p.show_crop_marks is True

    def test_all_four_presets_exist(self):
        assert set(PROFILES.keys()) == {"home", "etsy_standard", "pro_print", "poster"}

    def test_profiles_are_frozen(self):
        p = PROFILES["home"]
        with pytest.raises(AttributeError):
            p.dpi = 300  # type: ignore[misc]

    def test_bleed_points_conversion(self):
        p = PROFILES["pro_print"]
        # 3mm * 2.8346 = ~8.5 points
        assert 8.0 < p.bleed_points < 9.0

    def test_bleed_points_zero_for_home(self):
        p = PROFILES["home"]
        assert p.bleed_points == 0

    def test_get_profile_valid(self):
        p = get_profile("etsy_standard")
        assert p.name == "etsy_standard"

    def test_get_profile_invalid(self):
        with pytest.raises(ValueError, match="Unknown profile"):
            get_profile("nonexistent")

    def test_custom_profile_creation(self):
        p = PrintProfile(
            name="custom",
            dpi=600,
            color_space="rgb",
            bleed_mm=10,
            show_crop_marks=True,
            jpeg_quality=100,
            max_file_size_mb=50,
            page_size="a4",
        )
        assert p.dpi == 600
        assert p.bleed_mm == 10

    def test_invalid_dpi_low(self):
        with pytest.raises(ValueError, match="DPI must be"):
            PrintProfile(
                name="bad", dpi=10, color_space="rgb", bleed_mm=0,
                show_crop_marks=False, jpeg_quality=90,
                max_file_size_mb=0, page_size="letter",
            )

    def test_invalid_dpi_high(self):
        with pytest.raises(ValueError, match="DPI must be"):
            PrintProfile(
                name="bad", dpi=1200, color_space="rgb", bleed_mm=0,
                show_crop_marks=False, jpeg_quality=90,
                max_file_size_mb=0, page_size="letter",
            )

    def test_invalid_color_space(self):
        with pytest.raises(ValueError, match="color_space"):
            PrintProfile(
                name="bad", dpi=300, color_space="cmyk", bleed_mm=0,
                show_crop_marks=False, jpeg_quality=90,
                max_file_size_mb=0, page_size="letter",
            )

    def test_invalid_jpeg_quality(self):
        with pytest.raises(ValueError, match="jpeg_quality"):
            PrintProfile(
                name="bad", dpi=300, color_space="rgb", bleed_mm=0,
                show_crop_marks=False, jpeg_quality=0,
                max_file_size_mb=0, page_size="letter",
            )

    def test_negative_bleed(self):
        with pytest.raises(ValueError, match="bleed_mm"):
            PrintProfile(
                name="bad", dpi=300, color_space="rgb", bleed_mm=-1,
                show_crop_marks=False, jpeg_quality=90,
                max_file_size_mb=0, page_size="letter",
            )
