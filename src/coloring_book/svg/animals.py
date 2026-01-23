"""Animal implementations for SVG generation."""
from .base import AnimalDrawer


class CatDrawer(AnimalDrawer):
    """Draw a cat as SVG."""

    def __init__(self, width: int = 200, height: int = 200):
        """Initialize CatDrawer."""
        super().__init__("cat", width, height)

    def draw(self) -> str:
        """Draw a cat and return SVG string."""
        self.reset()
        
        # Body
        self.add_element(
            f'<ellipse cx="{self.width/2}" cy="{self.height/2}" '
            f'rx="60" ry="70" fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Head
        self.add_element(
            f'<circle cx="{self.width/2}" cy="{self.height/2 - 70}" '
            f'r="40" fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Left ear
        self.add_element(
            f'<polygon points="{self.width/2 - 30},{self.height/2 - 110} '
            f'{self.width/2 - 20},{self.height/2 - 70} '
            f'{self.width/2 - 40},{self.height/2 - 80}" '
            f'fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Right ear
        self.add_element(
            f'<polygon points="{self.width/2 + 30},{self.height/2 - 110} '
            f'{self.width/2 + 20},{self.height/2 - 70} '
            f'{self.width/2 + 40},{self.height/2 - 80}" '
            f'fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Left eye
        self.add_element(
            f'<circle cx="{self.width/2 - 15}" cy="{self.height/2 - 75}" '
            f'r="5" fill="black"/>'
        )
        
        # Right eye
        self.add_element(
            f'<circle cx="{self.width/2 + 15}" cy="{self.height/2 - 75}" '
            f'r="5" fill="black"/>'
        )
        
        # Nose
        self.add_element(
            f'<polygon points="{self.width/2},{self.height/2 - 55} '
            f'{self.width/2 - 5},{self.height/2 - 50} '
            f'{self.width/2 + 5},{self.height/2 - 50}" '
            f'fill="pink"/>'
        )
        
        # Mouth
        self.add_element(
            f'<path d="M {self.width/2} {self.height/2 - 50} '
            f'Q {self.width/2 - 10} {self.height/2 - 45} {self.width/2 - 15} {self.height/2 - 40}" '
            f'fill="none" stroke="black" stroke-width="1.5"/>'
        )
        self.add_element(
            f'<path d="M {self.width/2} {self.height/2 - 50} '
            f'Q {self.width/2 + 10} {self.height/2 - 45} {self.width/2 + 15} {self.height/2 - 40}" '
            f'fill="none" stroke="black" stroke-width="1.5"/>'
        )
        
        # Front left leg
        self.add_element(
            f'<line x1="{self.width/2 - 30}" y1="{self.height/2 + 60}" '
            f'x2="{self.width/2 - 30}" y2="{self.height/2 + 100}" '
            f'stroke="black" stroke-width="2"/>'
        )
        
        # Front right leg
        self.add_element(
            f'<line x1="{self.width/2 + 30}" y1="{self.height/2 + 60}" '
            f'x2="{self.width/2 + 30}" y2="{self.height/2 + 100}" '
            f'stroke="black" stroke-width="2"/>'
        )
        
        # Tail
        self.add_element(
            f'<path d="M {self.width/2 + 60} {self.height/2} '
            f'Q {self.width/2 + 80} {self.height/2 - 40} {self.width/2 + 70} {self.height/2 - 80}" '
            f'fill="none" stroke="black" stroke-width="2"/>'
        )
        
        return self.export_svg()


class DogDrawer(AnimalDrawer):
    """Draw a dog as SVG."""

    def __init__(self, width: int = 200, height: int = 200):
        """Initialize DogDrawer."""
        super().__init__("dog", width, height)

    def draw(self) -> str:
        """Draw a dog and return SVG string."""
        self.reset()
        
        # Body
        self.add_element(
            f'<ellipse cx="{self.width/2}" cy="{self.height/2 + 10}" '
            f'rx="70" ry="60" fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Head
        self.add_element(
            f'<circle cx="{self.width/2 - 50}" cy="{self.height/2 - 40}" '
            f'r="45" fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Left ear (floppy)
        self.add_element(
            f'<ellipse cx="{self.width/2 - 85}" cy="{self.height/2 - 60}" '
            f'rx="20" ry="40" fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Right ear (floppy)
        self.add_element(
            f'<ellipse cx="{self.width/2 - 15}" cy="{self.height/2 - 60}" '
            f'rx="20" ry="40" fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Left eye
        self.add_element(
            f'<circle cx="{self.width/2 - 65}" cy="{self.height/2 - 50}" '
            f'r="6" fill="black"/>'
        )
        
        # Right eye
        self.add_element(
            f'<circle cx="{self.width/2 - 35}" cy="{self.height/2 - 50}" '
            f'r="6" fill="black"/>'
        )
        
        # Nose
        self.add_element(
            f'<circle cx="{self.width/2 - 50}" cy="{self.height/2 - 30}" '
            f'r="8" fill="black"/>'
        )
        
        # Mouth
        self.add_element(
            f'<path d="M {self.width/2 - 50} {self.height/2 - 30} '
            f'L {self.width/2 - 50} {self.height/2 - 15}" '
            f'stroke="black" stroke-width="2"/>'
        )
        
        # Front left leg
        self.add_element(
            f'<line x1="{self.width/2 - 20}" y1="{self.height/2 + 60}" '
            f'x2="{self.width/2 - 20}" y2="{self.height/2 + 110}" '
            f'stroke="black" stroke-width="3"/>'
        )
        
        # Front right leg
        self.add_element(
            f'<line x1="{self.width/2 + 20}" y1="{self.height/2 + 60}" '
            f'x2="{self.width/2 + 20}" y2="{self.height/2 + 110}" '
            f'stroke="black" stroke-width="3"/>'
        )
        
        # Back left leg
        self.add_element(
            f'<line x1="{self.width/2 - 60}" y1="{self.height/2 + 60}" '
            f'x2="{self.width/2 - 60}" y2="{self.height/2 + 110}" '
            f'stroke="black" stroke-width="3"/>'
        )
        
        # Back right leg
        self.add_element(
            f'<line x1="{self.width/2 + 60}" y1="{self.height/2 + 60}" '
            f'x2="{self.width/2 + 60}" y2="{self.height/2 + 110}" '
            f'stroke="black" stroke-width="3"/>'
        )
        
        # Tail
        self.add_element(
            f'<path d="M {self.width/2 + 70} {self.height/2 + 10} '
            f'Q {self.width/2 + 100} {self.height/2 - 20} {self.width/2 + 80} {self.height/2 - 60}" '
            f'fill="none" stroke="black" stroke-width="2.5"/>'
        )
        
        return self.export_svg()


class BirdDrawer(AnimalDrawer):
    """Draw a bird as SVG."""

    def __init__(self, width: int = 200, height: int = 200):
        """Initialize BirdDrawer."""
        super().__init__("bird", width, height)

    def draw(self) -> str:
        """Draw a bird and return SVG string."""
        self.reset()
        
        # Body
        self.add_element(
            f'<ellipse cx="{self.width/2 - 20}" cy="{self.height/2}" '
            f'rx="40" ry="50" fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Head
        self.add_element(
            f'<circle cx="{self.width/2 - 50}" cy="{self.height/2 - 40}" '
            f'r="30" fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Eye
        self.add_element(
            f'<circle cx="{self.width/2 - 55}" cy="{self.height/2 - 45}" '
            f'r="5" fill="black"/>'
        )
        
        # Beak
        self.add_element(
            f'<polygon points="{self.width/2 - 80},{self.height/2 - 40} '
            f'{self.width/2 - 100},{self.height/2 - 35} '
            f'{self.width/2 - 80},{self.height/2 - 30}" '
            f'fill="orange" stroke="orange" stroke-width="1"/>'
        )
        
        # Left wing
        self.add_element(
            f'<ellipse cx="{self.width/2 - 30}" cy="{self.height/2 - 10}" '
            f'rx="35" ry="50" fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Right wing
        self.add_element(
            f'<ellipse cx="{self.width/2 - 10}" cy="{self.height/2 - 10}" '
            f'rx="35" ry="50" fill="none" stroke="black" stroke-width="2"/>'
        )
        
        # Left leg
        self.add_element(
            f'<line x1="{self.width/2 - 35}" y1="{self.height/2 + 50}" '
            f'x2="{self.width/2 - 35}" y2="{self.height/2 + 90}" '
            f'stroke="black" stroke-width="2"/>'
        )
        
        # Right leg
        self.add_element(
            f'<line x1="{self.width/2 - 5}" y1="{self.height/2 + 50}" '
            f'x2="{self.width/2 - 5}" y2="{self.height/2 + 90}" '
            f'stroke="black" stroke-width="2"/>'
        )
        
        # Tail feathers
        self.add_element(
            f'<path d="M {self.width/2 + 20} {self.height/2} '
            f'L {self.width/2 + 60} {self.height/2 - 30}" '
            f'stroke="black" stroke-width="2"/>'
        )
        self.add_element(
            f'<path d="M {self.width/2 + 20} {self.height/2 + 5} '
            f'L {self.width/2 + 60} {self.height/2 + 35}" '
            f'stroke="black" stroke-width="2"/>'
        )
        
        return self.export_svg()
