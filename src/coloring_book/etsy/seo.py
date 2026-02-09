"""Etsy SEO metadata generation for workbook listings."""

from __future__ import annotations

from ..workbook.models import WorkbookConfig
from ..workbook.themes import get_theme


class EtsySEOEngine:
    """Generate Etsy-optimized metadata for workbook listings."""

    def generate_title(self, config: WorkbookConfig) -> str:
        """Generate Etsy-optimized listing title.

        Pattern: "{Theme} {Activity} Workbook for {Audience} Ages {Range} | {Pages} Pages"
        Max: 140 characters (Etsy limit)
        """
        theme = get_theme(config.theme)
        display_name = theme.display_name

        # Build title parts
        parts = [
            f"{display_name} Tracing Workbook",
            config.subtitle or f"Ages {config.age_range[0]}-{config.age_range[1]}",
            f"{config.total_activity_pages + 1} Pages",
            "Printable PDF",
        ]

        title = " | ".join(parts)

        # Truncate to 140 chars (Etsy limit)
        if len(title) > 140:
            title = title[:137] + "..."

        return title

    def generate_description(self, config: WorkbookConfig) -> str:
        """Generate Etsy-optimized listing description.

        Structured with sections for SEO + readability.
        """
        theme = get_theme(config.theme)
        total_pages = config.total_activity_pages + 1  # +1 for cover
        age_min, age_max = config.age_range

        # Activity type descriptions
        activity_names = {
            "trace_and_color": "Trace & Color",
            "which_different": "Which One Is Different?",
            "count_circle": "Count and Circle",
            "match": "Match the Pairs",
            "word_to_image": "Word to Image Match",
            "find_circle": "Find and Circle",
        }

        # Build activity list
        activities = []
        for key, count in config.activity_mix.items():
            if count > 0:
                name = activity_names.get(key, key.replace("_", " ").title())
                activities.append(f"  - {count} {name} pages")

        items_sample = [n.replace("_", " ").title() for n in config.items[:8]]
        items_text = ", ".join(items_sample)
        if len(config.items) > 8:
            items_text += f", and {len(config.items) - 8} more"

        description = f"""{config.title}

A fun-filled activity workbook designed for children ages {age_min}-{age_max}!

WHAT'S INCLUDED:
- {total_pages} pages of engaging activities
- 1 colorful cover page
{chr(10).join(activities)}

FEATURED {theme.display_name.upper()}:
{items_text}

ACTIVITY TYPES:
This workbook includes 6 different activity types to keep children engaged:
1. Trace & Color - Practice tracing with dashed outlines
2. Which One Is Different? - Develop observation skills
3. Count and Circle - Practice counting and number recognition
4. Match the Pairs - Build matching and memory skills
5. Word to Image - Connect words with pictures
6. Find and Circle - Practice identification skills

HOW TO USE:
- Download the PDF file after purchase
- Print on standard {config.page_size.upper()} paper
- Use colored pencils, crayons, or markers
- Perfect for home learning, classroom activities, or travel entertainment

PRINT TIPS:
- Print at 100% scale for best results
- Use white matte paper (80gsm or higher) for best coloring experience
- Single-sided printing recommended

This is a DIGITAL DOWNLOAD - no physical item will be shipped.
You will receive a high-quality PDF file ready for printing.

Keywords: {theme.display_name.lower()} activity book, tracing workbook, coloring pages, printable activities, preschool worksheet, kids learning book"""

        return description

    def generate_tags(self, config: WorkbookConfig) -> list[str]:
        """Generate Etsy tags (max 13, each max 20 chars).

        Combines theme-specific tags with generic activity book tags.
        """
        theme = get_theme(config.theme)

        # Start with theme's pre-defined Etsy tags
        tags = list(theme.etsy_tags)

        # Add age-specific tags
        age_min, age_max = config.age_range
        age_tags = [
            f"ages {age_min}-{age_max}",
            f"ages {age_min} to {age_max}",
        ]

        # Add generic tags
        generic_tags = [
            "activity book",
            "printable pdf",
            "kids worksheet",
            "learning activity",
            "homeschool resource",
        ]

        # Combine, deduplicate, enforce limits
        all_tags = tags + age_tags + generic_tags
        seen = set()
        unique_tags = []
        for tag in all_tags:
            tag_lower = tag.lower().strip()
            if tag_lower not in seen and len(tag_lower) <= 20:
                seen.add(tag_lower)
                unique_tags.append(tag_lower)

        return unique_tags[:13]  # Etsy max

    def suggest_price(self, config: WorkbookConfig) -> float:
        """Suggest a price based on workbook content.

        Pricing tiers:
        - 5-20 pages: $2.99-$3.99
        - 20-30 pages: $3.99-$4.99
        - 30-50 pages: $4.99-$6.99
        - 50+ pages: $6.99-$9.99
        """
        total_pages = config.total_activity_pages + 1
        activity_variety = sum(1 for v in config.activity_mix.values() if v > 0)

        # Base price from page count
        if total_pages <= 20:
            base = 2.99
        elif total_pages <= 30:
            base = 3.99
        elif total_pages <= 50:
            base = 4.99
        else:
            base = 6.99

        # Bonus for activity variety (more types = more value)
        variety_bonus = max(0, (activity_variety - 2)) * 0.50

        price = base + variety_bonus

        # Cap at $9.99
        return min(round(price, 2), 9.99)
