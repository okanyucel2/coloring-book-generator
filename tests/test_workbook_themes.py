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

    def test_get_nonexistent_theme_raises(self):
        with pytest.raises(KeyError, match="Unknown theme"):
            get_theme("dinosaurs")

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


class TestRegisterTheme:
    def test_register_new_theme(self):
        new_theme = ThemeConfig(
            slug="dinosaurs",
            display_name="Dinosaurs",
            category="animal",
            items=["t_rex", "triceratops", "stegosaurus"],
            age_groups=["preschool"],
            etsy_tags=["dinosaur coloring book"],
        )
        register_theme(new_theme)
        assert "dinosaurs" in THEMES
        assert get_theme("dinosaurs").display_name == "Dinosaurs"

        # Cleanup
        del THEMES["dinosaurs"]

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
