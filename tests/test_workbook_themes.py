"""Tests for workbook theme registry."""

import pytest

from coloring_book.workbook.themes import (
    THEMES,
    ThemeConfig,
    get_theme,
    list_themes,
    register_theme,
)


class TestThemeConfig:
    def test_vehicles_theme_exists(self):
        assert "vehicles" in THEMES

    def test_animals_theme_exists(self):
        assert "animals" in THEMES

    def test_dinosaurs_theme_exists(self):
        assert "dinosaurs" in THEMES
        theme = THEMES["dinosaurs"]
        assert theme.display_name == "Dinosaurs"
        assert theme.category == "animal"
        assert "t_rex" in theme.items
        assert "triceratops" in theme.items

    def test_ocean_theme_exists(self):
        assert "ocean" in THEMES
        theme = THEMES["ocean"]
        assert theme.display_name == "Ocean Animals"
        assert theme.category == "animal"
        assert "dolphin" in theme.items
        assert "shark" in theme.items

    def test_space_theme_exists(self):
        assert "space" in THEMES
        theme = THEMES["space"]
        assert theme.display_name == "Space & Rockets"
        assert theme.category == "science"
        assert "rocket" in theme.items
        assert "astronaut" in theme.items

    def test_food_theme_exists(self):
        assert "food" in THEMES
        theme = THEMES["food"]
        assert theme.display_name == "Yummy Food"
        assert theme.category == "food"
        assert "pizza" in theme.items
        assert "cupcake" in theme.items

    def test_all_themes_have_at_least_18_items(self):
        for slug, theme in THEMES.items():
            assert len(theme.items) >= 18, (
                f"Theme '{slug}' has only {len(theme.items)} items (need at least 18)"
            )

    def test_all_themes_etsy_tags_under_20_chars(self):
        for slug, theme in THEMES.items():
            for tag in theme.etsy_tags:
                assert len(tag) <= 20, (
                    f"Theme '{slug}' has tag '{tag}' with {len(tag)} chars (max 20)"
                )

    def test_vehicles_has_items(self):
        theme = THEMES["vehicles"]
        assert len(theme.items) >= 18
        assert "fire_truck" in theme.items
        assert "police_car" in theme.items

    def test_animals_has_items(self):
        theme = THEMES["animals"]
        assert len(theme.items) >= 18
        assert "cat" in theme.items
        assert "dog" in theme.items

    def test_item_count_property(self):
        theme = THEMES["vehicles"]
        assert theme.item_count == len(theme.items)

    def test_vehicles_category(self):
        assert THEMES["vehicles"].category == "vehicle"

    def test_animals_category(self):
        assert THEMES["animals"].category == "animal"

    def test_etsy_tags_max_13(self):
        for slug, theme in THEMES.items():
            assert len(theme.etsy_tags) <= 13, (
                f"Theme '{slug}' has {len(theme.etsy_tags)} tags (max 13)"
            )

    def test_etsy_tags_not_empty(self):
        for slug, theme in THEMES.items():
            assert len(theme.etsy_tags) > 0, f"Theme '{slug}' has no etsy tags"

    def test_default_subtitle(self):
        theme = THEMES["vehicles"]
        subtitle = theme.get_default_subtitle(3, 5)
        assert "3" in subtitle
        assert "5" in subtitle

    def test_default_subtitle_custom_ages(self):
        theme = THEMES["animals"]
        subtitle = theme.get_default_subtitle(6, 8)
        assert "6" in subtitle
        assert "8" in subtitle

    def test_age_groups_not_empty(self):
        for slug, theme in THEMES.items():
            assert len(theme.age_groups) > 0, f"Theme '{slug}' has no age groups"

    def test_no_duplicate_items_within_theme(self):
        for slug, theme in THEMES.items():
            assert len(theme.items) == len(set(theme.items)), (
                f"Theme '{slug}' has duplicate items"
            )


class TestGetTheme:
    def test_get_existing_theme(self):
        theme = get_theme("vehicles")
        assert theme.slug == "vehicles"
        assert theme.display_name == "Vehicles"

    def test_get_dinosaurs_theme(self):
        theme = get_theme("dinosaurs")
        assert theme.slug == "dinosaurs"
        assert theme.display_name == "Dinosaurs"

    def test_get_ocean_theme(self):
        theme = get_theme("ocean")
        assert theme.slug == "ocean"
        assert theme.display_name == "Ocean Animals"

    def test_get_space_theme(self):
        theme = get_theme("space")
        assert theme.slug == "space"
        assert theme.display_name == "Space & Rockets"

    def test_get_food_theme(self):
        theme = get_theme("food")
        assert theme.slug == "food"
        assert theme.display_name == "Yummy Food"

    def test_get_nonexistent_theme_raises(self):
        with pytest.raises(KeyError, match="Unknown theme"):
            get_theme("mythical_creatures")

    def test_error_message_lists_available(self):
        with pytest.raises(KeyError, match="vehicles"):
            get_theme("nonexistent")


class TestListThemes:
    def test_returns_list(self):
        themes = list_themes()
        assert isinstance(themes, list)

    def test_returns_all_themes(self):
        themes = list_themes()
        assert len(themes) == len(THEMES)

    def test_returns_theme_configs(self):
        themes = list_themes()
        for theme in themes:
            assert isinstance(theme, ThemeConfig)

    def test_list_includes_all_six_themes(self):
        themes = list_themes()
        slugs = {t.slug for t in themes}
        expected = {"vehicles", "animals", "dinosaurs", "ocean", "space", "food"}
        assert expected == slugs


class TestRegisterTheme:
    def test_register_new_theme(self):
        new_theme = ThemeConfig(
            slug="fantasy",
            display_name="Fantasy",
            category="fantasy",
            items=["dragon", "unicorn", "wizard"],
            age_groups=["preschool"],
            etsy_tags=["fantasy coloring"],
        )
        register_theme(new_theme)
        assert "fantasy" in THEMES
        assert get_theme("fantasy").display_name == "Fantasy"

        # Cleanup
        del THEMES["fantasy"]

    def test_register_overwrites_existing(self):
        original = THEMES["vehicles"]
        modified = ThemeConfig(
            slug="vehicles",
            display_name="Vehicles Modified",
            category="vehicle",
            items=["car"],
        )
        register_theme(modified)
        assert THEMES["vehicles"].item_count == 1

        # Restore original
        THEMES["vehicles"] = original
