# 🚀 AI GENERATION V2 EPIC - Comprehensive Planning

**Epic Title:** AI Generation v2 - Multi-Model & Batch  
**Project:** Coloring Book Generator (project001)  
**Status:** PLANNED  
**Total Story Points:** 26  
**Total Tasks:** 21  
**Priority:** HIGH  

---

## 📋 STORY BREAKDOWN

### STORY 1: Multi-Model Comparison UI
**Story Points:** 5  
**Priority:** HIGH  
**Epic:** AI Generation v2  

**User Story:**  
As a coloring book creator, I want to compare outputs from Gemini, Imagen, and Imagen Ultra side-by-side so that I can choose the best quality image for my books.

**Acceptance Criteria:**
- Three-column UI showing Gemini | Imagen | Ultra simultaneously
- Same seed/prompt for fair comparison
- Quick toggle between models
- Performance metrics displayed

**Tasks:**
1. Design 3-column comparison layout
2. Implement simultaneous API calls (async)
3. Add caching layer for same-seed comparisons
4. Create model selection UI component

---

### STORY 2: Batch Generation + ZIP Export
**Story Points:** 5  
**Priority:** HIGH  
**Epic:** AI Generation v2  

**User Story:**  
As a seller, I want to generate 10-20 coloring book designs in one batch and download them as a ZIP file so that I can prepare multiple listings efficiently.

**Acceptance Criteria:**
- Batch size: 10-20 animals
- Single ZIP file download
- Progress bar during generation
- Memory-efficient streaming (no temp files)

**Tasks:**
1. Extend BatchRunner for multi-generate
2. Implement ZIP creation logic
3. Add progress tracking UI
4. Memory optimization (streaming)

---

### STORY 3: Custom Prompt Support
**Story Points:** 3  
**Priority:** MEDIUM  
**Epic:** AI Generation v2  

**User Story:**  
As an advanced user, I want to write custom prompts for image generation so that I can create unique coloring book styles beyond predefined animals.

**Acceptance Criteria:**
- Prompt template builder with variables
- Safety validation (no harmful content)
- Example prompts library
- Prompt history

**Tasks:**
1. Create prompt template system
2. Implement content safety filter
3. Build example library (50+ prompts)
4. Add prompt history & search

---

### STORY 4: A4 Print-Ready PDF Export
**Story Points:** 5  
**Priority:** HIGH  
**Epic:** AI Generation v2  

**User Story:**  
As a publisher, I want to export coloring books as print-ready PDFs with 300 DPI and proper A4 layout so that I can send them directly to printers.

**Acceptance Criteria:**
- 300 DPI minimum resolution
- A4 (210x297mm) page format
- Proper margins & bleed area
- Print preview before export

**Tasks:**
1. Upgrade ReportLab PDF generator
2. Implement DPI/resolution control
3. Add multi-page handling
4. Create print preview UI

---

### STORY 5: Etsy Listing Automation
**Story Points:** 8  
**Priority:** URGENT  
**Epic:** AI Generation v2  

**User Story:**  
As an Etsy seller, I want to automatically generate listing metadata, mockup images, and thumbnails for my coloring books so that I can publish them directly without manual work.

**Acceptance Criteria:**
- Auto-generated title + description
- Mockup image (book cover preview)
- Thumbnail generation
- SEO-optimized tags
- Direct Etsy API integration

**Tasks:**
1. Create Etsy API wrapper
2. Implement listing template system
3. Build auto-tagging (animal + difficulty)
4. Generate product mockups
5. Thumbnail creation logic

---

## 📊 ROADMAP VISUALIZATION

```
AI Generation v2 Epic (26 pts)
├── Story 1: Multi-Model UI (5 pts)
│   ├── Task: Layout Design
│   ├── Task: Async API
│   ├── Task: Caching
│   └── Task: UI Component
├── Story 2: Batch + ZIP (5 pts)
│   ├── Task: Batch Extension
│   ├── Task: ZIP Creation
│   ├── Task: Progress Bar
│   └── Task: Memory Optimization
├── Story 3: Custom Prompts (3 pts)
│   ├── Task: Template System
│   ├── Task: Safety Filter
│   ├── Task: Example Library
│   └── Task: History/Search
├── Story 4: Print-Ready PDF (5 pts)
│   ├── Task: ReportLab Upgrade
│   ├── Task: DPI Control
│   ├── Task: Multi-page
│   └── Task: Print Preview
└── Story 5: Etsy Automation (8 pts)
    ├── Task: Etsy API Wrapper
    ├── Task: Listing Template
    ├── Task: Auto-tagging
    ├── Task: Mockup Gen
    └── Task: Thumbnail Gen
```

---

## 🎯 DEPENDENCIES & PREREQUISITES

### Technical Requirements
- Imagen 4.0 API integration ✅ (exists)
- Gemini API integration ✅ (exists)
- ReportLab PDF library ✅ (exists)
- Etsy API credentials (new)

### Data Dependencies
- Animal registry (multi-model seeds)
- Prompt templates library
- Etsy API documentation

### External Integrations
- Etsy API v3
- Google Cloud Vision (optional - quality scoring)

---

## 📅 IMPLEMENTATION SEQUENCE

**Phase 1 (Sprint 1-2):**
- Story 1: Multi-Model Comparison
- Story 2: Batch Generation

**Phase 2 (Sprint 3):**
- Story 3: Custom Prompts
- Story 4: Print PDF

**Phase 3 (Sprint 4-5):**
- Story 5: Etsy Automation

---

## ✅ SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Multi-model comparison speed | < 2s for 3 models |
| Batch generation (20 items) | < 1 min |
| PDF generation (A4, 300 DPI) | < 5s per book |
| Etsy API reliability | 99.5% uptime |
| Custom prompt safety | 0 false rejections |

---

## 📝 NOTES

- All tasks follow TDD (Red-Green-Refactor)
- Every story requires acceptance test suite
- Code reviews mandatory before merge
- Documentation required for each story completion

**Created:** 2026-01-23  
**Next Review:** After Story 1 completion  

