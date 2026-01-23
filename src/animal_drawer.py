"""Animal drawing implementations using SVG."""
from abc import ABC, abstractmethod
from svg_builder import SVGBuilder


class AnimalDrawer(ABC):
    """Base class for animal drawings."""
    
    def __init__(self, name: str):
        self.name = name
        self.builder = SVGBuilder()
    
    @abstractmethod
    def draw(self) -> str:
        """Draw the animal and return SVG."""
        pass


class Cat(AnimalDrawer):
    """Cat drawing implementation."""
    
    def __init__(self):
        super().__init__("Cat")
    
    def draw(self) -> str:
        """Draw a cat using SVG."""
        svg = self.builder.create(200, 200)
        
        # Body
        svg.add_circle(cx=100, cy=120, r=50, fill="orange", stroke="black", stroke_width=2)
        
        # Head
        svg.add_circle(cx=100, cy=60, r=40, fill="orange", stroke="black", stroke_width=2)
        
        # Eyes
        svg.add_circle(cx=90, cy=50, r=5, fill="green")
        svg.add_circle(cx=110, cy=50, r=5, fill="green")
        
        # Ears (triangles using polygon)
        svg.add_polygon([(75, 20), (85, 5), (80, 25)], fill="orange", stroke="black", stroke_width=2)
        svg.add_polygon([(115, 20), (125, 5), (120, 25)], fill="orange", stroke="black", stroke_width=2)
        
        # Nose
        svg.add_circle(cx=100, cy=65, r=3, fill="pink")
        
        # Mouth (simple line)
        svg.add_line(x1=100, y1=65, x2=100, y2=75, stroke="black", stroke_width=1)
        
        # Tail
        svg.add_path("M 145 120 Q 180 100 170 60", stroke="orange", stroke_width=6, fill="none")
        
        # Front legs
        svg.add_rect(x=85, y=160, width=8, height=30, fill="orange", stroke="black", stroke_width=1)
        svg.add_rect(x=107, y=160, width=8, height=30, fill="orange", stroke="black", stroke_width=1)
        
        # Back legs
        svg.add_rect(x=75, y=160, width=8, height=30, fill="orange", stroke="black", stroke_width=1)
        svg.add_rect(x=117, y=160, width=8, height=30, fill="orange", stroke="black", stroke_width=1)
        
        return svg.build()
