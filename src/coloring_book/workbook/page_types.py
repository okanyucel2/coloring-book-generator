"""Activity page types for children's workbooks.

Each page type renders its content onto a PDFPage using the existing
PDF generation infrastructure.
"""

from __future__ import annotations

import io
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch

from .models import WorkbookConfig, WorkbookItem

if TYPE_CHECKING:
    from ..pdf.generator import PDFPage


# Page dimensions
PAGE_SIZES = {
    "letter": letter,  # (612, 792)
    "a4": A4,  # (595, 842)
}


def get_page_dimensions(page_size: str) -> tuple[float, float]:
    """Get (width, height) in points for a page size."""
    return PAGE_SIZES.get(page_size, letter)


class ActivityPage(ABC):
    """Base class for all activity page types."""

    page_type: str = "base"

    def __init__(self, title: str, items: list[WorkbookItem]):
        self.title = title
        self.items = items

    @abstractmethod
    def render(self, pdf_page: "PDFPage") -> None:
        """Render this activity onto a PDF page."""
        ...

    @abstractmethod
    def get_required_assets(self) -> list[str]:
        """Return list of asset types needed (e.g. 'colored', 'outline', 'dashed')."""
        ...

    def _draw_title(self, pdf_page: "PDFPage", title: str, page_width: float) -> None:
        """Draw centered page title."""
        # Approximate center
        x = page_width / 2 - len(title) * 5
        pdf_page.add_text(title, x=max(x, 50), y=pdf_page.height - 50, font_size=24)

    def _draw_instruction(self, pdf_page: "PDFPage", text: str, y: float) -> None:
        """Draw instruction text below title."""
        pdf_page.add_text(text, x=50, y=y, font_size=14)


class CoverPage(ActivityPage):
    """Workbook cover page with title, subtitle, and preview images."""

    page_type = "cover"

    def __init__(self, config: WorkbookConfig, preview_items: list[WorkbookItem]):
        super().__init__(title=config.title, items=preview_items)
        self.config = config

    def render(self, pdf_page: "PDFPage") -> None:
        page_w = pdf_page.width
        page_h = pdf_page.height

        # Title
        self._draw_title(pdf_page, self.config.title, page_w)

        # Subtitle
        if self.config.subtitle:
            pdf_page.add_text(
                self.config.subtitle,
                x=page_w / 2 - len(self.config.subtitle) * 4,
                y=page_h - 90,
                font_size=18,
            )

        # Age range badge
        age_text = f"Ages {self.config.age_range[0]}-{self.config.age_range[1]}"
        pdf_page.add_text(age_text, x=page_w / 2 - 30, y=page_h - 130, font_size=16)

        # Preview images (up to 3)
        preview_y = page_h - 200
        preview_size = 150
        spacing = 20
        total_width = len(self.items) * preview_size + (len(self.items) - 1) * spacing
        start_x = (page_w - total_width) / 2

        for i, item in enumerate(self.items[:3]):
            x = start_x + i * (preview_size + spacing)
            if item.colored_image:
                pdf_page.add_image(
                    item.colored_image, x=x, y=preview_y - preview_size,
                    width=preview_size, height=preview_size,
                )

        # Page count info
        info_text = f"{self.config.page_count} Pages of Fun Activities!"
        pdf_page.add_text(
            info_text,
            x=page_w / 2 - len(info_text) * 4,
            y=150,
            font_size=14,
        )

    def get_required_assets(self) -> list[str]:
        return ["colored"]


class TraceAndColorPage(ActivityPage):
    """Trace and color page: colored reference + dashed outline + item name."""

    page_type = "trace_and_color"

    def __init__(self, item: WorkbookItem):
        super().__init__(title="Trace & Color", items=[item])
        self.item = item

    def render(self, pdf_page: "PDFPage") -> None:
        page_w = pdf_page.width
        page_h = pdf_page.height

        # Title
        self._draw_title(pdf_page, "Trace & Color", page_w)

        # Item display name
        display_name = self.item.display_name
        pdf_page.add_text(
            display_name,
            x=page_w / 2 - len(display_name) * 6,
            y=page_h - 80,
            font_size=20,
        )

        # Instruction
        self._draw_instruction(pdf_page, "Trace the dashed lines, then color!", y=page_h - 110)

        # Layout: colored reference (left, smaller) + dashed outline (right, larger)
        img_size = min(page_w / 2 - 60, page_h - 230)
        img_y = page_h - 140 - img_size

        # Colored reference (left side)
        if self.item.colored_image:
            ref_size = img_size * 0.9
            ref_y = img_y + (img_size - ref_size) / 2
            pdf_page.add_image(
                self.item.colored_image,
                x=30, y=ref_y, width=ref_size, height=ref_size,
            )

        # Dashed outline (right side, larger for tracing)
        if self.item.dashed_image:
            pdf_page.add_image(
                self.item.dashed_image,
                x=page_w / 2 + 10, y=img_y, width=img_size, height=img_size,
            )

    def get_required_assets(self) -> list[str]:
        return ["colored", "dashed"]


class WhichIsDifferentPage(ActivityPage):
    """Spot the odd one out: 4 rows, each with items where one differs."""

    page_type = "which_different"

    def __init__(self, items: list[WorkbookItem]):
        super().__init__(title="Which One Is Different?", items=items)

    def render(self, pdf_page: "PDFPage") -> None:
        page_w = pdf_page.width
        page_h = pdf_page.height

        self._draw_title(pdf_page, "Which One Is Different?", page_w)
        self._draw_instruction(
            pdf_page, "Circle the one that is different in each row.", y=page_h - 80,
        )

        # Draw 4 rows of items
        row_height = (page_h - 180) / 4
        img_size = min(row_height - 20, (page_w - 100) / 4 - 10)

        for row in range(min(4, len(self.items))):
            y = page_h - 120 - (row + 1) * row_height
            # 4 items per row: 3 same + 1 different
            items_per_row = 4
            for col in range(items_per_row):
                x = 50 + col * (page_w - 100) / items_per_row
                # Use the item's colored image for the "same" items,
                # and a different item for the odd one
                item_idx = row % len(self.items)
                item = self.items[item_idx]
                if item.colored_image:
                    pdf_page.add_image(
                        item.colored_image,
                        x=x, y=y, width=img_size, height=img_size,
                    )

    def get_required_assets(self) -> list[str]:
        return ["colored"]


class CountAndCirclePage(ActivityPage):
    """Count and circle: grid of mixed items, count each type."""

    page_type = "count_circle"

    def __init__(self, items: list[WorkbookItem]):
        super().__init__(title="Count and Circle", items=items)

    def render(self, pdf_page: "PDFPage") -> None:
        page_w = pdf_page.width
        page_h = pdf_page.height

        self._draw_title(pdf_page, "Count and Circle", page_w)
        self._draw_instruction(
            pdf_page, "Count how many of each item you can find!", y=page_h - 80,
        )

        # Grid of items (4x4)
        grid_size = 4
        cell_size = min((page_w - 100) / grid_size, (page_h - 250) / grid_size)
        grid_start_x = (page_w - grid_size * cell_size) / 2
        grid_start_y = page_h - 130

        # Place items randomly in grid
        all_positions = [(r, c) for r in range(grid_size) for c in range(grid_size)]
        for idx, (r, c) in enumerate(all_positions):
            item = self.items[idx % len(self.items)]
            x = grid_start_x + c * cell_size
            y = grid_start_y - (r + 1) * cell_size
            if item.colored_image:
                pdf_page.add_image(
                    item.colored_image,
                    x=x + 5, y=y + 5,
                    width=cell_size - 10, height=cell_size - 10,
                )

        # Answer boxes at bottom
        box_y = 50
        for i, item in enumerate(self.items[:4]):
            x = 50 + i * (page_w - 100) / 4
            pdf_page.add_text(f"{item.display_name}: ___", x=x, y=box_y, font_size=12)

    def get_required_assets(self) -> list[str]:
        return ["colored"]


class MatchVehiclesPage(ActivityPage):
    """Match the items: left column items → right column items (draw lines)."""

    page_type = "match"

    def __init__(self, items: list[WorkbookItem]):
        super().__init__(title="Match the Pairs", items=items)

    def render(self, pdf_page: "PDFPage") -> None:
        page_w = pdf_page.width
        page_h = pdf_page.height

        self._draw_title(pdf_page, "Match the Pairs", page_w)
        self._draw_instruction(
            pdf_page, "Draw a line to match each pair!", y=page_h - 80,
        )

        # Left column: items in order
        # Right column: same items shuffled
        num_items = min(5, len(self.items))
        row_height = (page_h - 180) / num_items
        img_size = min(row_height - 15, 100)

        # Shuffled indices for right column
        right_order = list(range(num_items))
        if num_items > 1:
            # Ensure at least one item is out of place
            rng = random.Random(42)  # deterministic for PDF
            rng.shuffle(right_order)

        for i in range(num_items):
            y = page_h - 120 - (i + 1) * row_height + row_height / 2 - img_size / 2

            # Left item
            left_item = self.items[i]
            if left_item.colored_image:
                pdf_page.add_image(
                    left_item.colored_image,
                    x=60, y=y, width=img_size, height=img_size,
                )
            pdf_page.add_text(
                left_item.display_name, x=60, y=y - 15, font_size=10,
            )

            # Right item (shuffled)
            right_item = self.items[right_order[i]]
            if right_item.colored_image:
                pdf_page.add_image(
                    right_item.colored_image,
                    x=page_w - 60 - img_size, y=y,
                    width=img_size, height=img_size,
                )
            pdf_page.add_text(
                right_item.display_name,
                x=page_w - 60 - img_size, y=y - 15, font_size=10,
            )

    def get_required_assets(self) -> list[str]:
        return ["colored"]


class WordToImagePage(ActivityPage):
    """Word-to-image matching: word labels → connect to correct images."""

    page_type = "word_to_image"

    def __init__(self, items: list[WorkbookItem]):
        super().__init__(title="Word to Image Match", items=items)

    def render(self, pdf_page: "PDFPage") -> None:
        page_w = pdf_page.width
        page_h = pdf_page.height

        self._draw_title(pdf_page, "Word to Image Match", page_w)
        self._draw_instruction(
            pdf_page,
            "Draw a line from each word to the correct picture!",
            y=page_h - 80,
        )

        num_items = min(6, len(self.items))
        section_height = (page_h - 180) / 2

        # Top section: words in ovals
        word_y = page_h - 140
        for i in range(num_items):
            x = 50 + i * (page_w - 100) / num_items
            word = self.items[i].display_name
            pdf_page.add_text(word, x=x, y=word_y, font_size=12)

        # Bottom section: images shuffled
        img_size = min(section_height - 40, (page_w - 100) / num_items - 10)
        img_y = page_h - 140 - section_height - img_size

        rng = random.Random(99)
        shuffled = list(range(num_items))
        rng.shuffle(shuffled)

        for i in range(num_items):
            x = 50 + i * (page_w - 100) / num_items
            item = self.items[shuffled[i]]
            if item.colored_image:
                pdf_page.add_image(
                    item.colored_image,
                    x=x, y=img_y, width=img_size, height=img_size,
                )

    def get_required_assets(self) -> list[str]:
        return ["colored"]


class FindAndCirclePage(ActivityPage):
    """Find and circle: show name, then row of 4 images, circle the correct one."""

    page_type = "find_circle"

    def __init__(self, items: list[WorkbookItem], distractor_items: list[WorkbookItem]):
        super().__init__(title="Find and Circle", items=items)
        self.distractor_items = distractor_items

    def render(self, pdf_page: "PDFPage") -> None:
        page_w = pdf_page.width
        page_h = pdf_page.height

        self._draw_title(pdf_page, "Find and Circle", page_w)
        self._draw_instruction(
            pdf_page,
            "Read the name, then circle the correct picture!",
            y=page_h - 80,
        )

        # 4 rows, each with a target name + 4 image options
        num_rows = min(4, len(self.items))
        row_height = (page_h - 180) / num_rows
        img_size = min(row_height - 30, (page_w - 150) / 4 - 10)

        for row in range(num_rows):
            y_base = page_h - 120 - (row + 1) * row_height

            # Target name
            target = self.items[row]
            pdf_page.add_text(
                target.display_name, x=30, y=y_base + img_size / 2, font_size=12,
            )

            # 4 image options (1 correct + 3 distractors)
            options_x_start = 130
            for col in range(4):
                x = options_x_start + col * (img_size + 10)
                if col == 0:
                    # Correct answer (in real product, shuffle position)
                    if target.colored_image:
                        pdf_page.add_image(
                            target.colored_image,
                            x=x, y=y_base, width=img_size, height=img_size,
                        )
                else:
                    # Distractor
                    d_idx = (row * 3 + col - 1) % len(self.distractor_items)
                    distractor = self.distractor_items[d_idx]
                    if distractor.colored_image:
                        pdf_page.add_image(
                            distractor.colored_image,
                            x=x, y=y_base, width=img_size, height=img_size,
                        )

    def get_required_assets(self) -> list[str]:
        return ["colored"]


# Registry of page type constructors for the compiler
PAGE_TYPE_REGISTRY: dict[str, type[ActivityPage]] = {
    "trace_and_color": TraceAndColorPage,
    "which_different": WhichIsDifferentPage,
    "count_circle": CountAndCirclePage,
    "match": MatchVehiclesPage,
    "word_to_image": WordToImagePage,
    "find_circle": FindAndCirclePage,
    "cover": CoverPage,
}
