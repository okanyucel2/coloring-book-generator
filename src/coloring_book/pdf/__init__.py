"""PDF generation module for coloring books."""

from .generator import PDFGenerator, PDFPage
from .layouts import (
    PageLayout,
    PageLayoutPreset,
    MarginConfig,
    get_preset,
    create_custom_layout,
)
from .profiles import PrintProfile, PROFILES, get_profile
from .auditor import PDFAuditor, AuditResult, PDFQualityError

__all__ = [
    "PDFGenerator",
    "PDFPage",
    "PageLayout",
    "PageLayoutPreset",
    "MarginConfig",
    "get_preset",
    "create_custom_layout",
    "PrintProfile",
    "PROFILES",
    "get_profile",
    "PDFAuditor",
    "AuditResult",
    "PDFQualityError",
]
__version__ = "0.2.0"
