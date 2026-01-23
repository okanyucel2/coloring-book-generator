"""
Base AnimalDrawer class for SVG animal generation.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple


class AnimalDrawer(ABC):
    """Abstract base class for drawing animals as SVG."""

    def __init__(self, name: str, width: int = 200, height: int = 200):
        """
        Initialize AnimalDrawer.

        Args:
            name: Animal name (e.g., 'cat', 'dog')
            width: Canvas width in pixels
            height: Canvas height in pixels
        """
        self.name = name
        self.width = width
        self.height = height
        self.svg_elements = []

    @abstractmethod
    def draw(self) -> str:
        """
        Draw the animal and return SVG string.

        Returns:
            SVG string representation of the animal
        """
        pass

    def to_svg(self) -> str:
        """
        Convert drawing to SVG string (alias for draw).

        Returns:
            SVG string representation of the animal
        """
        return self.draw()

    def add_element(self, element: str) -> None:
        """Add an SVG element to the drawing."""
        self.svg_elements.append(element)

    def get_dimensions(self) -> Tuple[int, int]:
        """Get canvas dimensions."""
        return (self.width, self.height)

    def get_name(self) -> str:
        """Get animal name."""
        return self.name

    def reset(self) -> None:
        """Clear all SVG elements."""
        self.svg_elements = []

    def get_elements(self) -> List[str]:
        """Get all SVG elements."""
        return self.svg_elements.copy()

    def export_svg(self) -> str:
        """
        Export complete SVG with wrapper.

        Returns:
            Complete SVG document string
        """
        elements_str = "\n  ".join(self.svg_elements)
        return (
            f'<svg width="{self.width}" height="{self.height}" '
            f'xmlns="http://www.w3.org/2000/svg">\n'
            f'  {elements_str}\n'
            f'</svg>'
        )
