"""Tests for Etsy SEO engine."""

import pytest

from coloring_book.etsy.seo import EtsySEOEngine
from coloring_book.workbook.models import WorkbookConfig


def _make_config(**overrides) -> WorkbookConfig:
    defaults = {
        "theme": "vehicles",
        "title": "Vehicles Tracing Workbook",
        "subtitle": "For Boys Ages 3-5",
        "age_range": (3, 5),
        "page_count": 30,
        "items": ["fire_truck", "police_car", "ambulance"],
        "activity_mix": {
            "trace_and_color": 18,
            "which_different": 2,
            "count_circle": 2,
            "match": 2,
            "word_to_image": 1,
            "find_circle": 2,
        },
        "page_size": "letter",
    }
    defaults.update(overrides)
    return WorkbookConfig(**defaults)


class TestGenerateTitle:
    def test_contains_theme(self):
        seo = EtsySEOEngine()
        title = seo.generate_title(_make_config())
        assert "Vehicles" in title

    def test_contains_page_count(self):
        seo = EtsySEOEngine()
        config = _make_config()
        title = seo.generate_title(config)
        assert "Pages" in title

    def test_max_length_140(self):
        seo = EtsySEOEngine()
        config = _make_config(
            title="A Very Long Title That Goes On And On And On",
            subtitle="With An Extremely Detailed Subtitle For Maximum SEO Impact And Keyword Coverage",
        )
        title = seo.generate_title(config)
        assert len(title) <= 140

    def test_contains_printable(self):
        seo = EtsySEOEngine()
        title = seo.generate_title(_make_config())
        assert "Printable" in title or "PDF" in title

    def test_animals_theme(self):
        seo = EtsySEOEngine()
        title = seo.generate_title(_make_config(theme="animals"))
        assert "Animals" in title


class TestGenerateDescription:
    def test_contains_title(self):
        seo = EtsySEOEngine()
        desc = seo.generate_description(_make_config())
        assert "Vehicles Tracing Workbook" in desc

    def test_contains_age_range(self):
        seo = EtsySEOEngine()
        desc = seo.generate_description(_make_config())
        assert "ages 3-5" in desc

    def test_contains_activity_types(self):
        seo = EtsySEOEngine()
        desc = seo.generate_description(_make_config())
        assert "Trace & Color" in desc
        assert "Which One Is Different" in desc
        assert "Count and Circle" in desc

    def test_contains_items(self):
        seo = EtsySEOEngine()
        desc = seo.generate_description(_make_config())
        assert "Fire Truck" in desc

    def test_contains_print_instructions(self):
        seo = EtsySEOEngine()
        desc = seo.generate_description(_make_config())
        assert "PRINT" in desc or "print" in desc

    def test_mentions_digital_download(self):
        seo = EtsySEOEngine()
        desc = seo.generate_description(_make_config())
        assert "DIGITAL DOWNLOAD" in desc

    def test_contains_page_count(self):
        seo = EtsySEOEngine()
        desc = seo.generate_description(_make_config())
        assert "28" in desc  # 27 activity pages + 1 cover


class TestGenerateTags:
    def test_returns_list(self):
        seo = EtsySEOEngine()
        tags = seo.generate_tags(_make_config())
        assert isinstance(tags, list)

    def test_max_13_tags(self):
        seo = EtsySEOEngine()
        tags = seo.generate_tags(_make_config())
        assert len(tags) <= 13

    def test_each_tag_max_20_chars(self):
        seo = EtsySEOEngine()
        tags = seo.generate_tags(_make_config())
        for tag in tags:
            assert len(tag) <= 20, f"Tag '{tag}' exceeds 20 chars"

    def test_tags_lowercase(self):
        seo = EtsySEOEngine()
        tags = seo.generate_tags(_make_config())
        for tag in tags:
            assert tag == tag.lower(), f"Tag '{tag}' is not lowercase"

    def test_no_duplicate_tags(self):
        seo = EtsySEOEngine()
        tags = seo.generate_tags(_make_config())
        assert len(tags) == len(set(tags)), "Tags contain duplicates"

    def test_contains_theme_keywords(self):
        seo = EtsySEOEngine()
        tags = seo.generate_tags(_make_config())
        tag_str = " ".join(tags)
        assert "vehicle" in tag_str or "coloring" in tag_str

    def test_animals_theme_tags(self):
        seo = EtsySEOEngine()
        tags = seo.generate_tags(_make_config(theme="animals"))
        tag_str = " ".join(tags)
        assert "animal" in tag_str


class TestSuggestPrice:
    def test_small_workbook(self):
        seo = EtsySEOEngine()
        config = _make_config(
            activity_mix={"trace_and_color": 10},
        )
        price = seo.suggest_price(config)
        assert 2.99 <= price <= 4.99

    def test_medium_workbook(self):
        seo = EtsySEOEngine()
        config = _make_config()  # 27 activity pages
        price = seo.suggest_price(config)
        assert 3.99 <= price <= 7.99

    def test_large_workbook(self):
        seo = EtsySEOEngine()
        config = _make_config(
            activity_mix={"trace_and_color": 50},
        )
        price = seo.suggest_price(config)
        assert price >= 4.99

    def test_variety_bonus(self):
        seo = EtsySEOEngine()
        # 6 activity types = more variety = higher price
        config_varied = _make_config(
            activity_mix={
                "trace_and_color": 5,
                "which_different": 1,
                "count_circle": 1,
                "match": 1,
                "word_to_image": 1,
                "find_circle": 1,
            },
        )
        config_simple = _make_config(
            activity_mix={"trace_and_color": 10},
        )
        price_varied = seo.suggest_price(config_varied)
        price_simple = seo.suggest_price(config_simple)
        assert price_varied >= price_simple

    def test_max_price_cap(self):
        seo = EtsySEOEngine()
        config = _make_config(
            activity_mix={
                "trace_and_color": 80,
                "which_different": 5,
                "count_circle": 5,
                "match": 5,
                "word_to_image": 5,
                "find_circle": 5,
            },
        )
        price = seo.suggest_price(config)
        assert price <= 9.99

    def test_returns_float(self):
        seo = EtsySEOEngine()
        price = seo.suggest_price(_make_config())
        assert isinstance(price, float)
