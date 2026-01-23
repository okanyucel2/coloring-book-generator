"""Tests for AnimalRegistry and AnimalFactory."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from coloring_book.svg.registry import AnimalRegistry
from coloring_book.svg.factory import AnimalFactory
from coloring_book.svg.animals import CatDrawer, DogDrawer, BirdDrawer
from coloring_book.svg.base import AnimalDrawer


class TestAnimalRegistry:
    """Test AnimalRegistry functionality."""

    def setup_method(self):
        """Reset registry before each test."""
        AnimalRegistry.clear()

    def test_register_animal(self):
        """Test registering an animal."""
        AnimalRegistry.register("cat", CatDrawer)
        assert AnimalRegistry.is_registered("cat")
        assert AnimalRegistry.get("cat") == CatDrawer

    def test_register_duplicate_raises_error(self):
        """Test registering duplicate animal raises error."""
        AnimalRegistry.register("cat", CatDrawer)
        with pytest.raises(ValueError, match="already registered"):
            AnimalRegistry.register("cat", DogDrawer)

    def test_register_invalid_class_raises_error(self):
        """Test registering non-AnimalDrawer class raises error."""
        class NotAnimal:
            pass

        with pytest.raises(ValueError, match="must inherit from AnimalDrawer"):
            AnimalRegistry.register("invalid", NotAnimal)

    def test_get_unregistered_returns_none(self):
        """Test getting unregistered animal returns None."""
        assert AnimalRegistry.get("nonexistent") is None

    def test_list_animals(self):
        """Test listing all registered animals."""
        AnimalRegistry.register("cat", CatDrawer)
        AnimalRegistry.register("dog", DogDrawer)

        animals = AnimalRegistry.list_animals()
        assert len(animals) == 2
        assert "cat" in animals
        assert "dog" in animals
        assert animals["cat"] == CatDrawer
        assert animals["dog"] == DogDrawer

    def test_is_registered(self):
        """Test checking if animal is registered."""
        AnimalRegistry.register("cat", CatDrawer)
        assert AnimalRegistry.is_registered("cat") is True
        assert AnimalRegistry.is_registered("dog") is False

    def test_unregister_animal(self):
        """Test unregistering an animal."""
        AnimalRegistry.register("cat", CatDrawer)
        assert AnimalRegistry.unregister("cat") is True
        assert AnimalRegistry.is_registered("cat") is False

    def test_unregister_nonexistent_returns_false(self):
        """Test unregistering nonexistent animal returns False."""
        assert AnimalRegistry.unregister("nonexistent") is False

    def test_clear_all(self):
        """Test clearing all registered animals."""
        AnimalRegistry.register("cat", CatDrawer)
        AnimalRegistry.register("dog", DogDrawer)
        assert AnimalRegistry.count() == 2

        AnimalRegistry.clear()
        assert AnimalRegistry.count() == 0

    def test_count_animals(self):
        """Test counting registered animals."""
        assert AnimalRegistry.count() == 0
        AnimalRegistry.register("cat", CatDrawer)
        assert AnimalRegistry.count() == 1
        AnimalRegistry.register("dog", DogDrawer)
        assert AnimalRegistry.count() == 2


class TestAnimalFactory:
    """Test AnimalFactory functionality."""

    def setup_method(self):
        """Reset registry and register defaults before each test."""
        AnimalRegistry.clear()
        AnimalRegistry.register("cat", CatDrawer)
        AnimalRegistry.register("dog", DogDrawer)
        AnimalRegistry.register("bird", BirdDrawer)

    def test_create_animal(self):
        """Test creating an animal instance."""
        cat = AnimalFactory.create("cat")
        assert isinstance(cat, CatDrawer)
        assert cat.get_name() == "cat"
        assert cat.get_dimensions() == (200, 200)

    def test_create_animal_custom_dimensions(self):
        """Test creating animal with custom dimensions."""
        cat = AnimalFactory.create("cat", width=300, height=400)
        assert cat.get_dimensions() == (300, 400)

    def test_create_unregistered_raises_error(self):
        """Test creating unregistered animal raises error."""
        with pytest.raises(ValueError, match="not registered"):
            AnimalFactory.create("elephant")

    def test_create_unregistered_shows_available(self):
        """Test error message shows available animals."""
        with pytest.raises(ValueError, match="Available"):
            AnimalFactory.create("unknown")

    def test_create_all_default_animals(self):
        """Test creating all default animals."""
        animals = {
            "cat": AnimalFactory.create("cat"),
            "dog": AnimalFactory.create("dog"),
            "bird": AnimalFactory.create("bird"),
        }

        for name, animal in animals.items():
            assert animal.get_name() == name
            assert isinstance(animal, AnimalDrawer)

    def test_create_batch(self):
        """Test creating multiple animals from specifications."""
        specs = {
            "fluffy": {"type": "cat", "width": 250, "height": 250},
            "buddy": {"type": "dog", "width": 300, "height": 350},
            "tweety": {"type": "bird"},
        }

        animals = AnimalFactory.create_batch(specs)

        assert len(animals) == 3
        assert animals["fluffy"].get_name() == "cat"
        assert animals["fluffy"].get_dimensions() == (250, 250)
        assert animals["buddy"].get_name() == "dog"
        assert animals["buddy"].get_dimensions() == (300, 350)
        assert animals["tweety"].get_name() == "bird"
        assert animals["tweety"].get_dimensions() == (200, 200)

    def test_create_batch_invalid_type_raises_error(self):
        """Test batch creation with invalid type raises error."""
        specs = {
            "unknown": {"type": "elephant"},
        }

        with pytest.raises(ValueError, match="not registered"):
            AnimalFactory.create_batch(specs)

    def test_create_batch_missing_type_raises_error(self):
        """Test batch creation missing type raises error."""
        specs = {
            "invalid": {"width": 200},
        }

        with pytest.raises(ValueError, match="missing 'type'"):
            AnimalFactory.create_batch(specs)

    def test_create_batch_invalid_spec_raises_error(self):
        """Test batch creation with non-dict spec raises error."""
        specs = {
            "invalid": "not a dict",
        }

        with pytest.raises(ValueError, match="must be dict"):
            AnimalFactory.create_batch(specs)

    def test_get_available_animals(self):
        """Test getting available animals."""
        available = AnimalFactory.get_available_animals()
        assert len(available) == 3
        assert "cat" in available
        assert "dog" in available
        assert "bird" in available

    def test_is_available(self):
        """Test checking if animal is available."""
        assert AnimalFactory.is_available("cat") is True
        assert AnimalFactory.is_available("dog") is True
        assert AnimalFactory.is_available("elephant") is False

    def test_created_animals_are_independent(self):
        """Test created animals are independent instances."""
        cat1 = AnimalFactory.create("cat")
        cat2 = AnimalFactory.create("cat")

        assert cat1 is not cat2
        assert cat1.get_name() == cat2.get_name()

        # Modifying one shouldn't affect the other
        cat1.add_element("<circle/>")
        assert len(cat1.get_elements()) == 1
        assert len(cat2.get_elements()) == 0
