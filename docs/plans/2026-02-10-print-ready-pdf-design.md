# Print-Ready PDF Generation (300 DPI) — Design

## Context

Current PDF pipeline produces 150 DPI output suitable for home printing. Need to support professional print quality (300 DPI) with bleed marks, crop marks, and quality validation for Etsy digital downloads and professional print shops.

## Key Decisions

1. **Dual output** — home print (150 DPI) + pro print (300 DPI) via compile-time flag
2. **Product-agnostic** — PrintProfile abstraction supports coloring books, planners, posters, etc.
3. **Etsy constraints** — 20MB per file, 5 files per listing, 300 DPI recommended
4. **Compression** — JPEG compression + grayscale conversion for line art keeps 300 DPI under 20MB
5. **Quality validation** — Build-time + post-build audit (trust but verify)
6. **Bleed** — Configurable per profile (0mm home, 3mm pro, 5mm poster)

## Architecture

```
SVG → PNG (profile.dpi) → ReportLab PDF → PDFAuditor → validated output
                                ↑
                          PrintProfile config
```

## PrintProfile Presets

| Profile | DPI | Color | Bleed | Crop Marks | Max Size | Target |
|---------|-----|-------|-------|------------|----------|--------|
| home | 150 | RGB | 0 | No | — | Home printer |
| etsy_standard | 300 | Grayscale | 0 | No | 20MB | Etsy digital download |
| pro_print | 300 | RGB | 3mm | Yes | — | Professional print shop |
| poster | 300 | RGB | 5mm | Yes | — | Poster/art print |

## PDFAuditor Checks

1. File size vs profile limit (hard fail if over, warning at 90%)
2. Effective DPI measurement (5% tolerance)
3. Page count sanity
4. Bleed area verification (pro profiles)

## Implementation Order

| Step | File | Change |
|------|------|--------|
| 1 | `pdf/profiles.py` | PrintProfile dataclass + 4 presets (NEW) |
| 2 | `pdf/generator.py` | Profile param, bleed, crop marks, JPEG compression |
| 3 | `png/exporter.py` | profile.dpi passthrough (minimal) |
| 4 | `pdf/auditor.py` | PDFAuditor + AuditResult (NEW) |
| 5 | `workbook/compiler.py` | Profile param + audit gate |
| 6 | `api/etsy_routes.py` | Publish uses etsy_standard profile |
| 7 | Tests | Unit + integration tests |

## Files

| Action | File |
|--------|------|
| CREATE | `src/coloring_book/pdf/profiles.py` |
| MODIFY | `src/coloring_book/pdf/generator.py` |
| MODIFY | `src/coloring_book/png/exporter.py` |
| CREATE | `src/coloring_book/pdf/auditor.py` |
| MODIFY | `src/coloring_book/workbook/compiler.py` |
| MODIFY | `src/coloring_book/api/etsy_routes.py` |
| CREATE | `tests/test_print_profiles.py` |
| CREATE | `tests/test_pdf_auditor.py` |
