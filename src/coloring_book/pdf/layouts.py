"""Advanced page layout configurations for PDF generation."""

from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass, field


@dataclass
class MarginConfig:
    """Margin configuration."""

    top: float = 50
    bottom: float = 50
    left: float = 50
    right: float = 50

    @classmethod
    def symmetrical(cls, value: float) -> "MarginConfig":
        """Create symmetrical margins."""
        return cls(top=value, bottom=value, left=value, right=value)

    @classmethod
    def all_sides(cls, value: float) -> "MarginConfig":
        """Alias for symmetrical."""
        return cls.symmetrical(value)


class PageLayout:
    """Advanced page layout configuration."""

    def __init__(
        self,
        margin_top: float = 50,
        margin_left: float = 50,
        margin_right: float = 50,
        margin_bottom: float = 50,
        line_spacing: float = 1.2,
        font_name: str = "Helvetica",
        font_size: int = 12,
        orientation: str = "portrait",
        columns: int = 1,
        column_gap: float = 20,
        has_header: bool = False,
        has_footer: bool = False,
        header_height: float = 40,
        footer_height: float = 30,
        gutter_margin: float = 0,
        is_left_page: bool = True,
        page_numbering: bool = False,
        page_number_position: str = "bottom-right",
        page_number_format: str = "{page}",
        background_color: Optional[Tuple[int, int, int]] = None,
        bleed_area: float = 0,
        show_crop_marks: bool = False,
        crop_mark_distance: float = 5,
    ):
        """Initialize PageLayout.

        Args:
            margin_top: Top margin
            margin_left: Left margin
            margin_right: Right margin
            margin_bottom: Bottom margin
            line_spacing: Line spacing multiplier
            font_name: Default font
            font_size: Default font size
            orientation: "portrait" or "landscape"
            columns: Number of columns
            column_gap: Gap between columns
            has_header: Include header area
            has_footer: Include footer area
            header_height: Header height
            footer_height: Footer height
            gutter_margin: Binding gutter margin
            is_left_page: Left or right page (for duplex)
            page_numbering: Enable page numbers
            page_number_position: Position of page number
            page_number_format: Format string for page number
            background_color: Background color RGB
            bleed_area: Bleed area for printing
            show_crop_marks: Show crop marks
            crop_mark_distance: Distance from edge for crop marks
        """
        # Validate inputs
        if margin_top < 0 or margin_left < 0 or margin_right < 0 or margin_bottom < 0:
            raise ValueError("Margins must be non-negative")
        if font_size <= 0:
            raise ValueError("Font size must be positive")
        if columns < 1:
            raise ValueError("Columns must be at least 1")
        if column_gap < 0:
            raise ValueError("Column gap must be non-negative")
        if orientation not in ("portrait", "landscape"):
            raise ValueError("Orientation must be 'portrait' or 'landscape'")

        self.margin_top = margin_top
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_bottom = margin_bottom
        self.line_spacing = line_spacing
        self.font_name = font_name
        self.font_size = font_size
        self.orientation = orientation
        self.columns = columns
        self.column_gap = column_gap
        self.has_header = has_header
        self.has_footer = has_footer
        self.header_height = header_height
        self.footer_height = footer_height
        self.gutter_margin = gutter_margin
        self.is_left_page = is_left_page
        self.page_numbering = page_numbering
        self.page_number_position = page_number_position
        self.page_number_format = page_number_format
        self.background_color = background_color
        self.bleed_area = bleed_area
        self.show_crop_marks = show_crop_marks
        self.crop_mark_distance = crop_mark_distance

    def set_margins(
        self,
        top: Optional[float] = None,
        bottom: Optional[float] = None,
        left: Optional[float] = None,
        right: Optional[float] = None,
    ) -> Optional["PageLayout"]:
        """Set margins and return self for chaining."""
        if top is not None:
            self.margin_top = top
        if bottom is not None:
            self.margin_bottom = bottom
        if left is not None:
            self.margin_left = left
        if right is not None:
            self.margin_right = right
        return self

    def get_available_width(self) -> float:
        """Get available content width."""
        page_width = 842 if self.orientation == "landscape" else 595
        return page_width - self.margin_left - self.margin_right - self.gutter_margin

    def get_available_height(self) -> float:
        """Get available content height."""
        page_height = 595 if self.orientation == "landscape" else 842
        height = page_height - self.margin_top - self.margin_bottom

        if self.has_header:
            height -= self.header_height
        if self.has_footer:
            height -= self.footer_height

        return height

    def get_column_width(self) -> float:
        """Get width of a single column."""
        available = self.get_available_width()
        total_gaps = self.column_gap * (self.columns - 1)
        return (available - total_gaps) / self.columns

    def get_content_area(self) -> Dict[str, float]:
        """Get content area rectangle."""
        return {
            "x": self.margin_left + self.gutter_margin,
            "y": self.margin_top + (self.header_height if self.has_header else 0),
            "width": self.get_available_width(),
            "height": self.get_available_height(),
        }


class PageLayoutPreset:
    """Predefined page layout presets."""

    _presets: Dict[str, PageLayout] = {
        "DEFAULT": PageLayout(),
        "WIDE_MARGINS": PageLayout(
            margin_top=100,
            margin_bottom=100,
            margin_left=100,
            margin_right=100,
        ),
        "NARROW_MARGINS": PageLayout(
            margin_top=20,
            margin_bottom=20,
            margin_left=20,
            margin_right=20,
        ),
        "COLORING_BOOK": PageLayout(
            margin_top=50,
            margin_bottom=50,
            margin_left=60,
            margin_right=60,
            line_spacing=2.0,
            font_size=14,
        ),
        "LANDSCAPE": PageLayout(
            orientation="landscape",
            margin_top=50,
            margin_bottom=50,
            margin_left=60,
            margin_right=60,
        ),
        "TWO_COLUMN": PageLayout(
            columns=2,
            column_gap=20,
            margin_left=40,
            margin_right=40,
        ),
        "WITH_HEADER_FOOTER": PageLayout(
            has_header=True,
            has_footer=True,
            header_height=50,
            footer_height=40,
        ),
        "BOOK_DUPLEX": PageLayout(
            margin_top=60,
            margin_bottom=60,
            margin_left=50,
            margin_right=70,
            gutter_margin=30,
            is_left_page=True,
            page_numbering=True,
        ),
    }

    @classmethod
    def list_presets(cls) -> List[str]:
        """Get list of preset names."""
        return list(cls._presets.keys())

    @classmethod
    def register(cls, name: str, layout: PageLayout) -> None:
        """Register a custom preset."""
        cls._presets[name] = layout

    @classmethod
    def get(cls, name: str) -> PageLayout:
        """Get preset by name."""
        if name not in cls._presets:
            raise ValueError(f"Unknown preset: {name}. Available: {cls.list_presets()}")
        return cls._presets[name]


def get_preset(name: str) -> PageLayout:
    """Get a predefined layout preset.

    Args:
        name: Preset name

    Returns:
        PageLayout instance

    Raises:
        ValueError: If preset not found
    """
    return PageLayoutPreset.get(name)


def create_custom_layout(
    name: str,
    margin_top: float = 50,
    margin_left: float = 50,
    margin_right: float = 50,
    margin_bottom: float = 50,
    line_spacing: float = 1.2,
    font_name: str = "Helvetica",
    font_size: int = 12,
    orientation: str = "portrait",
    columns: int = 1,
    column_gap: float = 20,
    has_header: bool = False,
    has_footer: bool = False,
    header_height: float = 40,
    footer_height: float = 30,
    gutter_margin: float = 0,
    is_left_page: bool = True,
    page_numbering: bool = False,
    page_number_position: str = "bottom-right",
    background_color: Optional[Tuple[int, int, int]] = None,
    bleed_area: float = 0,
    show_crop_marks: bool = False,
) -> PageLayout:
    """Create a custom layout and optionally register it.

    Args:
        name: Layout name (for registration)
        margin_top: Top margin
        margin_left: Left margin
        margin_right: Right margin
        margin_bottom: Bottom margin
        line_spacing: Line spacing
        font_name: Font name
        font_size: Font size
        orientation: Page orientation
        columns: Number of columns
        column_gap: Gap between columns
        has_header: Include header
        has_footer: Include footer
        header_height: Header height
        footer_height: Footer height
        gutter_margin: Binding gutter
        is_left_page: Left page flag
        page_numbering: Enable page numbers
        page_number_position: Page number position
        background_color: Background color
        bleed_area: Bleed area
        show_crop_marks: Show crop marks

    Returns:
        PageLayout instance
    """
    layout = PageLayout(
        margin_top=margin_top,
        margin_left=margin_left,
        margin_right=margin_right,
        margin_bottom=margin_bottom,
        line_spacing=line_spacing,
        font_name=font_name,
        font_size=font_size,
        orientation=orientation,
        columns=columns,
        column_gap=column_gap,
        has_header=has_header,
        has_footer=has_footer,
        header_height=header_height,
        footer_height=footer_height,
        gutter_margin=gutter_margin,
        is_left_page=is_left_page,
        page_numbering=page_numbering,
        page_number_position=page_number_position,
        background_color=background_color,
        bleed_area=bleed_area,
        show_crop_marks=show_crop_marks,
    )

    # Register if name provided
    if name:
        PageLayoutPreset.register(name, layout)

    return layout
