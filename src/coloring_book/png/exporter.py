"""PNG exporter for converting SVG drawings to PNG images."""

from typing import Tuple, Optional, Dict, List
from PIL import Image, ImageDraw
from io import BytesIO
import xml.etree.ElementTree as ET
import os
import re

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    SVGLIB_AVAILABLE = True
except ImportError:
    SVGLIB_AVAILABLE = False


class PNGExporter:
    """Export SVG drawings to PNG format."""

    def __init__(
        self,
        dpi: int = 150,
        quality: int = 90,
        background_color: str = "white",
    ):
        """Initialize PNG exporter.

        Args:
            dpi: Resolution in DPI (100-500)
            quality: Quality level (1-100)
            background_color: Background color for PNG

        Raises:
            ValueError: If DPI or quality out of range
        """
        if dpi < 72 or dpi > 600:
            raise ValueError("DPI must be between 72 and 600")
        if quality < 1 or quality > 100:
            raise ValueError("Quality must be between 1 and 100")

        self.dpi = dpi
        self.quality = quality
        self.background_color = background_color
        self.format = "PNG"

    def export_svg_to_png(self, svg_content: str) -> bytes:
        """Convert SVG content to PNG bytes.

        Args:
            svg_content: SVG XML content as string

        Returns:
            PNG image data as bytes
        """
        # ✅ ATTEMPT 1: Use svglib + ReportLab for proper SVG rendering
        if SVGLIB_AVAILABLE:
            try:
                return self._export_with_svglib(svg_content)
            except Exception as e:
                print(f"SVG rendering with svglib failed: {e}, falling back...")

        # ✅ FALLBACK: Render SVG shapes to PIL Image
        return self._export_with_enhanced_fallback(svg_content)

    def _export_with_svglib(self, svg_content: str) -> bytes:
        """Render SVG using svglib + ReportLab."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write(svg_content)
            svg_path = f.name
        
        try:
            drawing = svg2rlg(svg_path)
            
            if drawing is None:
                raise ValueError("SVG rendering returned None")
            
            png_path = "/tmp/svg_output.png"
            renderPM.drawToFile(
                drawing, 
                png_path, 
                fmt="PNG",
                dpi=self.dpi
            )
            
            with open(png_path, 'rb') as f:
                png_bytes = f.read()
            
            os.remove(png_path)
            return png_bytes
            
        finally:
            os.remove(svg_path)

    def _export_with_enhanced_fallback(self, svg_content: str) -> bytes:
        """Enhanced SVG rendering using PIL.
        
        Parses SVG and renders all elements (circles, ellipses, paths, etc.)
        with proper stroke widths and colors.
        """
        try:
            root = ET.fromstring(svg_content)
        except ET.ParseError:
            # Fallback to blank if parsing fails
            return self._create_blank_png()
        
        # Parse dimensions
        width_str = root.get("width", "200")
        height_str = root.get("height", "200")
        
        width = int(float(width_str.replace("px", "")))
        height = int(float(height_str.replace("px", "")))
        
        # Apply DPI scaling
        scale = self.dpi / 96
        pixel_width = max(100, int(width * scale))
        pixel_height = max(100, int(height * scale))
        
        # Create image
        bg_color = (255, 255, 255) if self.background_color.lower() == "white" else (0, 0, 0)
        img = Image.new("RGB", (pixel_width, pixel_height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # ✅ Render all SVG elements with stronger strokes
        self._render_svg_elements_enhanced(root, draw, scale, pixel_width, pixel_height)
        
        # Save to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG", quality=self.quality)
        buffer.seek(0)
        return buffer.getvalue()

    def _render_svg_elements_enhanced(self, root, draw, scale, width, height):
        """Enhanced SVG element rendering with thicker strokes."""
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        # Default stroke width (2-3 pixels minimum)
        min_stroke = max(2, int(6 * scale))
        
        # ✅ Render ellipses (most common in animal SVGs)
        for ellipse in root.findall('.//svg:ellipse', ns):
            self._draw_ellipse_enhanced(draw, ellipse, scale, min_stroke)
        
        # ✅ Render circles
        for circle in root.findall('.//svg:circle', ns):
            self._draw_circle_enhanced(draw, circle, scale, min_stroke)
        
        # ✅ Render rectangles
        for rect in root.findall('.//svg:rect', ns):
            self._draw_rect_enhanced(draw, rect, scale, min_stroke)
        
        # ✅ Render paths
        for path in root.findall('.//svg:path', ns):
            self._draw_path_enhanced(draw, path, scale, min_stroke)
        
        # ✅ Render polylines
        for poly in root.findall('.//svg:polyline', ns):
            self._draw_polyline_enhanced(draw, poly, scale, min_stroke)
        
        # ✅ Render polygons
        for poly in root.findall('.//svg:polygon', ns):
            self._draw_polygon_enhanced(draw, poly, scale, min_stroke)
        
        # ✅ Render lines
        for line in root.findall('.//svg:line', ns):
            self._draw_line_enhanced(draw, line, scale, min_stroke)

    def _draw_ellipse_enhanced(self, draw, element, scale, min_stroke):
        """Draw ellipse with enhanced stroke."""
        try:
            cx = float(element.get('cx', 0)) * scale
            cy = float(element.get('cy', 0)) * scale
            rx = float(element.get('rx', 10)) * scale
            ry = float(element.get('ry', 10)) * scale
            
            stroke = element.get('stroke', 'black')
            stroke_width = max(min_stroke, int(float(element.get('stroke-width', 2)) * scale))
            
            # Convert color name to RGB if needed
            color = self._parse_color(stroke)
            
            draw.ellipse(
                [(cx - rx, cy - ry), (cx + rx, cy + ry)],
                outline=color,
                width=stroke_width
            )
        except (ValueError, AttributeError):
            pass

    def _draw_circle_enhanced(self, draw, element, scale, min_stroke):
        """Draw circle with enhanced stroke."""
        try:
            cx = float(element.get('cx', 0)) * scale
            cy = float(element.get('cy', 0)) * scale
            r = float(element.get('r', 10)) * scale
            
            stroke = element.get('stroke', 'black')
            stroke_width = max(min_stroke, int(float(element.get('stroke-width', 2)) * scale))
            
            color = self._parse_color(stroke)
            
            draw.ellipse(
                [(cx - r, cy - r), (cx + r, cy + r)],
                outline=color,
                width=stroke_width
            )
        except (ValueError, AttributeError):
            pass

    def _draw_rect_enhanced(self, draw, element, scale, min_stroke):
        """Draw rectangle with enhanced stroke."""
        try:
            x = float(element.get('x', 0)) * scale
            y = float(element.get('y', 0)) * scale
            w = float(element.get('width', 100)) * scale
            h = float(element.get('height', 100)) * scale
            
            stroke = element.get('stroke', 'black')
            stroke_width = max(min_stroke, int(float(element.get('stroke-width', 2)) * scale))
            
            color = self._parse_color(stroke)
            
            draw.rectangle(
                [(x, y), (x + w, y + h)],
                outline=color,
                width=stroke_width
            )
        except (ValueError, AttributeError):
            pass

    def _draw_path_enhanced(self, draw, element, scale, min_stroke):
        """Draw SVG path with enhanced stroke."""
        try:
            d = element.get('d', '')
            stroke = element.get('stroke', 'black')
            stroke_width = max(min_stroke, int(float(element.get('stroke-width', 2)) * scale))
            
            color = self._parse_color(stroke)
            
            # Extract coordinates from path
            coords = re.findall(r'([0-9.-]+)[,\s]+([0-9.-]+)', d)
            if coords:
                points = [(float(x) * scale, float(y) * scale) for x, y in coords]
                if len(points) > 1:
                    draw.line(points, fill=color, width=stroke_width)
        except (ValueError, AttributeError, IndexError):
            pass

    def _draw_polyline_enhanced(self, draw, element, scale, min_stroke):
        """Draw polyline with enhanced stroke."""
        try:
            points_str = element.get('points', '')
            points = self._parse_points(points_str, scale)
            
            if points:
                stroke = element.get('stroke', 'black')
                stroke_width = max(min_stroke, int(float(element.get('stroke-width', 2)) * scale))
                
                color = self._parse_color(stroke)
                draw.line(points, fill=color, width=stroke_width)
        except (ValueError, AttributeError):
            pass

    def _draw_polygon_enhanced(self, draw, element, scale, min_stroke):
        """Draw polygon with enhanced stroke."""
        try:
            points_str = element.get('points', '')
            points = self._parse_points(points_str, scale)
            
            if points and len(points) >= 3:
                stroke = element.get('stroke', 'black')
                stroke_width = max(min_stroke, int(float(element.get('stroke-width', 2)) * scale))
                
                color = self._parse_color(stroke)
                
                # Close the polygon
                closed_points = points + [points[0]]
                draw.line(closed_points, fill=color, width=stroke_width)
        except (ValueError, AttributeError):
            pass

    def _draw_line_enhanced(self, draw, element, scale, min_stroke):
        """Draw line with enhanced stroke."""
        try:
            x1 = float(element.get('x1', 0)) * scale
            y1 = float(element.get('y1', 0)) * scale
            x2 = float(element.get('x2', 100)) * scale
            y2 = float(element.get('y2', 100)) * scale
            
            stroke = element.get('stroke', 'black')
            stroke_width = max(min_stroke, int(float(element.get('stroke-width', 2)) * scale))
            
            color = self._parse_color(stroke)
            
            draw.line([(x1, y1), (x2, y2)], fill=color, width=stroke_width)
        except (ValueError, AttributeError):
            pass

    def _parse_points(self, points_str: str, scale: float) -> List[Tuple[float, float]]:
        """Parse SVG points string."""
        try:
            points = []
            parts = points_str.replace(',', ' ').split()
            for i in range(0, len(parts) - 1, 2):
                x = float(parts[i]) * scale
                y = float(parts[i + 1]) * scale
                points.append((x, y))
            return points
        except (ValueError, IndexError):
            return []

    def _parse_color(self, color_str: str) -> str:
        """Parse color string to PIL-compatible format."""
        color_map = {
            'black': 'black',
            'white': 'white',
            'red': 'red',
            'blue': 'blue',
            'green': 'green',
            'gray': 'gray',
            'grey': 'gray',
        }
        
        if color_str.lower() in color_map:
            return color_map[color_str.lower()]
        
        # If it's hex color, return as-is
        if color_str.startswith('#'):
            return color_str
        
        # Default to black
        return 'black'

    def _create_blank_png(self) -> bytes:
        """Create a blank white PNG (fallback)."""
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        buffer = BytesIO()
        img.save(buffer, format="PNG", quality=90)
        buffer.seek(0)
        return buffer.getvalue()

    def export_svg_to_file(self, svg_content: str, output_path: str) -> str:
        """Export SVG to PNG file."""
        png_bytes = self.export_svg_to_png(svg_content)

        with open(output_path, "wb") as f:
            f.write(png_bytes)

        return output_path

    def get_image_dimensions(self, svg_content: str) -> Tuple[int, int]:
        """Get PNG image dimensions from SVG."""
        try:
            root = ET.fromstring(svg_content)
            
            viewbox = root.get("viewBox")
            width_str = root.get("width", "800")
            height_str = root.get("height", "600")
            
            if viewbox:
                parts = viewbox.split()
                width = int(float(parts[2]))
                height = int(float(parts[3]))
            else:
                width = int(float(width_str.replace("px", "")))
                height = int(float(height_str.replace("px", "")))
            
            scale = self.dpi / 96
            pixel_width = int(width * scale)
            pixel_height = int(height * scale)
            
            return (pixel_width, pixel_height)
        except:
            return (312, 312)  # Default

    def get_file_size(self, file_path: str) -> int:
        """Get size of PNG file in bytes."""
        return os.path.getsize(file_path)

    def convert_bytes_to_image(self, png_bytes: bytes) -> Image.Image:
        """Convert PNG bytes to PIL Image object."""
        return Image.open(BytesIO(png_bytes))

    def batch_export(self, svg_dict: dict, output_dir: str) -> dict:
        """Export multiple SVGs to PNG files."""
        os.makedirs(output_dir, exist_ok=True)

        results = {}
        for name, svg_content in svg_dict.items():
            output_path = os.path.join(output_dir, f"{name}.png")
            self.export_svg_to_file(svg_content, output_path)
            results[name] = output_path

        return results

    def set_quality(self, quality: int) -> "PNGExporter":
        """Set quality and return self for chaining."""
        if quality < 1 or quality > 100:
            raise ValueError("Quality must be between 1 and 100")
        self.quality = quality
        return self

    def set_dpi(self, dpi: int) -> "PNGExporter":
        """Set DPI and return self for chaining."""
        if dpi < 72 or dpi > 600:
            raise ValueError("DPI must be between 72 and 600")
        self.dpi = dpi
        return self
