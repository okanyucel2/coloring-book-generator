"""Tests for PDF Generation - PDFGenerator class."""

import sys
import os
from pathlib import Path
from io import BytesIO

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from coloring_book.pdf.generator import PDFGenerator, PDFPage, PageLayout


class TestPDFGenerator:
    """Test PDFGenerator class."""

    def test_pdf_generator_initialization(self):
        """Test PDFGenerator initializes with defaults."""
        gen = PDFGenerator()
        
        assert gen is not None
        assert hasattr(gen, "add_page")
        assert hasattr(gen, "generate")

    def test_pdf_generator_custom_title(self):
        """Test PDFGenerator with custom title."""
        gen = PDFGenerator(title="My Coloring Book")
        assert gen.title == "My Coloring Book"

    def test_pdf_generator_custom_author(self):
        """Test PDFGenerator with custom author."""
        gen = PDFGenerator(author="John Doe")
        assert gen.author == "John Doe"

    def test_pdf_generator_custom_dimensions(self):
        """Test PDFGenerator with custom page dimensions."""
        gen = PDFGenerator(page_width=600, page_height=800)
        assert gen.page_width == 600
        assert gen.page_height == 800

    def test_add_page_returns_pdf_page(self):
        """Test add_page returns PDFPage object."""
        gen = PDFGenerator()
        page = gen.add_page()
        
        assert isinstance(page, PDFPage)

    def test_add_multiple_pages(self):
        """Test adding multiple pages."""
        gen = PDFGenerator()
        page1 = gen.add_page()
        page2 = gen.add_page()
        page3 = gen.add_page()
        
        assert gen.page_count == 3

    def test_page_count_property(self):
        """Test page count is accurate."""
        gen = PDFGenerator()
        assert gen.page_count == 0
        
        gen.add_page()
        assert gen.page_count == 1
        
        gen.add_page()
        assert gen.page_count == 2

    def test_generate_returns_bytes(self):
        """Test generate returns PDF bytes."""
        gen = PDFGenerator(title="Test PDF")
        page = gen.add_page()
        page.add_text("Hello World")
        
        pdf_bytes = gen.generate()
        
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")  # PDF magic number

    def test_generate_empty_pdf(self):
        """Test generating empty PDF."""
        gen = PDFGenerator()
        pdf_bytes = gen.generate()
        
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_creates_valid_pdf(self):
        """Test generated PDF has valid structure."""
        gen = PDFGenerator(title="Test Book")
        page = gen.add_page()
        page.add_text("Test Content")
        
        pdf_bytes = gen.generate()
        
        # Check PDF structure
        assert b"%PDF" in pdf_bytes
        assert b"endobj" in pdf_bytes
        assert b"xref" in pdf_bytes
        
        # ✅ SIZE VERIFICATION - PDF with content > empty PDF
        # Empty PDF ~600-800 bytes, PDF with text > 1000 bytes
        assert len(pdf_bytes) > 800, f"PDF too small: {len(pdf_bytes)} bytes - might be empty"
        
        # ✅ CONTENT VERIFICATION - Text should be in content stream
        # PDF stores text in content streams (usually between "stream" and "endstream")
        assert b"stream" in pdf_bytes, "No content streams found"
        assert b"endstream" in pdf_bytes, "Incomplete content stream"

    def test_pdf_generator_set_metadata(self):
        """Test setting PDF metadata."""
        gen = PDFGenerator()
        gen.set_metadata(
            title="Book Title",
            author="Author Name",
            subject="Coloring Book",
            keywords="art,coloring"
        )
        
        assert gen.title == "Book Title"
        assert gen.author == "Author Name"

    def test_metadata_in_generated_pdf(self):
        """Test metadata appears in generated PDF."""
        gen = PDFGenerator()
        gen.set_metadata(
            title="My Book",
            author="Test Author"
        )
        
        pdf_bytes = gen.generate()
        
        # Metadata should be in PDF
        assert b"My Book" in pdf_bytes
        assert b"Test Author" in pdf_bytes
        
        # ✅ SIZE VERIFICATION
        assert len(pdf_bytes) > 600

    def test_pdf_generator_chainable(self):
        """Test PDFGenerator methods are chainable where appropriate."""
        gen = PDFGenerator()
        result = gen.set_metadata(title="Book")
        
        assert result is gen or result is None


class TestPDFPage:
    """Test PDFPage class."""

    def test_pdf_page_initialization(self):
        """Test PDFPage initializes correctly."""
        page = PDFPage()
        
        assert page is not None
        assert hasattr(page, "add_text")
        assert hasattr(page, "add_image")

    def test_pdf_page_with_layout(self):
        """Test PDFPage with layout configuration."""
        layout = PageLayout(margin_top=50, margin_left=50)
        page = PDFPage(layout=layout)
        
        assert page.layout is not None

    def test_add_text_to_page(self):
        """Test adding text to page."""
        page = PDFPage()
        page.add_text("Hello World")
        
        assert len(page.elements) > 0

    def test_add_text_with_styling(self):
        """Test adding text with font and size."""
        page = PDFPage()
        page.add_text("Styled Text", font_name="Helvetica", font_size=14)
        
        assert len(page.elements) > 0

    def test_add_text_returns_page(self):
        """Test add_text returns page for chaining."""
        page = PDFPage()
        result = page.add_text("Text")
        
        assert result is page

    def test_add_multiple_text_elements(self):
        """Test adding multiple text elements."""
        page = PDFPage()
        page.add_text("Line 1")
        page.add_text("Line 2")
        page.add_text("Line 3")
        
        assert len(page.elements) == 3

    def test_add_image_to_page(self):
        """Test adding image to page."""
        page = PDFPage()
        # Mock image data
        image_data = b"fake_image_data"
        page.add_image(image_data, width=100, height=100)
        
        assert len(page.elements) > 0

    def test_page_dimensions(self):
        """Test page has dimensions."""
        page = PDFPage(width=600, height=800)
        assert page.width == 600
        assert page.height == 800

    def test_page_default_dimensions(self):
        """Test page default dimensions (A4)."""
        page = PDFPage()
        # A4 is approximately 595x842
        assert page.width > 0
        assert page.height > 0

    def test_add_svg_to_page(self):
        """Test adding SVG content to page."""
        page = PDFPage()
        svg_content = '<svg><circle cx="50" cy="50" r="40"/></svg>'
        page.add_svg(svg_content, width=100, height=100)
        
        assert len(page.elements) > 0

    def test_page_content_list(self):
        """Test page maintains list of content."""
        page = PDFPage()
        page.add_text("Text 1")
        page.add_text("Text 2")
        
        elements = page.get_elements()
        assert len(elements) == 2


class TestPageLayout:
    """Test PageLayout configuration."""

    def test_page_layout_initialization(self):
        """Test PageLayout initializes with defaults."""
        layout = PageLayout()
        
        assert layout.margin_top >= 0
        assert layout.margin_left >= 0
        assert layout.margin_right >= 0
        assert layout.margin_bottom >= 0

    def test_page_layout_custom_margins(self):
        """Test PageLayout with custom margins."""
        layout = PageLayout(
            margin_top=50,
            margin_left=60,
            margin_right=60,
            margin_bottom=50
        )
        
        assert layout.margin_top == 50
        assert layout.margin_left == 60

    def test_page_layout_line_spacing(self):
        """Test PageLayout line spacing."""
        layout = PageLayout(line_spacing=1.5)
        assert layout.line_spacing == 1.5

    def test_page_layout_font_defaults(self):
        """Test PageLayout font defaults."""
        layout = PageLayout()
        
        assert layout.font_name is not None
        assert layout.font_size > 0

    def test_page_layout_custom_font(self):
        """Test PageLayout with custom font."""
        layout = PageLayout(
            font_name="Times-Roman",
            font_size=12
        )
        
        assert layout.font_name == "Times-Roman"
        assert layout.font_size == 12

    def test_page_layout_orientation(self):
        """Test PageLayout orientation."""
        layout_portrait = PageLayout(orientation="portrait")
        layout_landscape = PageLayout(orientation="landscape")
        
        assert layout_portrait.orientation == "portrait"
        assert layout_landscape.orientation == "landscape"


class TestPDFIntegration:
    """Integration tests for PDF generation."""

    def test_generate_simple_pdf(self):
        """Test generating a simple PDF."""
        gen = PDFGenerator(title="Simple PDF")
        page = gen.add_page()
        page.add_text("This is a simple PDF")
        
        pdf_bytes = gen.generate()
        
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")
        
        # ✅ SIZE CHECK
        assert len(pdf_bytes) > 800

    def test_generate_multi_page_pdf(self):
        """Test generating multi-page PDF."""
        gen = PDFGenerator(title="Multi-Page")
        
        for i in range(3):
            page = gen.add_page()
            page.add_text(f"Page {i+1}")
        
        pdf_bytes = gen.generate()
        
        assert len(pdf_bytes) > 0
        assert gen.page_count == 3
        
        # ✅ SIZE CHECK - 3 pages should be larger
        assert len(pdf_bytes) > 1500, f"PDF with 3 pages too small: {len(pdf_bytes)} bytes"
        
        # ✅ CONTENT CHECK - Each page text should be in PDF
        assert b"Page 1" in pdf_bytes
        assert b"Page 2" in pdf_bytes
        assert b"Page 3" in pdf_bytes

    def test_pdf_with_layout_configuration(self):
        """Test PDF with layout configuration."""
        layout = PageLayout(
            margin_top=50,
            margin_left=50,
            margin_right=50,
            margin_bottom=50
        )
        
        gen = PDFGenerator(title="Formatted PDF")
        page = gen.add_page(layout=layout)
        page.add_text("Content with margins")
        
        pdf_bytes = gen.generate()
        
        assert len(pdf_bytes) > 0
        assert len(pdf_bytes) > 800
        assert b"Content with margins" in pdf_bytes

    def test_pdf_with_metadata(self):
        """Test PDF with complete metadata."""
        gen = PDFGenerator()
        gen.set_metadata(
            title="My Coloring Book",
            author="John Doe",
            subject="Coloring Book for Kids",
            keywords="coloring,art,kids"
        )
        
        page = gen.add_page()
        page.add_text("Content")
        
        pdf_bytes = gen.generate()
        
        assert b"My Coloring Book" in pdf_bytes
        assert b"John Doe" in pdf_bytes
        assert len(pdf_bytes) > 800

    def test_pdf_from_svg_content(self):
        """Test generating PDF from SVG content."""
        gen = PDFGenerator(title="SVG to PDF")
        page = gen.add_page()
        
        svg_content = '''
        <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
            <circle cx="100" cy="100" r="80" fill="none" stroke="black" stroke-width="2"/>
        </svg>
        '''
        page.add_svg(svg_content, width=200, height=200)
        
        pdf_bytes = gen.generate()
        
        assert len(pdf_bytes) > 0
        assert len(pdf_bytes) > 800

    def test_pdf_save_to_file(self):
        """Test saving PDF to file."""
        import tempfile
        
        gen = PDFGenerator(title="Save Test")
        page = gen.add_page()
        page.add_text("Test content")
        
        pdf_bytes = gen.generate()
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            temp_path = f.name
        
        # Verify file was created
        assert os.path.exists(temp_path)
        
        # ✅ FILE SIZE CHECK
        file_size = os.path.getsize(temp_path)
        assert file_size > 800, f"Saved PDF too small: {file_size} bytes"
        
        # Cleanup
        os.unlink(temp_path)

    def test_pdf_with_multiple_content_types(self):
        """Test PDF with mixed content (text, images, SVG)."""
        gen = PDFGenerator(title="Mixed Content")
        page = gen.add_page()
        
        page.add_text("Header Text")
        page.add_text("More text content")
        
        svg = '<svg><rect width="100" height="100" fill="none" stroke="black"/></svg>'
        page.add_svg(svg, width=100, height=100)
        
        pdf_bytes = gen.generate()
        
        assert len(pdf_bytes) > 0
        assert len(pdf_bytes) > 1000, "PDF with multiple content types too small"
        assert b"Header Text" in pdf_bytes
        assert b"More text content" in pdf_bytes

    def test_pdf_multiple_text_larger_than_single(self):
        """Test that PDFs with more content are larger."""
        # PDF with single text
        gen_single = PDFGenerator(title="Single")
        page = gen_single.add_page()
        page.add_text("Text")
        pdf_single = gen_single.generate()
        
        # PDF with multiple text
        gen_multi = PDFGenerator(title="Multiple")
        page = gen_multi.add_page()
        for i in range(10):
            page.add_text(f"Line {i}: This is longer content to make file bigger")
        pdf_multi = gen_multi.generate()
        
        # ✅ More content = larger file
        assert len(pdf_multi) > len(pdf_single), \
            f"PDF with more content should be larger: single={len(pdf_single)}, multi={len(pdf_multi)}"
