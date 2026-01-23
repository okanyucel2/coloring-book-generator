# Pipeline Architecture

## ColoringBookPipeline Class

Core orchestrator for AI-first, SVG-fallback generation.

### Initialization

```python
from coloring_book.pipeline import ColoringBookPipeline

# Default: AI enabled, Genesis on localhost:5000
pipeline = ColoringBookPipeline()

# Custom configuration
pipeline = ColoringBookPipeline(
    ai_enabled=True,              # Enable AI generation
    ai_base_url="http://localhost:5000",  # Genesis API URL
    png_dpi=150                   # PNG export DPI
)
```

### Core Methods

#### `generate()` - Single Page

```python
png_bytes = pipeline.generate(
    animal="cat",                 # Required
    style="coloring_book",        # Optional: coloring_book|kawaii|realistic
    difficulty="medium",          # Optional: easy|medium|hard
    output_path=Path("out.png")   # Optional: save location
)

# Returns: PNG image bytes
# Saves: to output_path if provided
```

**Flow:**
1. Validate style and difficulty
2. Try AI generation (if enabled)
3. Fallback to SVG if AI fails
4. Return PNG bytes

#### `batch_generate()` - Multiple Pages

```python
results = pipeline.batch_generate(
    animals=["cat", "dog", "elephant"],
    style="kawaii",               # All animals use same style
    difficulty="medium",          # All animals use same difficulty
    output_dir=Path("docs/examples/")  # Save all to dir
)

# Returns: {animal: png_bytes or None}
# Example: {"cat": b'...', "dog": b'...', "elephant": None}
```

**Behavior:**
- Generates each animal, continues on failures
- Saves to `{output_dir}/{animal}.png` if path provided
- Returns dict with success/failure status
- Logs summary: "✅ 2/3 succeeded"

### Validation

```python
from coloring_book.pipeline import VALID_STYLES, VALID_DIFFICULTIES

VALID_STYLES       # {"coloring_book", "kawaii", "realistic"}
VALID_DIFFICULTIES # {"easy", "medium", "hard"}

# Raises ValueError if invalid
pipeline.generate(animal="cat", style="invalid")
# → ValueError: Invalid style 'invalid'. Must be one of: ...
```

---

## AI Integration

### AIColoringGenerator

Client for Genesis Image Generation API.

```python
from coloring_book.ai.generator import AIColoringGenerator

generator = AIColoringGenerator(
    base_url="http://localhost:5000",
    timeout=30.0
)

# Single generation
png_bytes = generator.generate(
    animal="cat",
    output_path=Path("cat.png"),  # Optional
    style="coloring_book",
    difficulty="medium"
)

# Returns: PNG bytes or None if failed
```

### API Endpoint

**Endpoint:** `POST /api/v1/image-generation/generate/raw`

**Request:**
```json
{
  "animal": "cat",
  "style": "coloring_book",
  "difficulty": "medium"
}
```

**Response:**
- **200**: PNG binary data
- **4xx/5xx**: Error (logged, no exception raised)

### Error Handling

```python
# Generator.generate() returns None on API error
png_bytes = generator.generate(animal="nonexistent")
if png_bytes is None:
    print("AI generation failed, falling back...")
```

### Logging

```
2026-01-23 18:12:28,531 - coloring_book.ai.generator - INFO - Attempting AI generation...
2026-01-23 18:12:28,547 - coloring_book.ai.generator - INFO - Successfully generated image
2026-01-23 18:12:28,547 - coloring_book.pipeline - INFO - ✅ AI generation succeeded for 'cat'
```

Or on failure:

```
2026-01-23 18:12:47,797 - coloring_book.ai.generator - WARNING - AI generation failed for 'cat': ConnectionError
2026-01-23 18:12:47,797 - coloring_book.pipeline - INFO - Falling back to SVG pipeline
```

---

## SVG Fallback Pipeline

### AnimalFactory Registry

```python
from coloring_book.svg.factory import AnimalFactory

# Check if animal available
if AnimalFactory.is_available("cat"):
    drawer = AnimalFactory.create("cat")
    svg = drawer.draw()

# List available
animals = AnimalFactory.get_available_animals()
# → {"cat": <class Cat>, "dog": <class Dog>, "bird": <class Bird>}

# Get available
for name in AnimalFactory.get_available_animals():
    print(f"  - {name}")
```

### SVG Generation

```python
from coloring_book.svg.factory import AnimalFactory

drawer = AnimalFactory.create("cat", width=312, height=312)
svg_string = drawer.draw()
# → "<svg xmlns='...'><circle cx='...' ... </svg>"
```

### PNG Export

```python
from coloring_book.png.exporter import PNGExporter

exporter = PNGExporter(dpi=150)
png_bytes = exporter.export_svg_to_png(svg_string)
# → b'\x89PNG\r\n\x1a\n...'
```

---

## Complete Example

### Manual Pipeline

```python
from pathlib import Path
from coloring_book.pipeline import ColoringBookPipeline

# Initialize
pipeline = ColoringBookPipeline(
    ai_enabled=True,
    ai_base_url="http://localhost:5000",
    png_dpi=150
)

# Single generation
png_bytes = pipeline.generate(
    animal="cat",
    style="kawaii",
    difficulty="easy",
    output_path=Path("cat_kawaii.png")
)
print(f"Generated: {len(png_bytes)} bytes")

# Batch generation
results = pipeline.batch_generate(
    animals=["cat", "dog", "bird"],
    style="coloring_book",
    difficulty="medium",
    output_dir=Path("examples/")
)

success = sum(1 for v in results.values() if v is not None)
print(f"Batch: {success}/3 succeeded")
```

### CLI Usage

```bash
# Single
python -m coloring_book generate --animal cat --style kawaii

# Batch
python -m coloring_book batch --animals cat dog bird --output examples/

# Verbose logging
python -m coloring_book -v generate --animal cat
```

---

## Configuration Reference

### Environment Variables

Currently no env vars - use CLI flags or constructor params.

### Genesis API Configuration

```python
# Custom Genesis URL
pipeline = ColoringBookPipeline(ai_base_url="http://custom.host:5000")

# Disable AI
pipeline = ColoringBookPipeline(ai_enabled=False)

# Custom PNG DPI
pipeline = ColoringBookPipeline(png_dpi=300)
```

### Logging Configuration

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or per-module
logging.getLogger("coloring_book.pipeline").setLevel(logging.DEBUG)
logging.getLogger("coloring_book.ai.generator").setLevel(logging.DEBUG)
```

---

## Testing

### Unit Tests

```bash
# Run tests
pytest tests/

# Specific test
pytest tests/test_pipeline.py::test_generate

# With coverage
pytest --cov=coloring_book tests/
```

### Integration Tests

```bash
# Test with mock Genesis API
pytest tests/integration/test_ai_integration.py

# Test SVG fallback
pytest tests/integration/test_svg_fallback.py
```

### Manual Testing

```bash
# Test CLI
python -m coloring_book --help
python -m coloring_book list

# Test generation (SVG only)
python -m coloring_book --no-ai generate --animal cat --output test.png

# Test with actual Genesis API
python -m coloring_book generate --animal cat --output test.png
```

---

## Debugging

### Enable Verbose Logging

```bash
python -m coloring_book -v generate --animal cat
```

### Check API Connectivity

```bash
curl http://localhost:5000/api/v1/image-generation/generate/raw \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"animal": "cat", "style": "coloring_book", "difficulty": "medium"}'
```

### Inspect Generated PNG

```bash
# Check file info
file cat.png
identify cat.png  # ImageMagick

# Check dimensions
python -c "from PIL import Image; img = Image.open('cat.png'); print(img.size)"
```

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| AI generation | 1-5s | Depends on Genesis API |
| SVG generation | 50-100ms | Instant for cat/dog/bird |
| PNG export | 10-50ms | Variable by image size |
| Batch (10 animals) | ~2-10s | Sequential processing |

---

## Future Roadmap

- [ ] Async/parallel batch generation
- [ ] Image caching
- [ ] Custom animal registration
- [ ] Web API wrapper
- [ ] Progress reporting
- [ ] Retry logic for AI failures
- [ ] Multiple style/difficulty combinations
