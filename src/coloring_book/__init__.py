"""Coloring Book - Animal Drawing Engine"""

from .svg.base import AnimalDrawer
from .svg.builder import SVGBuilder
from .svg.animals import CatDrawer, DogDrawer, BirdDrawer
from .svg.registry import AnimalRegistry
from .svg.factory import AnimalFactory

__all__ = [
    "AnimalDrawer",
    "SVGBuilder",
    "CatDrawer",
    "DogDrawer",
    "BirdDrawer",
    "AnimalRegistry",
    "AnimalFactory",
]
__version__ = "0.1.0"
