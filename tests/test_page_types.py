"""Tests for workbook activity page types."""

import io

import pytest
from PIL import Image

from coloring_book.workbook.models import WorkbookConfig, WorkbookItem
from coloring_book.workbook.page_types import (
    PAGE_TYPE_REGISTRY,
    ActivityPage,
    CoverPage,
    CountAndCirclePage,
    FindAndCirclePage,
    MatchVehiclesPage,
    TraceAndColorPage,
    WhichIsDifferentPage,
    WordToImagePage,
    get_page_dimensions,
)
from coloring_book.pdf.generator import PDFGenerator, PDFPage


def _make_test_image(width=100, height=100) -> bytes:
    """Create a minimal test PNG image."""
    img = Image.new("RGBA", (width, height), (255, 0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_item(name="fire_truck", category="vehicle", complete=True) -> WorkbookItem:
    """Create a test WorkbookItem."""
    kwargs = {"name": name, "category": category}
    if complete:
        kwargs["colored_image"] = _make_test_image()
        kwargs["outline_image"] = _make_test_image()
        kwargs["dashed_image"] = _make_test_image()
    return WorkbookItem(**kwargs)


def _make_items(count=5) -> list[WorkbookItem]:
    """Create multiple test items."""
    names = ["fire_truck", "police_car", "ambulance", "school_bus", "taxi",
             "helicopter", "airplane", "train"]
    return [_make_item(name=names[i % len(names)]) for i in range(count)]


class TestGetPageDimensions:
    def test_letter_size(self):
        w, h = get_page_dimensions("letter")
        assert w == 612.0
        assert h == 792.0

    def test_a4_size(self):
        w, h = get_page_dimensions("a4")
        assert abs(w - 595.28) < 0.5  # A4 width in points (~595.28)
        assert abs(h - 841.89) < 0.5  # A4 height in points (~841.89)

    def test_unknown_defaults_to_letter(self):
        w, h = get_page_dimensions("unknown")
        assert w == 612.0


class TestPageTypeRegistry:
    def test_all_types_registered(self):
        expected = {
            "trace_and_color", "which_different", "count_circle",
            "match", "word_to_image", "find_circle", "cover",
        }
        assert set(PAGE_TYPE_REGISTRY.keys()) == expected

    def test_all_types_are_activity_page_subclasses(self):
        for name, cls in PAGE_TYPE_REGISTRY.items():
            assert issubclass(cls, ActivityPage), f"{name} is not ActivityPage subclass"


class TestCoverPage:
    def test_render_produces_elements(self):
        config = WorkbookConfig(
            theme="vehicles", title="Test Workbook", subtitle="Ages 3-5",
            items=["fire_truck"], page_count=30,
        )
        items = _make_items(3)
        cover = CoverPage(config=config, preview_items=items)

        pdf = PDFGenerator(title="Test")
        page = pdf.add_page()
        cover.render(page)

        elements = page.get_elements()
        assert len(elements) > 0

        # Should have text elements for title, subtitle, age range
        text_elements = [e for e in elements if e["type"] == "text"]
        assert len(text_elements) >= 3

    def test_required_assets(self):
        config = WorkbookConfig(theme="vehicles", title="Test", items=["a"])
        cover = CoverPage(config=config, preview_items=[])
        assert "colored" in cover.get_required_assets()

    def test_page_type(self):
        config = WorkbookConfig(theme="vehicles", title="Test", items=["a"])
        cover = CoverPage(config=config, preview_items=[])
        assert cover.page_type == "cover"


class TestTraceAndColorPage:
    def test_render_produces_elements(self):
        item = _make_item()
        page_obj = TraceAndColorPage(item=item)

        pdf = PDFGenerator(title="Test")
        pdf_page = pdf.add_page()
        page_obj.render(pdf_page)

        elements = pdf_page.get_elements()
        assert len(elements) > 0

        # Should have images for colored reference and dashed outline
        image_elements = [e for e in elements if e["type"] == "image"]
        assert len(image_elements) >= 2

    def test_required_assets(self):
        item = _make_item()
        page = TraceAndColorPage(item=item)
        assets = page.get_required_assets()
        assert "colored" in assets
        assert "dashed" in assets

    def test_page_type(self):
        item = _make_item()
        page = TraceAndColorPage(item=item)
        assert page.page_type == "trace_and_color"


class TestWhichIsDifferentPage:
    def test_render_produces_elements(self):
        items = _make_items(4)
        page_obj = WhichIsDifferentPage(items=items)

        pdf = PDFGenerator(title="Test")
        pdf_page = pdf.add_page()
        page_obj.render(pdf_page)

        elements = pdf_page.get_elements()
        assert len(elements) > 0

    def test_required_assets(self):
        page = WhichIsDifferentPage(items=_make_items(2))
        assert "colored" in page.get_required_assets()


class TestCountAndCirclePage:
    def test_render_produces_elements(self):
        items = _make_items(3)
        page_obj = CountAndCirclePage(items=items)

        pdf = PDFGenerator(title="Test")
        pdf_page = pdf.add_page()
        page_obj.render(pdf_page)

        elements = pdf_page.get_elements()
        assert len(elements) > 0

        # Should have answer boxes at the bottom
        text_elements = [e for e in elements if e["type"] == "text"]
        answer_texts = [e for e in text_elements if "___" in e.get("text", "")]
        assert len(answer_texts) >= 1

    def test_required_assets(self):
        page = CountAndCirclePage(items=_make_items(2))
        assert "colored" in page.get_required_assets()


class TestMatchVehiclesPage:
    def test_render_produces_elements(self):
        items = _make_items(5)
        page_obj = MatchVehiclesPage(items=items)

        pdf = PDFGenerator(title="Test")
        pdf_page = pdf.add_page()
        page_obj.render(pdf_page)

        elements = pdf_page.get_elements()
        assert len(elements) > 0

        # Should have images on both left and right sides
        image_elements = [e for e in elements if e["type"] == "image"]
        assert len(image_elements) >= 6  # At least 3 pairs * 2

    def test_required_assets(self):
        page = MatchVehiclesPage(items=_make_items(2))
        assert "colored" in page.get_required_assets()


class TestWordToImagePage:
    def test_render_produces_elements(self):
        items = _make_items(4)
        page_obj = WordToImagePage(items=items)

        pdf = PDFGenerator(title="Test")
        pdf_page = pdf.add_page()
        page_obj.render(pdf_page)

        elements = pdf_page.get_elements()
        assert len(elements) > 0

        # Should have word labels + images
        text_elements = [e for e in elements if e["type"] == "text"]
        image_elements = [e for e in elements if e["type"] == "image"]
        assert len(text_elements) >= 3  # title + instruction + word labels
        assert len(image_elements) >= 1

    def test_required_assets(self):
        page = WordToImagePage(items=_make_items(2))
        assert "colored" in page.get_required_assets()


class TestFindAndCirclePage:
    def test_render_produces_elements(self):
        items = _make_items(4)
        distractors = _make_items(6)
        page_obj = FindAndCirclePage(items=items, distractor_items=distractors)

        pdf = PDFGenerator(title="Test")
        pdf_page = pdf.add_page()
        page_obj.render(pdf_page)

        elements = pdf_page.get_elements()
        assert len(elements) > 0

    def test_required_assets(self):
        page = FindAndCirclePage(items=_make_items(2), distractor_items=_make_items(3))
        assert "colored" in page.get_required_assets()


class TestAllPageTypesProduceValidPDF:
    """Integration test: each page type renders into a valid PDF."""

    def _render_page_type(self, page_instance: ActivityPage) -> bytes:
        """Render a page type and return PDF bytes."""
        pdf = PDFGenerator(title="Test", page_width=612, page_height=792)
        pdf_page = pdf.add_page()
        page_instance.render(pdf_page)
        return pdf.generate()

    def test_cover_renders_to_pdf(self):
        config = WorkbookConfig(
            theme="vehicles", title="Test", subtitle="Ages 3-5",
            items=["fire_truck"], page_count=30,
        )
        page = CoverPage(config=config, preview_items=_make_items(3))
        pdf_bytes = self._render_page_type(page)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_trace_and_color_renders_to_pdf(self):
        page = TraceAndColorPage(item=_make_item())
        pdf_bytes = self._render_page_type(page)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_which_different_renders_to_pdf(self):
        page = WhichIsDifferentPage(items=_make_items(4))
        pdf_bytes = self._render_page_type(page)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_count_circle_renders_to_pdf(self):
        page = CountAndCirclePage(items=_make_items(3))
        pdf_bytes = self._render_page_type(page)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_match_renders_to_pdf(self):
        page = MatchVehiclesPage(items=_make_items(5))
        pdf_bytes = self._render_page_type(page)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_word_to_image_renders_to_pdf(self):
        page = WordToImagePage(items=_make_items(4))
        pdf_bytes = self._render_page_type(page)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_find_circle_renders_to_pdf(self):
        page = FindAndCirclePage(items=_make_items(4), distractor_items=_make_items(6))
        pdf_bytes = self._render_page_type(page)
        assert pdf_bytes[:5] == b"%PDF-"
