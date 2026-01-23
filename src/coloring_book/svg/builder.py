"""SVG Builder - High-level SVG construction for coloring books."""

from typing import List, Optional, Dict, Tuple, Union


class SVGBuilder:
    """Builder pattern for constructing SVG elements."""
    
    def __init__(self, width: int = 400, height: int = 400, viewBox: Optional[str] = None):
        """Initialize SVG builder.
        
        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
            viewBox: Optional viewBox attribute (e.g., "0 0 400 400")
        """
        self.width = width
        self.height = height
        self.viewBox = viewBox or f"0 0 {width} {height}"
        self.elements: List[str] = []
        
        # Coloring-book defaults
        self.line_width = 2
        self.line_color = "black"
        self.fill_color = "none"
    
    def set_layer_config(self, line_width: float = 2, line_color: str = "black", 
                        fill_color: str = "none") -> 'SVGBuilder':
        """Configure default layer settings for all elements.
        
        Args:
            line_width: Stroke width for all elements
            line_color: Stroke color for all elements
            fill_color: Fill color (default "none" for coloring books)
        
        Returns:
            Self for chaining
        """
        self.line_width = line_width
        self.line_color = line_color
        self.fill_color = fill_color
        return self
    
    def add_circle(self, cx: float, cy: float, r: float, 
                  fill: Optional[str] = None, stroke: Optional[str] = None) -> 'SVGBuilder':
        """Add circle element (coloring-friendly: stroke only by default).
        
        Args:
            cx: Center X coordinate
            cy: Center Y coordinate
            r: Radius
            fill: Fill color (default: none)
            stroke: Stroke color (default: black)
        
        Returns:
            Self for chaining
        """
        attrs = f'cx="{cx}" cy="{cy}" r="{r}" stroke="{stroke or self.line_color}" stroke-width="{self.line_width}"'
        fill_color = fill if fill is not None else self.fill_color
        attrs += f' fill="{fill_color}"'
        self.elements.append(f'<circle {attrs} />')
        return self
    
    def add_path(self, d: str, fill: Optional[str] = None, stroke: Optional[str] = None) -> 'SVGBuilder':
        """Add path element.
        
        Args:
            d: Path data (SVG path commands)
            fill: Fill color
            stroke: Stroke color
        
        Returns:
            Self for chaining
        """
        attrs = f'd="{d}" stroke="{stroke or self.line_color}" stroke-width="{self.line_width}"'
        fill_color = fill if fill is not None else self.fill_color
        attrs += f' fill="{fill_color}"'
        self.elements.append(f'<path {attrs} />')
        return self
    
    def add_polygon(self, points: Union[str, List[Tuple[float, float]]], 
                   fill: Optional[str] = None, stroke: Optional[str] = None) -> 'SVGBuilder':
        """Add polygon element.
        
        Args:
            points: Points string or list of (x, y) tuples
            fill: Fill color
            stroke: Stroke color
        
        Returns:
            Self for chaining
        """
        # Convert list of tuples to points string if needed
        if isinstance(points, list):
            points = ' '.join([f'{x},{y}' for x, y in points])
        
        attrs = f'points="{points}" stroke="{stroke or self.line_color}" stroke-width="{self.line_width}"'
        fill_color = fill if fill is not None else self.fill_color
        attrs += f' fill="{fill_color}"'
        self.elements.append(f'<polygon {attrs} />')
        return self
    
    def add_line(self, x1: float, y1: float, x2: float, y2: float, 
                stroke: Optional[str] = None, stroke_width: Optional[float] = None) -> 'SVGBuilder':
        """Add line element.
        
        Args:
            x1: Start X coordinate
            y1: Start Y coordinate
            x2: End X coordinate
            y2: End Y coordinate
            stroke: Stroke color
            stroke_width: Stroke width
        
        Returns:
            Self for chaining
        """
        stroke_val = stroke or self.line_color
        width_val = stroke_width if stroke_width is not None else self.line_width
        attrs = f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke_val}" stroke-width="{width_val}"'
        self.elements.append(f'<line {attrs} />')
        return self
    
    def add_ellipse(self, cx: float, cy: float, rx: float, ry: float,
                   fill: Optional[str] = None, stroke: Optional[str] = None) -> 'SVGBuilder':
        """Add ellipse element.
        
        Args:
            cx: Center X coordinate
            cy: Center Y coordinate
            rx: Horizontal radius
            ry: Vertical radius
            fill: Fill color
            stroke: Stroke color
        
        Returns:
            Self for chaining
        """
        attrs = f'cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" stroke="{stroke or self.line_color}" stroke-width="{self.line_width}"'
        fill_color = fill if fill is not None else self.fill_color
        attrs += f' fill="{fill_color}"'
        self.elements.append(f'<ellipse {attrs} />')
        return self
    
    def add_rect(self, x: float, y: float, width: float, height: float,
                fill: Optional[str] = None, stroke: Optional[str] = None) -> 'SVGBuilder':
        """Add rectangle element.
        
        Args:
            x: Left X coordinate
            y: Top Y coordinate
            width: Rectangle width
            height: Rectangle height
            fill: Fill color
            stroke: Stroke color
        
        Returns:
            Self for chaining
        """
        attrs = f'x="{x}" y="{y}" width="{width}" height="{height}" stroke="{stroke or self.line_color}" stroke-width="{self.line_width}"'
        fill_color = fill if fill is not None else self.fill_color
        attrs += f' fill="{fill_color}"'
        self.elements.append(f'<rect {attrs} />')
        return self
    
    def to_string(self) -> str:
        """Convert to SVG string.
        
        Returns:
            Complete SVG document string
        """
        svg_attrs = f'width="{self.width}" height="{self.height}" viewBox="{self.viewBox}" xmlns="http://www.w3.org/2000/svg"'
        inner = '\n  '.join(self.elements)
        return f'<svg {svg_attrs}>\n  {inner}\n</svg>'
    
    def __str__(self) -> str:
        """String representation."""
        return self.to_string()
