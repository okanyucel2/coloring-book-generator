"""SVG Template System - Base templates for all animal drawings."""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum


class ColorScheme(Enum):
    """Standard color schemes for animals."""
    PASTEL = {"primary": "#FFB6C1", "secondary": "#FFE4E1", "accent": "#FF69B4"}
    VIBRANT = {"primary": "#FF0000", "secondary": "#00FF00", "accent": "#0000FF"}
    NATURAL = {"primary": "#8B4513", "secondary": "#D2B48C", "accent": "#654321"}


@dataclass
class SVGElement:
    """Represents a single SVG element."""
    tag: str
    attributes: Dict[str, str]
    children: List['SVGElement'] = None
    content: str = None

    def to_svg(self) -> str:
        """Convert element to SVG string."""
        attrs = " ".join([f'{k}="{v}"' for k, v in self.attributes.items()])
        if self.children or self.content:
            inner = self.content or "".join([child.to_svg() for child in (self.children or [])])
            return f"<{self.tag} {attrs}>{inner}</{self.tag}>"
        return f"<{self.tag} {attrs} />"


class SVGTemplate:
    """Base SVG template for all animals."""
    
    def __init__(self, width: int = 400, height: int = 400, color_scheme: ColorScheme = ColorScheme.NATURAL):
        self.width = width
        self.height = height
        self.color_scheme = color_scheme
        self.elements: List[SVGElement] = []
    
    def add_element(self, element: SVGElement) -> 'SVGTemplate':
        """Add SVG element to template."""
        self.elements.append(element)
        return self
    
    def add_circle(self, cx: float, cy: float, r: float, fill: str = None, stroke: str = None) -> 'SVGTemplate':
        """Add circle element."""
        attrs = {"cx": str(cx), "cy": str(cy), "r": str(r)}
        if fill:
            attrs["fill"] = fill
        if stroke:
            attrs["stroke"] = stroke
            attrs["stroke-width"] = "2"
        self.add_element(SVGElement("circle", attrs))
        return self
    
    def add_path(self, d: str, fill: str = None, stroke: str = None) -> 'SVGTemplate':
        """Add path element."""
        attrs = {"d": d}
        if fill:
            attrs["fill"] = fill
        if stroke:
            attrs["stroke"] = stroke
            attrs["stroke-width"] = "2"
        self.add_element(SVGElement("path", attrs))
        return self
    
    def add_line(self, x1: float, y1: float, x2: float, y2: float, stroke: str = "black") -> 'SVGTemplate':
        """Add line element."""
        attrs = {"x1": str(x1), "y1": str(y1), "x2": str(x2), "y2": str(y2), "stroke": stroke, "stroke-width": "2"}
        self.add_element(SVGElement("line", attrs))
        return self
    
    def render(self) -> str:
        """Render complete SVG."""
        svg_attrs = {
            "width": str(self.width),
            "height": str(self.height),
            "viewBox": f"0 0 {self.width} {self.height}",
            "xmlns": "http://www.w3.org/2000/svg"
        }
        svg = SVGElement("svg", svg_attrs)
        svg.children = self.elements
        return svg.to_svg()


# Preset templates
class AnimalTemplates:
    """Collection of animal-specific SVG templates."""
    
    @staticmethod
    def create_cat_template(color_scheme: ColorScheme = ColorScheme.NATURAL) -> SVGTemplate:
        """Create base template for cat drawing."""
        template = SVGTemplate(400, 400, color_scheme)
        # Grid reference lines (optional, can be removed in coloring book version)
        return template
    
    @staticmethod
    def create_dog_template(color_scheme: ColorScheme = ColorScheme.NATURAL) -> SVGTemplate:
        """Create base template for dog drawing."""
        template = SVGTemplate(400, 400, color_scheme)
        return template
    
    @staticmethod
    def create_bird_template(color_scheme: ColorScheme = ColorScheme.NATURAL) -> SVGTemplate:
        """Create base template for bird drawing."""
        template = SVGTemplate(400, 400, color_scheme)
        return template
