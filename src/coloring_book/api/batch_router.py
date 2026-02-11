"""FastAPI router for batch generation endpoints with SSE progress streaming."""

import asyncio
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..services.batch_queue_optimized import BatchItem, BatchJob, BatchQueue, JobStatus
from ..services.progress_tracker_optimized import ProgressFormatter, ProgressTracker, ProgressUpdate
from ..services.zip_export import ZipExportService
from .batch_schemas import BatchSubmitRequest, BatchSubmitResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])

# Module-level singletons — initialized by app lifespan (see app.py)
batch_queue: BatchQueue | None = None
progress_tracker: ProgressTracker | None = None
zip_service: ZipExportService | None = None


def _require_services():
    """Guard: ensure services are initialized before handling requests."""
    if batch_queue is None or progress_tracker is None:
        raise HTTPException(status_code=503, detail="Batch services not initialized")


# ---------------------------------------------------------------------------
# POST /api/v1/batch/generate — Submit a new batch job
# ---------------------------------------------------------------------------
@router.post("/generate", response_model=BatchSubmitResponse, status_code=201)
async def submit_batch(body: BatchSubmitRequest):
    _require_services()

    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    items = [
        BatchItem(
            id=f"item_{uuid.uuid4().hex[:8]}",
            file=item.file,
            prompt=item.prompt,
        )
        for item in body.items
    ]

    job = BatchJob(
        id=batch_id,
        items=items,
        model=body.model,
        options={
            "quality": body.options.quality,
            "include_pdf": body.options.include_pdf,
        },
    )

    try:
        await batch_queue.add_job(job)
    except Exception as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    logger.info(f"Batch job {batch_id} submitted with {len(items)} items")
    return BatchSubmitResponse(
        batch_id=batch_id,
        status="pending",
        total_items=len(items),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/batch/{batch_id}/progress — SSE stream (EventSource)
# ---------------------------------------------------------------------------
@router.get("/{batch_id}/progress")
async def batch_progress_stream(batch_id: str):
    _require_services()

    # Verify job exists
    job = batch_queue.get_job_status(batch_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    queue = await progress_tracker.subscribe(batch_id)

    async def event_generator():
        try:
            while True:
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send keep-alive comment to prevent connection timeout
                    yield ": keepalive\n\n"
                    continue

                if update is None:
                    # End-of-stream signal
                    break

                yield ProgressFormatter.format_sse(update)

                if update.status in ("completed", "failed"):
                    break
        finally:
            await progress_tracker.unsubscribe(batch_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# GET /api/v1/batch/{batch_id}/status — Poll progress (JSON)
# ---------------------------------------------------------------------------
@router.get("/{batch_id}/status")
async def batch_status(batch_id: str):
    _require_services()

    progress = batch_queue.get_job_progress(batch_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    return progress


# ---------------------------------------------------------------------------
# GET /api/v1/batch/{batch_id}/download — Download ZIP
# ---------------------------------------------------------------------------
@router.get("/{batch_id}/download")
async def download_batch(batch_id: str):
    _require_services()

    job = batch_queue.get_job_status(batch_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Batch not ready (status: {job.status.value})")

    # Collect output files
    files_to_zip = []
    for item in job.items:
        if item.output_path:
            files_to_zip.append({
                "path": item.output_path,
                "arcname": item.file,
            })

    if not files_to_zip:
        raise HTTPException(status_code=404, detail="No output files available")

    try:
        zip_buffer = zip_service.stream_zip(files_to_zip)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"ZIP creation failed for batch {batch_id}: {exc}")
        raise HTTPException(status_code=500, detail="ZIP creation failed")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="batch_{batch_id}.zip"',
        },
    )


# ---------------------------------------------------------------------------
# GET /api/v1/batch — List batches
# ---------------------------------------------------------------------------
@router.get("")
async def list_batches(limit: int = 20, status: str | None = None):
    _require_services()

    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    jobs = batch_queue.list_jobs(status=status_filter, limit=limit)
    return {"batches": jobs, "count": len(jobs)}


# ---------------------------------------------------------------------------
# POST /api/v1/batch/{batch_id}/cancel — Cancel batch
# ---------------------------------------------------------------------------
@router.post("/{batch_id}/cancel")
async def cancel_batch(batch_id: str):
    _require_services()

    success = batch_queue.update_job_status(batch_id, JobStatus.CANCELLED)
    if not success:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Notify all SSE subscribers that the job is cancelled
    await progress_tracker.publish_progress(
        ProgressUpdate(
            job_id=batch_id,
            processed=0,
            total=0,
            status="failed",
            error="Batch cancelled by user",
        )
    )
    await progress_tracker.close_all_subscriptions(batch_id)

    logger.info(f"Batch {batch_id} cancelled")
    return {"message": f"Batch {batch_id} cancelled"}
