"""PDF generation module for coloring books."""

from .generator import PDFGenerator, PDFPage
from .layouts import (
    PageLayout,
    PageLayoutPreset,
    MarginConfig,
    get_preset,
    create_custom_layout,
)

__all__ = [
    "PDFGenerator",
    "PDFPage",
    "PageLayout",
    "PageLayoutPreset",
    "MarginConfig",
    "get_preset",
    "create_custom_layout",
]
__version__ = "0.1.0"
