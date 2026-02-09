"""Workbook compiler: orchestrates image gen → page sequence → PDF output."""

from __future__ import annotations

import logging
import random
from typing import Optional

from ..pdf.generator import PDFGenerator
from ..pdf.layouts import PageLayout
from .image_gen import WorkbookImageGenerator
from .models import Workbook, WorkbookConfig, WorkbookItem
from .page_types import (
    CoverPage,
    CountAndCirclePage,
    FindAndCirclePage,
    MatchVehiclesPage,
    TraceAndColorPage,
    WhichIsDifferentPage,
    WordToImagePage,
    get_page_dimensions,
)
from .themes import get_theme

logger = logging.getLogger(__name__)


class WorkbookCompiler:
    """Compiles a WorkbookConfig into a multi-page PDF workbook."""

    def __init__(
        self,
        config: WorkbookConfig,
        image_generator: Optional[WorkbookImageGenerator] = None,
    ):
        self.config = config
        self.image_gen = image_generator or WorkbookImageGenerator(ai_enabled=False)

    async def compile(self) -> bytes:
        """Generate all assets and compile into a PDF.

        Returns:
            PDF bytes
        """
        # Validate config
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Invalid workbook config: {'; '.join(errors)}")

        # 1. Resolve items from theme if needed
        items_to_generate = self._resolve_items()

        # 2. Generate all item assets
        logger.info(f"Generating assets for {len(items_to_generate)} items...")
        theme = get_theme(self.config.theme)
        item_pairs = [(name, theme.category) for name in items_to_generate]
        workbook_items = await self.image_gen.generate_items_batch(item_pairs)

        # 3. Build workbook
        workbook = Workbook(config=self.config, items=workbook_items)

        # 4. Build page sequence
        pages = self._build_page_sequence(workbook_items)

        # 5. Create PDF
        page_w, page_h = get_page_dimensions(self.config.page_size)
        pdf = PDFGenerator(
            title=self.config.title,
            author="Coloring Book Generator",
            page_width=page_w,
            page_height=page_h,
        )
        pdf.set_metadata(
            title=self.config.title,
            author="Coloring Book Generator",
            subject=f"{self.config.theme.title()} activity workbook",
        )

        # 6. Render cover
        cover = CoverPage(config=self.config, preview_items=workbook_items[:3])
        cover_page = pdf.add_page()
        cover.render(cover_page)

        # 7. Render activity pages
        for activity_page in pages:
            pdf_page = pdf.add_page()
            activity_page.render(pdf_page)

        # 8. Generate PDF
        logger.info(f"Compiled workbook: {pdf.page_count} pages")
        return pdf.generate()

    def _resolve_items(self) -> list[str]:
        """Resolve item list: use config items or pick from theme."""
        if self.config.items:
            return self.config.items

        theme = get_theme(self.config.theme)
        return theme.items[: self.config.page_count]

    def _build_page_sequence(self, items: list[WorkbookItem]) -> list:
        """Build the sequence of activity pages based on activity_mix.

        Distributes items across page types according to the config's activity_mix.
        """
        pages = []
        rng = random.Random(42)  # Deterministic for reproducible PDFs

        mix = self.config.activity_mix

        # Trace and Color pages (most common - one item per page)
        tc_count = mix.get("trace_and_color", 0)
        for i in range(tc_count):
            item = items[i % len(items)]
            pages.append(TraceAndColorPage(item=item))

        # Which Is Different pages
        wd_count = mix.get("which_different", 0)
        for i in range(wd_count):
            # Pick 4-5 items for each page
            start = (i * 4) % len(items)
            page_items = [items[(start + j) % len(items)] for j in range(min(4, len(items)))]
            pages.append(WhichIsDifferentPage(items=page_items))

        # Count and Circle pages
        cc_count = mix.get("count_circle", 0)
        for i in range(cc_count):
            start = (i * 3) % len(items)
            page_items = [items[(start + j) % len(items)] for j in range(min(3, len(items)))]
            pages.append(CountAndCirclePage(items=page_items))

        # Match pages
        m_count = mix.get("match", 0)
        for i in range(m_count):
            start = (i * 5) % len(items)
            page_items = [items[(start + j) % len(items)] for j in range(min(5, len(items)))]
            pages.append(MatchVehiclesPage(items=page_items))

        # Word to Image pages
        wi_count = mix.get("word_to_image", 0)
        for i in range(wi_count):
            start = (i * 6) % len(items)
            page_items = [items[(start + j) % len(items)] for j in range(min(6, len(items)))]
            pages.append(WordToImagePage(items=page_items))

        # Find and Circle pages
        fc_count = mix.get("find_circle", 0)
        for i in range(fc_count):
            start = (i * 4) % len(items)
            target_items = [items[(start + j) % len(items)] for j in range(min(4, len(items)))]
            # Distractors are other items not in the target set
            distractor_pool = [it for it in items if it not in target_items]
            if not distractor_pool:
                distractor_pool = items  # Fallback if not enough items
            distractors = [distractor_pool[j % len(distractor_pool)] for j in range(6)]
            pages.append(FindAndCirclePage(items=target_items, distractor_items=distractors))

        # Shuffle non-trace pages for variety (keep trace pages first for consistency)
        trace_pages = [p for p in pages if isinstance(p, TraceAndColorPage)]
        other_pages = [p for p in pages if not isinstance(p, TraceAndColorPage)]
        rng.shuffle(other_pages)

        # Interleave: trace pages with occasional activity pages mixed in
        result = []
        other_idx = 0
        for i, trace in enumerate(trace_pages):
            result.append(trace)
            # Insert an activity page every 3-4 trace pages
            if (i + 1) % 4 == 0 and other_idx < len(other_pages):
                result.append(other_pages[other_idx])
                other_idx += 1

        # Append remaining activity pages
        while other_idx < len(other_pages):
            result.append(other_pages[other_idx])
            other_idx += 1

        return result
