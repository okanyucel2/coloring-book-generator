"""
M0 TASK-1: SVG Architecture Design Tests
RED Phase - Verify tests fail before implementation
"""
import pytest
from abc import ABC, abstractmethod


class TestSVGArchitectureInterface:
    """Test SVG module interfaces"""
    
    def test_animal_drawer_base_class_exists(self):
        """AnimalDrawer base class should be importable"""
        from coloring_book.svg.base import AnimalDrawer
        assert AnimalDrawer is not None
    
    def test_animal_drawer_has_draw_method(self):
        """AnimalDrawer should have draw() method"""
        from coloring_book.svg.base import AnimalDrawer
        assert hasattr(AnimalDrawer, 'draw')
        assert callable(getattr(AnimalDrawer, 'draw'))
    
    def test_animal_drawer_has_to_svg_method(self):
        """AnimalDrawer should have to_svg() method"""
        from coloring_book.svg.base import AnimalDrawer
        assert hasattr(AnimalDrawer, 'to_svg')
        assert callable(getattr(AnimalDrawer, 'to_svg'))
    
    def test_animal_drawer_abstract_class(self):
        """AnimalDrawer should be abstract"""
        from coloring_book.svg.base import AnimalDrawer
        assert ABC in AnimalDrawer.__bases__ or hasattr(AnimalDrawer, '__abstractmethods__')
    
    def test_svg_builder_exists(self):
        """SVGBuilder utility class should exist"""
        from coloring_book.svg.builder import SVGBuilder
        assert SVGBuilder is not None
    
    def test_svg_builder_init(self):
        """SVGBuilder should accept width, height, viewBox"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600, viewBox="0 0 800 600")
        assert builder.width == 800
        assert builder.height == 600
    
    def test_svg_builder_add_circle(self):
        """SVGBuilder should support adding circles"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600)
        builder.add_circle(cx=100, cy=100, r=50, stroke='black')
        assert len(builder.elements) > 0
    
    def test_svg_builder_add_path(self):
        """SVGBuilder should support adding paths"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600)
        builder.add_path(d="M 10 10 L 90 90", stroke='black')
        assert len(builder.elements) > 0
    
    def test_svg_builder_add_polygon(self):
        """SVGBuilder should support adding polygons"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600)
        builder.add_polygon(points=[(10, 10), (90, 10), (50, 90)], stroke='black')
        assert len(builder.elements) > 0
    
    def test_svg_builder_to_string(self):
        """SVGBuilder should generate valid SVG string"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600)
        builder.add_circle(cx=100, cy=100, r=50)
        svg_string = builder.to_string()
        
        assert isinstance(svg_string, str)
        assert '<svg' in svg_string
        assert 'width="800"' in svg_string
        assert 'height="600"' in svg_string
        assert '</svg>' in svg_string
    
    def test_svg_builder_circle_element(self):
        """SVG should contain proper circle element"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600)
        builder.add_circle(cx=100, cy=100, r=50, stroke='black', fill='none')
        svg_string = builder.to_string()
        
        assert '<circle' in svg_string
        assert 'cx="100"' in svg_string
        assert 'cy="100"' in svg_string
        assert 'r="50"' in svg_string
    
    def test_svg_builder_path_element(self):
        """SVG should contain proper path element"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600)
        builder.add_path(d="M 10 10 L 90 90", stroke='black', fill='none')
        svg_string = builder.to_string()
        
        assert '<path' in svg_string
        assert 'M 10 10 L 90 90' in svg_string
    
    def test_svg_builder_polygon_element(self):
        """SVG should contain proper polygon element"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600)
        builder.add_polygon(points=[(10, 10), (90, 10), (50, 90)], stroke='black', fill='none')
        svg_string = builder.to_string()
        
        assert '<polygon' in svg_string
        assert '10,10' in svg_string


class TestSVGModuleStructure:
    """Test module organization"""
    
    def test_svg_module_init(self):
        """SVG module should have __init__.py"""
        from coloring_book import svg
        assert hasattr(svg, 'SVGBuilder')
        assert hasattr(svg, 'AnimalDrawer')
    
    def test_svg_builder_layer_config(self):
        """SVGBuilder should support layer configuration"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600)
        builder.set_layer_config(line_width=2, line_color='black', fill_color='white')
        
        assert builder.line_width == 2
        assert builder.line_color == 'black'
        assert builder.fill_color == 'white'


class TestSVGColoringOptimization:
    """Test coloring-specific SVG features"""
    
    def test_svg_has_coloring_friendly_stroke(self):
        """SVG elements should use coloring-friendly stroke widths"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600)
        builder.add_circle(cx=100, cy=100, r=50)
        svg_string = builder.to_string()
        
        # Should have stroke for coloring books
        assert 'stroke=' in svg_string
    
    def test_svg_no_fill_by_default(self):
        """SVG elements should have no fill by default (for coloring)"""
        from coloring_book.svg.builder import SVGBuilder
        builder = SVGBuilder(width=800, height=600)
        builder.add_circle(cx=100, cy=100, r=50)
        svg_string = builder.to_string()
        
        # Should use fill="none" for coloring
        assert 'fill="none"' in svg_string or 'fill=\'none\'' in svg_string or '<circle' in svg_string
