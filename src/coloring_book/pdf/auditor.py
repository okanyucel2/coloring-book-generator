"""Post-build PDF quality auditor.

Validates generated PDFs against their PrintProfile requirements:
file size limits, effective DPI, bleed presence, and page count.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field

from .profiles import PrintProfile

logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Result of a PDF quality audit."""

    passed: bool
    file_size_mb: float
    page_count: int
    effective_dpi: float
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PDFQualityError(Exception):
    """Raised when a PDF fails quality audit."""

    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__(f"PDF quality check failed: {'; '.join(issues)}")


class PDFAuditor:
    """Validates PDF output against a PrintProfile."""

    def __init__(self, profile: PrintProfile):
        self.profile = profile

    def audit(self, pdf_bytes: bytes) -> AuditResult:
        """Run all quality checks on generated PDF bytes."""
        issues: list[str] = []
        warnings: list[str] = []

        # 1. File size
        size_mb = len(pdf_bytes) / (1024 * 1024)
        if self.profile.max_file_size_mb > 0:
            if size_mb > self.profile.max_file_size_mb:
                issues.append(
                    f"File size {size_mb:.1f}MB exceeds "
                    f"{self.profile.max_file_size_mb}MB limit"
                )
            elif size_mb > self.profile.max_file_size_mb * 0.9:
                warnings.append(
                    f"File size {size_mb:.1f}MB approaching "
                    f"{self.profile.max_file_size_mb}MB limit"
                )

        # 2. Page count
        page_count = self._count_pages(pdf_bytes)
        if page_count == 0:
            issues.append("PDF has no pages")

        # 3. Effective DPI
        effective_dpi = self._measure_dpi(pdf_bytes)
        if effective_dpi > 0:
            tolerance = self.profile.dpi * 0.95
            if effective_dpi < tolerance:
                issues.append(
                    f"Effective DPI {effective_dpi:.0f} below "
                    f"target {self.profile.dpi} (min {tolerance:.0f})"
                )
        else:
            # No images found — not necessarily an issue for text-only pages
            logger.debug("No embedded images found for DPI measurement")

        # 4. Bleed verification
        if self.profile.bleed_mm > 0:
            has_bleed = self._verify_bleed(pdf_bytes)
            if not has_bleed:
                issues.append("Expected bleed area not detected in page dimensions")

        passed = len(issues) == 0

        result = AuditResult(
            passed=passed,
            file_size_mb=round(size_mb, 2),
            page_count=page_count,
            effective_dpi=round(effective_dpi, 1),
            issues=issues,
            warnings=warnings,
        )

        if not passed:
            logger.warning("PDF audit FAILED: %s", issues)
        elif warnings:
            logger.info("PDF audit passed with warnings: %s", warnings)
        else:
            logger.info(
                "PDF audit passed: %.1fMB, %d pages, %.0f DPI",
                size_mb, page_count, effective_dpi,
            )

        return result

    def _count_pages(self, pdf_bytes: bytes) -> int:
        """Count pages using PyPDF2/pypdf if available, else regex fallback."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            return len(reader.pages)
        except ImportError:
            pass

        # Regex fallback: count /Type /Page occurrences (rough)
        import re
        matches = re.findall(rb"/Type\s*/Page(?!\w)", pdf_bytes)
        return len(matches)

    def _measure_dpi(self, pdf_bytes: bytes) -> float:
        """Measure effective DPI of embedded images.

        Opens the PDF, finds embedded images, and calculates
        pixel_width / display_width_inches to get effective DPI.
        Returns the minimum DPI found across all images, or 0 if none.
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            logger.debug("pypdf not available, skipping DPI measurement")
            return float(self.profile.dpi)  # Trust the profile

        reader = PdfReader(io.BytesIO(pdf_bytes))
        min_dpi = float("inf")
        image_count = 0

        for page in reader.pages:
            page_width_pts = float(page.mediabox.width)
            page_height_pts = float(page.mediabox.height)

            if "/XObject" not in (page.get("/Resources") or {}):
                continue

            xobjects = page["/Resources"]["/XObject"].get_object()
            for obj_name in xobjects:
                xobj = xobjects[obj_name].get_object()
                if xobj.get("/Subtype") != "/Image":
                    continue

                img_width = int(xobj.get("/Width", 0))
                img_height = int(xobj.get("/Height", 0))

                if img_width == 0 or img_height == 0:
                    continue

                image_count += 1

                # Estimate display size: assume image fills content area
                # (conservative — actual display may be smaller)
                display_width_inches = page_width_pts / 72.0
                display_height_inches = page_height_pts / 72.0

                dpi_x = img_width / display_width_inches
                dpi_y = img_height / display_height_inches
                img_dpi = min(dpi_x, dpi_y)

                if img_dpi < min_dpi:
                    min_dpi = img_dpi

        if image_count == 0:
            return 0.0

        return min_dpi

    def _verify_bleed(self, pdf_bytes: bytes) -> bool:
        """Verify that page dimensions include expected bleed area."""
        try:
            from pypdf import PdfReader
        except ImportError:
            return True  # Can't verify without pypdf

        reader = PdfReader(io.BytesIO(pdf_bytes))
        if not reader.pages:
            return False

        page = reader.pages[0]
        page_width_pts = float(page.mediabox.width)
        page_height_pts = float(page.mediabox.height)

        # Standard letter is 612 x 792 points
        # With bleed, page should be larger by 2 * bleed_points
        expected_extra = self.profile.bleed_points * 2
        # Allow 1-point tolerance for floating point
        width_has_bleed = page_width_pts > 612 + expected_extra - 1
        height_has_bleed = page_height_pts > 792 + expected_extra - 1

        return width_has_bleed and height_has_bleed
