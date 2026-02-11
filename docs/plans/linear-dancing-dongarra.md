# Story 2: Batch Generation + ZIP Export — Integration Plan

## Context

Optimized batch services exist but are **not wired** to the FastAPI app. A frontend UI exists in the wrong directory. The goal is to integrate everything so users can submit a batch of images, see real-time SSE progress, and download a ZIP.

**What exists (ready):**
- `services/batch_queue_optimized.py` — BatchQueue with TTL, O(1) lookups, retry, backpressure
- `services/progress_tracker_optimized.py` — ProgressTracker with SSE, parallel broadcast, metrics
- `services/zip_export.py` — ZIP creation/streaming
- `api/batch_routes.py` — Reference class-based API (NOT a FastAPI router)
- `src/components/BatchGenerationUI.vue` — Full frontend UI (wrong directory, not integrated)

**What's missing:**
- FastAPI router with SSE endpoint
- Service initialization in app lifespan
- Async batch worker (processes items, publishes progress)
- Frontend component in correct location + tab in App.vue

---

## Implementation

### Step 1: Create FastAPI batch router — `api/batch_router.py`

Convert the class-based `batch_routes.py` to a proper FastAPI router using optimized services.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/batch/generate` | Submit batch job |
| GET | `/api/v1/batch/{batch_id}/progress` | SSE stream (EventSource) |
| GET | `/api/v1/batch/{batch_id}/status` | Poll progress (JSON) |
| GET | `/api/v1/batch/{batch_id}/download` | Download ZIP |
| GET | `/api/v1/batch` | List batches |
| POST | `/api/v1/batch/{batch_id}/cancel` | Cancel batch |

**SSE endpoint pattern:**
```python
@router.get("/batch/{batch_id}/progress")
async def batch_progress_stream(batch_id: str):
    queue = await progress_tracker.subscribe(batch_id)
    async def event_generator():
        while True:
            update = await queue.get()
            if update is None:  # End of stream
                break
            yield ProgressFormatter.format_sse(update)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Dependencies:** Services injected via module-level singletons (same pattern as `_pdfs` dict in workbook_routes.py).

### Step 2: Implement async batch worker — `services/batch_worker.py`

Background async worker that:
1. Polls `BatchQueue.get_job()` for pending jobs
2. For each job item: generates coloring page using `WorkbookImageGenerator`
3. Publishes `ProgressUpdate` to `ProgressTracker` after each item
4. On completion: creates ZIP via `ZipExportService`, publishes `completed` event
5. On error: publishes `failed` event, retries if `RetryableError`

Worker lifecycle managed in app lifespan (start on startup, cancel on shutdown).

### Step 3: Mount router + init services in `api/app.py`

In the `lifespan` context manager:
```python
# Startup
batch_queue = BatchQueue()
await batch_queue.start()          # Start cleanup task
progress_tracker = ProgressTracker()
await progress_tracker.start_cleanup_task()
worker_task = asyncio.create_task(batch_worker(batch_queue, progress_tracker))

# Shutdown
worker_task.cancel()
await batch_queue.stop()
await progress_tracker.shutdown()
```

Mount: `app.include_router(batch_router)`

### Step 4: Move frontend component + add tab

1. Move `src/components/BatchGenerationUI.vue` → `frontend/src/components/BatchGenerationUI.vue`
2. Re-style to match existing design tokens (current CSS uses hardcoded colors)
3. Add "Batch" tab to `App.vue` tabs array + `v-show` section

### Step 5: Pydantic schemas — `api/batch_schemas.py`

```python
class BatchSubmitRequest(BaseModel):
    items: list[BatchItemInput]
    model: str = "claude"
    options: BatchOptions = BatchOptions()

class BatchItemInput(BaseModel):
    file: str
    prompt: str

class BatchOptions(BaseModel):
    quality: str = "standard"
    include_pdf: bool = False

class BatchSubmitResponse(BaseModel):
    batch_id: str
    status: str
    total_items: int
```

---

## Files

| Action | File | Change |
|--------|------|--------|
| CREATE | `src/coloring_book/api/batch_router.py` | FastAPI router with SSE, download, CRUD |
| CREATE | `src/coloring_book/api/batch_schemas.py` | Pydantic request/response models |
| CREATE | `src/coloring_book/services/batch_worker.py` | Async worker processing items |
| MODIFY | `src/coloring_book/api/app.py` | Mount batch router, init services in lifespan |
| MOVE | `src/components/BatchGenerationUI.vue` → `frontend/src/components/BatchGenerationUI.vue` | Re-style with design tokens |
| MODIFY | `frontend/src/App.vue` | Add "Batch" tab |
| DELETE | `src/coloring_book/api/batch_routes.py` | Replaced by batch_router.py |

---

## Verification

1. Start backend + frontend
2. Navigate to "Batch" tab
3. Upload 2-3 images, set prompts
4. Click "Start Batch" → verify SSE progress updates in ticker
5. On completion → download ZIP → verify images inside
6. Test cancel mid-batch
7. `curl /api/v1/batch` → list shows recent batches
