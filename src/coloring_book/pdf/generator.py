"""PDF Generator - Create PDFs from coloring book content."""

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
    """Generate PDF documents for coloring books."""

    def __init__(
        self,
        title: str = "Untitled",
        author: str = "",
        page_width: float = 595,  # A4
        page_height: float = 842,  # A4
    ):
        """Initialize PDFGenerator.

        Args:
            title: Document title
            author: Document author
            page_width: Default page width in points
            page_height: Default page height in points
        """
        self.title = title
        self.author = author
        self.page_width = page_width
        self.page_height = page_height
        self.pages: List[PDFPage] = []
        self.metadata: Dict[str, str] = {
            "title": title,
            "author": author,
        }

    def add_page(self, layout: Optional[PageLayout] = None) -> PDFPage:
        """Add a new page to document.

        Args:
            layout: PageLayout configuration

        Returns:
            PDFPage object
        """
        page = PDFPage(width=self.page_width, height=self.page_height, layout=layout)
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

        # Create canvas
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

        Args:
            c: ReportLab canvas
            page: PDFPage to draw
        """
        for element in page.elements:
            if element["type"] == "text":
                self._draw_text(c, element)
            elif element["type"] == "image":
                self._draw_image(c, element)
            elif element["type"] == "svg":
                self._draw_svg(c, element)

    def _draw_text(self, c: canvas.Canvas, element: Dict[str, Any]) -> None:
        """Draw text element.

        Args:
            c: ReportLab canvas
            element: Text element dictionary
        """
        c.setFont(element["font_name"], element["font_size"])
        c.drawString(element["x"], element["y"], element["text"])

    def _draw_image(self, c: canvas.Canvas, element: Dict[str, Any]) -> None:
        """Draw image element.

        Args:
            c: ReportLab canvas
            element: Image element dictionary
        """
        try:
            # Pass image bytes directly via ImageReader (no temp file)
            img_reader = ImageReader(io.BytesIO(element["data"]))

            # Draw on canvas
            c.drawImage(
                img_reader,
                element["x"],
                element["y"],
                width=element["width"],
                height=element["height"],
                preserveAspectRatio=True,
            )
        except Exception as e:
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
            
            # Create a simple placeholder for SVG (render as text for now)
            # In production, use svglib or cairosvg for proper rendering
            
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
            
        except Exception as e:
            # Fallback: draw error box
            c.setStrokeColorRGB(1, 0, 0)
            c.setLineWidth(1)
            c.rect(element["x"], element["y"], element["width"], element["height"])
            c.drawString(element["x"] + 5, element["y"] + element["height"] - 15, "[SVG Error]")
