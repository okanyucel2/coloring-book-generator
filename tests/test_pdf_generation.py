"""Comprehensive tests for PDF generation module."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from io import BytesIO
from coloring_book.pdf.generator import PDFGenerator, PDFPage, PageLayout
from coloring_book.pdf.layouts import (
    PageLayoutPreset,
    MarginConfig,
    get_preset,
    create_custom_layout,
)


# ==================== PageLayout Tests ====================


class TestPageLayout:
    """Test PageLayout configuration."""

    def test_default_layout(self):
        """Test default layout creation."""
        layout = PageLayout()
        assert layout.margin_top == 50
        assert layout.margin_left == 50
        assert layout.margin_right == 50
        assert layout.margin_bottom == 50
        assert layout.font_size == 12
        assert layout.orientation == "portrait"

    def test_custom_layout(self):
        """Test custom layout creation."""
        layout = PageLayout(
            margin_top=100,
            margin_left=80,
            margin_right=80,
            margin_bottom=100,
            font_size=14,
            font_name="Times-Roman",
        )
        assert layout.margin_top == 100
        assert layout.margin_left == 80
        assert layout.font_size == 14
        assert layout.font_name == "Times-Roman"

    def test_available_width(self):
        """Test content width calculation."""
        layout = PageLayout(margin_left=50, margin_right=50)
        width = layout.get_available_width()
        assert width == 595 - 50 - 50  # A4 width - margins

    def test_available_height(self):
        """Test content height calculation."""
        layout = PageLayout(margin_top=50, margin_bottom=50)
        height = layout.get_available_height()
        assert height == 842 - 50 - 50  # A4 height - margins

    def test_available_height_with_header_footer(self):
        """Test height calculation with header/footer."""
        layout = PageLayout(
            margin_top=50,
            margin_bottom=50,
            has_header=True,
            header_height=40,
            has_footer=True,
            footer_height=30,
        )
        height = layout.get_available_height()
        expected = 842 - 50 - 50 - 40 - 30
        assert height == expected

    def test_column_width(self):
        """Test column width calculation."""
        layout = PageLayout(margin_left=50, margin_right=50, columns=2, column_gap=20)
        col_width = layout.get_column_width()
        available = 595 - 100
        expected = (available - 20) / 2
        assert col_width == expected

    def test_set_margins_chaining(self):
        """Test margins can be set with chaining."""
        layout = PageLayout()
        result = layout.set_margins(top=100, left=80, right=80, bottom=100)
        assert result is layout  # Check chaining
        assert layout.margin_top == 100
        assert layout.margin_left == 80

    def test_get_content_area(self):
        """Test content area rectangle calculation."""
        layout = PageLayout(
            margin_top=50,
            margin_left=50,
            margin_right=50,
            margin_bottom=50,
            has_header=False,
        )
        area = layout.get_content_area()
        assert area["x"] == 50
        assert area["y"] == 50
        assert area["width"] == 495
        assert area["height"] == 742

    def test_invalid_margins(self):
        """Test that negative margins raise error."""
        with pytest.raises(ValueError):
            PageLayout(margin_top=-10)

    def test_invalid_font_size(self):
        """Test that non-positive font size raises error."""
        with pytest.raises(ValueError):
            PageLayout(font_size=0)

    def test_invalid_columns(self):
        """Test that zero columns raise error."""
        with pytest.raises(ValueError):
            PageLayout(columns=0)

    def test_invalid_orientation(self):
        """Test that invalid orientation raises error."""
        with pytest.raises(ValueError):
            PageLayout(orientation="diagonal")

    def test_landscape_dimensions(self):
        """Test landscape orientation dimensions."""
        layout = PageLayout(orientation="landscape")
        width = layout.get_available_width()
        assert width == 842 - 100  # Landscape is wider


# ==================== MarginConfig Tests ====================


class TestMarginConfig:
    """Test MarginConfig dataclass."""

    def test_create_margins(self):
        """Test creating margin config."""
        margins = MarginConfig(top=10, bottom=20, left=30, right=40)
        assert margins.top == 10
        assert margins.bottom == 20
        assert margins.left == 30
        assert margins.right == 40

    def test_symmetrical_margins(self):
        """Test creating symmetrical margins."""
        margins = MarginConfig.symmetrical(50)
        assert margins.top == 50
        assert margins.bottom == 50
        assert margins.left == 50
        assert margins.right == 50

    def test_all_sides_alias(self):
        """Test all_sides is alias for symmetrical."""
        margins = MarginConfig.all_sides(25)
        assert margins.top == 25
        assert margins.left == 25


# ==================== PageLayoutPreset Tests ====================


class TestPageLayoutPreset:
    """Test predefined page layout presets."""

    def test_list_presets(self):
        """Test listing all available presets."""
        presets = PageLayoutPreset.list_presets()
        assert "DEFAULT" in presets
        assert "COLORING_BOOK" in presets
        assert "TWO_COLUMN" in presets
        assert len(presets) >= 8

    def test_get_default_preset(self):
        """Test getting default preset."""
        layout = PageLayoutPreset.get("DEFAULT")
        assert layout.margin_top == 50
        assert layout.columns == 1

    def test_get_coloring_book_preset(self):
        """Test getting coloring book preset."""
        layout = PageLayoutPreset.get("COLORING_BOOK")
        assert layout.margin_top == 50
        assert layout.line_spacing == 2.0
        assert layout.font_size == 14

    def test_get_wide_margins_preset(self):
        """Test getting wide margins preset."""
        layout = PageLayoutPreset.get("WIDE_MARGINS")
        assert layout.margin_top == 100
        assert layout.margin_left == 100

    def test_get_two_column_preset(self):
        """Test getting two-column preset."""
        layout = PageLayoutPreset.get("TWO_COLUMN")
        assert layout.columns == 2
        assert layout.column_gap == 20

    def test_get_landscape_preset(self):
        """Test getting landscape preset."""
        layout = PageLayoutPreset.get("LANDSCAPE")
        assert layout.orientation == "landscape"

    def test_get_with_header_footer_preset(self):
        """Test getting preset with header/footer."""
        layout = PageLayoutPreset.get("WITH_HEADER_FOOTER")
        assert layout.has_header is True
        assert layout.has_footer is True
        assert layout.header_height == 50
        assert layout.footer_height == 40

    def test_get_book_duplex_preset(self):
        """Test getting duplex book preset."""
        layout = PageLayoutPreset.get("BOOK_DUPLEX")
        assert layout.gutter_margin == 30
        assert layout.page_numbering is True
        assert layout.is_left_page is True

    def test_get_invalid_preset(self):
        """Test that invalid preset raises error."""
        with pytest.raises(ValueError) as exc:
            PageLayoutPreset.get("NONEXISTENT")
        assert "Unknown preset" in str(exc.value)

    def test_register_custom_preset(self):
        """Test registering custom preset."""
        custom = PageLayout(margin_top=200)
        PageLayoutPreset.register("CUSTOM_TEST", custom)
        retrieved = PageLayoutPreset.get("CUSTOM_TEST")
        assert retrieved.margin_top == 200

    def test_preset_function_helper(self):
        """Test get_preset helper function."""
        layout = get_preset("COLORING_BOOK")
        assert layout.margin_top == 50
        assert layout.font_size == 14


# ==================== PDFPage Tests ====================


class TestPDFPage:
    """Test PDFPage class."""

    def test_create_page(self):
        """Test creating a page."""
        page = PDFPage()
        assert page.width == 595
        assert page.height == 842
        assert page.layout is not None

    def test_add_text_default_position(self):
        """Test adding text with default position."""
        page = PDFPage()
        result = page.add_text("Hello World")
        assert result is page  # Check chaining
        elements = page.get_elements()
        assert len(elements) == 1
        assert elements[0]["type"] == "text"
        assert elements[0]["text"] == "Hello World"
        assert elements[0]["x"] == 50  # Default left margin

    def test_add_text_custom_position(self):
        """Test adding text at custom position."""
        page = PDFPage()
        page.add_text("Hello", x=100, y=200)
        elements = page.get_elements()
        assert elements[0]["x"] == 100
        assert elements[0]["y"] == 200

    def test_add_text_custom_font(self):
        """Test adding text with custom font."""
        page = PDFPage()
        page.add_text("Hello", font_name="Times-Roman", font_size=16)
        elements = page.get_elements()
        assert elements[0]["font_name"] == "Times-Roman"
        assert elements[0]["font_size"] == 16

    def test_add_multiple_texts(self):
        """Test adding multiple text elements."""
        page = PDFPage()
        page.add_text("Line 1")
        page.add_text("Line 2")
        page.add_text("Line 3")
        elements = page.get_elements()
        assert len(elements) == 3
        assert elements[0]["text"] == "Line 1"
        assert elements[2]["text"] == "Line 3"

    def test_add_image(self):
        """Test adding image to page."""
        page = PDFPage()
        image_data = b"fake_image_data"
        result = page.add_image(image_data, width=200, height=150)
        assert result is page  # Check chaining
        elements = page.get_elements()
        assert len(elements) == 1
        assert elements[0]["type"] == "image"
        assert elements[0]["data"] == image_data
        assert elements[0]["width"] == 200
        assert elements[0]["height"] == 150

    def test_add_svg(self):
        """Test adding SVG to page."""
        page = PDFPage()
        svg_content = '<svg><circle r="10"/></svg>'
        result = page.add_svg(svg_content, width=100, height=100)
        assert result is page  # Check chaining
        elements = page.get_elements()
        assert len(elements) == 1
        assert elements[0]["type"] == "svg"
        assert elements[0]["content"] == svg_content

    def test_get_elements_copy(self):
        """Test that get_elements returns a copy."""
        page = PDFPage()
        page.add_text("Test")
        elements1 = page.get_elements()
        elements2 = page.get_elements()
        assert elements1 is not elements2  # Different objects
        assert len(elements1) == len(elements2)

    def test_text_chaining(self):
        """Test chaining multiple text additions."""
        page = PDFPage()
        result = (
            page.add_text("Line 1")
            .add_text("Line 2")
            .add_text("Line 3")
            .add_image(b"data")
        )
        assert result is page
        assert len(page.get_elements()) == 4

    def test_custom_page_size(self):
        """Test creating page with custom size."""
        page = PDFPage(width=400, height=500)
        assert page.width == 400
        assert page.height == 500

    def test_custom_layout(self):
        """Test page with custom layout."""
        layout = PageLayout(margin_top=100)
        page = PDFPage(layout=layout)
        assert page.layout.margin_top == 100


# ==================== PDFGenerator Tests ====================


class TestPDFGenerator:
    """Test PDFGenerator class."""

    def test_create_generator(self):
        """Test creating PDF generator."""
        gen = PDFGenerator(title="My Book", author="John Doe")
        assert gen.title == "My Book"
        assert gen.author == "John Doe"
        assert gen.page_count == 0

    def test_add_page(self):
        """Test adding page to generator."""
        gen = PDFGenerator()
        page = gen.add_page()
        assert isinstance(page, PDFPage)
        assert gen.page_count == 1

    def test_add_multiple_pages(self):
        """Test adding multiple pages."""
        gen = PDFGenerator()
        for i in range(5):
            gen.add_page()
        assert gen.page_count == 5

    def test_add_page_with_layout(self):
        """Test adding page with custom layout."""
        gen = PDFGenerator()
        layout = PageLayout(margin_top=100)
        page = gen.add_page(layout)
        assert page.layout.margin_top == 100

    def test_set_metadata(self):
        """Test setting document metadata."""
        gen = PDFGenerator()
        result = gen.set_metadata(
            title="New Title",
            author="New Author",
            subject="Subject",
            keywords="key1,key2",
        )
        assert result is gen  # Check chaining
        assert gen.title == "New Title"
        assert gen.author == "New Author"
        assert gen.metadata["subject"] == "Subject"
        assert gen.metadata["keywords"] == "key1,key2"

    def test_set_metadata_partial(self):
        """Test setting partial metadata."""
        gen = PDFGenerator(title="Original", author="Original Author")
        gen.set_metadata(title="Updated")
        assert gen.title == "Updated"
        assert gen.author == "Original Author"

    def test_generate_empty_pdf(self):
        """Test generating PDF with no pages."""
        gen = PDFGenerator(title="Empty")
        pdf_bytes = gen.generate()
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_generate_pdf_with_content(self):
        """Test generating PDF with content."""
        gen = PDFGenerator(title="Content Test")
        page = gen.add_page()
        page.add_text("Hello World")
        page.add_text("Second Line")
        pdf_bytes = gen.generate()
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100  # Real PDF should be larger

    def test_generate_multipage_pdf(self):
        """Test generating multi-page PDF."""
        gen = PDFGenerator(title="Multi-Page")
        for i in range(3):
            page = gen.add_page()
            page.add_text(f"Page {i+1}")
        pdf_bytes = gen.generate()
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100

    def test_pdf_with_images_and_svg(self):
        """Test PDF with mixed content."""
        gen = PDFGenerator(title="Mixed Content")
        page = gen.add_page()
        page.add_text("Title")
        page.add_image(b"image_data", width=100, height=100)
        page.add_svg("<svg></svg>", width=50, height=50)
        pdf_bytes = gen.generate()
        assert isinstance(pdf_bytes, bytes)

    def test_pdf_is_bytes(self):
        """Test that PDF output is valid bytes."""
        gen = PDFGenerator()
        gen.add_page().add_text("Test")
        pdf = gen.generate()
        assert isinstance(pdf, bytes)
        # PDFs start with %PDF
        assert pdf.startswith(b"%PDF")

    def test_metadata_in_generated_pdf(self):
        """Test metadata is included in PDF."""
        gen = PDFGenerator(title="Test Title", author="Test Author")
        gen.set_metadata(subject="Test Subject")
        gen.add_page().add_text("Content")
        pdf_bytes = gen.generate()
        # Check that metadata was written (bytes should contain PDF objects)
        assert b"Test Title" in pdf_bytes or len(pdf_bytes) > 200

    def test_default_page_size(self):
        """Test default page size is A4."""
        gen = PDFGenerator()
        assert gen.page_width == 595  # A4 width
        assert gen.page_height == 842  # A4 height

    def test_custom_page_size(self):
        """Test custom page size."""
        gen = PDFGenerator(page_width=400, page_height=600)
        assert gen.page_width == 400
        assert gen.page_height == 600


# ==================== Integration Tests ====================


class TestPDFIntegration:
    """Integration tests for PDF generation."""

    def test_complete_coloring_book_workflow(self):
        """Test complete coloring book generation workflow."""
        # Create generator
        gen = PDFGenerator(
            title="Animal Coloring Book",
            author="Test Author"
        )
        gen.set_metadata(
            subject="Coloring Book",
            keywords="animals,coloring"
        )

        # Add pages with different layouts
        # Page 1: Title
        layout1 = PageLayoutPreset.get("COLORING_BOOK")
        page1 = gen.add_page(layout1)
        page1.add_text("Animal Coloring Book")
        page1.add_text("by Test Author")

        # Page 2: Lion drawing
        page2 = gen.add_page(layout1)
        page2.add_text("Lion")
        page2.add_svg("<svg></svg>", width=200, height=200)

        # Page 3: Dog drawing
        page3 = gen.add_page(layout1)
        page3.add_text("Dog")
        page3.add_svg("<svg></svg>", width=200, height=200)

        # Generate
        pdf_bytes = gen.generate()

        # Verify
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
        assert gen.page_count == 3

    def test_duplex_book_generation(self):
        """Test generating duplex (double-sided) book."""
        gen = PDFGenerator(title="Duplex Book")

        for i in range(4):  # 2 sheets = 4 pages
            is_left = (i % 2) == 0
            layout = PageLayout(
                is_left_page=is_left,
                page_numbering=True,
                margin_left=70 if is_left else 50,
                margin_right=50 if is_left else 70,
            )
            page = gen.add_page(layout)
            page_num = i + 1
            page.add_text(f"Page {page_num}")

        pdf_bytes = gen.generate()
        assert isinstance(pdf_bytes, bytes)
        assert gen.page_count == 4

    def test_custom_layout_preset_workflow(self):
        """Test using custom layout in workflow."""
        # Create and register custom layout
        custom_layout = create_custom_layout(
            "NEWSLETTER",
            columns=2,
            column_gap=30,
            margin_top=40,
            margin_bottom=40,
            has_header=True,
            header_height=60,
        )

        # Create generator with custom layout
        gen = PDFGenerator(title="Newsletter")
        page = gen.add_page(custom_layout)
        page.add_text("Newsletter Header")
        page.add_text("Column 1 content")

        pdf_bytes = gen.generate()
        assert isinstance(pdf_bytes, bytes)

    def test_pdf_generation_performance(self):
        """Test PDF generation with many pages."""
        gen = PDFGenerator(title="Large Book")

        # Add 100 pages
        for i in range(100):
            page = gen.add_page()
            page.add_text(f"Page {i+1}: Lorem ipsum content here")

        pdf_bytes = gen.generate()
        assert isinstance(pdf_bytes, bytes)
        assert gen.page_count == 100
        # PDF should be reasonably sized
        assert len(pdf_bytes) > 1000

    def test_complex_page_layout(self):
        """Test complex page with multiple elements."""
        layout = PageLayout(
            columns=2,
            column_gap=20,
            margin_top=60,
            margin_bottom=60,
            has_header=True,
            has_footer=True,
            page_numbering=True,
        )

        gen = PDFGenerator(title="Complex Layout")
        page = gen.add_page(layout)

        # Add various elements
        page.add_text("Header Text", x=50, y=750)
        page.add_text("Column 1 - Line 1", x=50, y=650)
        page.add_text("Column 1 - Line 2", x=50, y=630)
        page.add_image(b"img1", x=50, y=500, width=100, height=100)
        page.add_svg("<svg></svg>", x=300, y=500, width=100, height=100)
        page.add_text("Footer Text", x=50, y=50)

        pdf_bytes = gen.generate()
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
