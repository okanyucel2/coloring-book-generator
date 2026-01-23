# AI Image Generation Integration

## Overview

The Coloring Book Generator now features **AI-first, SVG-fallback** architecture:

1. **Tries AI generation first** via Genesis Backend API
2. **Falls back to SVG** if AI is unavailable or fails
3. **Supports unlimited animals** (not just cat/dog/bird)
4. **Extended CLI** with style and difficulty options

---

## Architecture

### Pipeline Flow

```
ColoringBookPipeline.generate()
│
├─ AI Enabled?
│  ├─ YES: Try AIColoringGenerator.generate()
│  │       ├─ POST /api/v1/image-generation/generate/raw
│  │       ├─ Return PNG bytes on success ✅
│  │       └─ Log warning on failure → fallback
│  │
│  └─ NO: Skip to SVG pipeline
│
└─ SVG Pipeline (Fallback)
   ├─ AnimalFactory.create(animal)
   ├─ drawer.draw() → SVG string
   ├─ PNGExporter(dpi=150).export_svg_to_png()
   └─ Return PNG bytes
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **ColoringBookPipeline** | Orchestrates AI + SVG | `src/coloring_book/pipeline.py` |
| **AIColoringGenerator** | Calls Genesis API | `src/coloring_book/ai/generator.py` |
| **ColoringBookCLI** | CLI interface | `src/coloring_book/cli.py` |
| **AnimalFactory** | SVG registry | `src/coloring_book/svg/factory.py` |
| **PNGExporter** | SVG → PNG conversion | `src/coloring_book/png/exporter.py` |

---

## CLI Usage

### Single Page Generation

```bash
# Basic usage (defaults to coloring_book style, medium difficulty)
python -m coloring_book generate --animal cat

# With style and difficulty
python -m coloring_book generate \
  --animal elephant \
  --style kawaii \
  --difficulty hard \
  --output elephant_kawaii.png

# Force SVG pipeline only (no AI)
python -m coloring_book --no-ai generate --animal cat
```

### Batch Generation

```bash
# From file (one animal per line)
python -m coloring_book batch \
  --file animals.txt \
  --style coloring_book \
  --difficulty medium \
  --output docs/examples/

# Inline animals
python -m coloring_book batch \
  --animals cat dog elephant bird \
  --output docs/examples/
```

### List Available Animals

```bash
# List SVG animals only
python -m coloring_book list

# JSON output
python -m coloring_book list --json
```

### Help

```bash
# Global help
python -m coloring_book --help

# Command-specific help
python -m coloring_book generate --help
python -m coloring_book batch --help
```

---

## Options

### Global Options

| Option | Default | Description |
|--------|---------|-------------|
| `-v, --verbose` | - | Enable debug logging |
| `--no-ai` | - | Disable AI, use SVG only |
| `--ai-url` | `http://localhost:5000` | Genesis API base URL |
| `--dpi` | `150` | PNG export DPI |

### Style Options

| Style | Description |
|-------|-------------|
| `coloring_book` | Traditional coloring page style (default) |
| `kawaii` | Cute, rounded style |
| `realistic` | Detailed, realistic style |

### Difficulty Options

| Difficulty | Description |
|------------|-------------|
| `easy` | Fewer details, larger areas |
| `medium` | Balanced details (default) |
| `hard` | More intricate details |

---

## animals.txt Format

```
# Example animals file
# Lines starting with # are ignored

# SVG animals (must be registered)
cat
dog
bird

# AI animals (any valid name)
elephant
lion
tiger
butterfly
penguin
```

---

## Genesis API Integration

### Endpoint

```
POST /api/v1/image-generation/generate/raw
```

### Request Body

```json
{
  "animal": "cat",
  "style": "coloring_book",
  "difficulty": "medium"
}
```

### Response

- **Status 200**: PNG image bytes (raw binary)
- **Status 4xx/5xx**: Error (logged, falls back to SVG)

### Configuration

```python
from coloring_book.pipeline import ColoringBookPipeline

# Create pipeline with custom Genesis URL
pipeline = ColoringBookPipeline(
    ai_enabled=True,
    ai_base_url="http://localhost:5000",
    png_dpi=150
)

# Generate
png_bytes = pipeline.generate(
    animal="cat",
    style="kawaii",
    difficulty="medium"
)
```

---

## Supported Animals

### SVG Registry (Always Available)

- `cat`
- `dog`
- `bird`

### AI Generation (If Genesis API Available)

Any valid animal name, including:
- Common: elephant, lion, tiger, penguin, rabbit, dolphin
- Exotic: giraffe, zebra, crocodile, owl, butterfly
- Custom: Any animal name that Genesis API understands

---

## Error Handling

### AI Generation Fails

```
⚠️ Warning: AI generation failed for 'cat': [error]
             Falling back to SVG pipeline
✅ Generated SVG PNG for 'cat'
```

### Animal Not in SVG Registry

```
❌ Error: Animal 'elephant' not registered
✅ Solution: Use --ai flag or register custom SVG drawer
```

### Genesis API Unavailable

```
⚠️ Warning: Cannot connect to http://localhost:5000
             Falling back to SVG pipeline
```

---

## Testing

### Test CLI Help

```bash
python -m coloring_book --help
python -m coloring_book generate --help
python -m coloring_book batch --help
```

### Test Single Generation

```bash
python -m coloring_book generate --animal cat --output test.png
file test.png  # Should show PNG image
```

### Test Batch Generation

```bash
python -m coloring_book batch \
  --animals cat dog bird \
  --output /tmp/batch_test/
ls -la /tmp/batch_test/
```

### Test with Verbose Logging

```bash
python -m coloring_book -v generate --animal cat
```

---

## Performance Notes

- **SVG Pipeline**: ~50-100ms per image (instant for cat/dog/bird)
- **AI Generation**: Depends on Genesis API latency (typically 1-5s)
- **Batch Processing**: Processes animals sequentially (can be parallelized)

---

## Future Enhancements

- [ ] Parallel batch processing
- [ ] Caching of AI-generated images
- [ ] Custom SVG drawer registration
- [ ] Web API endpoint wrapper
- [ ] Progress bar for batch operations
- [ ] PDF output support
