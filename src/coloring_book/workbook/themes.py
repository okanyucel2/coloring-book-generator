"""Theme registry for workbook generation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ThemeConfig:
    """Configuration for a workbook theme."""

    slug: str
    display_name: str
    items: list[str]
    age_groups: list[str] = field(default_factory=list)
    etsy_tags: list[str] = field(default_factory=list)
    default_subtitle_template: str = "Ages {age_min}-{age_max}"
    category: str = ""  # "vehicle", "animal"

    @property
    def item_count(self) -> int:
        return len(self.items)

    def get_default_subtitle(self, age_min: int = 3, age_max: int = 5) -> str:
        return self.default_subtitle_template.format(age_min=age_min, age_max=age_max)


THEMES: dict[str, ThemeConfig] = {
    "vehicles": ThemeConfig(
        slug="vehicles",
        display_name="Vehicles",
        category="vehicle",
        items=[
            "traffic_light",
            "police_car",
            "ambulance",
            "school_bus",
            "crane",
            "dump_truck",
            "excavator",
            "cement_mixer",
            "fire_truck",
            "garbage_truck",
            "helicopter",
            "airplane",
            "tractor",
            "train",
            "tow_truck",
            "bulldozer",
            "taxi",
            "bicycle",
        ],
        age_groups=["preschool", "early_elementary"],
        etsy_tags=[
            "vehicle coloring",
            "tracing workbook",
            "truck coloring book",
            "preschool worksheet",
            "cars coloring pages",
            "boys activity book",
            "toddler learning",
            "trace and color",
            "construction vehicle",
            "emergency vehicles",
            "printable workbook",
            "coloring pages kids",
            "kindergarten work",
        ],
        default_subtitle_template="For Boys Ages {age_min}-{age_max}",
    ),
    "animals": ThemeConfig(
        slug="animals",
        display_name="Animals",
        category="animal",
        items=[
            "cat",
            "dog",
            "bird",
            "elephant",
            "lion",
            "giraffe",
            "monkey",
            "rabbit",
            "bear",
            "fish",
            "butterfly",
            "turtle",
            "frog",
            "owl",
            "horse",
            "dolphin",
            "penguin",
            "panda",
        ],
        age_groups=["preschool", "early_elementary"],
        etsy_tags=[
            "animal coloring",
            "animal tracing",
            "preschool worksheet",
            "zoo animals coloring",
            "cute animal coloring",
            "kids activity book",
            "animal learning",
            "toddler coloring",
            "trace and color",
            "kindergarten work",
            "wildlife coloring",
            "farm animal coloring",
            "printable workbook",
        ],
        default_subtitle_template="For Kids Ages {age_min}-{age_max}",
    ),
}


def get_theme(slug: str) -> ThemeConfig:
    """Get theme by slug.

    Raises:
        KeyError: If theme not found
    """
    if slug not in THEMES:
        available = ", ".join(THEMES.keys())
        raise KeyError(f"Unknown theme '{slug}'. Available: {available}")
    return THEMES[slug]


def list_themes() -> list[ThemeConfig]:
    """Get all available themes."""
    return list(THEMES.values())


def register_theme(config: ThemeConfig) -> None:
    """Register a new theme."""
    THEMES[config.slug] = config
