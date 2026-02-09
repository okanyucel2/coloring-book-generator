"""Data models for workbook generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..metadata.schema import PackageMetadata


@dataclass
class WorkbookItem:
    """A single item (vehicle, animal, etc.) with its image assets."""

    name: str  # e.g. "Fire Truck", "Ambulance"
    category: str  # e.g. "vehicle", "animal"
    colored_image: Optional[bytes] = None  # PNG - colored reference
    outline_image: Optional[bytes] = None  # PNG - line art for coloring
    dashed_image: Optional[bytes] = None  # PNG - dashed tracing version

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return self.name.replace("_", " ").title()

    @property
    def has_all_assets(self) -> bool:
        """Check if all image assets are generated."""
        return all([self.colored_image, self.outline_image, self.dashed_image])


DEFAULT_ACTIVITY_MIX = {
    "trace_and_color": 18,
    "which_different": 2,
    "count_circle": 2,
    "match": 2,
    "word_to_image": 1,
    "find_circle": 2,
}


@dataclass
class WorkbookConfig:
    """Configuration for a workbook to be generated."""

    theme: str  # "vehicles", "animals"
    title: str  # "Vehicles Tracing Workbook"
    subtitle: str = ""  # "For Boys Ages 3-5"
    age_range: tuple[int, int] = (3, 5)
    page_count: int = 30
    items: list[str] = field(default_factory=list)  # ["fire_truck", "ambulance", ...]
    activity_mix: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_ACTIVITY_MIX))
    page_size: str = "letter"  # "letter" or "a4"

    @property
    def total_activity_pages(self) -> int:
        """Total pages from activity mix (excludes cover)."""
        return sum(self.activity_mix.values())

    def validate(self) -> list[str]:
        """Validate config and return list of errors (empty = valid)."""
        errors: list[str] = []

        if not self.theme:
            errors.append("Theme is required")

        if not self.title:
            errors.append("Title is required")

        if self.page_size not in ("letter", "a4"):
            errors.append(f"Invalid page size: {self.page_size}. Must be 'letter' or 'a4'")

        age_min, age_max = self.age_range
        if age_min < 0 or age_max < 0:
            errors.append("Age range values must be non-negative")
        if age_min > age_max:
            errors.append("Age range min must be <= max")

        if self.page_count < 5:
            errors.append("Page count must be at least 5")
        if self.page_count > 100:
            errors.append("Page count must not exceed 100")

        if not self.items:
            errors.append("At least one item is required")

        valid_activities = set(DEFAULT_ACTIVITY_MIX.keys())
        for activity in self.activity_mix:
            if activity not in valid_activities:
                errors.append(f"Unknown activity type: {activity}")

        for activity, count in self.activity_mix.items():
            if count < 0:
                errors.append(f"Activity count for '{activity}' must be non-negative")

        return errors


@dataclass
class Workbook:
    """A fully assembled workbook ready for PDF compilation."""

    config: WorkbookConfig
    items: list[WorkbookItem] = field(default_factory=list)
    metadata: Optional[PackageMetadata] = None

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def ready_items(self) -> list[WorkbookItem]:
        """Items with all assets generated."""
        return [item for item in self.items if item.has_all_assets]

    @property
    def is_ready(self) -> bool:
        """Whether all items have their assets generated."""
        return len(self.items) > 0 and all(item.has_all_assets for item in self.items)
