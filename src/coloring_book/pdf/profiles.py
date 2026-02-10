"""Print profiles for PDF generation.

Defines product-agnostic print profiles that control DPI, bleed, compression,
and other print parameters. Each profile targets a specific output context
(home printer, Etsy download, professional print shop, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrintProfile:
    """Immutable print configuration for PDF generation."""

    name: str
    dpi: int
    color_space: str  # "rgb" or "grayscale"
    bleed_mm: float  # 0 = no bleed
    show_crop_marks: bool
    jpeg_quality: int  # 1-100, used for image compression in PDF
    max_file_size_mb: int  # 0 = no limit
    page_size: str  # "letter", "a4"

    def __post_init__(self) -> None:
        if self.dpi < 72 or self.dpi > 600:
            raise ValueError(f"DPI must be 72-600, got {self.dpi}")
        if self.color_space not in ("rgb", "grayscale"):
            raise ValueError(f"color_space must be 'rgb' or 'grayscale', got {self.color_space}")
        if self.jpeg_quality < 1 or self.jpeg_quality > 100:
            raise ValueError(f"jpeg_quality must be 1-100, got {self.jpeg_quality}")
        if self.bleed_mm < 0:
            raise ValueError(f"bleed_mm must be >= 0, got {self.bleed_mm}")

    @property
    def bleed_points(self) -> float:
        """Bleed in PDF points (1 mm = 2.8346 points)."""
        return self.bleed_mm * 2.8346


PROFILES: dict[str, PrintProfile] = {
    "home": PrintProfile(
        name="home",
        dpi=150,
        color_space="rgb",
        bleed_mm=0,
        show_crop_marks=False,
        jpeg_quality=85,
        max_file_size_mb=0,
        page_size="letter",
    ),
    "etsy_standard": PrintProfile(
        name="etsy_standard",
        dpi=300,
        color_space="grayscale",
        bleed_mm=0,
        show_crop_marks=False,
        jpeg_quality=90,
        max_file_size_mb=20,
        page_size="letter",
    ),
    "pro_print": PrintProfile(
        name="pro_print",
        dpi=300,
        color_space="rgb",
        bleed_mm=3,
        show_crop_marks=True,
        jpeg_quality=95,
        max_file_size_mb=0,
        page_size="letter",
    ),
    "poster": PrintProfile(
        name="poster",
        dpi=300,
        color_space="rgb",
        bleed_mm=5,
        show_crop_marks=True,
        jpeg_quality=95,
        max_file_size_mb=0,
        page_size="letter",
    ),
}


def get_profile(name: str) -> PrintProfile:
    """Get a print profile by name.

    Args:
        name: Profile name (home, etsy_standard, pro_print, poster)

    Returns:
        PrintProfile instance

    Raises:
        ValueError: If profile not found
    """
    if name not in PROFILES:
        raise ValueError(f"Unknown profile: {name}. Available: {list(PROFILES.keys())}")
    return PROFILES[name]
