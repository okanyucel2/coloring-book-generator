"""Tests for workbook data models."""

import pytest

from coloring_book.workbook.models import (
    DEFAULT_ACTIVITY_MIX,
    Workbook,
    WorkbookConfig,
    WorkbookItem,
)


class TestWorkbookItem:
    def test_creation_minimal(self):
        item = WorkbookItem(name="fire_truck", category="vehicle")
        assert item.name == "fire_truck"
        assert item.category == "vehicle"
        assert item.colored_image is None
        assert item.outline_image is None
        assert item.dashed_image is None

    def test_display_name(self):
        item = WorkbookItem(name="fire_truck", category="vehicle")
        assert item.display_name == "Fire Truck"

    def test_display_name_single_word(self):
        item = WorkbookItem(name="cat", category="animal")
        assert item.display_name == "Cat"

    def test_has_all_assets_false_when_empty(self):
        item = WorkbookItem(name="cat", category="animal")
        assert item.has_all_assets is False

    def test_has_all_assets_false_when_partial(self):
        item = WorkbookItem(
            name="cat",
            category="animal",
            colored_image=b"colored",
            outline_image=b"outline",
        )
        assert item.has_all_assets is False

    def test_has_all_assets_true(self):
        item = WorkbookItem(
            name="cat",
            category="animal",
            colored_image=b"colored",
            outline_image=b"outline",
            dashed_image=b"dashed",
        )
        assert item.has_all_assets is True


class TestWorkbookConfig:
    def _make_config(self, **overrides):
        defaults = {
            "theme": "vehicles",
            "title": "Test Workbook",
            "subtitle": "Ages 3-5",
            "age_range": (3, 5),
            "page_count": 30,
            "items": ["fire_truck", "police_car", "ambulance"],
            "page_size": "letter",
        }
        defaults.update(overrides)
        return WorkbookConfig(**defaults)

    def test_creation_with_defaults(self):
        config = self._make_config()
        assert config.theme == "vehicles"
        assert config.title == "Test Workbook"
        assert config.page_size == "letter"
        assert config.age_range == (3, 5)

    def test_default_activity_mix(self):
        config = self._make_config()
        assert config.activity_mix == DEFAULT_ACTIVITY_MIX

    def test_total_activity_pages(self):
        config = self._make_config(
            activity_mix={"trace_and_color": 10, "which_different": 2}
        )
        assert config.total_activity_pages == 12

    def test_validate_valid_config(self):
        config = self._make_config()
        errors = config.validate()
        assert errors == []

    def test_validate_missing_theme(self):
        config = self._make_config(theme="")
        errors = config.validate()
        assert "Theme is required" in errors

    def test_validate_missing_title(self):
        config = self._make_config(title="")
        errors = config.validate()
        assert "Title is required" in errors

    def test_validate_invalid_page_size(self):
        config = self._make_config(page_size="b5")
        errors = config.validate()
        assert any("Invalid page size" in e for e in errors)

    def test_validate_negative_age(self):
        config = self._make_config(age_range=(-1, 5))
        errors = config.validate()
        assert any("non-negative" in e for e in errors)

    def test_validate_age_range_inverted(self):
        config = self._make_config(age_range=(8, 3))
        errors = config.validate()
        assert any("min must be <= max" in e for e in errors)

    def test_validate_page_count_too_low(self):
        config = self._make_config(page_count=2)
        errors = config.validate()
        assert any("at least 5" in e for e in errors)

    def test_validate_page_count_too_high(self):
        config = self._make_config(page_count=200)
        errors = config.validate()
        assert any("not exceed 100" in e for e in errors)

    def test_validate_empty_items(self):
        config = self._make_config(items=[])
        errors = config.validate()
        assert any("At least one item" in e for e in errors)

    def test_validate_unknown_activity(self):
        config = self._make_config(activity_mix={"unknown_type": 5})
        errors = config.validate()
        assert any("Unknown activity type" in e for e in errors)

    def test_validate_negative_activity_count(self):
        config = self._make_config(activity_mix={"trace_and_color": -1})
        errors = config.validate()
        assert any("non-negative" in e for e in errors)

    def test_validate_multiple_errors(self):
        config = self._make_config(theme="", title="", items=[])
        errors = config.validate()
        assert len(errors) >= 3


class TestWorkbook:
    def _make_item(self, name="cat", complete=False):
        kwargs = {"name": name, "category": "animal"}
        if complete:
            kwargs.update(
                colored_image=b"c",
                outline_image=b"o",
                dashed_image=b"d",
            )
        return WorkbookItem(**kwargs)

    def _make_config(self):
        return WorkbookConfig(
            theme="animals",
            title="Test",
            items=["cat", "dog"],
        )

    def test_creation(self):
        wb = Workbook(config=self._make_config())
        assert wb.item_count == 0
        assert wb.is_ready is False

    def test_item_count(self):
        wb = Workbook(
            config=self._make_config(),
            items=[self._make_item("cat"), self._make_item("dog")],
        )
        assert wb.item_count == 2

    def test_ready_items_filters_incomplete(self):
        wb = Workbook(
            config=self._make_config(),
            items=[
                self._make_item("cat", complete=True),
                self._make_item("dog", complete=False),
            ],
        )
        assert len(wb.ready_items) == 1
        assert wb.ready_items[0].name == "cat"

    def test_is_ready_when_all_complete(self):
        wb = Workbook(
            config=self._make_config(),
            items=[
                self._make_item("cat", complete=True),
                self._make_item("dog", complete=True),
            ],
        )
        assert wb.is_ready is True

    def test_is_ready_false_when_partial(self):
        wb = Workbook(
            config=self._make_config(),
            items=[
                self._make_item("cat", complete=True),
                self._make_item("dog", complete=False),
            ],
        )
        assert wb.is_ready is False

    def test_is_ready_false_when_empty(self):
        wb = Workbook(config=self._make_config())
        assert wb.is_ready is False
