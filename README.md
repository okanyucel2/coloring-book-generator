# Coloring Book Generator

Etsy-ready coloring book page generator. Produces SVG line art → PNG export → PDF compilation.

## Architecture

```
src/coloring_book/
├── svg/        # SVG generation (animal drawings, base shapes)
├── png/        # PNG export + watermark
├── pdf/        # PDF compilation (reportlab)
├── metadata/   # Etsy listing metadata
└── qc/         # Quality control validator
```

## Setup

```bash
pip install -e ".[dev]"
```

## Testing

```bash
pytest tests/ -v
```

## Tech Stack

- Python 3.11+
- Pillow (PNG processing)
- svglib + reportlab (SVG→PDF)
- Pydantic (metadata schemas)
