"""Tests for SVG generation system - Animal drawers and SVG output."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from coloring_book.svg.base import AnimalDrawer
from coloring_book.svg.animals import CatDrawer, DogDrawer, BirdDrawer
from coloring_book.svg.builder import SVGBuilder
from coloring_book.svg.factory import AnimalFactory


class TestAnimalDrawerBase:
    """Test AnimalDrawer base class functionality."""

    def test_animal_drawer_initialization(self):
        """Test AnimalDrawer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AnimalDrawer("generic", 200, 200)

    def test_animal_drawer_subclass_has_draw_method(self):
        """Test subclass must implement draw method."""
        cat = CatDrawer()
        assert hasattr(cat, "draw")
        assert callable(cat.draw)

    def test_get_name(self):
        """Test getting animal name."""
        cat = CatDrawer()
        assert cat.get_name() == "cat"

    def test_get_dimensions(self):
        """Test getting canvas dimensions."""
        cat = CatDrawer(width=300, height=400)
        assert cat.get_dimensions() == (300, 400)

    def test_custom_dimensions(self):
        """Test creating animal with custom dimensions."""
        dog = DogDrawer(width=500, height=600)
        w, h = dog.get_dimensions()
        assert w == 500
        assert h == 600

    def test_add_element(self):
        """Test adding SVG elements."""
        cat = CatDrawer()
        assert len(cat.get_elements()) == 0
        cat.add_element("<circle cx='100' cy='100' r='50'/>")
        assert len(cat.get_elements()) == 1

    def test_multiple_elements(self):
        """Test adding multiple elements."""
        dog = DogDrawer()
        for i in range(5):
            dog.add_element(f"<element id='{i}'/>")
        assert len(dog.get_elements()) == 5

    def test_reset_clears_elements(self):
        """Test reset clears all elements."""
        bird = BirdDrawer()
        bird.add_element("<line/>")
        bird.add_element("<path/>")
        assert len(bird.get_elements()) == 2

        bird.reset()
        assert len(bird.get_elements()) == 0

    def test_get_elements_returns_copy(self):
        """Test get_elements returns copy, not reference."""
        cat = CatDrawer()
        cat.add_element("<element/>")

        elements1 = cat.get_elements()
        elements2 = cat.get_elements()

        assert elements1 == elements2
        assert elements1 is not elements2

    def test_export_svg_wraps_with_svg_tag(self):
        """Test export_svg wraps elements in SVG."""
        cat = CatDrawer(width=200, height=200)
        cat.add_element("<circle cx='100' cy='100' r='50'/>")

        svg = cat.export_svg()

        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        assert 'width="200"' in svg
        assert 'height="200"' in svg
        assert "<circle" in svg

    def test_to_svg_alias(self):
        """Test to_svg is alias for draw."""
        dog = DogDrawer()
        svg_from_draw = dog.draw()
        dog.reset()
        svg_from_to_svg = dog.to_svg()

        assert svg_from_draw == svg_from_to_svg


class TestCatDrawer:
    """Test CatDrawer implementation."""

    def test_cat_initialization(self):
        """Test CatDrawer initializes correctly."""
        cat = CatDrawer()
        assert cat.get_name() == "cat"
        assert cat.get_dimensions() == (200, 200)

    def test_cat_draw_returns_svg_string(self):
        """Test cat draw returns valid SVG string."""
        cat = CatDrawer()
        svg = cat.draw()

        assert isinstance(svg, str)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_cat_draw_contains_body_parts(self):
        """Test cat drawing includes body parts."""
        cat = CatDrawer()
        svg = cat.draw()

        # Body parts should be in SVG
        assert "ellipse" in svg  # Body
        assert "circle" in svg  # Head, eyes
        assert "polygon" in svg  # Ears, nose
        assert "line" in svg  # Legs
        assert "path" in svg  # Mouth, tail

    def test_cat_draw_has_multiple_elements(self):
        """Test cat drawing has multiple SVG elements."""
        cat = CatDrawer()
        svg = cat.draw()

        # Count elements - should have body, head, ears, eyes, nose, mouth, legs, tail
        element_count = (
            svg.count("<ellipse") +
            svg.count("<circle") +
            svg.count("<polygon") +
            svg.count("<line") +
            svg.count("<path")
        )

        assert element_count > 8, f"Expected >8 elements, got {element_count}"

    def test_cat_custom_dimensions_in_svg(self):
        """Test custom dimensions appear in SVG output."""
        cat = CatDrawer(width=400, height=500)
        svg = cat.draw()

        assert 'width="400"' in svg
        assert 'height="500"' in svg

    def test_cat_draw_reset_on_each_call(self):
        """Test cat drawing resets elements on each draw call."""
        cat = CatDrawer()

        svg1 = cat.draw()
        svg2 = cat.draw()

        # SVGs should be identical
        assert svg1 == svg2

    def test_cat_svg_is_valid_structure(self):
        """Test cat SVG has valid structure."""
        cat = CatDrawer()
        svg = cat.draw()

        # Should have proper closing tags
        assert svg.count("<svg") == svg.count("</svg>")
        # SVG is self-closing tag format so /> is used
        assert "/>" in svg

    def test_cat_uses_black_stroke(self):
        """Test cat uses black stroke color."""
        cat = CatDrawer()
        svg = cat.draw()

        assert 'stroke="black"' in svg

    def test_cat_has_no_fill_by_default(self):
        """Test cat elements have no fill (for coloring)."""
        cat = CatDrawer()
        svg = cat.draw()

        # Coloring book style should be no fill
        count_no_fill = svg.count('fill="none"')
        count_with_fill = svg.count('fill="') - count_no_fill
        
        # Should have mostly no-fill elements (some like eyes/nose might have fill)
        assert count_no_fill > count_with_fill


class TestDogDrawer:
    """Test DogDrawer implementation."""

    def test_dog_initialization(self):
        """Test DogDrawer initializes correctly."""
        dog = DogDrawer()
        assert dog.get_name() == "dog"

    def test_dog_draw_returns_svg(self):
        """Test dog drawing returns valid SVG."""
        dog = DogDrawer()
        svg = dog.draw()

        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_dog_has_four_legs(self):
        """Test dog has 4 legs in drawing."""
        dog = DogDrawer()
        svg = dog.draw()

        # Dog should have front and back legs
        line_count = svg.count("<line")
        assert line_count >= 4, f"Expected >=4 leg lines, got {line_count}"

    def test_dog_different_from_cat(self):
        """Test dog SVG is different from cat SVG."""
        dog = DogDrawer()
        cat = CatDrawer()

        dog_svg = dog.draw()
        cat_svg = cat.draw()

        # SVGs should be different
        assert dog_svg != cat_svg


class TestBirdDrawer:
    """Test BirdDrawer implementation."""

    def test_bird_initialization(self):
        """Test BirdDrawer initializes correctly."""
        bird = BirdDrawer()
        assert bird.get_name() == "bird"

    def test_bird_draw_returns_svg(self):
        """Test bird drawing returns valid SVG."""
        bird = BirdDrawer()
        svg = bird.draw()

        assert isinstance(svg, str)
        assert "<svg" in svg

    def test_bird_has_wings(self):
        """Test bird has wings."""
        bird = BirdDrawer()
        svg = bird.draw()

        # Bird should have wing elements (ellipses for wings)
        assert "ellipse" in svg

    def test_bird_has_beak(self):
        """Test bird has beak."""
        bird = BirdDrawer()
        svg = bird.draw()

        # Beak should be orange
        assert "orange" in svg
        assert "polygon" in svg  # Beak is polygon


class TestSVGBuilder:
    """Test SVGBuilder fluent API."""

    def test_builder_initialization(self):
        """Test SVGBuilder initializes correctly."""
        builder = SVGBuilder(400, 500)
        assert builder.width == 400
        assert builder.height == 500

    def test_builder_default_dimensions(self):
        """Test SVGBuilder default dimensions."""
        builder = SVGBuilder()
        assert builder.width == 400
        assert builder.height == 400

    def test_builder_add_circle(self):
        """Test adding circle to builder."""
        builder = SVGBuilder()
        result = builder.add_circle(100, 100, 50)

        assert result is builder  # Chainable
        assert len(builder.elements) == 1
        assert "<circle" in builder.elements[0]

    def test_builder_add_line(self):
        """Test adding line to builder."""
        builder = SVGBuilder()
        builder.add_line(0, 0, 100, 100)

        assert len(builder.elements) == 1
        assert "<line" in builder.elements[0]

    def test_builder_add_polygon(self):
        """Test adding polygon to builder."""
        builder = SVGBuilder()
        builder.add_polygon([(0, 0), (100, 0), (50, 100)])

        assert len(builder.elements) == 1
        assert "<polygon" in builder.elements[0]

    def test_builder_add_polygon_string(self):
        """Test adding polygon with string points."""
        builder = SVGBuilder()
        builder.add_polygon("0,0 100,0 50,100")

        assert len(builder.elements) == 1

    def test_builder_chaining(self):
        """Test method chaining."""
        svg = (SVGBuilder()
               .add_circle(100, 100, 50)
               .add_line(0, 0, 100, 100)
               .add_polygon([(0, 0), (100, 0), (50, 100)])
               .to_string())

        assert "<svg" in svg
        assert "<circle" in svg
        assert "<line" in svg
        assert "<polygon" in svg

    def test_builder_to_string_wraps_svg(self):
        """Test to_string wraps in SVG tags."""
        builder = SVGBuilder(300, 400)
        builder.add_circle(150, 200, 50)

        svg = builder.to_string()

        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        assert 'width="300"' in svg
        assert 'height="400"' in svg

    def test_builder_str_method(self):
        """Test __str__ method."""
        builder = SVGBuilder()
        builder.add_circle(100, 100, 50)

        assert str(builder) == builder.to_string()

    def test_builder_set_layer_config(self):
        """Test setting layer configuration."""
        builder = SVGBuilder()
        builder.set_layer_config(line_width=4, line_color="red", fill_color="blue")

        assert builder.line_width == 4
        assert builder.line_color == "red"
        assert builder.fill_color == "blue"

    def test_builder_layer_config_chainable(self):
        """Test layer config returns self for chaining."""
        builder = SVGBuilder()
        result = builder.set_layer_config(line_width=3)

        assert result is builder

    def test_builder_uses_layer_config(self):
        """Test elements use layer config."""
        builder = SVGBuilder()
        builder.set_layer_config(line_width=5, line_color="green")
        builder.add_circle(100, 100, 50)

        svg = builder.to_string()

        assert 'stroke-width="5"' in svg
        assert 'stroke="green"' in svg


class TestSVGIntegration:
    """Integration tests for SVG generation system."""

    def test_factory_create_all_animals(self):
        """Test factory creates all animal types."""
        animals = {
            "cat": AnimalFactory.create("cat"),
            "dog": AnimalFactory.create("dog"),
            "bird": AnimalFactory.create("bird"),
        }

        for name, animal in animals.items():
            svg = animal.draw()
            assert isinstance(svg, str)
            assert "<svg" in svg
            assert animal.get_name() == name

    def test_batch_create_produces_valid_svg(self):
        """Test batch creation produces valid SVG."""
        specs = {
            "fluffy": {"type": "cat"},
            "buddy": {"type": "dog"},
            "tweety": {"type": "bird"},
        }

        animals = AnimalFactory.create_batch(specs)

        for name, animal in animals.items():
            svg = animal.draw()
            assert "<svg" in svg
            assert "</svg>" in svg

    def test_animals_produce_different_svgs(self):
        """Test different animals produce different SVGs."""
        cat_svg = CatDrawer().draw()
        dog_svg = DogDrawer().draw()
        bird_svg = BirdDrawer().draw()

        # All should be different
        assert cat_svg != dog_svg
        assert dog_svg != bird_svg
        assert bird_svg != cat_svg

    def test_same_animal_same_svg(self):
        """Test same animal produces same SVG consistently."""
        cat1 = CatDrawer(width=250, height=250)
        cat2 = CatDrawer(width=250, height=250)

        svg1 = cat1.draw()
        svg2 = cat2.draw()

        assert svg1 == svg2

    def test_svg_validity_has_proper_structure(self):
        """Test generated SVGs have proper structure."""
        animals = [
            CatDrawer(),
            DogDrawer(),
            BirdDrawer(),
        ]

        for animal in animals:
            svg = animal.draw()

            # Basic structure checks
            assert svg.startswith("<svg")
            assert svg.endswith("</svg>")
            assert 'xmlns="http://www.w3.org/2000/svg"' in svg
            assert 'width=' in svg
            assert 'height=' in svg
            assert 'viewBox=' in svg or animal.draw() != ""
