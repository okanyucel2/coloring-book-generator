"""Tests for advanced page layout configuration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from coloring_book.pdf.layouts import (
    PageLayout,
    PageLayoutPreset,
    MarginConfig,
    get_preset,
    create_custom_layout,
)


class TestPageLayoutPresets:
    """Test predefined page layout presets."""

    def test_preset_default(self):
        """Test DEFAULT preset."""
        layout = get_preset("DEFAULT")
        assert layout is not None
        assert layout.margin_top == 50
        assert layout.margin_bottom == 50

    def test_preset_wide_margins(self):
        """Test WIDE_MARGINS preset."""
        layout = get_preset("WIDE_MARGINS")
        assert layout.margin_left >= 100
        assert layout.margin_right >= 100

    def test_preset_narrow_margins(self):
        """Test NARROW_MARGINS preset."""
        layout = get_preset("NARROW_MARGINS")
        assert layout.margin_left <= 30
        assert layout.margin_right <= 30

    def test_preset_coloring_book(self):
        """Test COLORING_BOOK preset (optimized for coloring)."""
        layout = get_preset("COLORING_BOOK")
        assert layout is not None
        # Coloring books need space for drawings
        assert layout.line_spacing > 1.0

    def test_preset_landscape(self):
        """Test LANDSCAPE preset."""
        layout = get_preset("LANDSCAPE")
        assert layout.orientation == "landscape"

    def test_get_invalid_preset_raises(self):
        """Test getting invalid preset raises error."""
        with pytest.raises(ValueError):
            get_preset("NONEXISTENT")

    def test_list_available_presets(self):
        """Test listing all available presets."""
        presets = PageLayoutPreset.list_presets()
        assert len(presets) > 0
        assert "DEFAULT" in presets
        assert "COLORING_BOOK" in presets

    def test_preset_independence(self):
        """Test each preset is independent."""
        layout1 = get_preset("DEFAULT")
        layout2 = get_preset("WIDE_MARGINS")
        
        assert layout1.margin_left != layout2.margin_left


class TestMarginConfig:
    """Test margin configuration."""

    def test_margin_config_symmetrical(self):
        """Test symmetrical margins."""
        margin = MarginConfig.symmetrical(50)
        assert margin.top == 50
        assert margin.left == 50
        assert margin.right == 50
        assert margin.bottom == 50

    def test_margin_config_asymmetrical(self):
        """Test asymmetrical margins."""
        margin = MarginConfig(top=40, bottom=50, left=60, right=70)
        assert margin.top == 40
        assert margin.bottom == 50
        assert margin.left == 60
        assert margin.right == 70

    def test_margin_config_all_sides(self):
        """Test setting all margins together."""
        margin = MarginConfig.all_sides(30)
        assert margin.top == 30
        assert margin.left == 30
        assert margin.right == 30
        assert margin.bottom == 30

    def test_margin_config_top_bottom(self):
        """Test top/bottom margins with left/right."""
        margin = MarginConfig(top=40, bottom=50, left=60, right=60)
        assert margin.top == 40
        assert margin.bottom == 50
        assert margin.left == 60
        assert margin.right == 60


class TestPageLayoutAdvanced:
    """Test advanced page layout features."""

    def test_layout_with_columns(self):
        """Test creating multi-column layout."""
        layout = PageLayout(columns=2)
        assert layout.columns == 2

    def test_layout_column_gap(self):
        """Test column gap configuration."""
        layout = PageLayout(columns=2, column_gap=20)
        assert layout.column_gap == 20

    def test_layout_header_footer(self):
        """Test header and footer area configuration."""
        layout = PageLayout(has_header=True, has_footer=True, header_height=40)
        assert layout.has_header is True
        assert layout.has_footer is True
        assert layout.header_height == 40

    def test_layout_gutter_margin(self):
        """Test binding gutter margin (for duplex printing)."""
        layout = PageLayout(gutter_margin=30, is_left_page=True)
        assert layout.gutter_margin == 30

    def test_layout_page_numbering(self):
        """Test page numbering configuration."""
        layout = PageLayout(
            page_numbering=True,
            page_number_position="bottom-right",
            page_number_format="{page}"
        )
        assert layout.page_numbering is True
        assert layout.page_number_position == "bottom-right"

    def test_layout_background(self):
        """Test background configuration."""
        layout = PageLayout(background_color=(255, 255, 255))
        assert layout.background_color == (255, 255, 255)

    def test_layout_bleed_area(self):
        """Test bleed area (for printing)."""
        layout = PageLayout(bleed_area=10)
        assert layout.bleed_area == 10

    def test_layout_crop_marks(self):
        """Test crop marks for printing."""
        layout = PageLayout(show_crop_marks=True, crop_mark_distance=5)
        assert layout.show_crop_marks is True
        assert layout.crop_mark_distance == 5


class TestCustomLayoutBuilder:
    """Test building custom layouts."""

    def test_create_custom_layout_basic(self):
        """Test creating custom layout with builder."""
        layout = create_custom_layout(
            name="MyCustom",
            margin_top=40,
            margin_bottom=50
        )
        assert layout is not None
        assert layout.margin_top == 40
        assert layout.margin_bottom == 50

    def test_create_custom_layout_full(self):
        """Test creating fully configured custom layout."""
        layout = create_custom_layout(
            name="FullConfig",
            margin_top=50,
            margin_bottom=50,
            margin_left=60,
            margin_right=60,
            columns=2,
            has_header=True,
            has_footer=True,
            page_numbering=True
        )
        assert layout.columns == 2
        assert layout.has_header is True
        assert layout.page_numbering is True

    def test_custom_layout_chainable_config(self):
        """Test custom layout configuration is chainable."""
        layout = create_custom_layout("Test")
        result = layout.set_margins(top=40, bottom=40)
        
        assert result is layout or result is None


class TestLayoutCalculations:
    """Test layout calculations."""

    def test_available_width_single_column(self):
        """Test calculating available width (single column)."""
        layout = PageLayout(margin_left=50, margin_right=50)
        width = layout.get_available_width()
        
        assert width > 0
        assert width == 595 - 50 - 50  # A4 minus margins

    def test_available_width_multi_column(self):
        """Test calculating available width (multi-column)."""
        layout = PageLayout(columns=2, column_gap=20, margin_left=50, margin_right=50)
        column_width = layout.get_column_width()
        
        assert column_width > 0
        # (Available width - gaps) / columns
        expected = (595 - 50 - 50 - 20) / 2
        assert column_width == expected

    def test_available_height_with_header_footer(self):
        """Test calculating available height with header/footer."""
        layout = PageLayout(
            has_header=True,
            header_height=40,
            has_footer=True,
            footer_height=30,
            margin_top=50,
            margin_bottom=50
        )
        height = layout.get_available_height()
        
        assert height > 0
        assert height == 842 - 50 - 50 - 40 - 30  # A4 minus margins and header/footer

    def test_content_area_rect(self):
        """Test getting content area rectangle."""
        layout = PageLayout(margin_left=50, margin_top=40)
        rect = layout.get_content_area()
        
        assert rect["x"] == 50
        assert rect["y"] == 40
        assert rect["width"] > 0
        assert rect["height"] > 0


class TestLayoutValidation:
    """Test layout validation."""

    def test_validate_margins_positive(self):
        """Test margins must be non-negative."""
        with pytest.raises(ValueError):
            PageLayout(margin_left=-10)

    def test_validate_font_size_positive(self):
        """Test font size must be positive."""
        with pytest.raises(ValueError):
            PageLayout(font_size=0)

    def test_validate_columns_at_least_one(self):
        """Test columns must be at least 1."""
        with pytest.raises(ValueError):
            PageLayout(columns=0)

    def test_validate_column_gap_non_negative(self):
        """Test column gap must be non-negative."""
        with pytest.raises(ValueError):
            PageLayout(column_gap=-5)

    def test_validate_orientation(self):
        """Test orientation must be valid."""
        with pytest.raises(ValueError):
            PageLayout(orientation="diagonal")


class TestLayoutIntegration:
    """Integration tests for layouts."""

    def test_preset_layout_is_valid(self):
        """Test preset layouts are valid."""
        presets = PageLayoutPreset.list_presets()
        for preset_name in presets:
            layout = get_preset(preset_name)
            assert layout is not None
            assert layout.margin_top >= 0
            assert layout.font_size > 0

    def test_use_preset_in_document(self):
        """Test using preset layout in PDF generation."""
        from coloring_book.pdf.generator import PDFGenerator
        
        layout = get_preset("COLORING_BOOK")
        gen = PDFGenerator()
        page = gen.add_page(layout=layout)
        page.add_text("Test content")
        
        pdf_bytes = gen.generate()
        assert pdf_bytes.startswith(b"%PDF")

    def test_custom_layout_in_document(self):
        """Test using custom layout in PDF generation."""
        from coloring_book.pdf.generator import PDFGenerator
        
        layout = create_custom_layout(
            "Custom",
            margin_top=60,
            margin_left=70,
            columns=2
        )
        gen = PDFGenerator()
        page = gen.add_page(layout=layout)
        page.add_text("Column 1 content")
        
        pdf_bytes = gen.generate()
        assert pdf_bytes.startswith(b"%PDF")
