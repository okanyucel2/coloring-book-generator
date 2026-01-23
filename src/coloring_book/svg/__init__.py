"""SVG Generation module for coloring book animals."""

from .base import AnimalDrawer
from .builder import SVGBuilder
from .animals import CatDrawer, DogDrawer, BirdDrawer
from .factory import AnimalFactory
from .registry import AnimalRegistry

__all__ = [
    "AnimalDrawer",
    "SVGBuilder",
    "CatDrawer",
    "DogDrawer",
    "BirdDrawer",
    "AnimalFactory",
    "AnimalRegistry",
]
