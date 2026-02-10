"""PDF Generator - Create PDFs from coloring book content."""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from PIL import Image
import xml.etree.ElementTree as ET
import io

# Import advanced PageLayout from layouts module
from .layouts import PageLayout
from .profiles import PrintProfile


class PDFPage:
    """A single page in a PDF document."""

    def __init__(
        self,
        width: float = 595,  # A4 width
        height: float = 842,  # A4 height
        layout: Optional[PageLayout] = None,
    ):
        """Initialize PDFPage.

        Args:
            width: Page width in points
            height: Page height in points
            layout: PageLayout configuration
        """
        self.width = width
        self.height = height
        self.layout = layout or PageLayout()
        self.elements: List[Dict[str, Any]] = []
        self.y_position = height - self.layout.margin_top

    def add_text(
        self,
        text: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
        font_name: Optional[str] = None,
        font_size: Optional[int] = None,
    ) -> "PDFPage":
        """Add text to page.

        Args:
            text: Text content
            x: X position (default: left margin)
            y: Y position (default: auto-advance)
            font_name: Font name
            font_size: Font size

        Returns:
            Self for chaining
        """
        if x is None:
            x = self.layout.margin_left

        if y is None:
            y = self.y_position
            self.y_position -= (font_size or self.layout.font_size) * self.layout.line_spacing

        element = {
            "type": "text",
            "text": text,
            "x": x,
            "y": y,
            "font_name": font_name or self.layout.font_name,
            "font_size": font_size or self.layout.font_size,
        }
        self.elements.append(element)
        return self

    def add_image(
        self,
        image_data: bytes,
        x: Optional[float] = None,
        y: Optional[float] = None,
        width: float = 100,
        height: float = 100,
    ) -> "PDFPage":
        """Add image to page.

        Args:
            image_data: Image bytes
            x: X position
            y: Y position
            width: Image width
            height: Image height

        Returns:
            Self for chaining
        """
        if x is None:
            x = self.layout.margin_left

        if y is None:
            y = self.y_position
            self.y_position -= height + 10

        element = {
            "type": "image",
            "data": image_data,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }
        self.elements.append(element)
        return self

    def add_svg(
        self,
        svg_content: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
        width: float = 100,
        height: float = 100,
    ) -> "PDFPage":
        """Add SVG content to page.

        Args:
            svg_content: SVG string
            x: X position
            y: Y position
            width: SVG width
            height: SVG height

        Returns:
            Self for chaining
        """
        if x is None:
            x = self.layout.margin_left

        if y is None:
            y = self.y_position
            self.y_position -= height + 10

        element = {
            "type": "svg",
            "content": svg_content,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }
        self.elements.append(element)
        return self

    def get_elements(self) -> List[Dict[str, Any]]:
        """Get all page elements.

        Returns:
            List of element dictionaries
        """
        return self.elements.copy()


class PDFGenerator:
    """Generate PDF documents with optional print profile support."""

    def __init__(
        self,
        title: str = "Untitled",
        author: str = "",
        page_width: float = 595,  # A4
        page_height: float = 842,  # A4
        profile: Optional[PrintProfile] = None,
    ):
        """Initialize PDFGenerator.

        Args:
            title: Document title
            author: Document author
            page_width: Default page width in points (content area, before bleed)
            page_height: Default page height in points (content area, before bleed)
            profile: Optional PrintProfile for print-ready output
        """
        self.title = title
        self.author = author
        self.content_width = page_width
        self.content_height = page_height
        self.profile = profile

        # Calculate actual page size including bleed
        bleed = profile.bleed_points if profile else 0
        self.page_width = page_width + 2 * bleed
        self.page_height = page_height + 2 * bleed

        self.pages: List[PDFPage] = []
        self.metadata: Dict[str, str] = {
            "title": title,
            "author": author,
        }

    def add_page(self, layout: Optional[PageLayout] = None) -> PDFPage:
        """Add a new page to document.

        Content coordinates are offset by bleed so callers don't need
        to know about bleed — (0,0) in content space maps to the bleed
        offset on the actual canvas.

        Args:
            layout: PageLayout configuration

        Returns:
            PDFPage object
        """
        page = PDFPage(
            width=self.content_width,
            height=self.content_height,
            layout=layout,
        )
        self.pages.append(page)
        return page

    @property
    def page_count(self) -> int:
        """Get number of pages in document."""
        return len(self.pages)

    def set_metadata(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        subject: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> "PDFGenerator":
        """Set document metadata.

        Args:
            title: Document title
            author: Document author
            subject: Document subject
            keywords: Document keywords

        Returns:
            Self for chaining
        """
        if title is not None:
            self.title = title
            self.metadata["title"] = title

        if author is not None:
            self.author = author
            self.metadata["author"] = author

        if subject is not None:
            self.metadata["subject"] = subject

        if keywords is not None:
            self.metadata["keywords"] = keywords

        return self

    def generate(self) -> bytes:
        """Generate PDF document.

        Returns:
            PDF as bytes
        """
        buffer = BytesIO()

        # Create canvas with full page size (including bleed)
        c = canvas.Canvas(buffer, pagesize=(self.page_width, self.page_height))

        # Set metadata
        c.setTitle(self.metadata.get("title", ""))
        c.setAuthor(self.metadata.get("author", ""))
        if "subject" in self.metadata:
            c.setSubject(self.metadata["subject"])

        # Draw pages
        for page in self.pages:
            self._draw_page(c, page)
            c.showPage()

        # Finalize
        c.save()

        # Get bytes
        buffer.seek(0)
        return buffer.getvalue()

    def _draw_page(self, c: canvas.Canvas, page: PDFPage) -> None:
        """Draw a page on the canvas.

        Applies bleed offset so content coordinates map correctly,
        then draws crop marks in the bleed area if profile requires them.
        """
        bleed = self.profile.bleed_points if self.profile else 0

        # Draw crop marks first (in bleed area, behind content)
        if self.profile and self.profile.show_crop_marks and bleed > 0:
            self._draw_crop_marks(c, bleed)

        # Apply bleed offset for content elements
        for element in page.elements:
            offset_element = self._offset_element(element, bleed)
            if offset_element["type"] == "text":
                self._draw_text(c, offset_element)
            elif offset_element["type"] == "image":
                self._draw_image(c, offset_element)
            elif offset_element["type"] == "svg":
                self._draw_svg(c, offset_element)

    def _offset_element(self, element: Dict[str, Any], bleed: float) -> Dict[str, Any]:
        """Create a copy of element with coordinates offset by bleed."""
        offset = dict(element)
        offset["x"] = element["x"] + bleed
        offset["y"] = element["y"] + bleed
        return offset

    def _draw_crop_marks(self, c: canvas.Canvas, bleed: float) -> None:
        """Draw L-shaped crop marks at the four corners of the content area."""
        mark_len = 18  # ~6mm
        mark_offset = 6  # gap between content edge and mark start

        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.25)

        # Content area corners in canvas coordinates
        corners = [
            (bleed, bleed),  # bottom-left
            (bleed + self.content_width, bleed),  # bottom-right
            (bleed, bleed + self.content_height),  # top-left
            (bleed + self.content_width, bleed + self.content_height),  # top-right
        ]

        for cx, cy in corners:
            # Determine direction of marks (outward from content)
            h_dir = -1 if cx > self.page_width / 2 else 1
            v_dir = -1 if cy > self.page_height / 2 else 1

            # Horizontal mark
            x_start = cx - h_dir * mark_offset
            c.line(x_start, cy, x_start - h_dir * mark_len, cy)

            # Vertical mark
            y_start = cy - v_dir * mark_offset
            c.line(cx, y_start, cx, y_start - v_dir * mark_len)

    def _draw_text(self, c: canvas.Canvas, element: Dict[str, Any]) -> None:
        """Draw text element."""
        c.setFont(element["font_name"], element["font_size"])
        c.drawString(element["x"], element["y"], element["text"])

    def _draw_image(self, c: canvas.Canvas, element: Dict[str, Any]) -> None:
        """Draw image element with optional grayscale conversion and JPEG compression."""
        try:
            img = Image.open(io.BytesIO(element["data"]))

            # Grayscale conversion if profile requests it
            if self.profile and self.profile.color_space == "grayscale":
                img = img.convert("L")
            elif img.mode == "RGBA":
                # Flatten alpha onto white background for PDF
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Re-encode with profile's JPEG quality for compression
            img_buffer = io.BytesIO()
            save_format = "JPEG" if self.profile else "PNG"
            save_kwargs: Dict[str, Any] = {}
            if save_format == "JPEG":
                save_kwargs["quality"] = self.profile.jpeg_quality
                # JPEG doesn't support palette or alpha
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
            img.save(img_buffer, format=save_format, **save_kwargs)
            img_buffer.seek(0)

            img_reader = ImageReader(img_buffer)
            c.drawImage(
                img_reader,
                element["x"],
                element["y"],
                width=element["width"],
                height=element["height"],
                preserveAspectRatio=True,
            )
        except Exception:
            # Fallback: draw a placeholder rectangle
            c.setStrokeColorRGB(0, 0, 0)
            c.setLineWidth(1)
            c.rect(
                element["x"],
                element["y"],
                element["width"],
                element["height"]
            )
            c.drawString(element["x"] + 5, element["y"] + element["height"] - 15, "[Image]")

    def _draw_svg(self, c: canvas.Canvas, element: Dict[str, Any]) -> None:
        """Draw SVG element by converting to image.

        Args:
            c: ReportLab canvas
            element: SVG element dictionary
        """
        try:
            svg_content = element["content"]

            # Parse SVG to get dimensions
            root = ET.fromstring(svg_content)
            width_str = root.get("width", "200")
            height_str = root.get("height", "200")

            # Extract numeric values
            svg_width = float(width_str.replace("px", ""))
            svg_height = float(height_str.replace("px", ""))

            # For now, draw a frame and text
            c.setStrokeColorRGB(0.5, 0.5, 0.5)
            c.setLineWidth(2)
            c.rect(
                element["x"],
                element["y"],
                element["width"],
                element["height"]
            )

            # Draw SVG indicator
            c.setFont("Helvetica", 10)
            c.drawString(
                element["x"] + 10,
                element["y"] + element["height"] - 20,
                f"SVG Drawing ({int(svg_width)}x{int(svg_height)})"
            )

        except Exception:
            # Fallback: draw error box
            c.setStrokeColorRGB(1, 0, 0)
            c.setLineWidth(1)
            c.rect(element["x"], element["y"], element["width"], element["height"])
            c.drawString(element["x"] + 5, element["y"] + element["height"] - 15, "[SVG Error]")
