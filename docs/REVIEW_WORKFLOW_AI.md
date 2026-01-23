# AI-Generated Coloring Book Review Workflow

## Overview
Review workflow for AI-generated coloring books (Gemini, Imagen) ensuring quality standards for Etsy listing.

---

## Review Output Structure

### 1. **Review Report JSON** (`review_report.json`)
```json
{
  "review_id": "rev_f7b2932e19fa96bf",
  "timestamp": "2026-01-23T16:27:26Z",
  "image_filename": "f7b2932e19fa96bf.png",
  "model_used": "imagen",
  "style": "coloring_book",
  "difficulty": "medium",
  
  "quality_metrics": {
    "line_clarity": {
      "score": 92,
      "notes": "Crisp, well-defined black lines with no bleeding",
      "status": "pass"
    },
    "white_coverage": {
      "score": 88,
      "target_range": [75, 95],
      "actual_ratio": 0.864,
      "status": "pass"
    },
    "animal_recognition": {
      "score": 95,
      "notes": "Clear snake shape, easily identifiable",
      "status": "pass"
    },
    "detail_level": {
      "score": 87,
      "difficulty": "medium",
      "notes": "Good balance of detail without overcrowding",
      "status": "pass"
    },
    "print_readiness": {
      "dpi": 150,
      "dimensions": "1024x1024",
      "color_mode": "RGB",
      "file_size_kb": 567,
      "status": "pass"
    }
  },
  
  "quality_gates": {
    "minimum_line_clarity": { "required": 85, "actual": 92, "pass": true },
    "maximum_white_ratio": { "required": 0.95, "actual": 0.864, "pass": true },
    "minimum_animal_score": { "required": 70, "actual": 95, "pass": true },
    "file_size_valid": { "required": "200-600 KB", "actual": "567 KB", "pass": true },
    "dimensions_correct": { "required": "1024x1024", "actual": "1024x1024", "pass": true }
  },
  
  "print_tests": {
    "4x6_print": {
      "status": "pass",
      "resolution_dpi": 150,
      "notes": "Clear and sharp at 4x6 inches"
    },
    "8x10_print": {
      "status": "pass",
      "resolution_dpi": 75,
      "notes": "Acceptable quality, slight softening"
    },
    "a4_print": {
      "status": "pass",
      "resolution_dpi": 47,
      "notes": "Large format, line clarity maintained"
    }
  },
  
  "reviewer_notes": {
    "approved_for_listing": true,
    "approved_by": "nadya_human_review",
    "review_date": "2026-01-23",
    "comments": "Excellent snake drawing with intricate scales. Medium difficulty is appropriate. Ready for Etsy.",
    "requested_changes": [],
    "re_generation_needed": false
  },
  
  "listing_metadata": {
    "title": "Coloring Book Page - Snake | Medium Difficulty",
    "tags": ["snake", "coloring_book", "medium_difficulty", "printable"],
    "category": "Coloring Pages - Animals",
    "seo_keywords": ["snake coloring page", "printable coloring", "animal coloring"],
    "suggested_price_usd": 2.99,
    "suggested_bundle": "10-Pack Animals Bundle"
  },
  
  "production_ready": true
}
```

---

## 2. **Automated Quality Gate Checks** (Pre-Review)

Before human review, run automated checks:

```python
class AIReviewValidator:
    """Pre-flight checks for AI-generated images"""
    
    def validate(self, image_path: str) -> ReviewReport:
        checks = {
            "pixel_content": self._check_pixel_content(),
            "line_clarity": self._check_line_clarity(),
            "white_ratio": self._check_white_ratio(),
            "file_integrity": self._check_file_integrity(),
            "dimensions": self._check_dimensions(),
            "model_quality": self._check_model_baseline(),
        }
        return ReviewReport(checks)
    
    def _check_white_ratio(self):
        """Ensure 75-95% white (room for coloring)"""
        # Should fail on completely black or white images
        
    def _check_line_clarity(self):
        """Edge detection - verify clean lines not blurry"""
        # Use Canny edge detection or morphological analysis
        
    def _check_pixel_content(self):
        """Block completely blank/generated-by-accident images"""
        # Reject if unique_colors <= 2
```

---

## 3. **Human Review Checklist**

```markdown
### Visual Quality Review
- [ ] Animal is clearly identifiable (not abstract)
- [ ] Lines are clean and crisp (no artifacts)
- [ ] No unintended color spots or noise
- [ ] Design fills the page appropriately
- [ ] Symmetry is acceptable (slight imperfections OK)

### Coloring Appropriateness
- [ ] White space suitable for marker/crayon (not too dense)
- [ ] Lines are thin enough to see where to color
- [ ] No areas impossible to color neatly
- [ ] Age-appropriate for stated difficulty level

### Print Quality
- [ ] Image appears sharp in 150 DPI preview
- [ ] No pixelation or blurriness visible
- [ ] Black lines have good contrast
- [ ] File size reasonable (200-600 KB)

### Etsy Listing Readiness
- [ ] Title is clear and searchable
- [ ] Description matches difficulty level
- [ ] Tags include relevant keywords
- [ ] Thumbnail preview is appealing
- [ ] Price is competitive with similar listings
```

---

## 4. **Review Workflow Process**

```
┌─────────────────────────────────────────┐
│  AI Image Generated (Gemini/Imagen)      │
│  d92e19a1eb7426b6.png                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  AUTOMATED QUALITY GATES                 │
│  - Line clarity > 85%                   │
│  - White ratio 75-95%                   │
│  - File size 200-600 KB                 │
│  - Dimensions 1024x1024                 │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
    PASS│             │FAIL
        │             │
        ▼             ▼
   HUMAN REVIEW   REGENERATE
   (Nadya)        (New prompt)
        │             │
        ▼             └─────┐
   ┌────────────┐           │
   │  Approved  │           │
   │  Rejected  │◄──────────┘
   │  Changes   │
   │  Required  │
   └─────┬──────┘
         │
         ▼
┌──────────────────────────────┐
│  GENERATE REVIEW REPORT      │
│  - Quality scores            │
│  - Print test results        │
│  - Listing metadata          │
│  - Reviewer notes            │
└──────────────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  ETSY PUBLISHING READY       │
│  - Image approved            │
│  - Metadata generated        │
│  - Price suggested           │
│  - Bundle recommendations    │
└──────────────────────────────┘
```

---

## 5. **Review Report Use Cases**

### A. Batch Review
```bash
# Process 50 AI-generated images
python -m coloring_book review batch \
  --input-dir ai_generated/ \
  --output-dir review_reports/ \
  --model imagen \
  --reviewer nadya

# Output: 50 review_report_*.json files
# Summary: 47 approved, 2 rejected, 1 needs changes
```

### B. Quality Dashboard
Display review metrics across all images:
```
Model Performance (Last 100 images)
├─ Imagen:      94% pass rate, avg quality 91/100
├─ Gemini:      88% pass rate, avg quality 87/100
└─ Imagen Ultra: 97% pass rate, avg quality 96/100

Most Approved Difficulty: MEDIUM
Least Approved: HARD (detail too dense)

Average Review Time: 3 min per image
```

### C. Feedback Loop
- Track which animals/styles fail most
- Adjust prompts for future generations
- Example: "Snakes with scales" → 96% approval
- Example: "Insects with fine details" → 72% approval

---

## 6. **API Integration**

```python
# POST /api/v1/coloring-book/review/generate
{
  "image_filename": "f7b2932e19fa96bf.png",
  "model_used": "imagen",
  "review_type": "auto" | "manual" | "full"
}

# Response
{
  "review_id": "rev_...",
  "review_report": {...},
  "approved": true,
  "suggested_actions": ["list_on_etsy", "add_to_bundle"]
}
```

---

## 7. **Quality Benchmarks by Model**

| Model | Avg Quality Score | Pass Rate | Best For |
|-------|------------------|-----------|----------|
| Gemini | 87/100 | 88% | Quick generation, consistent style |
| Imagen 4.0 | 91/100 | 94% | Default choice, clean lines |
| Imagen Ultra | 96/100 | 97% | Premium listings, fine detail |

---

## 8. **Re-generation Strategy**

When review fails:

```python
class RegenerationStrategy:
    def should_regenerate(review: ReviewReport) -> bool:
        """Decide if image should be re-generated"""
        if review.white_ratio > 0.95:  # Too dense
            return True
        if review.line_clarity < 80:   # Blurry
            return True
        if review.animal_score < 70:   # Unrecognizable
            return True
        return False
    
    def next_model(current_model: str) -> str:
        """Escalate to better model if needed"""
        return {
            "gemini": "imagen",          # Upgrade
            "imagen": "imagen-ultra",    # Premium
        }.get(current_model, current_model)
```

---

## Implementation Checklist

- [ ] Create `ReviewReport` dataclass
- [ ] Implement `AIReviewValidator` quality gates
- [ ] Create `review_report.json` template
- [ ] Build human review UI/checklist
- [ ] Integrate with batch processing
- [ ] Create review dashboard
- [ ] Setup re-generation workflow
- [ ] Document review SLA (target: 3 min per image)

