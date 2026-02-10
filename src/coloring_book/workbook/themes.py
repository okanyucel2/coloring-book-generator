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
    "dinosaurs": ThemeConfig(
        slug="dinosaurs",
        display_name="Dinosaurs",
        category="animal",
        items=[
            "t_rex",
            "triceratops",
            "stegosaurus",
            "brontosaurus",
            "pterodactyl",
            "velociraptor",
            "ankylosaurus",
            "spinosaurus",
            "parasaurolophus",
            "diplodocus",
            "iguanodon",
            "pachycephalosaurus",
            "brachiosaurus",
            "allosaurus",
            "dimetrodon",
            "plesiosaurus",
            "mosasaurus",
            "archaeopteryx",
        ],
        age_groups=["preschool", "early_elementary"],
        etsy_tags=[
            "dinosaur coloring",
            "dino workbook",
            "tracing book kids",
            "dino activity book",
            "preschool dinosaur",
            "t rex coloring page",
            "jurassic coloring",
            "toddler dino book",
            "trace and color dino",
            "dino pages kids",
            "printable dinosaur",
            "coloring book boys",
            "kindergarten dino",
        ],
        default_subtitle_template="For Kids Ages {age_min}-{age_max}",
    ),
    "ocean": ThemeConfig(
        slug="ocean",
        display_name="Ocean Animals",
        category="animal",
        items=[
            "dolphin",
            "whale",
            "shark",
            "octopus",
            "seahorse",
            "jellyfish",
            "starfish",
            "crab",
            "lobster",
            "sea_turtle",
            "clownfish",
            "pufferfish",
            "manta_ray",
            "seal",
            "penguin",
            "orca",
            "narwhal",
            "squid",
        ],
        age_groups=["preschool", "early_elementary"],
        etsy_tags=[
            "ocean coloring",
            "sea animal coloring",
            "ocean workbook",
            "under the sea book",
            "marine life pages",
            "fish coloring book",
            "preschool ocean",
            "shark coloring page",
            "ocean tracing book",
            "sea creature color",
            "kids ocean activity",
            "toddler sea animals",
            "printable ocean",
        ],
        default_subtitle_template="For Kids Ages {age_min}-{age_max}",
    ),
    "space": ThemeConfig(
        slug="space",
        display_name="Space & Rockets",
        category="science",
        items=[
            "rocket",
            "astronaut",
            "planet",
            "star",
            "moon",
            "sun",
            "satellite",
            "ufo",
            "space_shuttle",
            "mars_rover",
            "telescope",
            "comet",
            "asteroid",
            "space_station",
            "lunar_module",
            "meteor",
            "galaxy",
            "constellation",
        ],
        age_groups=["early_elementary", "elementary"],
        etsy_tags=[
            "space coloring book",
            "rocket coloring",
            "astronaut coloring",
            "planet coloring page",
            "space workbook kids",
            "outer space tracing",
            "solar system color",
            "kids space activity",
            "space tracing book",
            "science coloring",
            "galaxy coloring page",
            "printable space book",
            "stem coloring kids",
        ],
        default_subtitle_template="For Kids Ages {age_min}-{age_max}",
    ),
    "food": ThemeConfig(
        slug="food",
        display_name="Yummy Food",
        category="food",
        items=[
            "pizza",
            "hamburger",
            "ice_cream",
            "cupcake",
            "donut",
            "apple",
            "banana",
            "watermelon",
            "cookie",
            "cake",
            "taco",
            "hotdog",
            "french_fries",
            "lollipop",
            "chocolate",
            "sandwich",
            "sushi",
            "pancake",
        ],
        age_groups=["preschool", "early_elementary"],
        etsy_tags=[
            "food coloring book",
            "yummy food coloring",
            "food tracing book",
            "pizza coloring page",
            "cute food activity",
            "preschool food book",
            "toddler food color",
            "kawaii food coloring",
            "fruit coloring page",
            "dessert coloring",
            "kids food workbook",
            "trace and color food",
            "printable food pages",
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
