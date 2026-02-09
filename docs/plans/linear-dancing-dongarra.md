# Children's Activity Workbook Builder + Etsy Auto-Listing

## Context

Project001 (Coloring Book Generator) has strong infrastructure (CI/CD, Render deploy, 425 tests) but the core product is incomplete - image generation returns fake URLs. The user wants to pivot to a **specific, sellable product**: children's activity workbooks (like the "Vehicles Tracing Workbook for Boys Ages 3-5" reference PDF) with automatic Etsy listing.

**Reference Product Analysis** (31-page PDF, Letter size):
- Cover page with theme, age range, previews
- ~18 "Trace & Color" pages (colored reference + dashed outline + vehicle name)
- 2 "Which One Is Different?" pages (spot the odd one)
- 2 "Count and Circle" pages (count vehicles in grid)
- 2 "Match the Vehicles" pages (draw lines to match pairs)
- 1 "Word-to-Image Match" page (word → correct image)
- 2 "Find and Circle" pages (name → pick correct image from row)

**Decisions**: Hybrid image gen (AI + SVG fallback), Full Etsy auto-listing, All 6 activity types, Vehicles + Animals themes.

---

## Phase 1: Workbook Engine (Backend Core)

### 1.1 Activity Page Type System

**New file**: `src/coloring_book/workbook/page_types.py`

```python
class ActivityPage(ABC):
    """Base class for all activity page types"""
    page_type: str
    title: str
    items: list[WorkbookItem]  # vehicles/animals for this page

    @abstractmethod
    def render(self, pdf_page: PDFPage) -> None: ...

    @abstractmethod
    def get_required_assets(self) -> list[AssetRequest]: ...

class TraceAndColorPage(ActivityPage):       # "Trace and color" - colored ref + dashed outline
class WhichIsDifferentPage(ActivityPage):     # 4 rows, spot the odd one
class CountAndCirclePage(ActivityPage):       # Mixed grid, count each type
class MatchVehiclesPage(ActivityPage):        # Left-right matching
class WordToImagePage(ActivityPage):          # Word ovals → images
class FindAndCirclePage(ActivityPage):        # Name + row of 4, circle correct
class CoverPage(ActivityPage):               # Theme cover with previews
```

**New file**: `src/coloring_book/workbook/models.py`

```python
@dataclass
class WorkbookItem:
    name: str           # "Fire Truck", "Ambulance"
    category: str       # "vehicle", "animal"
    colored_image: bytes | None    # PNG - colored reference
    outline_image: bytes | None    # PNG - line art for coloring
    dashed_image: bytes | None     # PNG - dashed tracing version

@dataclass
class WorkbookConfig:
    theme: str          # "vehicles", "animals"
    title: str          # "Vehicles Tracing"
    subtitle: str       # "For Boys Ages 3-5"
    age_range: tuple[int, int]  # (3, 5)
    page_count: int     # 30
    items: list[str]    # ["fire_truck", "ambulance", "police_car", ...]
    activity_mix: dict[str, int]  # {"trace_and_color": 18, "which_different": 2, ...}
    page_size: str      # "letter" or "a4"

@dataclass
class Workbook:
    config: WorkbookConfig
    pages: list[ActivityPage]
    cover: CoverPage
    metadata: PackageMetadata  # existing schema
```

### 1.2 Image Generation for Workbook Items

**New file**: `src/coloring_book/workbook/image_gen.py`

Hybrid approach: AI-first, SVG fallback.

```python
class WorkbookImageGenerator:
    """Generates colored + outline + dashed versions of items"""

    async def generate_item(self, name: str, category: str) -> WorkbookItem:
        # 1. Try AI: Generate colored clipart via Imagen/DALL-E
        colored = await self._generate_ai_colored(name, category)
        if not colored:
            colored = self._generate_svg_colored(name, category)  # SVG fallback

        # 2. Convert colored → outline (edge detection + cleanup)
        outline = self._image_to_outline(colored)

        # 3. Convert outline → dashed (dash pattern on strokes)
        dashed = self._outline_to_dashed(outline)

        return WorkbookItem(name=name, category=category,
                           colored_image=colored, outline_image=outline,
                           dashed_image=dashed)

    def _image_to_outline(self, colored_png: bytes) -> bytes:
        """PIL: Convert colored image to black outline (Canny edge detection + threshold)"""
        ...

    def _outline_to_dashed(self, outline_png: bytes) -> bytes:
        """PIL: Convert solid outline to dashed tracing lines"""
        ...
```

**AI Prompt Template** for colored clipart:
```
"Simple flat-style cartoon {item_name} clipart for children's coloring book,
 white background, bright colors, cute style, no text, isolated object,
 clean edges, suitable for ages 3-5"
```

**Modify**: `src/coloring_book/ai/generator.py` - Add `generate_clipart(item, style)` method using existing Genesis API client.

### 1.3 Theme Registry

**New file**: `src/coloring_book/workbook/themes.py`

```python
THEMES = {
    "vehicles": {
        "display_name": "Vehicles",
        "items": [
            "traffic_light", "police_car", "ambulance", "school_bus",
            "crane", "dump_truck", "excavator", "cement_mixer",
            "fire_truck", "garbage_truck", "helicopter", "airplane",
            "tractor", "train", "tow_truck", "bulldozer", "taxi", "bicycle"
        ],
        "age_groups": ["preschool", "early_elementary"],
        "etsy_tags": ["vehicles coloring book", "tracing workbook", "toddler activity book", ...],
    },
    "animals": {
        "display_name": "Animals",
        "items": ["cat", "dog", "bird", "elephant", "lion", "giraffe", ...],
        ...
    }
}
```

### 1.4 PDF Compilation

**New file**: `src/coloring_book/workbook/compiler.py`

```python
class WorkbookCompiler:
    """Compiles WorkbookConfig → multi-page PDF"""

    def __init__(self, config: WorkbookConfig):
        self.config = config
        self.image_gen = WorkbookImageGenerator()
        self.pdf = PDFGenerator()  # existing

    async def compile(self) -> bytes:
        # 1. Generate all item assets (batch, parallel)
        items = await self._generate_all_items()

        # 2. Build page sequence
        pages = self._build_page_sequence(items)

        # 3. Render cover
        cover = CoverPage(config=self.config, preview_items=items[:3])

        # 4. Render each page to PDF
        self.pdf.set_metadata(title=self.config.title, author="Coloring Book Generator")
        cover.render(self.pdf.add_page())
        for page in pages:
            page.render(self.pdf.add_page())

        return self.pdf.generate()
```

### 1.5 Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| CREATE | `src/coloring_book/workbook/__init__.py` | Package init |
| CREATE | `src/coloring_book/workbook/models.py` | Data models |
| CREATE | `src/coloring_book/workbook/page_types.py` | 7 activity page renderers |
| CREATE | `src/coloring_book/workbook/image_gen.py` | Hybrid image generation |
| CREATE | `src/coloring_book/workbook/themes.py` | Theme registry |
| CREATE | `src/coloring_book/workbook/compiler.py` | PDF compilation orchestrator |
| MODIFY | `src/coloring_book/ai/generator.py` | Add clipart generation method |
| MODIFY | `src/coloring_book/pdf/generator.py` | Add dashed-line drawing support |
| CREATE | `tests/test_workbook_models.py` | Model tests |
| CREATE | `tests/test_page_types.py` | Page rendering tests |
| CREATE | `tests/test_image_gen.py` | Image pipeline tests |
| CREATE | `tests/test_compiler.py` | End-to-end compilation tests |

---

## Phase 2: Workbook API + Frontend

### 2.1 REST API Endpoints

**New file**: `src/coloring_book/api/workbook_routes.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/workbooks` | List all workbooks |
| POST | `/api/v1/workbooks` | Create workbook config |
| GET | `/api/v1/workbooks/{id}` | Get workbook details |
| PUT | `/api/v1/workbooks/{id}` | Update workbook config |
| DELETE | `/api/v1/workbooks/{id}` | Delete workbook |
| POST | `/api/v1/workbooks/{id}/generate` | Start PDF generation (async) |
| GET | `/api/v1/workbooks/{id}/status` | Generation progress |
| GET | `/api/v1/workbooks/{id}/download` | Download generated PDF |
| GET | `/api/v1/workbooks/{id}/preview` | Preview first 3 pages (fast) |
| GET | `/api/v1/themes` | List available themes |
| GET | `/api/v1/themes/{slug}` | Theme details + available items |

**New file**: `src/coloring_book/api/workbook_schemas.py`

```python
class WorkbookCreate(BaseModel):
    theme: str
    title: str
    subtitle: str | None
    age_min: int = 3
    age_max: int = 5
    page_count: int = 30
    items: list[str] | None  # None = auto-select from theme
    activity_mix: dict[str, int] | None  # None = default distribution
    page_size: str = "letter"

class WorkbookResponse(BaseModel):
    id: str
    config: WorkbookCreate
    status: str  # "draft", "generating", "ready", "failed"
    progress: float | None
    pdf_url: str | None
    created_at: datetime
```

### 2.2 Database Model

**Modify**: `src/coloring_book/api/app.py` - Add Workbook SQLAlchemy model

```python
class WorkbookModel(Base):
    __tablename__ = "workbooks"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    theme = Column(String, nullable=False)
    title = Column(String, nullable=False)
    config_json = Column(JSON)
    status = Column(String, default="draft")
    pdf_path = Column(String, nullable=True)
    etsy_listing_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

### 2.3 Frontend - Workbook Builder UI

**New file**: `frontend/src/components/WorkbookBuilder.vue`

Main workbook creation wizard with steps:
1. **Theme Selection** - Card grid (Vehicles, Animals, + coming soon placeholders)
2. **Configuration** - Title, age range, page count, item selection
3. **Activity Mix** - Slider/stepper for each activity type distribution
4. **Preview** - Live preview of first 3 pages
5. **Generate** - Progress bar → Download PDF

**New file**: `frontend/src/components/ThemeCard.vue` - Theme selection card
**New file**: `frontend/src/components/ActivityMixer.vue` - Activity distribution UI
**New file**: `frontend/src/components/WorkbookPreview.vue` - PDF page previewer

**Modify**: `frontend/src/App.vue` - Add "Workbook Builder" as primary tab (move existing tabs to secondary)

### 2.4 Files to Create/Modify

| Action | File |
|--------|------|
| CREATE | `src/coloring_book/api/workbook_routes.py` |
| CREATE | `src/coloring_book/api/workbook_schemas.py` |
| MODIFY | `src/coloring_book/api/app.py` (add WorkbookModel + mount routes) |
| CREATE | `frontend/src/components/WorkbookBuilder.vue` |
| CREATE | `frontend/src/components/ThemeCard.vue` |
| CREATE | `frontend/src/components/ActivityMixer.vue` |
| CREATE | `frontend/src/components/WorkbookPreview.vue` |
| MODIFY | `frontend/src/App.vue` (add Workbook Builder tab) |
| CREATE | `tests/test_workbook_api.py` |
| CREATE | `frontend/src/components/__tests__/WorkbookBuilder.spec.ts` |

---

## Phase 3: Etsy Integration

### 3.1 Etsy OAuth 2.0 Flow

**New file**: `src/coloring_book/etsy/client.py`

```python
class EtsyClient:
    """Etsy API v3 client with OAuth 2.0"""
    BASE_URL = "https://api.etsy.com/v3"

    def __init__(self, api_key: str, api_secret: str):
        ...

    def get_auth_url(self, redirect_uri: str, scopes: list[str]) -> str:
        """Generate OAuth authorization URL"""
        # Scopes needed: listings_w, listings_r, shops_r

    async def exchange_code(self, code: str) -> TokenResponse:
        """Exchange auth code for access + refresh tokens"""

    async def refresh_token(self) -> TokenResponse:
        """Refresh expired access token"""
```

### 3.2 Listing Management

**New file**: `src/coloring_book/etsy/listing.py`

```python
class EtsyListingService:
    """Create and manage Etsy listings for workbooks"""

    async def create_listing(self, workbook: Workbook) -> EtsyListing:
        # 1. Generate listing metadata from workbook
        metadata = self._build_listing_metadata(workbook)

        # 2. Create draft listing on Etsy
        listing = await self.client.create_draft_listing(
            title=metadata.title,        # "Vehicles Tracing Workbook for Boys Ages 3-5 | 30 Pages"
            description=metadata.description,  # Auto-generated SEO description
            price=metadata.price,         # Suggested: $4.99-$7.99
            taxonomy_id=DIGITAL_DOWNLOADS_TAXONOMY,
            tags=metadata.tags[:13],      # Etsy max 13 tags
            who_made="i_did",
            is_supply=False,
            when_made="made_to_order",
            is_digital=True,
        )

        # 3. Upload PDF as digital file
        await self.client.upload_listing_file(listing.id, workbook.pdf_bytes, "workbook.pdf")

        # 4. Upload cover as listing image
        await self.client.upload_listing_image(listing.id, workbook.cover_image)

        # 5. Upload preview pages as additional images (Etsy allows 10)
        for i, preview in enumerate(workbook.preview_images[:9]):
            await self.client.upload_listing_image(listing.id, preview)

        return listing

    def _build_listing_metadata(self, workbook: Workbook) -> ListingMetadata:
        """Auto-generate Etsy-optimized title, description, tags, price"""
        ...
```

### 3.3 SEO & Pricing Engine

**New file**: `src/coloring_book/etsy/seo.py`

```python
class EtsySEOEngine:
    """Generate Etsy-optimized metadata"""

    def generate_title(self, config: WorkbookConfig) -> str:
        # Pattern: "{Theme} {Activity} Workbook for {Gender} Ages {Range} | {Pages} Pages | {Keywords}"
        # Example: "Vehicles Tracing Workbook for Boys Ages 3-5 | 30 Pages | Coloring Book Printable"

    def generate_description(self, config: WorkbookConfig) -> str:
        # Structured description with sections:
        # - What's included (page count, activity types)
        # - Age appropriateness
        # - How to use / print instructions
        # - Keywords for search

    def generate_tags(self, config: WorkbookConfig) -> list[str]:
        # Max 13 tags, theme-specific + generic activity book tags
        # Example: ["vehicles coloring book", "tracing workbook toddler",
        #           "printable activity book", "preschool worksheet", ...]

    def suggest_price(self, config: WorkbookConfig) -> float:
        # Based on page count + activity variety
        # 20-30 pages: $3.99-$4.99
        # 30-50 pages: $4.99-$6.99
        # 50+ pages: $6.99-$9.99
```

### 3.4 Frontend - Etsy Integration UI

**New file**: `frontend/src/components/EtsyPublisher.vue`

- OAuth connect button (redirect flow)
- Shop selector (if multiple shops)
- Listing preview (title, description, tags, price - all editable)
- "Publish to Etsy" button with confirmation
- Listing status tracker (draft → active)

### 3.5 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/etsy/auth-url` | Get OAuth authorization URL |
| POST | `/api/v1/etsy/callback` | Handle OAuth callback |
| GET | `/api/v1/etsy/status` | Check connection status |
| POST | `/api/v1/etsy/disconnect` | Revoke tokens |
| POST | `/api/v1/workbooks/{id}/publish` | Create Etsy listing for workbook |
| GET | `/api/v1/workbooks/{id}/listing` | Get Etsy listing status |
| PUT | `/api/v1/workbooks/{id}/listing` | Update listing metadata |

### 3.6 Files to Create/Modify

| Action | File |
|--------|------|
| CREATE | `src/coloring_book/etsy/__init__.py` |
| CREATE | `src/coloring_book/etsy/client.py` |
| CREATE | `src/coloring_book/etsy/listing.py` |
| CREATE | `src/coloring_book/etsy/seo.py` |
| CREATE | `src/coloring_book/api/etsy_routes.py` |
| CREATE | `frontend/src/components/EtsyPublisher.vue` |
| MODIFY | `frontend/src/App.vue` (add Etsy section) |
| MODIFY | `requirements.txt` (add oauthlib if needed) |
| CREATE | `tests/test_etsy_client.py` |
| CREATE | `tests/test_etsy_seo.py` |
| CREATE | `tests/test_etsy_listing.py` |

---

## Implementation Order

```
Phase 1 (Workbook Engine) ─── 3 waves ───────────────────────
  Wave 1.1: models.py + themes.py + tests (foundation)
  Wave 1.2: image_gen.py + page_types.py + tests (rendering)
  Wave 1.3: compiler.py + PDF integration + tests (assembly)

Phase 2 (API + Frontend) ─── 2 waves ────────────────────────
  Wave 2.1: workbook_routes.py + schemas + DB model + tests
  Wave 2.2: WorkbookBuilder.vue + ThemeCard + ActivityMixer + Preview

Phase 3 (Etsy) ─── 2 waves ──────────────────────────────────
  Wave 3.1: etsy/client.py + seo.py + listing.py + tests
  Wave 3.2: etsy_routes.py + EtsyPublisher.vue + E2E
```

**Dependencies**: Phase 1 → Phase 2 → Phase 3 (sequential, each builds on previous)

---

## Verification Plan

### Phase 1 Verification
```bash
# Unit tests for all workbook engine components
pytest tests/test_workbook_models.py tests/test_page_types.py tests/test_image_gen.py tests/test_compiler.py -v

# Generate a test workbook PDF locally
python -c "
from coloring_book.workbook.compiler import WorkbookCompiler
from coloring_book.workbook.models import WorkbookConfig
config = WorkbookConfig(theme='vehicles', title='Test', subtitle='Ages 3-5',
                        age_range=(3,5), page_count=10, items=['fire_truck','police_car','ambulance'],
                        activity_mix={'trace_and_color': 6, 'which_different': 1, 'count_circle': 1, 'match': 1, 'find_circle': 1},
                        page_size='letter')
pdf = await WorkbookCompiler(config).compile()
open('test_workbook.pdf', 'wb').write(pdf)
"
# Open test_workbook.pdf and visually verify all 6 activity types render correctly
```

### Phase 2 Verification
```bash
# API tests
pytest tests/test_workbook_api.py -v

# Frontend tests
cd frontend && pnpm test

# E2E: Create workbook via API
curl -X POST http://localhost:5000/api/v1/workbooks \
  -H "Content-Type: application/json" \
  -d '{"theme":"vehicles","title":"Test Vehicles","page_count":10}'

# Check generation progress
curl http://localhost:5000/api/v1/workbooks/{id}/status

# Download PDF
curl -O http://localhost:5000/api/v1/workbooks/{id}/download
```

### Phase 3 Verification
```bash
# Etsy client tests (mocked)
pytest tests/test_etsy_client.py tests/test_etsy_seo.py tests/test_etsy_listing.py -v

# Manual: OAuth flow test with Etsy sandbox
# Manual: Create test listing in Etsy sandbox shop
# Manual: Verify PDF upload + cover image + preview images
```

---

## Key Dependencies to Add

```
# requirements.txt additions
Pillow>=10.0.0        # Image processing (edge detection, dashing)
numpy>=1.24.0         # Image array manipulation for outline extraction
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| AI image quality inconsistent | SVG fallback + QC validation before PDF |
| Etsy API rate limits | Queue-based publishing + retry with backoff |
| Edge detection fails on complex images | Tunable Canny thresholds + manual override |
| Large PDF generation time | Async generation + progress tracking (existing batch queue) |
| Etsy OAuth token expiry | Auto-refresh with stored refresh tokens |
