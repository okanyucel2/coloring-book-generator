"""Watermark and preview generation for PNG images."""

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Optional, Dict, Tuple


class WatermarkGenerator:
    """Add watermarks to PNG images."""

    VALID_POSITIONS = {
        "top-left",
        "top-right",
        "bottom-left",
        "bottom-right",
        "center",
    }

    def __init__(
        self,
        text: str = "© Coloring Book",
        opacity: float = 0.3,
        position: str = "center",
        font_size: int = 24,
        color: Tuple[int, int, int] = (128, 128, 128),
    ):
        """Initialize watermark generator.

        Args:
            text: Watermark text
            opacity: Transparency (0.0-1.0)
            position: Position (top-left, top-right, bottom-left, bottom-right, center)
            font_size: Font size
            color: RGB color tuple

        Raises:
            ValueError: If opacity or position invalid
        """
        if opacity < 0.0 or opacity > 1.0:
            raise ValueError("Opacity must be between 0.0 and 1.0")
        if position not in self.VALID_POSITIONS:
            raise ValueError(f"Position must be one of {self.VALID_POSITIONS}")

        self.text = text
        self.opacity = opacity
        self.position = position
        self.font_size = font_size
        self.color = color

    def add_watermark(self, png_bytes: bytes) -> bytes:
        """Add watermark to PNG image.

        Args:
            png_bytes: PNG image data

        Returns:
            PNG with watermark as bytes
        """
        img = Image.open(BytesIO(png_bytes)).convert("RGBA")
        
        # Create watermark layer
        watermark = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark)
        
        # Calculate text position
        text_bbox = draw.textbbox((0, 0), self.text)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        positions = {
            "top-left": (20, 20),
            "top-right": (img.width - text_width - 20, 20),
            "bottom-left": (20, img.height - text_height - 20),
            "bottom-right": (img.width - text_width - 20, img.height - text_height - 20),
            "center": ((img.width - text_width) // 2, (img.height - text_height) // 2),
        }
        
        pos = positions[self.position]
        
        # Draw text with opacity
        alpha = int(255 * self.opacity)
        text_color = (*self.color, alpha)
        draw.text(pos, self.text, fill=text_color)
        
        # Composite images
        result = Image.alpha_composite(img, watermark).convert("RGB")
        
        # Save to bytes
        buffer = BytesIO()
        result.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()

    def set_opacity(self, opacity: float) -> "WatermarkGenerator":
        """Set opacity and return self for chaining."""
        if opacity < 0.0 or opacity > 1.0:
            raise ValueError("Opacity must be between 0.0 and 1.0")
        self.opacity = opacity
        return self


class PreviewGenerator:
    """Generate thumbnails/previews from PNG images."""

    def __init__(self, size: Tuple[int, int] = (200, 200)):
        """Initialize preview generator.

        Args:
            size: Thumbnail size (width, height)
        """
        self.size = size
        self.format = "PNG"

    def create_thumbnail(self, png_bytes: bytes) -> bytes:
        """Create thumbnail from PNG.

        Args:
            png_bytes: PNG image data

        Returns:
            Thumbnail PNG as bytes
        """
        img = Image.open(BytesIO(png_bytes))
        
        # Maintain aspect ratio
        img.thumbnail(self.size, Image.Resampling.LANCZOS)
        
        # Pad with white if needed
        final_img = Image.new("RGB", self.size, "white")
        offset = ((self.size[0] - img.width) // 2, (self.size[1] - img.height) // 2)
        final_img.paste(img, offset)
        
        # Save to bytes
        buffer = BytesIO()
        final_img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()

    def batch_thumbnail(self, png_dict: Dict[str, bytes]) -> Dict[str, bytes]:
        """Create thumbnails for multiple PNGs.

        Args:
            png_dict: Dict mapping names to PNG bytes

        Returns:
            Dict mapping names to thumbnail bytes
        """
        results = {}
        for name, png_bytes in png_dict.items():
            results[name] = self.create_thumbnail(png_bytes)
        return results


class ListingImageGenerator:
    """Generate Etsy listing-ready images."""

    def __init__(self, size: Tuple[int, int] = (1000, 1000)):
        """Initialize listing image generator.

        Args:
            size: Output image size
        """
        self.size = size

    def generate(self, png_bytes: bytes, title: str = "") -> bytes:
        """Generate listing image from PNG.

        Args:
            png_bytes: PNG image data
            title: Image title/description

        Returns:
            Listing image as PNG bytes
        """
        img = Image.open(BytesIO(png_bytes))
        
        # Resize to fit in listing size
        img.thumbnail((self.size[0] - 40, self.size[1] - 40))
        
        # Create white background
        result = Image.new("RGB", self.size, "white")
        
        # Center image on background
        offset = ((self.size[0] - img.width) // 2, (self.size[1] - img.height) // 2)
        result.paste(img, offset)
        
        # Save to bytes
        buffer = BytesIO()
        result.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()

    def generate_with_metadata(self, png_bytes: bytes, metadata: Dict) -> bytes:
        """Generate listing image with metadata.

        Args:
            png_bytes: PNG image data
            metadata: Dict with title, category, etc.

        Returns:
            Listing image as PNG bytes
        """
        img = Image.open(BytesIO(png_bytes))
        
        # Resize to fit
        img.thumbnail((self.size[0] - 40, self.size[1] - 100))
        
        # Create white background with extra space for metadata
        result = Image.new("RGB", self.size, "white")
        
        # Paste image
        offset = ((self.size[0] - img.width) // 2, 20)
        result.paste(img, offset)
        
        # Save to bytes
        buffer = BytesIO()
        result.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
